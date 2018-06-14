"""Models representing vSphere items."""
from bodega_core.models import BaseModel, Farm, Item
from django.db import models


class VSphereFarm(Farm):
    location = models.ForeignKey('bodega_core.Location',
                                 null=False,
                                 on_delete=models.CASCADE)

    def can_grow(self, item):
        # TODO: Need more detailed logic on whether or not we can provide
        # a VirtualMachine
        return True


class VCenter(BaseModel):
    VERSION_5_5 = '5.5'
    VERSION_6_0 = '6.0'
    VERSION_6_5 = '6.5'

    VCENTER_VERSION_CHOICES = (
        (VERSION_5_5, VERSION_5_5),
        (VERSION_6_0, VERSION_6_0),
        (VERSION_6_5, VERSION_6_5)
    )

    url = models.CharField(max_length=255, null=False)
    version = models.CharField(max_length=3, blank=False, null=False,
                               choices=VCENTER_VERSION_CHOICES)
    username = models.CharField(max_length=255, null=False, blank=False)
    password = models.CharField(max_length=255, null=False, blank=False)
    vsphere_farm = models.ForeignKey('VSphereFarm',
                                     null=False,
                                     related_name='vcenters',
                                     on_delete=models.CASCADE)


class EsxHost(BaseModel):
    VERSION_5_5 = '5.5'
    VERSION_6_0 = '6.0'
    VERSION_6_5 = '6.5'

    ESXI_VERSION_CHOICES = (
        (VERSION_5_5, VERSION_5_5),
        (VERSION_6_0, VERSION_6_0),
        (VERSION_6_5, VERSION_6_5)
    )

    ESXI_HARDWARE_MEMORY1 = 'memory1'
    ESXI_HARDWARE_SPOTTY1 = 'spotty1'

    ESXI_HARDWARE_CHOICES = (
        (ESXI_HARDWARE_MEMORY1, '2u4n / Fat Twin hardware'),
        (ESXI_HARDWARE_SPOTTY1, 'Microcloud with possible oversubscribing')
    )

    # Explicitly map the various Esx hardwares to the sizes that we will
    # support for this Item. From this mapping, we will build the list of
    # models which the users can request. The sizes are mostly chosen
    # as a power of 2 to avoid situations where we have additional
    # capacity on a host but can't utilize it effectively.
    VSPHERE_MODELS_MAPPINGS = {
        ESXI_HARDWARE_MEMORY1: {
            'medium': (1, 8),
            'large': (2, 16),
            'xlarge': (4, 32)
        },
        ESXI_HARDWARE_SPOTTY1: {
            'medium': (1, 4),
            'large': (2, 8)
        }
    }

    url = models.CharField(max_length=255, null=False)
    version = models.CharField(max_length=3, blank=False, null=False,
                               choices=ESXI_VERSION_CHOICES)
    hardware = models.CharField(max_length=10, blank=False, null=False,
                                choices=ESXI_HARDWARE_CHOICES)
    vcenter = models.ForeignKey('VCenter',
                                null=False,
                                related_name='esx_hosts',
                                on_delete=models.CASCADE)


class VSphereVirtualMachine(Item):
    def __str_additional_info_nvps__(self):
        """Get additional name-value pairs for the string representation."""
        return [('_name', self._name)]

    _name = models.CharField(max_length=255, null=False)
    instance_uuid = models.CharField(max_length=64, null=False)
    moid = models.CharField(max_length=255, null=False)
    vcenter = models.ForeignKey('VCenter',
                                null=False,
                                related_name='virtual_machines',
                                on_delete=models.CASCADE)
