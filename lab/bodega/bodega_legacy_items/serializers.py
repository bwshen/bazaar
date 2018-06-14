"""Serializers for Bodega legacy items."""
from bodega_all import validators
from bodega_core.fields import LocationField, NetworkField
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from . import models


class JenkinsTaskSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the JenkinsTask model."""

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Meta class."""

        model = models.JenkinsTask
        fields = ('sid', 'url', 'uuid', 'cached_build',
                  'time_since_uuid_update')
        read_only_fields = ('cached_build', 'time_since_uuid_update')


class ReleaseQualBatonSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the ReleaseQualBaton model."""

    class Meta(object):
        """Meta class."""

        model = models.ReleaseQualBaton


class RktestYmlSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the RktestYml model."""

    location = LocationField()
    network = NetworkField()

    def validate(self, data):
        location_string = data.pop('location', 'COLO')
        location = validators.validate_location_string(location_string)
        data['location'] = location

        network_string = data.pop('network')
        network = validators.validate_network_string(network_string, location)
        data['network'] = network

        return super(RktestYmlSerializer, self).validate(data)

    class Meta(object):
        """Meta class."""

        model = models.RktestYml
        fields = (
            'filename',
            'description',
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
            'stronger',
            'tpm',
            'vcenter_5_1',
            'vcenter_5_5',
            'vcenter_6_0',
            'vcenter_6_5',
            'vcloud_8_1',
            'vcloud_8_2',
            'vcloud_9_0',
            'windows_app_test_only'
        )
