"""Models representing Bodega legacy items."""
from __future__ import unicode_literals
from datetime import datetime, timedelta
from uuid import uuid4

from bodega_core.models import BaseModel, Item
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from pytz import utc


class JenkinsTask(BaseModel):
    """A Jenkins build designated as an infrastructure task.

    Although this isn't an item, it lives here because it's only used for
    legacy items.

    A UUID should uniquely identify a build for future retrieval from Jenkins.
    """

    def __str_additional_info_nvps__(self):
        """Get additional name-value pairs for the string representation."""
        return [
            ('uuid', self.uuid)
        ]

    uuid = models.UUIDField(
        primary_key=False,
        default=uuid4,
        editable=True,
        help_text='The UUID tag used to identify builds from the Jenkins API.')
    cached_job_url = models.URLField(
        null=True,
        help_text='The cached URL of a Jenkins job, used for display only.')
    cached_buildnum = models.PositiveIntegerField(
        null=True,
        help_text='The cached buildnum of a Jenkins build.')
    holding_items = GenericRelation('bodega_core.Item',
                                    content_type_field='held_by_content_type',
                                    object_id_field='held_by_object_id')
    # This is not enforced; it is up to the user to update this field as well
    time_uuid_updated = models.DateTimeField(
        auto_now_add=True,
        help_text='The last time the UUID of this task was updated.')

    @property
    def cached_build(self):
        """Return cached information for a build.

        If both the job URL and buildnum are available, return a full URL.
        Else, return whatever we have in a sensible fashion.
        """
        if not self.cached_job_url:
            return self.cached_buildnum
        elif not self.cached_buildnum:
            return self.cached_job_url
        else:
            return str(self.cached_job_url) + str(self.cached_buildnum) + '/'

    @property
    def time_since_uuid_update(self):
        td = datetime.now(utc) - self.time_uuid_updated
        return str(td - timedelta(microseconds=td.microseconds))


class ReleaseQualBaton(Item):
    """A way for release qualification pipelines to cooperatively throttle."""

    @property
    def name(self):
        return 'release_qual_baton_%s' % self.sid


class RktestYml(Item):
    """An item which is an rktest.yml file representing an entire pod.

    This is a legacy resource type for us to slowly migrate our workflows
    towards Bodega by minimizing the workflow change while moving the
    management work out of Jenkins / lockable resources into Bodega.
    """

    def __str_additional_info_nvps__(self):
        """Get additional name-value pairs for the string representation."""
        return [
            ('filename', self.filename)
        ]

    @property
    def name(self):
        return self.filename

    PLATFORM_AWS = 'AWSPOD'
    PLATFORM_AZURE = 'AZUREPOD'
    PLATFORM_CISCO = 'CISCO'
    PLATFORM_DELL = 'DELL'
    PLATFORM_DYNAPOD = 'DYNAPOD'
    PLATFORM_DYNAPOD_ROBO = 'DYNAPOD_ROBO'
    PLATFORM_DYNAPOD_ROBO_AHV = 'DYNAPOD_ROBO_AHV'
    PLATFORM_DYNAPOD_ROBO_HYPERV = 'DYNAPOD_ROBO_HYPERV'
    PLATFORM_HPE = 'HPE'
    PLATFORM_LENOVO = 'LENOVO'
    PLATFORM_PROD_BRIK = 'PROD_BRIK'
    PLATFORM_STATIC = 'STATIC'
    PLATFORM_STATIC_ROBO = 'STATIC_ROBO'

    PLATFORM_CHOICES = (
        (PLATFORM_AWS, PLATFORM_AWS),
        (PLATFORM_AZURE, PLATFORM_AZURE),
        (PLATFORM_CISCO, PLATFORM_CISCO),
        (PLATFORM_DELL, PLATFORM_DELL),
        (PLATFORM_DYNAPOD, PLATFORM_DYNAPOD),
        (PLATFORM_DYNAPOD_ROBO, PLATFORM_DYNAPOD_ROBO),
        (PLATFORM_DYNAPOD_ROBO_AHV, PLATFORM_DYNAPOD_ROBO_AHV),
        (PLATFORM_DYNAPOD_ROBO_HYPERV, PLATFORM_DYNAPOD_ROBO_HYPERV),
        (PLATFORM_HPE, PLATFORM_HPE),
        (PLATFORM_LENOVO, PLATFORM_LENOVO),
        (PLATFORM_PROD_BRIK, PLATFORM_PROD_BRIK),
        (PLATFORM_STATIC, PLATFORM_STATIC),
        (PLATFORM_STATIC_ROBO, PLATFORM_STATIC_ROBO),
    )

    # The filename of the rktest.yml item.
    filename = models.CharField(
        max_length=80,
        blank=False,
        help_text='Filename of the rktest.yml item',
        unique=True)

    description = models.TextField(
        blank=True,
        default="",
        null=False,
        help_text='Description of this RktestYml item.')

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this RktestYml.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this RktestYml.')

    platform = models.CharField(
        max_length=24,
        blank=False,
        choices=PLATFORM_CHOICES,
        help_text='Platform, one of %s' %
                  repr([choice[0] for choice in PLATFORM_CHOICES]))

    acropolis = models.BooleanField(
        default=False,
        help_text='Has Acropolis host and VMs')

    benchmarking = models.BooleanField(
        default=False,
        help_text='Usable for benchmarking')

    encrypted = models.BooleanField(
        default=False,
        help_text='Is encrypted')

    esx_6_0 = models.BooleanField(
        default=False,
        help_text='Has ESX 6.0 host for general purpose usage')

    fc_aix_agent = models.BooleanField(
        default=False,
        help_text='Has AIX host which has access to Pure FC LUN')

    fc_linux_agent = models.BooleanField(
        default=False,
        help_text='Has Linux host which has access to Pure FC LUN')

    hyperv_2016 = models.BooleanField(
        default=False,
        help_text='Has HyperV 2016 host and VMs')

    linux_agent = models.BooleanField(
        default=False,
        help_text='Has Centos 6 and Ubuntu 14')

    linux_agent_all_versions = models.BooleanField(
        default=False,
        help_text='Has Centos 5,6,7 and Ubuntu 12,14,16')

    manufacturable = models.BooleanField(
        default=False,
        help_text='Is manufacturable')

    model_r6xx = models.BooleanField(
        default=False,
        help_text='Is R6xx series')

    mssql = models.BooleanField(
        default=False,
        help_text='Has MSSQL')

    robofm = models.BooleanField(
        default=False,
        help_text='Has fileset and mssql components')

    robossd = models.BooleanField(
        default=False,
        help_text='Has an ssd for the OS')

    stronger = models.BooleanField(
        default=False,
        help_text='Has double the compute power (4 vCPUs for DYNAPOD)')

    tpm = models.BooleanField(
        default=False,
        help_text='Has TPM')

    vcenter_5_1 = models.BooleanField(
        default=False,
        help_text='Has VCenter 5.1')

    vcenter_5_5 = models.BooleanField(
        default=False,
        help_text='Has VCenter 5.5')

    vcenter_6_0 = models.BooleanField(
        default=False,
        help_text='Has VCenter 6.0')

    vcenter_6_5 = models.BooleanField(
        default=False,
        help_text='Has VCenter 6.5')

    vcloud_8_1 = models.BooleanField(
        default=False,
        help_text='Has vCloud Director 8.1')

    vcloud_8_2 = models.BooleanField(
        default=False,
        help_text='Has vCloud Director 8.2')

    vcloud_9_0 = models.BooleanField(
        default=False,
        help_text='Has vCloud Director 9.0')

    windows_app_test_only = models.BooleanField(
        default=False,
        help_text='Has resources for testing windows applications')
