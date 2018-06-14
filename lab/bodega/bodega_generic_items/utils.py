"""Utility functions for Bodega generic items."""
import logging
import os
from bodega_aws.utils import search_for_ami_id_by_name
from bodega_core.exceptions import bodega_value_error
from bodega_utils.ssh import send_remote_command
from .models import MssqlServer

SDMAIN_ROOT = os.path.abspath('/opt/sdmain')  # noqa
SSH_KEYS_ROOT = os.path.join(SDMAIN_ROOT, 'deployment', 'ssh_keys')  # noqa
UBUNTU_PEM_FILE = os.path.join(SSH_KEYS_ROOT, 'ubuntu.pem')  # noqa

log = logging.getLogger(__name__)


def change_hostname_on_ubuntu_machine(ubuntu_machine):
    log.debug('Setting hostname of %s to %s'
              % (ubuntu_machine, ubuntu_machine.name))

    replace_etc_hosts_cmd = \
        ('sudo sed -i \'s/127.0.1.1.*/127.0.1.1\t\'"%s"\'/g\' /etc/hosts'
         % ubuntu_machine.name)
    send_remote_command(cmd=replace_etc_hosts_cmd,
                        ip_address=ubuntu_machine.ipv4,
                        key_filename=UBUNTU_PEM_FILE)
    curr_session_cmd = 'sudo hostname "%s"' % ubuntu_machine.name
    send_remote_command(cmd=curr_session_cmd,
                        ip_address=ubuntu_machine.ipv4,
                        key_filename=UBUNTU_PEM_FILE)
    persist_reboot_cmd = ('echo "%s" | sudo tee /etc/hostname'
                          % ubuntu_machine.name)
    send_remote_command(cmd=persist_reboot_cmd,
                        ip_address=ubuntu_machine.ipv4,
                        key_filename=UBUNTU_PEM_FILE)


def get_ami_id_for_mssql_server_version(version, aws_farm):
    """Use the Windows version to determine the AMI to use."""
    if version == MssqlServer.VERSION_WINDOWS_2012:
        return search_for_ami_id_by_name(aws_farm, 'BodegaWin2012r2SqlServer')
    else:
        bodega_value_error(log,
                           'Version %s is not a valid version for MssqlServer.'
                           % version)


def get_ami_id_for_ubuntu_version(version,
                                  kernel_version,
                                  aws_farm,
                                  root_disk_size=5):
    """Use the Ubuntu version to determine the AMI to use."""
    # TODO: We should create several Ubuntu images with different size disks
    # and try to find the best match. Right now we'll just use an image with
    # a 5GB OS disk. Disk size can be part of the requirements that users
    # pass in but we should predefine some sizes that users are able to use.

    ami_base_name = "BodegaUbuntuHost"
    ami_name = ami_base_name + str(version)
    ami_name += "_" + kernel_version
    ami_name += "_" + str(root_disk_size) + 'GB'

    return search_for_ami_id_by_name(aws_farm, ami_name)
