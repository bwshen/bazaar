#!/usr/bin/env python
# Run via sdmain/lab/bodega/test/client

'''
test cases for CRUD operations around resources in bodega
Created on 02/21/2016
@author: sandeep rikhi
'''

import sys
import os
import random
import json
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, '..'))
from bodega_client import BodegaClient, TokenAuth
from server_connection_settings import (
    BODEGA_CLIENT_AUTH_TOKEN, BODEGA_SERVER_HOST)


def test_create_delete_resource_definition_workflow():
    auth = TokenAuth(BODEGA_CLIENT_AUTH_TOKEN)
    bodega_client = BodegaClient(BODEGA_SERVER_HOST, auth)

    resource_name_prefix = "__RESERVED_DUMMY_TEST_RESOURCE"

    test_resource_id = 0
    # Create a random resource name if it does not exist.
    max_attempts = 10
    while max_attempts > 0:
        max_attempts = max_attempts - 1
        idx = random.randint(1, 1000)
        resource_name = "%s-%d" % (resource_name_prefix, idx)
        resource_info = bodega_client.get_resources_by_name(resource_name)
        if len(resource_info) == 0:
            rsrc_specs = {"name": resource_name, "priority": 1}
            resource_info = bodega_client.add_resource(rsrc_specs)
            test_resource_id = resource_info.json()['id']
            break

    if test_resource_id == 0:
        raise Exception("Unable to find a unique resource name to test with")

    resource_info = bodega_client.get_resource_by_id(test_resource_id)

    logging.debug("\nResource#%s\n%s" % (test_resource_id,
                                         json.dumps(resource_info,
                                                    indent=2,
                                                    sort_keys=True)))
    assert resource_info['id'] == test_resource_id

    # Update the newly added resource's vendor property
    vendor_details = {'vendor': 'RUBRIK'}
    bodega_client.update_resource_details(test_resource_id, vendor_details)
    resource_info = bodega_client.get_resource_by_id(test_resource_id)
    assert resource_info['vendor'] == vendor_details['vendor']

    # List all resources
    all_resources = bodega_client.get_all_resources()
    logging.debug("Found %d total resources" % (len(all_resources)))
    for resource_info in all_resources[:-1]:
        logging.debug("\nResource#%s\n%s" % (resource_info['id'],
                                             json.dumps(resource_info,
                                                        indent=2,
                                                        sort_keys=True)))

    resource_idx = int(all_resources[-1]['id'])
    resource_info = bodega_client.get_resource_by_id(resource_idx)
    logging.debug("\nResource#%s\n%s" % (resource_idx,
                                         json.dumps(resource_info,
                                                    indent=2,
                                                    sort_keys=True)))

    # Delete newly added resource
    bodega_client.delete_resource(test_resource_id)
