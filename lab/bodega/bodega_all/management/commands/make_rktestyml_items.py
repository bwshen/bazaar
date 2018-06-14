"""Create existing RktestYml objects in Bodega database."""

import logging
import os
import sys
import yaml
from bodega_legacy_items.models import RktestYml
from django.core.management.base import BaseCommand

SDMAIN_ROOT = os.path.abspath('/opt/sdmain')  # noqa
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'jenkins'))  # noqa
from jenkins_base_helpers import RkLabBaseJenkins

log = logging.getLogger(__name__)
JENKINS_CONFIG = '.myjenkins.conf.yml'


class Command(BaseCommand):

    def _get_rklab_base_jenkins(self):
        jenkins_profile = os.path.join(os.path.expanduser('~'), JENKINS_CONFIG)

        if not os.path.exists(jenkins_profile):
            raise Exception('Jenkins config file %s not found.' %
                            repr(jenkins_profile))

        with open(jenkins_profile, 'r') as jenkins_profile_data:
            profile_dict = yaml.safe_load(
                jenkins_profile_data)['jenkins_portal']

        rklab_jenkins = RkLabBaseJenkins(profile_dict.get('url'),
                                         profile_dict.get('username'),
                                         profile_dict.get('token'))
        return rklab_jenkins

    def _get_lockable_resources(self):
        """Return a dictionary summarizing lockable resource state."""
        rklab_jenkins = self._get_rklab_base_jenkins()
        jenkins_handle = rklab_jenkins.jenkins_handle

        lr_url = (rklab_jenkins.JENKINS_SERVER_URL +
                  'plugin/lockable-resources/api/json')
        log.debug("Getting lockable-resources info from: %s"
                  % (lr_url))
        response = jenkins_handle.requester.get_url(lr_url)
        response.raise_for_status()

        lr_info = response.json()
        resources = lr_info['resources']
        return resources

    def _process_labels(self, labels):

        for index, label in enumerate(labels):
            if label.endswith('_COLO'):
                label = label[:-5]
                labels[index] = label

            if label.endswith('_only'):
                label = label[:-5]
                labels[index] = label

        return labels

    def _set_location_of_rktest_yml(self, rktest_yml, resource):
        if resource['siteName'] == RktestYml.LOCATION_COLO:
            rktest_yml.location = RktestYml.LOCATION_COLO
        elif resource['siteName'] == RktestYml.LOCATION_HQ:
            rktest_yml.location = RktestYml.LOCATION_HQ
        else:
            error_msg = ('Unsupported location for Lockable Resource %s: '
                         '%s.' % (resource['name'], resource['siteName']))
            log.error(error_msg)
            raise Exception(error_msg)

    def _set_platform_of_rktest_yml(self, rktest_yml, resource,
                                    processed_labels):
        if 'DYNAROBO' in processed_labels:
            rktest_yml.platform = RktestYml.PLATFORM_DYNAPOD_ROBO
        elif 'robo' in processed_labels:
            rktest_yml.platform = RktestYml.PLATFORM_STATIC_ROBO
        elif 'PROD_BRIK' in processed_labels:
            rktest_yml.platform = RktestYml.PLATFORM_PROD_BRIK
        elif resource['name'].startswith('dynapod'):
            rktest_yml.platform = RktestYml.PLATFORM_DYNAPOD
        else:
            rktest_yml.platform = RktestYml.PLATFORM_STATIC

    def _convert_resource_into_item(self, resource):
        if resource['gearType'] == 'release_qualification_baton':
            return
        else:
            try:
                rktest_yml_name = resource['name']

                RktestYml.objects.get(filename=rktest_yml_name)
                log.debug('RktestYml with name %s already exists so skip '
                          'adding it again.' % rktest_yml_name)
                return
            except RktestYml.DoesNotExist:
                log.debug('Adding %s to the database.' % rktest_yml_name)

            rktest_yml = RktestYml.objects.create(
                filename=rktest_yml_name,
                description=resource['description'])

            labels = resource['labels']
            processed_labels = self._process_labels(labels)

            self._set_location_of_rktest_yml(rktest_yml, resource)
            self._set_platform_of_rktest_yml(rktest_yml, resource,
                                             processed_labels)

            if 'benchmarking' in processed_labels:
                rktest_yml.benchmarking = True

            if 'encrypted' in processed_labels:
                rktest_yml.encrypted = True

            if 'linux_agent' in processed_labels:
                rktest_yml.linux_agent = True

            if 'linux_agent_all_versions' in processed_labels:
                rktest_yml.linux_agent_all_versions = True

            if 'manufacturable' in processed_labels:
                rktest_yml.manufacturable = True

            if 'mssql' in processed_labels:
                rktest_yml.mssql = True

            if 'robofm' in processed_labels:
                rktest_yml.robofm = True

            if 'robossd' in processed_labels:
                rktest_yml.robossd = True

            if 'vcenter5.1' in processed_labels:
                rktest_yml.vcenter_5_1 = True

            if 'vcenter5.5' in processed_labels:
                rktest_yml.vcenter_5_5 = True

            if 'vcenter6.0' in processed_labels:
                rktest_yml.vcenter_6_0 = True

            if 'windows_app_test_only' in processed_labels:
                rktest_yml.windows_app_test_only = True

            rktest_yml.save()

    def handle(self, *args, **options):
        resources = self._get_lockable_resources()
        for resource in resources:
            self._convert_resource_into_item(resource)
