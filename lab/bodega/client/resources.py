#!/usr/bin/env python

'''
Created on 02/21/2016
@author: sandeep rikhi
'''

import argparse
import sys
import os
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..'))
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts'))

from bodega_client import BodegaClient
from dev import logging_utils

log = logging.getLogger(os.path.basename(__file__))
restful_client = BodegaClient()


def display_all_resources_names():
    all_resources = restful_client.get_all_resources()
    for resource in all_resources:
        print resource['name']


def main_bodega_resources_manager(args):
    logging_utils.init_logging()

    if args.listall:
        display_all_resources_names()

if __name__ == '__main__':
    desc = """
            Bodega operations related to subnet definitions
        """

    parser = argparse.ArgumentParser(prog=__file__, description=desc)

    parser.add_argument('-ll', '--listall', action="store_true",
                        help='list all resources names')

    args, unknown_args = parser.parse_known_args()
    main_bodega_resources_manager(args)
