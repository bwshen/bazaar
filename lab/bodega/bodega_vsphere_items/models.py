"""Models for vsphere items."""
import logging
from bodega_core.models import Item
from django.db import models

log = logging.getLogger(__name__)


class EsxHost(Item):

    ESXI_55 = "ESXI_55"
    ESXI_60 = "ESXI_60"
    ESXI_65 = "ESXI_65"

    VERSION_CHOICES = (
        (ESXI_55, "VMware vSphere Hypervisor (ESXi) 5.5"),
        (ESXI_60, "VMware vSphere Hypervisor (ESXi) 6.0"),
        (ESXI_65, "VMware vSphere Hypervisor (ESXi) 6.5")
    )

    version = models.CharField(
        max_length=16,
        blank=False,
        choices=VERSION_CHOICES,
        help_text='Version, one of %s'
                  % repr([choice[0] for choice in VERSION_CHOICES])
    )

    ipv4 = models.GenericIPAddressField(blank=False)
    hostname = models.CharField(max_length=100, blank=True)
    username = models.CharField(max_length=64, blank=False)
    password = models.CharField(max_length=64, blank=False)
    vcenter = models.CharField(max_length=128, blank=False)

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this Esx host')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this EsxHost.')

    @property
    def ip_address(self):
        return self.ipv4

    @property
    def name(self):
        return self.hostname or self.ipv4
