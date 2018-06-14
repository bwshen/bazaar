#!/usr/bin/env python
"""
Create rktest_B-*.yml and B-*_ipv6_inventory.j2 files for a brik.

This is a stopgap which won't be needed once we move to a la carte prod briks.
Usage: python generate_brik_config_files.py <location_to_input_json_file>
"""
import json
import os
import re
import sys

NODES = ['lb', 'lt', 'rb', 'rt']
SCRIPT_NAME = os.path.basename(__file__)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))


def get_file_data(filename):
    """
    Read and return the contents of a file.

    :param filename: str
    :return:
    """
    with open(filename, 'r') as file:
        file_data = file.read()
    return file_data


def create_new_file(filename, new_data):
    """
    Create a new file and write the given data to the file.

    :param filename: str
    :param new_data: str
    :return:
    """
    with open(filename, 'w') as new_file:
        new_file.write(new_data)


def generate_rktest_file_data(input_values, sample_rktest_data):
    """
    Replace the sample rktest data values with the given node values.

    :param input_values: dict
    :param sample_rktest_data: str
    :return:
    """
    new_data = re.sub('B-NODE*', input_values['hostname'], sample_rktest_data)
    for node in NODES:
        new_data = new_data.replace('<%s_ipmi_address>' % node,
                                    input_values['%s_ipmi_address' % node])
        new_data = new_data.replace('<%s_dhcp_address>' % node,
                                    input_values['%s_dhcp_address' % node])
        new_data = new_data.replace('<%s_ipv4_address>' % node,
                                    input_values['%s_ipv4_address' % node])
        new_data = new_data.replace('<%s_mac_address_0>' % node,
                                    input_values['%s_mac_address_0' % node])
        new_data = new_data.replace('<%s_mac_address_1>' % node,
                                    input_values['%s_mac_address_1' % node])
    return new_data


def generate_ansible_file_data(input_values, sample_ansible_data):
    """
    Replace the sample ansible data values with the given node values.

    :param input_values: dict
    :param sample_ansible_data: str
    :return:
    """
    new_data = re.sub('B-NODE*', input_values['hostname'], sample_ansible_data)
    for node in NODES:
        new_data = new_data.replace('<%s_inet_address>' % node,
                                    input_values['%s_inet_address' % node])
    return new_data


def generate_rktest_yml(input_values):
    """
    Generate the rktest_B-*.yml file.

    :param input_values: dict
    :return:
    """
    target_rktest_filename = 'rktest_%s.yml' % input_values['hostname']
    target_file_path = os.path.join(SDMAIN_ROOT, 'conf',
                                    target_rktest_filename)
    sample_file_path = os.path.join(SDMAIN_ROOT, 'conf', 'sample_rktest.yml')
    sample_rktest_data = get_file_data(sample_file_path)
    new_rktest_data = generate_rktest_file_data(input_values,
                                                sample_rktest_data)
    create_new_file(target_file_path, new_rktest_data)


def generate_ansible_j2(input_values):
    """
    Generate the new B-*_ipv6_inventory.j2 ansible file.

    :param input_values: dict
    :return:
    """
    target_ansible_filename = '%s_ipv6_inventory.j2' % input_values['hostname']
    target_file_path = os.path.join(SDMAIN_ROOT, 'deployment',
                                    'ansible', target_ansible_filename)
    sample_file_path = os.path.join(SDMAIN_ROOT, 'conf',
                                    'sample_ansible_file.j2')
    sample_ansible_data = get_file_data(sample_file_path)
    new_ansible_data = generate_ansible_file_data(input_values,
                                                  sample_ansible_data)
    create_new_file(target_file_path, new_ansible_data)


def generate_files_from_input_json(json_filename):
    """
    Read the input json file containing brik information.

    :param json_filename: str
    :return:
    """
    with open(json_filename) as json_file:
        brik = json.load(json_file)
    input_values = dict()
    for idx in range(0, len(brik['hosts'])):
        input_values['hostname'] = 'B-' + brik['hosts'][idx]['id']

        nodes = brik['hosts'][idx]['values']
        for item in nodes:
            for key, value in item.iteritems():
                input_values[key] = value

        generate_rktest_yml(input_values)
        generate_ansible_j2(input_values)


def usage():
    print 'Usage: %s <json_file_path>' % SCRIPT_NAME
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()

    json_file = sys.argv[1]
    if os.path.exists(json_file):
        generate_files_from_input_json(json_file)
    else:
        print 'Incorrect input filepath'
