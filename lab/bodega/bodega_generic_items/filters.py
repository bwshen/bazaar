"""Filters for Bodega generic items."""
from bodega_core.filters import ItemFilter
from django_filters import CharFilter, NumberFilter
from .models import IpAddress, MssqlServer, UbuntuMachine


class MssqlServerFilter(ItemFilter):
    """Filter for the MssqlServer model."""

    ipv4 = CharFilter(name='ipv4')
    model = CharFilter(name='model')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')
    version = CharFilter(name='version')

    class Meta:
        model = MssqlServer
        fields = ['sid',
                  'ipv4',
                  'model',
                  'location',
                  'network',
                  'state']


class UbuntuMachineFilter(ItemFilter):
    """Filter for the UbuntuMachine model."""

    ipv4 = CharFilter(name='ipv4')
    disk_size = NumberFilter(name='disk_size')
    model = CharFilter(name='model')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')
    version = CharFilter(name='version')
    root_disk_size = NumberFilter(name='root_disk_size')
    kernel_version = CharFilter(name='kernel_version')

    class Meta:
        model = UbuntuMachine
        fields = ['sid',
                  'ipv4',
                  'model',
                  'location',
                  'network',
                  'state']


class IpAddressFilter(ItemFilter):
    """Filter for the IpAddress model."""

    ip = CharFilter(name='ip')
    location = CharFilter(name='location__name')
    network = CharFilter(name='network__name')

    class Meta:
        model = IpAddress
        fields = ['sid',
                  'ip',
                  'location',
                  'network',
                  'state']
