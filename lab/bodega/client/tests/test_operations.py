#!/usr/bin/env python
# Run via sdmain/lab/bodega/test/client

'''
functional test cases for CR(U)D operations around reservation tasks/operations
Created on 02/25/2016
@author: sandeep rikhi
'''

import sys
import os
import json
import yaml
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR,
                                           '..', '..', '..', '..'))
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts'))
sys.path.append(os.path.join(SCRIPT_DIR, '..'))
from bodega_client import BodegaClient, TokenAuth
from server_connection_settings import (
    BODEGA_CLIENT_AUTH_TOKEN, BODEGA_SERVER_HOST)


def test_operation_flow():
    auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
    bodega_client = BodegaClient(BODEGA_SERVER_HOST, auth)

    # Create a reservation request
    conf_path = 'basic_testbed.yml'
    with open(conf_path, 'r') as conf_file:
        testbed_specs = yaml.load(conf_file)

    # Create a dummy operation request
    spec_name = 'BASIC_TESTBED'
    operation_info = \
        bodega_client.create_acquire_operation(testbed_specs[spec_name])

    logging.debug("\nOperation-Request\n%s" % (json.dumps(operation_info,
                                                          indent=2,
                                                          sort_keys=True)))
    test_operation_id = operation_info['id']

    # Get specific operation details and confirm id
    operation_info = \
        bodega_client.get_operation_details_by_id(test_operation_id)
    logging.debug("\nOperation-Info\n%s" % (json.dumps(operation_info,
                                                       indent=2,
                                                       sort_keys=True)))
    assert test_operation_id == operation_info['id']

    # List all reservation requests
    all_operations = bodega_client.get_all_operations_list()
    logging.debug("Found %d total operations" % (len(all_operations)))
    for operation_info in all_operations:
        logging.debug("\nOperation#%s\n%s" % (operation_info['id'],
                                              json.dumps(operation_info,
                                                         indent=2,
                                                         sort_keys=True)))

    # List all operations in 'CREATED' state
    list_operations = bodega_client.get_operations_list_by_state('CREATED')
    logging.debug("Found %d operations in CREATED state"
                  % (len(list_operations)))
    for operation_info in all_operations:
        logging.debug("\nOperation#%s\n%s" % (operation_info['id'],
                                              json.dumps(operation_info,
                                                         indent=2,
                                                         sort_keys=True)))
    list_operations = \
        bodega_client.get_operations_list_by_method_and_state('ACQUIRE',
                                                              'CREATED')
    for operation_info in all_operations:
        logging.debug("\nOperation#%s\n%s" % (operation_info['id'],
                                              json.dumps(operation_info,
                                                         indent=2,
                                                         sort_keys=True)))
    # Delete the dummy operation request we added
    bodega_client.abort_operation(test_operation_id)
