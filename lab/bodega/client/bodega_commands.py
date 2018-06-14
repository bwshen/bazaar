"""Wrapper methods to interact with Bodega API through Bodega Client.

These are called by Bodega CLI. This class borrows some code from
`bodega-reserve-pod` and `bodega-unreserve-pod`.
"""
import json
import logging
import os
import stat
import time

from collections import OrderedDict
from datetime import datetime, timedelta
from getpass import getpass
from subprocess import PIPE, Popen

import ansible.constants
import ansible.runner
import dateutil.parser
import pytz
import yaml

from bodega_client import BodegaClient
from bodega_items_converter import convert_fulfilled_items_to_resource_yml

log = logging.getLogger(os.path.basename(__name__))


class BodegaCommands(object):

    def __init__(self, bodega_url=None, auth_token=None):
        """Initialize the class object using url and auth token."""
        self.ORDERS_PATH = '/orders/'
        self.ORDER_UPDATES_PATH = '/order_updates/'
        self.PROFILE_PATH = '/profile/'
        self.USERS_PATH = '/users/'

        self.bodega_client = BodegaClient(bodega_url, auth_token)

    def get_current_user_profile(self):
        current_user_profile = self.bodega_client.get(self.PROFILE_PATH)
        return current_user_profile

    def _get_order_details(self, order_sid):
        order_details = \
            self.bodega_client.get('%s%s' % (self.ORDERS_PATH, order_sid))
        return order_details

    def _get_order_queue_length(self, order_creation_time, tab_based_priority):
        queue_length = \
            self.bodega_client.get(
                self.ORDERS_PATH,
                params={'status': 'OPEN',
                        'time_created__lt': order_creation_time,
                        'tab_based_priority__lte': tab_based_priority}
            )['count']
        return queue_length

    def consume_order(self, order_sid):
        prev_queue_length = None
        prev_mins_since_creation = None

        while True:
            order_details = self._get_order_details(order_sid)
            current_user_profile = self.get_current_user_profile()

            order_owner_sid = order_details['owner']['sid']
            current_user_sid = current_user_profile['sid']
            if order_owner_sid != current_user_sid:
                error_msg = ("""Requesting user\'s SID(%s) does not match
                                order owner\'s SID(%s)."""
                             % (current_user_sid, order_owner_sid))
                log.error(error_msg)
                raise Exception(error_msg)

            order_status = order_details['status']
            if order_status == 'FULFILLED':
                fulfilled_items = order_details['fulfilled_items']

                # TODO (Rohit):
                # This seems like a good candidate to convert to environment
                # variable. Basically the entry point to any execution should
                # set `CDM_ROOT`. And every place else just reads it instead
                # of having to map it on their own. This would require
                # changes to jenkins and pretty much every executable. However,
                # it would also help in following a standardized practice.
                script_dir = os.path.dirname(os.path.abspath(__file__))
                cdm_root_path = \
                    os.path.abspath(os.path.join(script_dir, '..', '..', '..'))

                try:
                    yaml_files, inventory_files = \
                        convert_fulfilled_items_to_resource_yml(
                            fulfilled_items, cdm_root_path
                        )

                except Exception:
                    log.warning("""Could not retrieve resource files
                                for \n%s.""" % fulfilled_items, exc_info=True)
                else:
                    message = "Fetched files:\n"
                    for nickname, filename in yaml_files.iteritems():
                        message += "\n\tNickname : %s\n\tfilename: %s" % \
                                   (nickname, filename)
                        message += "\n"

                    log.info(message)
                    print (message)

                return fulfilled_items
            elif order_status == 'OPEN':
                order_creation_time = \
                    dateutil.parser.parse(order_details['time_created'])
                current_time = datetime.utcnow().replace(tzinfo=pytz.utc)
                mins_since_creation = int(
                    (current_time - order_creation_time).total_seconds() / 60)

                tab_based_priority = order_details['tab_based_priority']
                queue_length = \
                    self._get_order_queue_length(order_creation_time,
                                                 tab_based_priority)

                if queue_length != prev_queue_length or \
                        mins_since_creation != prev_mins_since_creation:

                    print """It has been %sm since creation of %s and there are
                            at most %s orders ahead in queue"""\
                          % (mins_since_creation, order_sid, queue_length)

                    prev_queue_length = queue_length
                    prev_mins_since_creation = mins_since_creation

                time.sleep(10)
            else:
                error_msg = ("""Can not consume an order with status %s,
                                which is neither 'OPEN' nor 'FULFILLED'"""
                             % order_status)
                log.error(error_msg)
                raise Exception(error_msg)

    def place_order(self,
                    order_items,
                    cli_input,
                    no_wait=False,
                    is_maintenance_order=False,
                    time_limit=None,
                    comment=None):
        """Create a new Bodega order.

        Input format for order_items:
            order_items = {
                "nickname_0": {
                    "type": "rktest_yml",
                    "requirements": {
                        "platform": "DYNAPOD"
                    }
                },
            }
        """
        order_items_json = json.dumps(order_items, indent=4, sort_keys=True)
        full_comment = 'Placing order using command line: %s' % cli_input
        if comment:
            full_comment = '%s\n%s' % (full_comment, comment)

        log.info(full_comment)
        order = \
            self.bodega_client.post(
                self.ORDERS_PATH,
                data={'comment': full_comment,
                      'items': order_items_json,
                      'maintenance': is_maintenance_order,
                      'time_limit': time_limit}
            )

        order_sid = order['sid']
        fulfilled_items = None
        if not no_wait:
            fulfilled_items = self.consume_order(order_sid)

        return order_sid, fulfilled_items

    def close_order(self, order_sid, cli_input, comment=None):
        full_comment = 'Closing order %s using command line: %s'\
                       % (order_sid, cli_input)
        if comment:
            full_comment = '%s\n%s' % (full_comment, comment)

        log.info(full_comment)
        return self.bodega_client.close_order(order_sid, full_comment)

    def describe_order(self, order_sid, required_keys=None):
        result = self._get_order_details(order_sid)
        if required_keys:
            ordered_result = OrderedDict()
            for k in required_keys:
                if k in result:
                    ordered_result[k] = result[k]
            result = ordered_result
        return result

    def extend_order(self, order_sid, cli_input,
                     extension_time=None,
                     comment=None):
        if not extension_time:
            extension_time = timedelta(hours=2)

        full_comment = 'Extending order using command line: %s' % cli_input
        if comment:
            full_comment = '%s\n%s' % (full_comment, comment)

        log.info(full_comment)
        return self.bodega_client.extend_order(order_sid,
                                               extension_time,
                                               full_comment)

    def transfer_order(self, order_sid, cli_input, new_owner_sid=None,
                       new_owner_email=None, comment=None):
        current_user_profile = self.get_current_user_profile()

        full_comment = 'Transferring order %s by %s using command line: %s'\
                       % (order_sid, str(current_user_profile['username']),
                          cli_input)
        if comment:
            full_comment = '%s\n%s' % (full_comment, comment)

        log.info(full_comment)

        data = {'order_sid': order_sid, 'comment': full_comment}
        if new_owner_email:
            data['new_owner_email'] = new_owner_email
        if new_owner_sid:
            data['new_owner_sid'] = new_owner_sid

        return self.bodega_client.post(self.ORDER_UPDATES_PATH, data=data)

    def raw_request(self, method, relative_uri, params=None, data=None):
        if data:
            data = json.loads(data)
        if params:
            params = json.loads(params)

        return \
            self.bodega_client.request(
                method, relative_uri,
                params=params,
                data=data)

    def list(self, item_relative_uri, params=None, required_keys=None,
             max_count=1000):
        items = []
        if not params:
            params = {}
        page_count = 0

        while len(items) < max_count:
            page_count += 1
            params['page'] = page_count

            request_result = self.bodega_client.get(item_relative_uri,
                                                    params=params)
            for item in request_result['results']:
                if len(items) >= max_count:
                    break
                if required_keys:
                    ordered_item = OrderedDict()
                    for k in required_keys:
                        if k in item:
                            ordered_item[k] = item[k]
                    item = ordered_item
                items.append(item)

            if not request_result['next']:
                break
        return items

    def list_orders(self, user_email=None, status=None, required_keys=None,
                    max_count=1000):
        if user_email:
            user_sid = self.list(self.USERS_PATH,
                                 params={'email': user_email})[0]['sid']
        else:
            user_sid = None

        params = {}
        if user_sid:
            params['owner_sid'] = user_sid
        if status:
            if status == 'LIVE':
                params['status_live'] = True
            else:
                params['status'] = status

        return self.list(self.ORDERS_PATH, params=params, max_count=max_count,
                         required_keys=required_keys)

    def _check_ssh_agent_setup(self):
        msg = None
        ssh_sock_file = os.environ.get("SSH_AUTH_SOCK", None)
        if not ssh_sock_file:
            msg = "Check if ssh-agent is running and set $SSH_AUTH_SOCK"
        elif not os.path.exists(ssh_sock_file):
            msg = "$SSH_AUTH_SOCK [%s] points to a non existent sock file" % \
                  ssh_sock_file
        elif not stat.S_ISSOCK(os.stat(ssh_sock_file).st_mode):
            msg = "$SSH_AUTH_SOCK [%s] points to an invalid file" % \
                  ssh_sock_file
        else:
            ssh_key_info = Popen(["ssh-add", "-l"],
                                 stdout=PIPE).communicate()[0]
            if ssh_key_info == "The agent has no identities.\n":
                msg = "Run ssh-add to add ssh keys to the agent"
        if msg:
            setup_instruction = ("Instructions for ssh-agent forwarding:\n"
                                 "Run the following commands:\n"
                                 "eval `ssh-agent -s`\n"
                                 "ssh-add")
            raise EnvironmentError("SSH-Agent Error: %s\n%s" %
                                   (msg, setup_instruction))

    def configure_dev_machine(self, username, host, sync_file,
                              git_repo_file=None, pem_file=None,
                              password=None):
        """Configure the remote machine by copying files in sync_file."""
        sync_files = {}
        git_repos = []
        sync_file = os.path.expanduser(sync_file)
        with open(sync_file, 'r') as file_handler:
            for line_no, line in enumerate(file_handler, start=1):
                if line.strip() == "":
                    continue
                data = line.strip().split(':')
                if len(data) == 1:
                    src, dst = [data[0]] * 2
                elif len(data) == 2:
                    src, dst = data
                else:
                    raise Exception(('Ill-formatted line %d in %s,' +
                                     'skipping line') %
                                    (line_no, sync_file))

                src = os.path.expanduser(src)
                if not os.path.isfile(src):
                    log.warn('Source file %s does not exist, skipping it!' %
                             src)
                    continue
                if src in sync_files:
                    sync_files[src].append(dst)
                else:
                    sync_files[src] = [dst]
        if git_repo_file:
            git_repo_file = os.path.expanduser(git_repo_file)
            with open(git_repo_file, 'r') as file_handler:
                try:
                    git_repos = yaml.safe_load(file_handler)
                except Exception:
                    raise Exception("GIT_REPO file must follow yaml syntax")
                self._check_ssh_agent_setup()

        if not pem_file and not password:
            password = getpass('Enter the ssh password: ')

        ansible.constants.HOST_KEY_CHECKING = False
        ansible.constants.ANSIBLE_SSH_ARGS = "-o ForwardAgent=yes " + \
                                             "-o ControlMaster=auto " + \
                                             "-o ControlPersist=60s"

        ansible_common_args = {"remote_user": username,
                               "host_list": [host],
                               "remote_pass": password,
                               "private_key_file": pem_file
                               }

        for src, dest_files in sync_files.iteritems():
            for dest in dest_files:
                ansible_args = ansible_common_args.copy()
                ansible_args["module_name"] = "copy"
                ansible_args["module_args"] = "src=%s dest=%s" % (src, dest)
                try:
                    result = ansible.runner.Runner(**ansible_args).run()
                    try:
                        if "failed" in result["contacted"][host]:
                            log.error(("Transferring %s to %s failed with " +
                                       "following error: %s") %
                                      (src, dest,
                                       result["contacted"][host]["msg"]))
                        else:
                            log.info("Transferring %s to %s successful." %
                                     (src, dest))
                    except KeyError:
                        log.error(("Transferring %s to %s failed with " +
                                   "following error: %s") %
                                  (src, dest, result))
                except Exception as e:
                    log.exception("Error occurred while running ansible")
                    raise e

        for repo in git_repos:
            ansible_args = ansible_common_args.copy()
            ansible_args["module_name"] = "git"
            repo["accept_hostkey"] = True
            ansible_args["module_args"] = repo
            try:
                result = ansible.runner.Runner(**ansible_args).run()
                try:
                    if "failed" in result["contacted"][host]:
                        log.error(("Git clone of %s at %s failed with " +
                                   "following error: %s") %
                                  (repo["repo"], repo["dest"],
                                   result["contacted"][host]["msg"]))
                    else:
                        log.info("Git clone of %s at %s successful" %
                                 (repo["repo"], repo["dest"]))
                except KeyError:
                    log.error(("Git clone of %s at %s failed with " +
                               "following error: %s") %
                              (repo["repo"], repo["dest"], result))
            except Exception as e:
                log.exception("Error occurred while running ansible")
                raise e
