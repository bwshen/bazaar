#!/usr/bin/env python

import argparse
import logging
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'dev'))
import logging_utils

log = logging.getLogger(os.path.basename(__name__))

sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'jenkins'))
# Only for rktest.util.Util, which should be moved to a more common location
# someday.
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'tests'))

from jenkins_helpers import RkLabJenkins
from rktest.util import run_process_and_log_output


def wget(url, output_file=None):
    command = ['wget', '--progress=dot:giga', '--tries=50',
               '--waitretry=60', url]
    if output_file is not None:
        command += ['--output-document', output_file]
    run_process_and_log_output(command)


def download_rubrik_tarball(args):
    jenkins = RkLabJenkins()

    main_tarball_url = jenkins.get_rubrik_tarball_url(
        args.job_name, args.build_number)
    log.info('Downloading main Rubrik tarball from %s.' %
             repr(main_tarball_url))

    wget(main_tarball_url, output_file=args.main_output_file)

    internal_tarball_url = jenkins.get_internal_rubrik_tarball_url(
        args.job_name, args.build_number)
    if internal_tarball_url is not None:
        log.info('Downloading internal Rubrik tarball from %s.' %
                 repr(internal_tarball_url))
        wget(internal_tarball_url, output_file=args.internal_output_file)
    else:
        log.info('No internal Rubrik tarball found. Assuming this is an ' +
                 'older build without a separate internal tarball.')


if __name__ == '__main__':
    logging_utils.init_logging()

    parser = argparse.ArgumentParser(
        description='Download a Rubrik build artifiact from Jenkins.')
    parser.add_argument('--job_name', type=str, required=True,
                        help='Jenkins job name')
    parser.add_argument('--build_number', type=int, required=False,
                        default=None, help='Build number of the Jenkins job')
    parser.add_argument('--main_output_file', type=str, required=False,
                        default=None,
                        help='Main output file, or use current working ' +
                             'directory.')
    parser.add_argument('--internal_output_file', type=str, required=False,
                        default=None,
                        help='Internal output file, or use current working ' +
                             'directory.')
    args = parser.parse_args(args=sys.argv[1:])

    if len(args.job_name) == 0:
        raise ValueError('job_name cannot be empty')

    download_rubrik_tarball(args)
