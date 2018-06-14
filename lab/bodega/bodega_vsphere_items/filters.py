"""Filters for Bodega vsphere items."""
from bodega_core.filters import ItemFilter
from django_filters import CharFilter
from .models import EsxHost


class EsxHostFilter(ItemFilter):
    ipv4 = CharFilter(name='ipv4')
    hostname = CharFilter(name='hostname')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')
    vcenter = CharFilter(name='vcenter')
    version = CharFilter(name='version')

    class Meta:
        """Meta class."""

        model = EsxHost
        fields = ['sid',
                  'ipv4',
                  'hostname',
                  'vcenter',
                  'version',
                  'location',
                  'network',
                  'state']
