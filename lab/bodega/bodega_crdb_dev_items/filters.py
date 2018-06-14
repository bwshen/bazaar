"""Filters for Bodega generic items."""
from bodega_core.filters import ItemFilter
from django_filters import CharFilter, NumberFilter
from .models import CockroachDBDepsMachine


class CockroachDBDepsMachineFilter(ItemFilter):
    """Filter for the CockroachDBDepsMachine model."""

    ipv4 = CharFilter(name='ipv4')
    disk_size = NumberFilter(name='disk_size')
    model = CharFilter(name='model')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')
    version = CharFilter(name='version')
    image_version = CharFilter(name='image_version')

    class Meta:
        model = CockroachDBDepsMachine
        fields = ['sid',
                  'ipv4',
                  'model',
                  'location',
                  'network',
                  'state']
