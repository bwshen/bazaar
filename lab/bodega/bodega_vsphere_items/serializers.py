"""Serializers for Bodega vsphere items."""
from bodega_core.fields import LocationField, NetworkField
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from .models import EsxHost


class EsxHostSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the EsxHost model."""

    location = LocationField()
    network = NetworkField()

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Meta class."""

        model = EsxHost
        fields = (
            'ipv4',
            'vcenter',
            'version',
            'hostname',
            'password',
            'username',
            'location',
            'network'
        )
