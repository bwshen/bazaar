"""Item-specific cleanup managers."""

import logging
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

SDMAIN_ROOT = os.path.abspath('/opt/sdmain')  # noqa
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'py', 'utils'))  # noqa
from ftp_util import FtpUtil  # noqa
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'jenkins'))  # noqa
from jenkins_base_helpers import RkLabBaseJenkins  # noqa

from bodega_core import ItemManager
from bodega_core.exceptions import (bodega_type_error,
                                    bodega_validation_error,
                                    bodega_value_error)
from django.conf import settings
from pytz import utc
from .filters import RktestYmlFilter
from .models import Item, JenkinsTask, RktestYml

log = logging.getLogger(__name__)

RECOVERY_TIME_LIMIT = timedelta(hours=4)

DYNAPOD_FTP_SERVER = 'files-master.colo.rubrik-lab.com'
DYNAPOD_FTP_USER = 'ubuntu'
DYNAPOD_FTP_PASSWORD = 'qwerty'

BUILD_SEARCH_LIMIT = 250

AHV_RECOVERY_JOB = 'recover-ahv-pod'
CLOUD_RECOVERY_JOB = 'recover-cloud-pod'
DYNAMIC_RECOVERY_JOB = 'recover-dynamic-pod'
PROD_BRIK_RECOVERY_JOB = 'auto-recover-prod-brik-manufacture'
STATIC_RECOVERY_JOB = 'auto-recover-testbed'
HYPERV_RECOVERY_JOB = 'recover-hyperv-pod'

PLATFORM_TO_RECOVERY_JOB_NAME = {
    RktestYml.PLATFORM_AWS: CLOUD_RECOVERY_JOB,
    RktestYml.PLATFORM_AZURE: CLOUD_RECOVERY_JOB,
    RktestYml.PLATFORM_CISCO: PROD_BRIK_RECOVERY_JOB,
    RktestYml.PLATFORM_DELL: PROD_BRIK_RECOVERY_JOB,
    RktestYml.PLATFORM_DYNAPOD: DYNAMIC_RECOVERY_JOB,
    RktestYml.PLATFORM_DYNAPOD_ROBO: DYNAMIC_RECOVERY_JOB,
    RktestYml.PLATFORM_DYNAPOD_ROBO_AHV: AHV_RECOVERY_JOB,
    RktestYml.PLATFORM_DYNAPOD_ROBO_HYPERV: HYPERV_RECOVERY_JOB,
    RktestYml.PLATFORM_HPE: PROD_BRIK_RECOVERY_JOB,
    RktestYml.PLATFORM_LENOVO: PROD_BRIK_RECOVERY_JOB,
    RktestYml.PLATFORM_PROD_BRIK: PROD_BRIK_RECOVERY_JOB,
    RktestYml.PLATFORM_STATIC: STATIC_RECOVERY_JOB,
    RktestYml.PLATFORM_STATIC_ROBO: STATIC_RECOVERY_JOB,
}

"""
See INFRA-1074 for some introductory numbers.

We need 1.1 Microcloud hosts per dynapod, so we can come up with a final
(vanilla) dynapod price.

OPEX = 1.1 * $0.043 = $0.0473 per hour
CAPEX = 1.1 * $2000 = $2200
Bodega price = OPEX + 0.000022815*CAPEX = $0.0975, let's round up to $0.10.

Since we're doing all this rounding but want to retain the rationale behind
them for future updates, we simply return $0.10 as the price.

Theoretically we should also account for dynapods having special
(more expensive) data sources like MS SQL and Oracle, but it is not
a big deal for now. It might turn the 1.1 ratio into 1.2 or something
and add $0.01 to the final price.

Prod Briks: We fit ~15 of them per rack and they cost ~$20k CAPEX so
$5.55/15 + 0.000022815*$20k = ~$0.826 per hour. r528s are a big difference
(maybe about double) on both OPEX and CAPEX.

Edge nodes/pods: ~1/3 of a Microcloud host. So price probably about $0.03.

AWS pod: Comprised of 4 CDM nodes plus 2 data sources. An example conf
is in conf/awspod1.specs.yml. The 2 data sources are named winsql2012
and ubfio.

Each CDM node is a m4.xlarge Linux, so $0.2/hour in US West (Oregon).
Both winsql2012 and ubfio are t2.large instances, so $0.094/hour each.
https://aws.amazon.com/ec2/pricing/on-demand/

We round up to come to $1.0 for the AWS pod ((4 * 0.2) + (2 * 0.1)).
"""
PLATFORM_TO_ITEM_PRICE = {
    RktestYml.PLATFORM_AWS: 1.0,
    RktestYml.PLATFORM_DYNAPOD: 0.1,
    RktestYml.PLATFORM_DYNAPOD_ROBO: 0.03,
    RktestYml.PLATFORM_PROD_BRIK: 0.826,
    RktestYml.PLATFORM_STATIC: 0.1,
    RktestYml.PLATFORM_STATIC_ROBO: 0.03
}

UNKNOWN_PLATFORM_DEFAULT_PRICE = 0.1


def get_item_price_by_platform(item_requirements):
    platform = item_requirements.get('platform', None)
    # If platform is not specified, try getting an object that
    # meets the item's requirements and use the platform of
    # that item to calculate price.
    if platform is None:
        item = RktestYmlFilter(item_requirements).qs.first()
        if item:
            platform = item.platform

    price = PLATFORM_TO_ITEM_PRICE.get(platform)

    if price:
        return price
    else:
        log.warn('Unknown item price for platform %s' % platform)
        return UNKNOWN_PLATFORM_DEFAULT_PRICE


PROD_BRIK_MANUFACTURING_SERVER_FOR_LOCATION = {
    'COLO': '10.0.122.32',
    'HQ': '192.168.18.10'
}

CLOUD_PROVIDER_FOR_PLATFORM = {
    RktestYml.PLATFORM_AWS: 'aws',
    RktestYml.PLATFORM_AZURE: 'azure'
}


class ReleaseQualBatonManager(ItemManager):
    def __init__(self):
        """Override initialization in ItemManager."""
        pass

    def get_item_recipe(self, requirements):
        return None

    def get_item_price(self, requirements):
        return get_item_price_by_platform(requirements)

    def get_pending_items_queryset(self,
                                   item_queryset):
        return item_queryset.none()

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta()

    def get_status(self, release_qual_baton):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, release_qual_baton):
        release_qual_baton.held_by = None
        release_qual_baton.save()

    def taste_test(self, release_qual_baton, requirements):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        return


class RktestYmlManager(ItemManager):
    def __init__(self):
        """Initialize jenkins_handle to None.

        This is done to avoid unnecessary connections to Jenkins when it
        isn't necessary. We will set jenkins_handle when we need to use it.
        """
        self.jenkins_handle = None

    def _set_jenkins_handle(self):
        """Connect to a Jenkins instance under self.jenkins_handle.

        RkLabBaseJenkins has what we need to connect to Jenkins, and is
        relatively lightweight, so let's use it. RkLabJenkins (which uses
        RkLabBaseJenkins) handles config files, but is a bit too heavy-handed
        and unnecessary since we use the Django settings file.
        """
        rklab_jenkins = RkLabBaseJenkins(settings.JENKINS_API['url'],
                                         settings.JENKINS_API['username'],
                                         settings.JENKINS_API['token'])
        self.jenkins_handle = rklab_jenkins.jenkins_handle

    def _get_time_elapsed(self, rktestyml):
        """Return timedelta of time elapsed since latest cleanup started."""
        assert(isinstance(rktestyml.held_by, JenkinsTask))
        recovery_task = rktestyml.held_by
        delta = datetime.now(utc) - recovery_task.time_uuid_updated
        return delta

    def _get_timedelta_str(self, td):
        """Remove microseconds and return a printable string."""
        return str(td - timedelta(microseconds=td.microseconds))

    def _get_recovery_job_name(self, rktestyml):
        """Return the recovery job name for an RktestYml's platform."""
        platform = rktestyml.platform
        if platform not in PLATFORM_TO_RECOVERY_JOB_NAME:
            error_msg = 'Platform %s not supported for recovery' % platform
            bodega_value_error(log, error_msg)
        return PLATFORM_TO_RECOVERY_JOB_NAME[platform]

    def _process_jenkins_build_status(self, jenkins_build_status):
        """Convert a Jenkins build status string to our own format."""
        if jenkins_build_status == 'SUCCESS':
            return self.STATUS_SUCCESS
        elif jenkins_build_status == 'FAILURE' or \
                jenkins_build_status == 'ABORTED':
            return self.STATUS_FAILURE
        return self.STATUS_WAITING  # waiting for build to complete

    def _get_uuid_param(self, jenkins_build):
        """Get the value of the UUID parameter on a Jenkins build.

        The implementation of jenkins_build.get_params() relies on a "_class"
        field existing in action objects returned by the API. We don't know
        why, but somehow the legacy Jenkins instance that we outsource recovery
        jobs to has stopped including this "_class" field so
        jenkins_build.get_params() returns nothing. So, get the UUID value
        ourselves by examining the API response in _data.
        """
        uuid_param = None
        build_actions = jenkins_build._data.get('actions')
        for action in build_actions:
            params_action = action.get('parameters', [])
            for param in params_action:
                if param['name'] == 'UUID':
                    uuid_param = param['value']
        return uuid_param

    def is_managing(self, rktestyml):
        if not isinstance(rktestyml, RktestYml):
            return False
        if not isinstance(rktestyml.held_by, JenkinsTask):
            return False
        return True

    def get_item_recipe(self, requirements):
        return None

    def get_item_price(self, requirements):
        return get_item_price_by_platform(requirements)

    def get_pending_items_queryset(self,
                                   item_queryset):
        return item_queryset.none()

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta()

    def get_status(self, rktestyml):
        """Return one of the cleanup statuses from above.

        This behaves similarly to jenkinsapi.job.get_build_by_params(...),
        which moves back in time through the list of builds. Unlike
        get_build_by_params(), we are matching the UUID and only the UUID,
        instead of all parameters.
        """
        if not self.is_managing(rktestyml):
            return self.STATUS_NOT_MANAGING

        recovery_task = rktestyml.held_by
        build_uuid = recovery_task.uuid
        cached_buildnum = recovery_task.cached_buildnum

        log.debug(
            ('Getting status of %s ' % rktestyml) +
            ('which is being worked on by %s and ' % repr(build_uuid)) +
            ('currently has cached build number %s' % repr(cached_buildnum)))

        if not cached_buildnum:
            log.debug(
                ('%s is being ' % rktestyml) +
                ('worked on by %s and has no cached ' % repr(build_uuid)) +
                ('build number, so seems to be waiting to start.'))
            return self.STATUS_WAITING  # waiting for build to start

        job_name = self._get_recovery_job_name(rktestyml)
        job = self.jenkins_handle.get_job(job_name)

        try:
            build = job.get_build(cached_buildnum)
            build_status = build.get_status()
            current_build_uuid = self._get_uuid_param(build)
            if current_build_uuid == str(build_uuid):
                log.debug(
                    '%s %s: Found build: cached_buildnum=%s, status=%s' %
                    (rktestyml.filename, repr(build_uuid),
                     cached_buildnum, repr(build_status)))
                return self._process_jenkins_build_status(build_status)
            else:
                log.debug(
                    ('Cached build %s has ' % repr(cached_buildnum)) +
                    ('UUID %s instead of ' % repr(current_build_uuid)) +
                    ('expected %s, ' % repr(build_uuid)) +
                    ('so invalidating cache.'))
                recovery_task.cached_buildnum = None
                recovery_task.save()
        except:
            log.debug(
                ('Exception while finding cached build %s, ' %
                 repr(cached_buildnum)) +
                ('will assume it is still waiting to start.'),
                exc_info=True)
            return self.STATUS_WAITING

    def identify_jenkins_tasks(self, rktest_ymls):
        """Find Jenkins build numbers for the tasks holding these items.

        Outsourcing recovery work to Jenkins continues to be ugly, but until
        we have insourced a la carte replacements, we still need to do this.
        Set the cached_buildnum of the JenkinsTask instances holding the
        rktest_ymls while making a single pass over the Jenkins builds, which
        scales better than our prior technique of looking for only one
        JenkinsTask instance when scanning over Jenkins builds.
        """
        log.debug(
            'Identifying Jenkins tasks for %d rktest_ymls in recovery.' %
            len(rktest_ymls))

        self._set_jenkins_handle()
        tasks_by_job_and_uuid = {}
        for rktest_yml in rktest_ymls:
            jenkins_task = rktest_yml.held_by
            if not isinstance(jenkins_task, JenkinsTask):
                log.debug(
                    ('%s is held by %s instead of a JenkinsTask ' %
                     (rktest_yml, repr(jenkins_task))) +
                    ('so ignore it.'))
                continue

            if jenkins_task.cached_buildnum is not None:
                log.debug(
                    ('%s is held by %s ' %
                     (rktest_yml, repr(jenkins_task))) +
                    ('which has a cached build number of %s ' %
                     repr(jenkins_task.cached_buildnum)) +
                    ('for job URL %s ' % repr(jenkins_task.cached_job_url)) +
                    ('so no need to search for it again.'))
                continue

            recovery_job_name = self._get_recovery_job_name(rktest_yml)
            if recovery_job_name not in tasks_by_job_and_uuid:
                tasks_by_job_and_uuid[recovery_job_name] = {}
            tasks_by_uuid = tasks_by_job_and_uuid[recovery_job_name]
            tasks_by_uuid[str(jenkins_task.uuid)] = jenkins_task

        # Sort the recovery job names so those with the most tasks to search
        # for come first. Usually this will be recover-dynamic-pod. Since this
        # is all happening in a single thread, it's preferable to process the
        # jobs with more tasks before those with fewer tasks so the latter do
        # not block the former in the worst case of searching until the end
        # of the range. The jobs with more tasks also probably have higher
        # churn, making it more important to identify those tasks quickly to
        # reduce the risk of them rolling off before we can identify them.
        def num_recovery_job_tasks(recovery_job_name):
            return len(tasks_by_job_and_uuid[recovery_job_name])
        recovery_job_names = sorted(
            tasks_by_job_and_uuid.keys(),
            key=num_recovery_job_tasks,
            reverse=True)
        num_tasks_to_find = 0
        num_unidentified_tasks = 0
        log.debug(
            'Starting search for tasks among Jenkins jobs %s.' %
            (repr(recovery_job_names)))
        for recovery_job_name in recovery_job_names:
            tasks_by_uuid = tasks_by_job_and_uuid[recovery_job_name]
            num_tasks_to_find += len(tasks_by_uuid)
            num_unidentified_tasks += self._identify_jenkins_tasks_for_job(
                recovery_job_name, tasks_by_uuid)
        log.debug(
            ('Finished searching for %d tasks among Jenkins jobs %s. ' %
             (num_tasks_to_find, repr(recovery_job_names))) +
            ('%d tasks remained unidentified.' % num_unidentified_tasks))

    def _identify_jenkins_tasks_for_job(self,
                                        recovery_job_name,
                                        tasks_by_uuid):
        log.debug(
            ('Identifying %d Jenkins tasks ' % len(tasks_by_uuid)) +
            ('expected to be instances of Jenkins job %s.' %
             repr(recovery_job_name)))
        job = self.jenkins_handle.get_job(recovery_job_name)

        # Search backwards through the Jenkins builds. Consider
        # BUILD_SEARCH_LIMIT builds at minimum but scale it according to the
        # number of tasks we know we're searching for.
        last_build = job.get_last_buildnumber()
        build_search_limit = max(BUILD_SEARCH_LIMIT,
                                 2 * len(tasks_by_uuid))
        first_build = max(job.get_first_buildnumber(),
                          last_build - build_search_limit)
        log.debug('Looking through builds of %s numbers %d through %d...' %
                  (repr(recovery_job_name), last_build, first_build))
        for buildnum in range(last_build, first_build - 1, -1):
            if len(tasks_by_uuid) == 0:
                log.debug(
                    ('No more tasks left to identify for job %s ' %
                     repr(recovery_job_name)) +
                    ('so finishing.'))
                break

            try:
                build = job.get_build(buildnum)
                build_status = build.get_status()
                current_build_uuid = self._get_uuid_param(build)
            except:
                log.debug(
                    'Could not find build %s of job %s, moving on...' %
                    (repr(buildnum), repr(recovery_job_name)),
                    exc_info=True)
                continue

            log.debug(
                'Build %s of job %s has UUID=%s and status=%s.' %
                (repr(buildnum), repr(recovery_job_name),
                 repr(current_build_uuid), repr(build_status)))
            if current_build_uuid in tasks_by_uuid:
                recovery_task = tasks_by_uuid[current_build_uuid]
                recovery_task.cached_buildnum = buildnum
                recovery_task.save()
                log.debug(
                    ('Found build %s of job %s status=%s ' %
                     (repr(buildnum), repr(recovery_job_name),
                      repr(build_status))) +
                    ('matching recovery task %s ' % recovery_task.uuid) +
                    ('holding items %s' %
                     repr(recovery_task.holding_items.all())))
                tasks_by_uuid.pop(current_build_uuid)

        log.debug(
            ('Finished looking through builds of %s. ' %
             repr(recovery_job_name)) +
            ('%d tasks were still unidentified: %s' %
             (len(tasks_by_uuid), repr(sorted(tasks_by_uuid.keys())))))
        return len(tasks_by_uuid)

    def _build_recovery_job(self, rktestyml):
        """Trigger a Jenkins recovery job build for an RktestYml."""
        assert(isinstance(rktestyml.held_by, JenkinsTask))
        recovery_job_name = self._get_recovery_job_name(rktestyml)
        slave_label = ('%s:%s:rkslave' %
                       (rktestyml.location.name, rktestyml.network.name))
        build_params = {
            'ENCRYPTED': str(rktestyml.encrypted),
            'R6XX': str(rktestyml.model_r6xx),
            'RESERVED_RESOURCE': rktestyml.filename,
            'SLAVE_LABEL': slave_label,
            'UUID': str(rktestyml.held_by.uuid)
        }

        if rktestyml.platform == RktestYml.PLATFORM_PROD_BRIK:
            location = rktestyml.location.name
            build_params['MANUFACTURING_SERVER'] = \
                PROD_BRIK_MANUFACTURING_SERVER_FOR_LOCATION[location]

        if rktestyml.platform == RktestYml.PLATFORM_AWS or \
                rktestyml.platform == RktestYml.PLATFORM_AZURE:
            build_params['CLOUD_PROVIDER'] = \
                CLOUD_PROVIDER_FOR_PLATFORM[rktestyml.platform]

        job = self.jenkins_handle.get_job(recovery_job_name)
        recovery_task = rktestyml.held_by
        recovery_task.cached_job_url = job.url
        recovery_task.save()

        self.jenkins_handle.build_job(recovery_job_name, build_params)
        log.debug('Building job=%s with params=%s' %
                  (repr(recovery_job_name), repr(build_params)))

    def _start_cleanup(self, rktestyml):
        """Start the cleanup process.

        A new JenkinsTask should be created for recovery, and a new build
        should be triggered.
        """
        recovery_task = JenkinsTask.objects.create()
        rktestyml.held_by = recovery_task
        rktestyml.save()
        log.debug('%s %s: Assigned JenkinsTask to held_by' %
                  (rktestyml.filename, repr(recovery_task.uuid)))
        self._build_recovery_job(rktestyml)

    def _update_cleanup(self, rktestyml):
        """Retry the cleanup process.

        The existing JenkinsTask should receive a new UUID, and a new build
        should be triggered.
        """
        recovery_task = rktestyml.held_by
        assert(isinstance(recovery_task, JenkinsTask))
        old_uuid = recovery_task.uuid
        recovery_task.uuid = uuid4()
        recovery_task.cached_buildnum = None
        recovery_task.cached_job_url = None
        recovery_task.time_uuid_updated = datetime.now(utc)
        recovery_task.save()
        log.debug(
            ('Updated UUID of JenkinsTask %s holding RktestYml %s ' %
             (repr(recovery_task.sid), rktestyml.filename)) +
            ('from %s to %s' %
             (repr(old_uuid), repr(recovery_task.uuid))))
        self._build_recovery_job(rktestyml)

    def _end_cleanup(self, rktestyml):
        """End the cleanup process.

        The RktestYml should be freed by disassociating its JenkinsTask from
        the held_by field.
        """
        rktestyml.held_by = None
        rktestyml.save()
        log.debug('%s has been freed' % rktestyml.filename)

    def handle_cleanup(self, rktestyml):
        """Handle cleanup of an RktestYml."""
        if not isinstance(rktestyml, RktestYml):
            error_msg = 'Cannot handle cleanup for non-RktestYml %s' % \
                repr(rktestyml)
            bodega_type_error(log, error_msg)

        self._set_jenkins_handle()
        if not isinstance(rktestyml.held_by, JenkinsTask):
            if not rktestyml.held_by_object_in_final_state:
                log.warning('%s is held by %s which is not currently in a '
                            'final state. Will not attempt recovery on this '
                            'Item.'
                            % (rktestyml, rktestyml.held_by))
                return

            if rktestyml.state == Item.STATE_MAINTENANCE:
                log.debug('%s has state set to %s so will not attempt '
                          'recovery on this Item.'
                          % (rktestyml, Item.STATE_MAINTENANCE))
                self._end_cleanup(rktestyml)
            else:
                log.debug('%s: Starting cleanup' % rktestyml)
                self._start_cleanup(rktestyml)
        else:
            time_elapsed = self._get_time_elapsed(rktestyml)
            uuid = rktestyml.held_by.uuid
            if RECOVERY_TIME_LIMIT < time_elapsed:
                log.debug('%s %s: Updating cleanup after timeout (%s > %s)' %
                          (rktestyml, repr(uuid),
                           self._get_timedelta_str(time_elapsed),
                           self._get_timedelta_str(RECOVERY_TIME_LIMIT)))
                if rktestyml.state == Item.STATE_MAINTENANCE:
                    log.info('%s timed out during recovery but freeing '
                             'the resource since its state is set to %s'
                             % (rktestyml, Item.STATE_MAINTENANCE))
                    self._end_cleanup(rktestyml)
                else:
                    self._update_cleanup(rktestyml)
                    return

            status = self.get_status(rktestyml)
            if status == self.STATUS_SUCCESS:
                log.debug('%s %s: Ending cleanup for build success' %
                          (rktestyml, repr(uuid)))
                self._end_cleanup(rktestyml)
            elif status == self.STATUS_FAILURE:
                log.debug('%s %s: Updating cleanup for build failure' %
                          (rktestyml, repr(uuid)))
                if rktestyml.state == Item.STATE_MAINTENANCE:
                    log.info('%s failed recovery but freeing the resource '
                             'since its state is set to %s'
                             % (rktestyml, Item.STATE_MAINTENANCE))
                    self._end_cleanup(rktestyml)
                else:
                    self._update_cleanup(rktestyml)
            else:
                log.debug('%s %s: ... has been waiting for %s (limit %s)' %
                          (rktestyml, repr(uuid),
                           self._get_timedelta_str(time_elapsed),
                           self._get_timedelta_str(RECOVERY_TIME_LIMIT)))

    def taste_test(self, rktestyml, requirements):
        if rktestyml.platform != RktestYml.PLATFORM_DYNAPOD:
            return True

        ftp_util = FtpUtil(DYNAPOD_FTP_SERVER,
                           DYNAPOD_FTP_USER,
                           DYNAPOD_FTP_PASSWORD)
        file_path = 'Dynapod/%s/%s' % (rktestyml.filename.replace('.yml', ''),
                                       rktestyml.filename)
        if ftp_util.check_file(file_path):
            return True
        else:
            log.debug(
                'Taste test failed for %s - rejecting.' % repr(rktestyml))
            return False

    def get_non_rare_requirements(self):
        """Return a dictionary of requirements that filter out rare RktestYmls.

        These requirements allow for order fulfillment to serve non-rare
        RktestYmls whenever possible.
        """
        return {'acropolis': False,
                'encrypted': False,
                'esx_6_0': False,
                'hyperv_2016': False,
                'linux_agent_all_versions': False,
                'model_r6xx': False,
                'robofm': False,
                'robossd': False,
                'tpm': False,
                'vcenter_5_1': False,
                'vcenter_6_5': False,
                'vcloud_8_1': False,
                'vcloud_8_2': False,
                'vcloud_9_0': False,
                'windows_app_test_only': False}

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = RktestYmlFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the rktest_yml item type.'
                             % field)
                bodega_validation_error(log, error_msg)

        rktest_ymls = RktestYmlFilter(item_requirements).qs
        if not rktest_ymls.count():
            error_msg = ('No Items in the (static) inventory of rktest_ymls '
                         'were able to fulfill the requirements of %s so the '
                         'order is likely unfulfillable.'
                         % str(item_requirements))
            bodega_validation_error(log, error_msg)

        if settings.BLOCK_DYNAPODS_FROM_NON_JENKINS_USERS and \
                user_sid not in getattr(settings, 'ACCEPTED_USERS_SIDS', []) and \
                not is_maintenance_order:
            # If the BLOCK_DYNAPODS_FROM_NON_JENKINS_USERS toggle is enabled,
            # only Jenkins users will be able to order dynapods. This rejects
            # their Order POST request with an error message so users don't
            # wait endlessly in the queue.
            if 'platform' in item_requirements:
                platform = item_requirements['platform']
            elif 'filename' in item_requirements:
                yml = RktestYml.objects.get(
                    filename=item_requirements['filename'])
                platform = yml.platform
            else:
                log.debug('No platform specified in item requirements. '
                          'Blocking this request to avoid giving dynapods.')
                platform = RktestYml.PLATFORM_DYNAPOD

            if platform == RktestYml.PLATFORM_DYNAPOD:
                error_msg = ('Ordering dynapods is currently blocked. Please '
                             'place an order for the DYNAPOD_ROBO platform or '
                             'use a CdmCluster.')
                bodega_validation_error(log, error_msg)
