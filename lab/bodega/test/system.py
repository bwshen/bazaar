#
# For this test to work one needs 3 (not necessarily distinct) machines:
#   - A machine with the 'bodega' ansible role, to which the bodega server
#     will be deployed.
#   - A machine with the 'bodega_tester' ansible role, on which the celery
#     workers will be deployed.
#   - A machine to run this orchestration script.
#
# For a machine to be a target for our ansible roles ('bodega' or
# 'bodega_tester') it must have:
#   - An 'ubuntu' user with sdmain/deployment/ssh_keys/ubuntu.pem credentials.
#   - No-password permissions for the 'ubuntu' user to run commands as the
#     'bodega' user.
#
# Additional requirements:
#   - The o'auth token needs to work.  If the one hard-coded below stops
#     working you need to obtain a new one, as follows:
#       * Make sure that bodega is provisioned on your test machine.
#       * Open a browser in which you are not logged into Google.
#       * Open to the 'https://<dev-machine>/api' URL.  You should see the
#         bodega API top link page.
#       * On the right hand side click "log in using Google" and enter the
#         Jira Bugfiler user credentials.
#       * Back on the bodega API page go to the profiles list (at
#         https://<dev-machine>/api/profile)
#       * The auth token is listed as 'auth_token' under the
#         bugfiler@rubrik.com profile.
#

import argparse
import datetime
import json
import logging
import os
import random
import redis
import subprocess
import sys
import time
import unittest

from celery import Celery
from celery.result import ResultSet
from celery.task.control import inspect
from celery.utils.log import get_task_logger

log = get_task_logger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
BODEGA_ROOT_DIR = os.path.join(SCRIPT_DIR, '..')
CLIENT_DIR = os.path.join(SCRIPT_DIR, '..', 'client')

sys.path.append(BODEGA_ROOT_DIR)
from interface import ResourceType
sys.path.append(CLIENT_DIR)
from bodega_client import BodegaClient, ping, TokenAuth

#
# Settings constants.
#

# Test-related settings.
RUNTIME_SECONDS = 2 * 60  # test duration
QUIESCE_SECONDS = 60

# Deployment settings.
SDMAIN_ROOT = os.path.join(SCRIPT_DIR, '..', '..', '..')
DEPLOYMENT_DIR = os.path.join(SDMAIN_ROOT, 'deployment')
ANSIBLE_DIR = os.path.join(DEPLOYMENT_DIR, 'ansible')
LOCALHOST_INVENTORY = os.path.join(ANSIBLE_DIR, 'localhost_inventory')
ANSIBLE_PLAYBOOK = 'ansible-playbook'
INFRASTRUCTURE_SH = os.path.join(DEPLOYMENT_DIR, 'infrastructure.sh')
BODEGA_TESTER_PLAYBOOK = os.path.join(ANSIBLE_DIR, 'bodega_tester.yml')
LAB_SRC = os.path.join(SDMAIN_ROOT, 'lab')
LAB_DEST = '/opt/bodega_system_test/lab'

# Celery related settings.
CELERY_REDIS_HOST = 'localhost'
CELERY_REDIS_DATABASE = 0
CELERY_BROKER = 'redis://%s/%s' % (CELERY_REDIS_HOST, CELERY_REDIS_DATABASE)

# Bodega related settings.
BODEGA_CLIENT_AUTH_TOKEN = 'f1713149d2a04e2b4882d24dddefbbb43a155aad'
BODEGA_SERVER_HOST = 'bodega-dev.rubrik-lab.com'

#
# Celery app.
#

app = Celery('bodega_system_test', backend='redis', broker=CELERY_BROKER)
# Temporary fix for https://rubrik.atlassian.net/browse/CDM-6041
# Visibility timeout of 7 days
app.conf.BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 604800}

# Worker types.
WORKER_BRAHMA = 0  # The creator (of resources and relations)
WORKER_VISHNU = 1  # The preserver (acquires / releases)
WORKER_SHIVA = 2   # The destroyer (of resources and relations)

# Number of workers.
N_BRAHMA_WORKERS = 1
N_SHIVA_WORKERS = 1
N_VISHNU_WORKERS = 6
MAX_N_WORKERS = 8


def create_resource(payload):
    auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
    client = BodegaClient(BODEGA_SERVER_HOST, auth)
    operation = client.create_management_operation(
        'CREATE_RESOURCE',
        payload=payload)
    return operation['id']


def delete_resource(id):
    auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
    client = BodegaClient(BODEGA_SERVER_HOST, auth)
    operation = client.create_management_operation(
        'DELETE_RESOURCE',
        payload={'resource_id': id})
    return operation['id']


def acquire_resources(spec):
    auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
    client = BodegaClient(BODEGA_SERVER_HOST, auth)
    operation = client.create_acquire_operation_from_spec(spec)
    return operation['id']


def release(token):
    auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
    client = BodegaClient(BODEGA_SERVER_HOST, auth)
    operation = client.create_release_operation(token)
    return operation['id']


@app.task(name='run_worker')
def run_worker(worker_id, worker_type):
    class Worker(object):
        def __init__(self, id):
            self._id = id

        def __str__(self):
            return '%s/%d' % (self.__class__.__name__, self._id)

        def _debug_message(self, msg):
            '''Prepends this worker's name to the passed 'msg' parameter.'''

            return '[%s] %s' % (str(self), msg)

        def _log(self, level, msg):
            log.log(level, self._debug_message(msg))

        def _raise(self, msg):
            raise Exception(self._debug_message(msg))

        def _wait_for_operation_completions(self, op_ids, timeout=30):
            auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
            client = BodegaClient(BODEGA_SERVER_HOST, auth)
            for op_id in op_ids:
                # TODO(adi): have a single timeout for the list of op ids.
                client.wait_for_operation_completion(op_id, timeout)

        def _get_operation_details_by_id(self, op_id):
            auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
            client = BodegaClient(BODEGA_SERVER_HOST, auth)
            return client.get_operation_details_by_id(op_id)

        def _is_successful(self, op):
            state = op['state']
            if state == 'COMPLETED':
                return True
            elif state == 'ABORT_COMPLETED':
                return False
            else:
                self._raise('%s: Unexpected state %s' % (str(op), state))

        def run(self):
            self._log(
                logging.DEBUG,
                'Waiting for the bodega server to come up')
            ping()
            self.do_work()

        def do_work(self):
            raise Exception('Should be overridden by sub-classes')

    class Brahma(Worker):
        __N_RESOURCES_IN_BATCH = 5  # no. of resources created in an iteration
        __SLEEP_SEC = 4

        def __create_resource(self, iteration, index):
            name = 'resource-%d-%d-%d' % (self._id, iteration, index)
            payload = {
                'resource_type': random.choice(ResourceType.ALL_TYPES),
                'resource_attributes': {
                    'name': name,
                    'priority': iteration * index
                }
            }
            return create_resource(payload)

        def do_work(self):
            start_time = time.time()
            iteration = 0
            while time.time() <= start_time + RUNTIME_SECONDS:
                op_ids = []
                for i in range(self.__N_RESOURCES_IN_BATCH):
                    op_ids.append(self.__create_resource(iteration, i))
                self._wait_for_operation_completions(op_ids)
                time.sleep(self.__SLEEP_SEC)
                iteration = iteration + 1

    class Vishnu(Worker):
        def __get_all_resources_by_type(self, resource_type):
            auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
            client = BodegaClient(BODEGA_SERVER_HOST, auth)
            return client.get_all_resources(resource_type)

        # Number of seconds the resources will be held by this worker.
        __POSSESSION_DURATION = 2

        def __verify_acquired_resources(self, status):
            resources = self.__get_all_resources_by_type(ResourceType.VNODE)
            resource_ids = set([r['id'] for r in resources])
            n_resource_groups_aquired = len(status)
            if n_resource_groups_aquired != 1:
                self._raise(
                    'Unexpected number of acquired resource groups: %d'
                    % n_resource_groups_aquired)
            acquired_resource_group = status[0]
            n_resources_acquired = len(acquired_resource_group)
            if n_resources_acquired != 2:
                self._raise(
                    'Unexpected number of resources in group: %d'
                    % n_resources_acquired)
            for acquired_cascading_resource in acquired_resource_group:
                resource_id = acquired_cascading_resource['vnode']['id']
                if resource_id not in resource_ids:
                    self._raise(
                        'Unexpected resource acquired: %d' % resource_id)

        def __acquire(self, iteration):
            token = 'Vishnu-%d-%d' % (self._id, iteration)
            spec = {
                'resource_group_specs': [
                    # Resource group 1
                    {
                        'count': 2,
                        'category': 'vnode',
                        'spec': {
                            'vnode': [],
                        },
                    },
                ],
                'token': token,
            }
            op_id = acquire_resources(spec)
            # For the timeout we add 2 to the possession duration to account
            # for the delay in getting operation completion status.
            timeout = (N_VISHNU_WORKERS + 1) * (self.__POSSESSION_DURATION + 2)
            self._wait_for_operation_completions([op_id], timeout=timeout)
            op = self._get_operation_details_by_id(op_id)
            status = json.loads(op['status'])
            if self._is_successful(op):
                self.__verify_acquired_resources(status)
                # Take a nap to simulate work between ACQUIRE and RELEASE.
                time.sleep(self.__POSSESSION_DURATION)
                r_op_id = release(token)
                self._wait_for_operation_completions([r_op_id])
                # TODO(adi): need to retry here
            else:
                if 'No matches' in status:
                    # TODO(adi): check matches
                    self._log(logging.ERROR, 'No matches for token %s' % token)
                    time.sleep(self.__POSSESSION_DURATION)
                else:
                    self._log(
                        logging.ERROR,
                        'Unexpected state/status combo: %s/%s' %
                        (op['state'], status))

        def do_work(self):
            start_time = time.time()
            iteration = 0
            while time.time() <= start_time + RUNTIME_SECONDS:
                self.__acquire(iteration)
                iteration = iteration + 1

    class Shiva(Worker):
        __N_RESOURCES_IN_BATCH = 2  # no. of resources deleted in an iteration
        __SLEEP_SEC = 5

        def do_work(self):
            start_time = time.time()
            while time.time() <= start_time + RUNTIME_SECONDS:
                auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
                client = BodegaClient(BODEGA_SERVER_HOST, auth)
                resources = client.get_all_resources()
                resource_ids = [int(r['id']) for r in resources]
                random.shuffle(resource_ids)
                ids_to_be_deleted = resource_ids[:self.__N_RESOURCES_IN_BATCH]
                op_ids = []
                for id in ids_to_be_deleted:
                    op_ids.append(delete_resource(id))
                self._wait_for_operation_completions(op_ids)
                time.sleep(self.__SLEEP_SEC)

    if worker_type == WORKER_BRAHMA:
        worker = Brahma(worker_id)
    elif worker_type == WORKER_VISHNU:
        worker = Vishnu(worker_id)
    elif worker_type == WORKER_SHIVA:
        worker = Shiva(worker_id)
    else:
        raise Exception('Unrecognized worker type: %s' % repr(worker_type))

    worker.run()


class TestBodega(unittest.TestCase):
    __MANAGE_PY_PATH = '%s/manage.py' % SCRIPT_DIR

    def print_msg(self, msg):
        print '%s [Controller] %s' % (datetime.datetime.now(), msg)

    def setUp(self):
        n_workers = N_BRAHMA_WORKERS + N_SHIVA_WORKERS + N_VISHNU_WORKERS
        if n_workers > MAX_N_WORKERS:
            raise Exception('Too many workers')
        self.__next_worker_id = 0
        self.__setup_redis_broker()
        self.__deploy_celery_workers()
        self.__purge_celery_workers_queue()
        self.__deploy_server()

    def __setup_redis_broker(self):
        broker = redis.StrictRedis(
            host=CELERY_REDIS_HOST,
            db=CELERY_REDIS_DATABASE)
        broker.flushdb()  # clean up any leftovers from before

    def __deploy_celery_workers(self):
        self.print_msg('Deploying the celery workers')
        extra_vars = [
            'lab_dest=%s/' % LAB_DEST,
            'lab_src=%s/' % LAB_SRC,
            'celery_app=%s' % SCRIPT_NAME,
            'celery_broker=%s' % CELERY_BROKER,
            'bodega_client_auth_token=%s' % BODEGA_CLIENT_AUTH_TOKEN,
            'bodega_server_host=%s' % BODEGA_SERVER_HOST,
        ]
        argv = [
            ANSIBLE_PLAYBOOK,
            '--sudo',
            '-i', LOCALHOST_INVENTORY,
            '--extra-vars=%s' % ' '.join(extra_vars),
            BODEGA_TESTER_PLAYBOOK
        ]
        try:
            log.debug('Running Ansible playbook command: %s' % repr(argv))
            output = subprocess.check_output(argv)
            log.debug('Output from Ansible playbook command:\n%s' % output)
            return output
        except subprocess.CalledProcessError as e:
            log.debug(
                'Ansible playbook command failed with status %s. Output:\n%s' %
                (repr(e.returncode), e.output))
            raise

    def __purge_celery_workers_queue(self):
        self.print_msg('Purging the worker queue')
        app.control.purge()

    def __deploy_server(self):
        self.print_msg('Deploying the bodega server')
        cmd = [INFRASTRUCTURE_SH, 'provision-confirm', 'bodega-dev']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        if args.verbose:
            # Show the server deployment output.
            for c in iter(lambda: process.stdout.read(1), ''):
                if c:
                    sys.stdout.write(c)
        exit_code = process.wait()
        if exit_code != 0:
            raise Exception('Failed to deploy server')

    def __run_server(self):
        self.print_msg('Launching the bodega server')
        bodega_user_cmd = ('cd /webapps/bodega/project '
                           '&& ./manage.py runbodega --force')
        command = [
            'ssh',
            '-t',
            'ubuntu@%s' % BODEGA_SERVER_HOST,
            'sudo -u bodega -i /bin/bash -l -c "%s"' % bodega_user_cmd
        ]
        self.server = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    def __get_all_resources(self):
        auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
        client = BodegaClient(BODEGA_SERVER_HOST, auth)
        return client.get_all_resources()

    def __print_queue_info(self):
        q = inspect()
        self.print_msg('Queue information')
        self.print_msg('Registered: %s' % q.registered())
        self.print_msg('Active: %s' % q.active())
        self.print_msg('Scheduled: %s' % q.scheduled())
        self.print_msg('Reserved: %s' % q.reserved())
        self.print_msg('Stats: %s' % q.stats())

    def __run_worker(self, worker_type):
        worker_id = self.__next_worker_id
        self.__next_worker_id = self.__next_worker_id + 1
        return run_worker.delay(worker_id, worker_type)

    def __run_workers(self, n_workers, worker_type):
        result_set = ResultSet([])
        for i in range(n_workers):
            result_set.add(self.__run_worker(worker_type))
        return result_set

    def test_system(self):
        self.__run_server()
        self.print_msg('Dispatching the test workers')
        result_set = ResultSet([])
        result_set.update(
            self.__run_workers(N_BRAHMA_WORKERS, WORKER_BRAHMA))
        result_set.update(
            self.__run_workers(N_SHIVA_WORKERS, WORKER_SHIVA))
        result_set.update(
            self.__run_workers(N_VISHNU_WORKERS, WORKER_VISHNU))
        # self.__print_queue_info()
        timeout = RUNTIME_SECONDS + QUIESCE_SECONDS
        return result_set.join(timeout=timeout)

    def tearDown(self):
        self.print_msg('Killing the bodega server')
        self.server.kill()
        self.print_msg('Deleting all the resources')
        auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
        client = BodegaClient(BODEGA_SERVER_HOST, auth)
        for resource in self.__get_all_resources():
            client.delete_resource(resource['id'])
        self.print_msg('Done.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('unittest_args', nargs='*')
    args = parser.parse_args()
    # Set the sys.argv to the unittest_args (leaving sys.argv[0] alone)
    sys.argv[1:] = args.unittest_args
    unittest.main()
