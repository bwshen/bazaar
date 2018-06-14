"""Serializers for Bodega Sd Dev items."""
from bodega_core.fields import LocationField, NetworkField
from rest_framework import serializers
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from .models import SdDevMachine


class SdDevMachineSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the JenkinsTask model."""

    ip_address = serializers.CharField(read_only=True)
    location = LocationField()
    network = NetworkField()
    username = serializers.CharField(read_only=True)
    password = serializers.CharField(read_only=True)

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = SdDevMachine
        fields = ('ip_address',
                  'model',
                  'location',
                  'network',
                  'username',
                  'password',
                  'version',
                  'privileged_mode',
                  'time_created')
        read_only_fields = ('ip_address',
                            'username',
                            'password',
                            'time_created',
                            'privileged_mode')
