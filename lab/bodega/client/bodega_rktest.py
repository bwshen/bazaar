"""Module for dealing with rktest legacy in Bodega client."""
import logging
import os
import yaml

# Import ftp_util, adding the import path as necessary. The latter is needed
# by Bodega clients that are still run out of the source tree instead of as
# standalone executables.
try:
    from ftp_util import FtpUtil, FtpUtilException
except ImportError:
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sdmain_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    sys.path.append(os.path.join(sdmain_root, 'src', 'py', 'utils'))
    from ftp_util import FtpUtil, FtpUtilException


log = logging.getLogger(__name__)


def fetch_rktest_yml_files(rktest_yml_filename, cdm_root_path):
    """Fetch files for the legacy rktest_yml item type.

    This is only necessary because rktest_ymls do not include the full
    details for consumption in the fulfilled items JSON. No other items
    behave this way.
    """
    ftp = FtpUtil('files-master.colo.rubrik-lab.com', 'ubuntu', 'qwerty')
    try:
        output_paths = _fetch_dynapod_files(
            ftp, rktest_yml_filename, cdm_root_path)
    except FtpUtilException:
        log.debug(
            'Tolerating failure in fetching dynapod files and assuming ' +
            '%s is actually a staticpod.' % repr(rktest_yml_filename))
        output_paths = _fetch_staticpod_files(
            ftp, rktest_yml_filename, cdm_root_path)

    return output_paths


def _fetch_dynapod_files(ftp, rktest_yml_filename, cdm_root_path):
    dynapod_name = rktest_yml_filename.replace('.yml', '')
    dynapod_source_dir = os.path.join('Dynapod', dynapod_name)
    return _fetch_pod_files(
        ftp, dynapod_source_dir, dynapod_source_dir,
        rktest_yml_filename, cdm_root_path)


def _fetch_staticpod_files(ftp, rktest_yml_filename, cdm_root_path):
    staticpod_source_dir = 'Staticpod'
    conf_source_dir = os.path.join(staticpod_source_dir, 'conf')
    inventory_source_dir = os.path.join(
        staticpod_source_dir, 'deployment', 'ansible')
    return _fetch_pod_files(
        ftp, conf_source_dir, inventory_source_dir,
        rktest_yml_filename, cdm_root_path)


def _fetch_pod_files(ftp, conf_source_dir, inventory_source_dir,
                     conf_filename, cdm_root_path):
    log.debug(
        ('Fetching rktest.yml file from %s ' % repr(conf_source_dir)) +
        ('and Ansible inventory file from %s ' %
         repr(inventory_source_dir)) +
        ('for pod %s to be used in %s.' %
         (repr(conf_filename), repr(cdm_root_path))))
    conf_source = os.path.join(conf_source_dir, conf_filename)
    conf_destination = os.path.join(cdm_root_path, 'conf', conf_filename)
    ftp.get_file(conf_destination, conf_source)

    inventory_name = _get_rktest_yml_inventory_name(conf_destination)
    inventory_destination = None
    if inventory_name is None:
        log.debug(
            ('No inventory name found in %s. ' % repr(conf_destination)) +
            ('Will not be fetching an inventory file for it.'))
    else:
        inventory_filename = '%s_inventory.j2' % inventory_name
        inventory_source = os.path.join(
            inventory_source_dir, inventory_filename)
        inventory_destination = os.path.join(
            cdm_root_path, 'deployment', 'ansible', inventory_filename)
        ftp.get_file(inventory_destination, inventory_source)

    log.debug(
        ('Fetched rktest.yml file as %s ' % repr(conf_destination)) +
        ('and Ansible inventory file as %s.' % repr(inventory_destination)))
    return (conf_destination, inventory_destination)


def _get_rktest_yml_inventory_name(rktest_yml_path):
    with open(rktest_yml_path, 'r') as rktest_yml_file:
        rktest_yml = yaml.safe_load(rktest_yml_file)
        deployment = rktest_yml.get('deployment', {})
    return deployment.get('inventory', None)
