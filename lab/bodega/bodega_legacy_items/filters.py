"""Filters for Bodega legacy items."""
from bodega_core.filters import ExtendedBooleanFilter
from django_filters import CharFilter
from sid_from_id.filters import SidFromIdFilterSet
from .models import JenkinsTask, ReleaseQualBaton, RktestYml


class JenkinsTaskFilter(SidFromIdFilterSet):
    """Filter for the JenkinsTask model."""

    class Meta:
        """Meta class."""

        model = JenkinsTask
        fields = ['sid', 'uuid']


class ReleaseQualBatonFilter(SidFromIdFilterSet):
    """Filter for the ReleaseQualBaton model."""

    class Meta:
        """Meta class."""

        model = ReleaseQualBaton
        fields = ['sid']


class RktestYmlFilter(SidFromIdFilterSet):
    """Filter for the RktestYml model."""

    location = CharFilter(name='location__name', method='filter_location')
    network = CharFilter(name='network__name')

    benchmarking = ExtendedBooleanFilter()
    encrypted = ExtendedBooleanFilter()
    esx_6_0 = ExtendedBooleanFilter()
    fc_aix_agent = ExtendedBooleanFilter()
    fc_linux_agent = ExtendedBooleanFilter()
    hyperv_2016 = ExtendedBooleanFilter()
    linux_agent = ExtendedBooleanFilter()
    linux_agent_all_versions = ExtendedBooleanFilter()
    manufacturable = ExtendedBooleanFilter()
    model_r6xx = ExtendedBooleanFilter()
    mssql = ExtendedBooleanFilter()
    robofm = ExtendedBooleanFilter()
    robossd = ExtendedBooleanFilter()
    stronger = ExtendedBooleanFilter()
    tpm = ExtendedBooleanFilter()
    vcenter_5_1 = ExtendedBooleanFilter()
    vcenter_5_5 = ExtendedBooleanFilter()
    vcenter_6_0 = ExtendedBooleanFilter()
    vcenter_6_5 = ExtendedBooleanFilter()
    windows_app_test_only = ExtendedBooleanFilter()

    def filter_location(self, queryset, name, value):
        """Filter location with and without underscores.

        This supports more human-intuitive locations on top of the
        underscore-prefixed locations defined in the models. Ignore the 'name'
        parameter here - we know we're filtering on location.
        """
        if value == '_COLO':
            return queryset.filter(location__name='COLO')
        elif value == '_HQ':
            return queryset.filter(location__name='HQ')
        return queryset.filter(location__name=value)

    class Meta:
        """Meta Class."""

        model = RktestYml
        # TODO: The CharFields do not have an 'unknown' option among the
        # choices when filtering - should investigate
        fields = [
            'sid',
            'filename',
            'location',
            'network',
            'platform',
            'acropolis',
            'benchmarking',
            'encrypted',
            'esx_6_0',
            'fc_aix_agent',
            'fc_linux_agent',
            'hyperv_2016',
            'linux_agent',
            'linux_agent_all_versions',
            'manufacturable',
            'model_r6xx',
            'mssql',
            'robofm',
            'robossd',
            'tpm',
            'vcenter_5_1',
            'vcenter_5_5',
            'vcenter_6_0',
            'vcenter_6_5',
            'vcloud_8_1',
            'vcloud_8_2',
            'vcloud_9_0',
            'windows_app_test_only'
        ]
