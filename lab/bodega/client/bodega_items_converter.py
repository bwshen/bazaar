"""Converter for bodega fulfilled items to yaml config."""
import copy
import logging
import os
import uuid
import yaml
from bodega_rktest import fetch_rktest_yml_files

CLOUD_MODELS = ['aws-m4.large', 'aws-m4.xlarge']

log = logging.getLogger(os.path.basename(__name__))


def get_ubuntu_machine_specs(ubuntu_machine, cdm_root_path):
    """
    Convert ubuntu_machine type to yaml config.

    :param ubuntu_machine: bodega item for ubuntu machine
    :param cdm_root_path: Absolute path to sdmain directory
    :return: Dictionary containing ubuntu machine info which can be dumped
            out to yaml file
    """
    ubuntu_machine_specs = {}
    ubuntu_machine_specs['name'] = ubuntu_machine['name']
    ubuntu_machine_specs['hostname'] = ubuntu_machine['ipv4']

    key_file = os.path.join(cdm_root_path,
                            'deployment',
                            'ssh_keys',
                            'backup-agent.pem')
    ubuntu_machine_specs['ssh'] = {
        'key_file': key_file,
        'username': 'root'
    }

    # Ubuntu is equal to Debian for Rktests.
    ubuntu_machine_specs['os'] = 'deb'
    ubuntu_machine_specs['data_set'] = {'id': 'linux_basic'}

    if ubuntu_machine['model'] in CLOUD_MODELS:
        ubuntu_machine_specs['cloud'] = {'private_ip': ubuntu_machine['ipv4']}

    return ubuntu_machine_specs


def get_windows_machine_specs(mssql_db):
    """
    Convert mssql_db type to yaml config.

    :param mssql_db: bodega item for Mssql DB
    :return: Dictionary containing ubuntu machine info which can be dumped
            out to yaml file
    """
    windows_machine_specs = {}
    windows_machine_specs['name'] = mssql_db['name']
    windows_machine_specs['hostname'] = mssql_db['ipv4']
    windows_machine_specs['cifs'] = mssql_db['cifs']
    windows_machine_specs['os'] = 'windows'

    if mssql_db['model'] in CLOUD_MODELS:
        windows_machine_specs['cloud'] = {'private_ip': mssql_db['ipv4']}

    return windows_machine_specs


def get_mssql_db_specs(mssql_db):
    """
    Convert mssql_db type to yaml config.

    :param mssql_db: bodega item for Mssql DB
    :return: Dictionary containing ubuntu machine info which can be dumped
            out to yaml file
    """
    mssql_db_specs = {}
    mssql_db_specs['vm_name'] = mssql_db['name']
    mssql_db_specs['hostname'] = mssql_db['ipv4']
    mssql_db_specs['cifs'] = mssql_db['cifs']
    mssql_db_specs['odbc'] = mssql_db['odbc']
    mssql_db_specs['data_set'] = {'id': 'sql_server'}

    if mssql_db['model'] in CLOUD_MODELS:
        mssql_db_specs['cloud'] = {'private_ip': mssql_db['ipv4']}

    return mssql_db_specs


def get_cdm_cluster_and_node_specs(cdm_cluster):
    """
    Convert cdm cluster to yaml config and create inventory file.

    :param cdm_cluster: Dictionary containing cluster info
    :return: Dictionaries for node and cluster
    """
    cluster_specs = {}
    nodes_specs = []

    cluster_specs['dns_nameservers'] = cdm_cluster['dns_nameservers']
    cluster_specs['dns_search_domains'] = cdm_cluster['dns_search_domains']
    cluster_specs['ntp_servers'] = cdm_cluster['ntp_servers']
    cluster_specs['name'] = cdm_cluster['name']

    for node in cdm_cluster['nodes']:
        node_specs = {}
        node_specs['hostname'] = node['hostname']
        node_specs['ipv4'] = {
            'address': node['ipv4'],
            'gateway': node['gateway'],
            'netmask': node['netmask']
        }

        if node['model'] in CLOUD_MODELS:
            node_specs['cloud_private_ip'] = copy.deepcopy(node_specs['ipv4'])
        nodes_specs.append(node_specs)

    return cluster_specs, nodes_specs


def get_esx_host_specs(esx_host_item):
    """
    Convert esx info in fulfilled items to yml format.

    Example:
    Fulfilled items:
      Need to add example here

    rktest_yml format:
        esx_hosts:
        - name: esx-5-154.colo.rubrik.com
          username: root
          password: qwertyu
          ip_address: 1.2.3.4
          vcenter:
            datastore: esx-5-154_local_ssd
            hostname: testing-vcenter.colo.rubrik.com
            password: qwertyu
            port: 443
            username: podmaker@rubrik-lab.com

    :param esx_host_item: Esx host dict from bodega fulfilled items
    :return: dict containing information for esx host in rktest_yml format
    """
    esx_host_spec = {}
    # TODO (Rohit) Add local datastore name to EsxHost item in bodega
    # For now just assuming it's based on convention
    base_name = esx_host_item['hostname'].split('.')[0]
    datastore_name = "%s_local_ssd" % base_name

    esx_host_spec['name'] = esx_host_item['hostname']
    esx_host_spec['ip_address'] = esx_host_item['ipv4']
    esx_host_spec['username'] = esx_host_item['username']
    esx_host_spec['password'] = esx_host_item['password']

    vcenter_info = {}
    vcenter_info.setdefault('datastore', datastore_name)
    vcenter_info.setdefault('hostname', esx_host_item['vcenter'])
    vcenter_info.setdefault('username', "podmaker@rubrik-lab.com")
    vcenter_info.setdefault('password', "qwertyu")
    vcenter_info.setdefault('port', 443)

    esx_host_spec['vcenter'] = vcenter_info

    return esx_host_spec


def get_rktest_yml_spec(rktest_yml_item, cdm_root_path):
    """Download and return pod yaml and inventory files."""
    pod_filename = rktest_yml_item['name']
    yaml_filepath, inventory_filepath = \
        fetch_rktest_yml_files(pod_filename, cdm_root_path)

    return yaml_filepath, inventory_filepath


def add_default_entries_to_rktest_yml(rktest_yml):
    """Add the default hardcoded entries to the rktest yml."""
    rktest_yml['test_workers'] = {
        'inventory': '../deployment/ansible/localhost_inventory'
    }

    rktest_yml['deployment']['cluster_sh'] = '../deployment/cluster.sh'


def make_inventory_file(cluster_info, cdm_root_path):
    """
    Create inventory file based on cluster info.

    :param cluster_info: Dictionary containing cluster info
    :param cdm_root_path: Absolute path to sdmain directory
    :return: inventory ID and path to inventory file
    """
    inventory_file_data = []
    for node in cluster_info['nodes']:
        entry = ('%s ansible_ssh_host=%s'
                 % (node['hostname'], node['ipv4']['address']))
        inventory_file_data.append(entry)

    inventory_file_data.append('[nodes]')
    for node in cluster_info['nodes']:
        inventory_file_data.append(node['hostname'])

    inventory_file_data.append('[vagrant_nodes]')
    for node in cluster_info['nodes']:
        inventory_file_data.append(node['hostname'])

    inventory_file_prefix = ('%s_ipv4'
                             % (cluster_info['cluster']['name']))
    inventory_file_name = '%s_inventory.j2' % inventory_file_prefix
    inventory_file_path = os.path.join(cdm_root_path,
                                       'deployment',
                                       'ansible',
                                       inventory_file_name)
    with open(inventory_file_path, 'w') as file:
        file.write("\n".join(inventory_file_data))

    return inventory_file_prefix, inventory_file_path


def convert_fulfilled_items_to_resource_yml(fulfilled_items, cdm_root_path):
    """
    Convert and generate yaml files for all fulfilled items.

    :param fulfilled_items: List of bodega fulfilled items
    :param cdm_root_path: Absolute path to sdmain directory
    :return:
    """
    yaml_files = {}
    inventory_files = {}

    for nickname, item in fulfilled_items.iteritems():
        resource_info = {}
        static_file_name = ""
        if item['item_type'] == 'cdm_cluster':
            log.info('Found item type \'{}\'. Adding this to '
                     'to our config yaml.'.format(item['item_type']))
            cluster_specs, node_specs = \
                get_cdm_cluster_and_node_specs(item)

            resource_info['cluster'] = cluster_specs
            resource_info['nodes'] = \
                resource_info.get('nodes', []) + node_specs
            inventory_file_prefix, inventory_file_path = \
                make_inventory_file(resource_info, cdm_root_path)

            inventory_files[nickname] = inventory_file_path

            resource_info['deployment'] = {'inventory': inventory_file_prefix}
            add_default_entries_to_rktest_yml(resource_info)
            static_file_name = cluster_specs['name'] + ".yml"

        elif item['item_type'] == 'mssql_server':
            log.info('Found item type \'{}\'. Adding this to '
                     'to our config yaml.'.format(item['item_type']))
            mssql_db_specs = get_mssql_db_specs(item)
            resource_info.setdefault('protected_mssql_dbs', [])
            resource_info['protected_mssql_dbs'].append(mssql_db_specs)

            windows_machine_specs = get_windows_machine_specs(item)
            resource_info.setdefault('protected_hosts', [])
            resource_info['protected_hosts'].append(windows_machine_specs)

            windows_machine_name = windows_machine_specs['name']
            resource_info.setdefault('restore_hosts', [])
            resource_info['restore_hosts'].append(windows_machine_name)

            resource_info['restore_hosts'] = \
                resource_info.get('restore_hosts', []) + [windows_machine_name]

            static_file_name = windows_machine_name

        elif item['item_type'] == 'ubuntu_machine':
            log.info('Found item type \'{}\'. Adding this '
                     'to our config yaml.'.format(item['item_type']))
            ubuntu_machine_specs = get_ubuntu_machine_specs(item,
                                                            cdm_root_path)

            resource_info.setdefault('protected_hosts', [])
            resource_info['protected_hosts'].append(ubuntu_machine_specs)

            ubuntu_machine_name = ubuntu_machine_specs['name']
            resource_info.setdefault('restore_hosts', [])
            resource_info['restore_hosts'].append(ubuntu_machine_name)
            static_file_name = ubuntu_machine_name

        elif item['item_type'] == 'esx_host':
            log.info('Found item type \'{}\'. Adding this '
                     'to our config yaml.'.format(item['item_type']))
            resource_info.setdefault('esx_hosts', [])
            esx_spec = get_esx_host_specs(item)
            resource_info['esx_hosts'].append(esx_spec)

            static_file_name = \
                esx_spec['name'].replace('.rubrik.com', "") + ".yml"

        elif item['item_type'] == 'rktest_yml':
            # This doesn't get added to rktest_yml dict. That is only for the
            # ala carte items. Instead we dump it out and add it to the
            # file list
            log.info('Found item type \'rktest_yml\'. '
                     'Downloading yaml and inventory files')

            yaml_file, inventory_file = get_rktest_yml_spec(item,
                                                            cdm_root_path)

            yaml_files[nickname] = yaml_file
            inventory_files[nickname] = inventory_file

            continue

        elif item['item_type'] == 'ip_address':
            log.info('Found item type \'{}\'. Adding this '
                     'to our config yaml.'.format(item['item_type']))
            resource_info.setdefault('floating_ips', [])
            resource_info['floating_ips'].append(item['ip'])
            static_file_name = 'ip_' + item['sid']

        else:
            log.debug('Ignoring Item with type %s.' % item['item_type'])

        if resource_info:
            # Dump out the files and append to the list.
            # create a unique file name if static name is not provided
            filename = static_file_name or str(uuid.uuid4()) + ".yml"

            resource_yml_filepath = \
                os.path.join(cdm_root_path, 'conf', filename)

            with open(resource_yml_filepath, 'w') as res_yml_fd:
                yaml.safe_dump(resource_info, res_yml_fd,
                               default_flow_style=False)

            yaml_files[nickname] = resource_yml_filepath

    yaml_relative_paths = {}
    for nickname, yaml_file_path in yaml_files.iteritems():
        relative_file_path = os.path.relpath(yaml_file_path, cdm_root_path)
        yaml_relative_paths[nickname] = relative_file_path

    inventory_relative_paths = {}
    for nickname, inventory_file_path in inventory_files.iteritems():
        relative_file_path = os.path.relpath(inventory_file_path,
                                             cdm_root_path)
        inventory_relative_paths[nickname] = relative_file_path

    return yaml_relative_paths, inventory_relative_paths
