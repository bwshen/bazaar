"""Serializers for Bodega Sd Dev items."""
from bodega_core.fields import LocationField, NetworkField
from rest_framework import serializers
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from . import models


class CockroachDBDepsMachineSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the CockroachDBDepsMachine model."""

    ipv4 = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    password = serializers.CharField(read_only=True)
    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = models.CockroachDBDepsMachine
        fields = (
            'ipv4',
            'disk_size',
            'username',
            'password',
            'location',
            'network',
            'model',
            'image_version',
            'time_created'
        )
        read_only_fields = ('ipv4',
                            'disk_size',
                            'username',
                            'password',
                            'location',
                            'time_created',)
