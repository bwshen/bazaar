"""Serializers for Bodega Sd Dev items."""
from bodega_core.fields import LocationField, NetworkField
from rest_framework import serializers
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from . import models


class CdmNodeSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the CdmNode model."""

    ipv4 = serializers.CharField(read_only=True)
    hostname = serializers.CharField(source='name')
    gateway = serializers.CharField(read_only=True)
    netmask = serializers.CharField(read_only=True)
    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = models.CdmNode
        fields = (
            'ipv4',
            'hostname',
            'gateway',
            'netmask',
            'location',
            'network',
            'model',
            'artifacts_url',
            'location',
            'time_created'
        )
        read_only_fields = ('ipv4',
                            'hostname',
                            'gateway',
                            'netmask',
                            'time_created',)


class CdmClusterSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the CdmCluster model."""

    nodes = CdmNodeSerializer(many=True, read_only=True)
    ntp_servers = serializers.JSONField()
    dns_nameservers = serializers.JSONField()
    dns_search_domains = serializers.JSONField()
    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = models.CdmCluster
        fields = (
            'node_count',
            'nodes',
            'ntp_servers',
            'dns_nameservers',
            'dns_search_domains',
            'location',
            'network',
            'model',
            'artifacts_url',
            'location',
            'time_created'
        )
        read_only_fields = ('node_count',
                            'nodes',
                            'ntp_servers',
                            'dns_nameservers',
                            'dns_search_domains',
                            'time_created',)
