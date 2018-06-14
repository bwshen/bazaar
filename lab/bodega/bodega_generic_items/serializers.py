"""Serializers for Bodega Sd Dev items."""
from bodega_core.fields import LocationField, NetworkField
from rest_framework import serializers
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from . import models


class MssqlServerSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the MssqlServer model."""

    ipv4 = serializers.CharField(read_only=True)
    cifs = serializers.JSONField(read_only=True)
    odbc = serializers.JSONField(read_only=True)
    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = models.MssqlServer
        fields = (
            'ipv4',
            'cifs',
            'odbc',
            'location',
            'network',
            'model',
            'time_created'
        )
        read_only_fields = ('ipv4',
                            'cifs',
                            'odbc',
                            'location',
                            'time_created',)


class UbuntuMachineSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the UbuntuMachine model."""

    ipv4 = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    password = serializers.CharField(read_only=True)
    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = models.UbuntuMachine
        fields = (
            'ipv4',
            'disk_size',
            'username',
            'password',
            'location',
            'network',
            'model',
            'root_disk_size',
            'kernel_version',
            'time_created'
        )
        read_only_fields = ('ipv4',
                            'disk_size',
                            'username',
                            'password',
                            'location',
                            'time_created',)


class IpAddressSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the IpAddress model."""

    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = models.IpAddress
        fields = (
            'ip',
            'location')
