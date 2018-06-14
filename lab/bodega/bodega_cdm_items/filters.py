"""Filters for Bodega CdmNode items."""
from bodega_core.filters import ItemFilter
from django_filters import CharFilter, NumberFilter
from .models import CdmCluster, CdmNode


class CdmNodeFilter(ItemFilter):
    """Filter for the CdmNode model."""

    model = CharFilter(name='model')
    artifacts_url = CharFilter(name='artifacts_url')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')

    class Meta:
        model = CdmNode
        fields = ['sid',
                  'model',
                  'artifacts_url',
                  'location',
                  'network',
                  'state']


class CdmClusterFilter(ItemFilter):
    """Filter for the CdmCluster model."""

    node_count = NumberFilter(name='node_count')
    model = CharFilter(name='model')
    artifacts_url = CharFilter(name='artifacts_url')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')

    class Meta:
        model = CdmCluster
        fields = ['sid',
                  'node_count',
                  'model',
                  'artifacts_url',
                  'location',
                  'network',
                  'state']
