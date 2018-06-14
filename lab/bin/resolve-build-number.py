#!/usr/bin/env python
"""Resolve build number."""
import argparse
import logging
import os
import sys
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'dev'))
import logging_utils  # noqa

log = logging.getLogger(os.path.basename(__name__))

sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'jenkins'))
from jenkins_helpers import RkLabJenkins  # noqa

JENKINS_LOGIN_CREDENTIALS_MAP = {
    'timer-jobs': {
        'url': 'http://timer-jobs.corp.rubrik.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': False},
    'phab-jenkins': {
        'url': 'http://phab-jenkins-beta.rubrik-lab.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': False},
    'master': {
        'url': 'http://master-builds.corp.rubrik.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': True},
    '4-2': {
        'url': 'http://4-2-builds.corp.rubrik.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': True},
    '4-1': {
        'url': 'http://4-1-builds.corp.rubrik.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': True},
    '4-0': {
        'url': 'http://4-0-builds.corp.rubrik.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': True},
    '3-2': {
        'url': 'http://3-2-builds.corp.rubrik.com/',
        'username': 'jenkins',
        'token': '605a3a85c81883e3124250e826d3c982',
        'for_release_qualification': True}
}


def main(args):

    login_credentials = None
    if args.jenkins_instance:
        if args.jenkins_instance not in JENKINS_LOGIN_CREDENTIALS_MAP:
            raise "No login credentials defined for instance {}".format(
                args.jenkins_instance)
        login_credentials = JENKINS_LOGIN_CREDENTIALS_MAP[
            args.jenkins_instance]
    rklab_jenkins_obj = RkLabJenkins(login_credentials)

    session = requests.Session()
    retries = Retry(total=25,
                    backoff_factor=.5,
                    status_forcelist=[500, 502, 503, 504])
    session.mount(rklab_jenkins_obj.JENKINS_SERVER_URL,
                  HTTPAdapter(max_retries=retries))

    # If --smoke_passed_build defined override --build_number
    if args.smoke_passed_build:
        # Cannot use jenkins_helper function below as
        # this throws 500 Internal server error with 4.1 and master jenkins
        # rklab_jenkins_obj.get_upstream_build_id_for_successful_test(
        #     test_job_name="CDM_Smoke_Suite",
        #     upstream_job="Build_CDM")
        job_name = "CDM_Smoke_Suite"
        log.info("Getting last successful job id for {}".format(job_name))
        job_url = rklab_jenkins_obj.JENKINS_SERVER_URL + 'job/' + job_name
        last_successful_url = \
            job_url + \
            '/api/json?tree=lastSuccessfulBuild[id,description]'
        log.info("GET {}".format(last_successful_url))
        result = session.get(last_successful_url)

        if result.status_code == 200:
            job_id = result.json()['lastSuccessfulBuild']['id']
            # As CDM_Smoke_Suite is triggered by Build_CDM
            job_parameter_url = job_url + '/' + job_id + \
                '/api/json?tree=actions[causes[upstreamBuild]]'
            log.info("Getting upstream job id for {}/{}".format(
                job_url, job_id))
            log.info("GET {}".format(job_parameter_url))
            r = session.get(job_parameter_url)
            if r.status_code == 200:
                for action in r.json()['actions']:
                    if '_class' in action and \
                        action['_class'] == \
                            'hudson.model.CauseAction':
                        build_number_to_use = \
                            filter(lambda x: '_class' in x and x['_class'] ==
                                   'hudson.model.Cause$UpstreamCause',
                                   action['causes'])[0]['upstreamBuild']
                        log.info("Found upstream "
                                 "build: {}".format(build_number_to_use))

                        # 3-2 builds does not contain artifacts.json
                        if '3-2-builds' in \
                                rklab_jenkins_obj.JENKINS_SERVER_URL:
                            print build_number_to_use
                        else:
                            print "{}job/{}/{}/artifact/artifacts.json".format(
                                rklab_jenkins_obj.JENKINS_SERVER_URL,
                                args.job_name,
                                build_number_to_use)
                        return
                raise Exception("Could not find build "
                                "which passed {}".format(job_name))
            else:
                raise Exception("Could not get upstream "
                                "job id for {}/{}".format(job_url, job_id))

        else:
            raise Exception("Could not get last successful "
                            "job id for {}".format(job_name))

    if args.build_number and args.build_number > 0:
        build_number_to_use = args.build_number

        log.info('Non-zero build_number was provided so using '
                 ' build number %d from %s '
                 % (build_number_to_use, repr(args.job_name)))
    else:
        build_number_to_use = rklab_jenkins_obj.get_latest_successful_build_id(
            job_name=args.job_name,
            params={})
        log.info('A non-valid build_number was provided so using '
                 'build number %d from %s '
                 % (build_number_to_use, repr(args.job_name)))

    # Python cannot propagate environment variables to its parent process
    # therefore we need to to capture the output of this program and use it
    # as our environment variable.
    # Return artifacts.json link instead of build number for BUILD_CDM jobs
    if args.job_name == "BUILD_CDM":
        # 3-2 builds does not contain artifacts.json
        if '3-2-builds' in rklab_jenkins_obj.JENKINS_SERVER_URL:
            print build_number_to_use
        else:
            print "{}job/{}/{}/artifact/artifacts.json".format(
                rklab_jenkins_obj.JENKINS_SERVER_URL,
                args.job_name,
                build_number_to_use)
        return
    else:
        print build_number_to_use

if __name__ == '__main__':
    # Redirect console log messages to stderr or they'll show up in stdout
    logging_utils.init_logging(console_handler_stream=sys.stderr)

    parser = argparse.ArgumentParser(
        description='Resolves Build number and gets artifacts.json for '
                    'BUILD_CDM from any specific jenkins instance')
    parser.add_argument('--job_name', type=str, required=True,
                        help='Jenkins job name')
    parser.add_argument('--build_number', type=int, required=False,
                        default=None, help='Build number of the Jenkins job')
    parser.add_argument('--smoke_passed_build',
                        action='store_true',
                        help='if Build has passed CDM_Smoke_Suite')
    parser.add_argument(
        '--jenkins_instance',
        type=str,
        required=False,
        help="Hostname for jenkins instance, Eg: master/4-1/phab-jenkins etc.")

    args, unknown_args = parser.parse_known_args()
    if args.smoke_passed_build:
        assert args.job_name == "Build_CDM", "Smoke passed build is only " \
                                             "applicable to BUILD_CDM jobs"

    if len(args.job_name) == 0:
        raise ValueError('job_name cannot be empty')

    if args.smoke_passed_build:
        log.info("Ignore --build_number, getting CDM_Smoke_Suite passed build")
    main(args)
