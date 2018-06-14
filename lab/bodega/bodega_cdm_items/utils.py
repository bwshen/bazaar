"""Utility functions for Bodega CdmNode items."""
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta

import requests

SDMAIN_ROOT = os.path.abspath('/opt/sdmain')  # noqa
PY_ROOT = os.path.join(SDMAIN_ROOT, 'src', 'py')  # noqa
sys.path.append(PY_ROOT)  # noqa
import cdm_tivan  # noqa
from bodega_aws.models import Ec2Instance
from bodega_aws.utils import get_ec2_instance_tag_value, tag_ec2_instance
from bodega_aws.utils import search_for_ami_id_by_name
from bodega_core.exceptions import bodega_error
from bodega_utils.ssh import check_ssh_availability, send_remote_command, sftp
from memoize import memoize
from pytz import utc

SSH_KEYS_ROOT = os.path.join(SDMAIN_ROOT, 'deployment', 'ssh_keys')  # noqa
UBUNTU_PEM_FILE = os.path.join(SSH_KEYS_ROOT, 'ubuntu.pem')  # noqa

INSTALL_DIR = '/home/rksupport'
INSTALL_LOG_NAME = 'ansible.log.txt'
UBUNTU_HOME_DIR = '/home/ubuntu'

BOOTSTRAP_WAIT_TIME = timedelta(minutes=45)
REBOOT_WAIT_TIME = timedelta(minutes=10)
SPRAY_SERVER_WAIT_TIME = timedelta(minutes=10)

log = logging.getLogger(__name__)


def __change_hostname_on_cdm_node(cdm_node):
    # If the hostname of the CdmNode starts with 'VR' (always the case in AWS),
    # then any subsequent code deploys will disable the Ubuntu account. Modify
    # the hostname for the current boot session and persist it across all
    # reboots.
    curr_session_cmd = 'sudo hostname "%s"' % cdm_node.name
    send_remote_command(cmd=curr_session_cmd,
                        ip_address=cdm_node.ipv4,
                        key_filename=UBUNTU_PEM_FILE)
    persist_reboot_cmd = 'echo "%s" | sudo tee /etc/hostname' % cdm_node.name
    send_remote_command(cmd=persist_reboot_cmd,
                        ip_address=cdm_node.ipv4,
                        key_filename=UBUNTU_PEM_FILE)


def __get_services_status(cdm_node):
    """Get status of all services on CdmNode."""
    services_status = {}
    services_stat_cmd = 'sudo svstat /etc/service/*'

    log.debug('Fetching the status of each service on %s with %s'
              % (cdm_node, services_stat_cmd))
    stdout, stderr = send_remote_command(cdm_node.ipv4,
                                         services_stat_cmd,
                                         key_filename=UBUNTU_PEM_FILE,
                                         log_stdout=True)
    for service in stdout.splitlines():
        match = re.match('^/etc/service/(.*):\s+(\w+).*?([0-9]+)\s+seconds',
                         service)
        if match:
            service_name = match.group(0)
            status = match.group(1)
            uptime = match.group(2)
            services_status[service_name] = {}
            services_status[service_name]['status'] = status
            services_status[service_name]['uptime'] = uptime
    return services_status


def __verify_services_up(cdm_node):
    """Verify that all services are up on the CdmNode."""
    services_status = __get_services_status(cdm_node)
    down_services = []

    for service, value in services_status.items():
        if value['status'] == 'down':
            log.debug('Service %s is currently down.' % service)
            down_services.append(service)
    return (len(down_services) == 0)


def __await_services_up(cdm_node):
    """Wait for services to come up on the CdmNode."""
    start_time = datetime.now(utc)
    while True:
        all_services_up = __verify_services_up(cdm_node)
        if all_services_up:
            log.debug('All services are currently up on %s' % cdm_node)
            return
        if datetime.now(utc) - start_time > REBOOT_WAIT_TIME:
            bodega_error(log,
                         'Services not up on %s after %s.'
                         % (cdm_node, REBOOT_WAIT_TIME))
        else:
            log.debug('Services not up on %s. Trying again in 10 seconds.'
                      % cdm_node)
            time.sleep(10)


def __verify_spray_server_is_ready(cdm_node):
    """Verify that spray server is ready on the CdmNode.

    Even if the node is reporting that services are up, they may not
    be ready for operations yet. We will continually poll the
    /node_management/is_bootstrapped endpoint similar to what
    manufacturing does until we get a response from the spray-server.
    """
    is_bootstrapped_endpoint = \
        ('https://%s/api/internal/node_management/is_bootstrapped'
         % cdm_node.ipv4)
    start_time = datetime.now(utc)
    while True:
        if datetime.now(utc) - start_time > SPRAY_SERVER_WAIT_TIME:
            bodega_error(log, 'Spray server was not ready after %s'
                              % SPRAY_SERVER_WAIT_TIME)
        try:
            response = requests.get(is_bootstrapped_endpoint,
                                    verify=False)
            response.raise_for_status()
            log.debug('Spray server is up and running.')
            return
        except:
            log.debug('Spray server is not ready. Waiting for 15 '
                      'seconds and trying again.')
            time.sleep(15)


def __install_binaries_on_cdm_node(cdm_node, artifacts_url):
    """Install the binaries from the tarball described in artifacts_url.

    Installing the binaries involves a series of steps -

    1. Download the given tarball to the /tmp/ directory with a unique name.
    2. SCP the tarball onto the /home/ubuntu/ directory of the CdmNode.
    3. Move the tarball into the /home/rksupport/ directory of the CdmNode.

    The previous step is necessary because the /home/ubuntu/ directory is
    wiped clean during the install. Also this workflow mirrors the workflow
    support would take.

    4. Clean up the tarball.
    5. Untar the tarball in the /home/rksupport directory of the CdmNode.
    6. Install the binaries using `cluster.sh localhost install`.
    7. Reboot CdmNode and wait.
    8. Clean up the extracted binaries.
    """
    log.debug('Parsing artifacts information from %s' % artifacts_url)
    artifacts = cdm_tivan.Artifacts(artifacts_url)

    tarball_name = None
    if artifacts.tarball_content_aws_s3_object:
        aws_s3_object = artifacts.tarball_content_aws_s3_object
        tarball_name = os.path.basename(aws_s3_object.key)

        log.debug(
            'Found tarball %s as an AWS S3 object at %s' %
            (tarball_name, repr(aws_s3_object)))

        # TODO: This is a somewhat involved installation process for awscli,
        # and it relies on a connection to external sites like s3.amazonaws.com
        # and PyPI. Unfortunately it's not easy to avoid those dependencies
        # without building our own PEX or something, and at that point we might
        # as well make it a full-blown Tivan consumer per
        # https://rubrik.atlassian.net/browse/INFRA-1765 so it can be
        # configured in (hopefully) the same way we configure all Tivan
        # consumers instead of requiring specific AWS handling.

        awscli_url = 'https://s3.amazonaws.com/aws-cli/awscli-bundle.zip'
        awscli_zip = '/tmp/aws-cli-bundle.zip'
        awscli_path = '/tmp/awscli'
        download_awscli_cmd = ' && '.join([
            "cd /tmp",
            "wget --progress=dot:giga '%s' -O '%s'" % (awscli_url, awscli_zip),
            "unzip '%s'" % awscli_zip,
            "./awscli-bundle/install -i '%s'" % awscli_path
        ])
        send_remote_command(cmd=download_awscli_cmd,
                            ip_address=cdm_node.ipv4,
                            key_filename=UBUNTU_PEM_FILE)

        local_aws_config_path = os.path.join(
            SDMAIN_ROOT, 'conf', 'jenkins.artifacts.reader-aws.config')
        remote_aws_config_path = '/tmp/aws.config'
        sftp(ip_address=cdm_node.ipv4,
             key_filename=UBUNTU_PEM_FILE,
             local_path=local_aws_config_path,
             remote_path=remote_aws_config_path)

        awscli_config = "AWS_CONFIG_FILE='%s'" % remote_aws_config_path
        aws_s3_cmd = ('sudo %s %s/bin/aws s3 cp s3://%s/%s %s/%s' %
                      (awscli_config, awscli_path,
                       aws_s3_object.bucket_name, aws_s3_object.key,
                       INSTALL_DIR, tarball_name))
        send_remote_command(cmd=aws_s3_cmd,
                            ip_address=cdm_node.ipv4,
                            key_filename=UBUNTU_PEM_FILE)
    else:
        tarball_url = artifacts.tarball_content_url
        tarball_name = os.path.basename(tarball_url)

        log.debug(
            'Found tarball %s with a generic URL of %s' %
            (tarball_name, tarball_url))

        wget_tarball_cmd = 'wget -q %s' % tarball_url
        send_remote_command(cmd=wget_tarball_cmd,
                            ip_address=cdm_node.ipv4,
                            key_filename=UBUNTU_PEM_FILE)

        mv_cmd = 'sudo mv %s %s' % (tarball_name, INSTALL_DIR)
        send_remote_command(cmd=mv_cmd,
                            ip_address=cdm_node.ipv4,
                            key_filename=UBUNTU_PEM_FILE)

    untar_command = ('sudo tar -xzf %s/%s -C %s'
                     % (INSTALL_DIR, tarball_name, INSTALL_DIR))
    send_remote_command(cmd=untar_command,
                        ip_address=cdm_node.ipv4,
                        key_filename=UBUNTU_PEM_FILE)

    delete_tarball_cmd = 'sudo rm %s/%s' % (INSTALL_DIR, tarball_name)
    send_remote_command(cmd=delete_tarball_cmd,
                        ip_address=cdm_node.ipv4,
                        key_filename=UBUNTU_PEM_FILE)

    # The current interface for Bodega to install the binaries onto a CdmNode
    # will be to perform the `cluster.sh localhost install` and then `reboot`
    # This will also be the supported interface moving forwards which is
    # guaranteed by the Forge team
    folder_name = re.sub(r'\.tar\.gz', '', tarball_name)
    install_binaries_cmd = \
        ('SKIP_ROLLING_REBOOT_ON_INSTALL=1 INSTALL_CHECK=0 '
         '%s/%s/deployment/cluster.sh localhost install'
         % (INSTALL_DIR, folder_name))

    send_remote_command(cmd=install_binaries_cmd,
                        ip_address=cdm_node.ipv4,
                        key_filename=UBUNTU_PEM_FILE,
                        log_stdout=True)

    # Reboot the CdmNode to get kernel upgrade changes
    # Wait for 10 minutes for the node to come back online
    reboot_cmd = 'sleep 2 && sudo /sbin/shutdown -r now'
    stdout, stderr = send_remote_command(cmd=reboot_cmd,
                                         ip_address=cdm_node.ipv4,
                                         key_filename=UBUNTU_PEM_FILE,
                                         log_stdout=True)
    check_ssh_availability(cdm_node.ipv4,
                           key_filename=UBUNTU_PEM_FILE)
    __await_services_up(cdm_node)
    __verify_spray_server_is_ready(cdm_node)

    delete_binaries_cmd = 'sudo rm -rf %s/%s' % (INSTALL_DIR, folder_name)
    send_remote_command(cmd=delete_binaries_cmd,
                        ip_address=cdm_node.ipv4,
                        key_filename=UBUNTU_PEM_FILE)


@memoize(timeout=timedelta(minutes=15).total_seconds())
def __get_management_gateway_from_cli(cdm_node):
    """Send 'ip route' command to the CdmNode and match for the gateway."""
    gateway_cmd = 'ip route | grep default'
    stdout, stderr = send_remote_command(cmd=gateway_cmd,
                                         ip_address=cdm_node.ipv4,
                                         key_filename=UBUNTU_PEM_FILE,
                                         log_stdout=True)
    match = re.search('default via (.+?) dev eth0', stdout)
    gateway = match.group(1)
    log.debug('Using gateway %s for %s' % (gateway, cdm_node))

    return gateway


@memoize(timeout=timedelta(minutes=15).total_seconds())
def __get_management_subnet_mask_from_cli(cdm_node):
    """Send 'ipconfig eth0' command to the CdmNode and get the netmask."""
    gateway_cmd = 'ifconfig eth0 | grep Mask'
    stdout, stderr = send_remote_command(cmd=gateway_cmd,
                                         ip_address=cdm_node.ipv4,
                                         key_filename=UBUNTU_PEM_FILE,
                                         log_stdout=True)
    match = re.search('Mask:(.+?)\n', stdout)
    netmask = match.group(1)
    log.debug('Using netmask %s for %s' % (netmask, cdm_node))

    return netmask


def __get_node_configs(cdm_cluster):
    node_configs = {}
    for node in cdm_cluster.nodes:
        node_config = {}
        node_config['managementIpConfig'] = {
            'address': node.ipv4,
            'netmask': get_management_subnet_mask(node),
            'gateway': get_management_gateway(node)
        }
        node_configs[node.name] = node_config

    return node_configs


def __get_cluster_bootstrap_specs(cdm_cluster):
    cluster_bootstrap_specs = {
        'name': cdm_cluster.name,
        'ntpServers': get_ntp_servers(cdm_cluster),
        'dnsNameservers': get_dns_nameservers(cdm_cluster),
        'dnsSearchDomains': get_dns_search_domains(cdm_cluster),
        'nodeConfigs': __get_node_configs(cdm_cluster),
        'adminUserInfo': {
            'id': 'admin',
            'password': 'RubrikAdminPassword',
            'emailAddress': 'bodega@rubrik.com'
        },
        'enableSoftwareEncryptionAtRest': False
    }
    return cluster_bootstrap_specs


def get_ntp_servers(cdm_cluster):
    return ['pool.ntp.org']


def get_dns_search_domains(cdm_cluster):
    return ['']


def get_dns_nameservers(cdm_cluster):
    # TODO(INFRA-2856): Specify the DNS Nameserver based on which
    # location the nodes are located. This is currently hardcoded to the
    # AWS DNS Nameserver.
    return ['172.31.17.120']


def get_management_gateway(cdm_node):
    if isinstance(cdm_node._ingredient, Ec2Instance):
        return get_ec2_instance_tag_value(cdm_node._ingredient, 'Gateway')
    else:
        return __get_management_gateway_from_cli(cdm_node)


def get_management_subnet_mask(cdm_node):
    if isinstance(cdm_node._ingredient, Ec2Instance):
        return get_ec2_instance_tag_value(cdm_node._ingredient, 'Netmask')
    else:
        return __get_management_subnet_mask_from_cli(cdm_node)


def tag_cluster_nodes(cdm_cluster):
    """Tag the ec2 instances with the cluster name for diagnosibility."""
    nodes = cdm_cluster.nodes
    for node in nodes:
        tag_ec2_instance(node._ingredient,
                         key='Held By',
                         value=cdm_cluster.name)


def tag_cdm_node_with_network_info(cdm_node):
    gateway = __get_management_gateway_from_cli(cdm_node)
    netmask = __get_management_subnet_mask_from_cli(cdm_node)
    tag_ec2_instance(cdm_node._ingredient,
                     key='Gateway',
                     value=gateway)
    tag_ec2_instance(cdm_node._ingredient,
                     key='Netmask',
                     value=netmask)


def get_ami_id_for_code_version(aws_farm, version):
    """Use the code version to determine the best AMI to use.

    Each tarball contains a hash. We want to determine the closest AMI version
    to use for the code version.
    """
    # TODO(INFRA-732): Determine this at runtime
    # This is the rubrik-4-1-0-DA1-1958-devmode version. Keep it hardcoded for
    # now.
    ami_name = 'BodegaCdmNodeImage-4.1'
    return search_for_ami_id_by_name(aws_farm, ami_name)


def setup_cdm_node_with_build(cdm_node, artifacts_url):
    __change_hostname_on_cdm_node(cdm_node)

    __install_binaries_on_cdm_node(cdm_node, artifacts_url)


def bootstrap_cdm_cluster(cdm_cluster):
    """Run cluster bootstrap via the REST API to join our nodes together."""
    cluster_bootstrap_specs = __get_cluster_bootstrap_specs(cdm_cluster)
    log.info('Bootstrapping %s with cluster_bootstrap_specs %s'
             % (cdm_cluster, json.dumps(cluster_bootstrap_specs, indent=4)))
    driver_node = cdm_cluster.nodes[0]
    log.debug('Driving cluster bootstrap with %s (%s).'
              % (driver_node, driver_node.ipv4))

    bootstrap_endpoint = ('https://%s/api/internal/cluster/me/bootstrap'
                          % driver_node.ipv4)

    log.debug('Sending POST request to %s.' % bootstrap_endpoint)
    response = requests.post(bootstrap_endpoint,
                             verify=False,
                             json=cluster_bootstrap_specs)
    response.raise_for_status()
    request_id = response.json()['id']
    start_time = datetime.now(utc)
    while True:
        params = {'request_id': request_id}
        response = requests.get(bootstrap_endpoint,
                                verify=False,
                                params=params)
        response_json = response.json()

        if not response.ok:
            response.raise_for_status()
        elif response_json['status'] == 'SUCCESS':
            log.info('Successfully completed cluster bootstrap on %s.'
                     % cdm_cluster)
            break
        elif datetime.now(utc) - start_time > BOOTSTRAP_WAIT_TIME:
            bodega_error(log,
                         'Bootstrap for %s ran over time period of %s'
                         % (cdm_cluster, BOOTSTRAP_WAIT_TIME))
        elif response_json['status'] == 'IN_PROGRESS':
            log.debug('Cluster bootstrap status is IN_PROGRESS so wait for '
                      '30 seconds before checking again for %s.'
                      % cdm_cluster)
            time.sleep(30)
        else:
            bodega_error(log,
                         'Hit unexpected status (%s) for bootstrap of %s. '
                         'Response dictionary: %s'
                         % (response_json['status'], cdm_cluster,
                            response_json))
