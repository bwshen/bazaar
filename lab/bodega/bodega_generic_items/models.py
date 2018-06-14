"""Models representing Bodega generic items."""
import logging
from bodega_aws.models import AwsFarm, Ec2Instance
from bodega_aws.tasks import DestroyEc2InstanceTask
from bodega_aws.utils import get_ec2_instance_private_ip, get_ec2_instance_tags
from bodega_core.exceptions import bodega_error, bodega_value_error
from bodega_core.models import Item
from bodega_vsphere.models import EsxHost, VSphereVirtualMachine
from bodega_vsphere.tasks import DestroyVSphereVirtualMachineTask
from bodega_vsphere.utils import get_virtual_machine_ipv4_address
from django.contrib.contenttypes.models import ContentType
from django.db import models

log = logging.getLogger(__name__)


class MssqlServer(Item):
    """Model for MSSQL server."""

    AWS_MODEL_CHOICES = [
        AwsFarm.MODEL_AWS_M4_LARGE,
        AwsFarm.MODEL_AWS_T2_LARGE
    ]
    DEFAULT_MODEL = AwsFarm.MODEL_AWS_T2_LARGE

    VERSION_WINDOWS_2012 = 'windows2012'
    VERSION_CHOICES = (
        (VERSION_WINDOWS_2012, VERSION_WINDOWS_2012),
    )
    DEFAULT_VERSION = VERSION_WINDOWS_2012

    version = models.CharField(
        max_length=16,
        blank=False,
        choices=VERSION_CHOICES,
        help_text='Version, one of %s'
                  % repr([choice[0] for choice in VERSION_CHOICES]),
        default=DEFAULT_VERSION
    )

    model = models.CharField(
        max_length=16,
        blank=False,
        default=DEFAULT_MODEL)

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this MssqlServer.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this MssqlServer.')

    time_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_available_models(cls):
        available_models = []
        available_models.extend(cls.AWS_MODEL_CHOICES)
        return available_models

    @property
    def _ingredient(self):
        mssql_server_content_type = \
            ContentType.objects.get_for_model(MssqlServer)
        held_items = Item.objects.filter(
            held_by_content_type_id=mssql_server_content_type.id,
            held_by_object_id=self.id)

        held_item = held_items.first()
        if held_item is None:
            return None

        if hasattr(held_item, 'ec2instance'):
            return held_item.ec2instance
        else:
            bodega_value_error(log,
                               'MssqlServer instance %s is currently '
                               'holding an unsupported item %s.'
                               % (self, held_item))

    @property
    def name(self):
        ingredient = self._ingredient
        if not ingredient:
            return 'Not associated with an ingredient'
        return ingredient._name

    @property
    def ipv4(self):
        if Item.STATE_DESTROYED == self.state:
            return 'Item has been destroyed and has no IP Address'

        ingredient = self._ingredient
        if not ingredient:
            bodega_error(
                log,
                '%s is not currently tied to any ingredient.' % (self))

        if isinstance(ingredient, Ec2Instance):
            try:
                instance_ip = get_ec2_instance_private_ip(ingredient)
            except:
                log.warning('Could not get IP Address for %s but it is '
                            'currently in state %s with ingredient %s'
                            % (self, self.state, ingredient), exc_info=True)
                return ('Item is made from Ec2Instance %s but could not get IP'
                        % ingredient)
            return instance_ip

        return 'Could not retrieve IP address for this Item'

    @property
    def cifs(self):
        ingredient = self._ingredient
        if not ingredient:
            bodega_error(
                log,
                '%s is not currently tied to any ingredient.' % (self))
        cifs = {}
        if isinstance(ingredient, Ec2Instance):
            try:
                tags = get_ec2_instance_tags(ingredient)
            except:
                msg = ('Could not get tags for %s but it is '
                       'currently in state %s with ingredient %s'
                       % (self, self.state, ingredient))
                log.warning(msg, exc_info=True)
                cifs['Error'] = msg
                return cifs
            for tag in tags:
                if tag['Key'].startswith('cifs_'):
                    key = tag['Key'].split('cifs_', 1)[1]
                    value = tag['Value']

                    if key == 'mount_point':
                        # The cifs mount point needs to be unique or else two
                        # people trying to use the same mount point on the same
                        # machine may step all over each other. For VMs, this
                        # is not an issue but because we use containers, this
                        # problem arises.
                        value = value + '_' + self.name
                    cifs[key] = value
        return cifs

    @property
    def odbc(self):
        ingredient = self._ingredient
        if not ingredient:
            bodega_error(
                log,
                '%s is not currently tied to any ingredient.' % (self))
        odbc = {}
        if isinstance(ingredient, Ec2Instance):
            try:
                tags = get_ec2_instance_tags(ingredient)
            except:
                msg = ('Could not get tags for %s but it is '
                       'currently in state %s with ingredient %s'
                       % (self, self.state, ingredient))
                log.warning(msg, exc_info=True)
                odbc['Error'] = msg
                return odbc
            for tag in tags:
                if tag['Key'].startswith('odbc_'):
                    value = tag['Value']
                    if 'port' in tag['Key']:
                        value = int(value)
                    odbc[tag['Key'].split('odbc_', 1)[1]] = value
        return odbc

    @property
    def item_destroyer(self):
        ingredient = self._ingredient
        if ingredient is None:
            log.warning('%s has no ingredient associated with it. Item will '
                        'be marked as destroyed but we may have leaked the '
                        'ingredient.'
                        % (self))
            return None
        elif ingredient.state == Item.STATE_DESTROYED:
            log.debug('%s has an ingredient %s that was marked as %s.'
                      % (self, ingredient, Item.STATE_DESTROYED))
            return None
        elif isinstance(ingredient, Ec2Instance):
            log.debug('%s has an Ec2Instance ingredient so use %s to destroy '
                      'it. ' % (self, DestroyEc2InstanceTask))
            return DestroyEc2InstanceTask.si(ingredient.sid)
        else:
            error_msg = ('No item_destroyer for %s with ingredient %s'
                         % (self, ingredient))
            bodega_error(log, error_msg)


class UbuntuMachine(Item):
    """A machine with Ubuntu Linux distro."""

    AWS_MODEL_CHOICES = [
        AwsFarm.MODEL_AWS_M4_LARGE,
        AwsFarm.MODEL_AWS_M4_XLARGE,
        AwsFarm.MODEL_AWS_M4_2XLARGE,
        AwsFarm.MODEL_AWS_T2_LARGE
    ]
    DEFAULT_MODEL = AwsFarm.MODEL_AWS_T2_LARGE

    # Explicitly map the various Esx hardwares to the sizes that we will
    # support for this Item. From this mapping, we will build the list of
    # models which the users can request. The sizes are mostly chosen
    # as a power of 2 to avoid situations where we have additional
    # capacity on a host but can't utilize it effectively.
    VSPHERE_MODEL_CHOICES = {
        EsxHost.ESXI_HARDWARE_SPOTTY1: [
            'medium',
            'large'
        ],
        EsxHost.ESXI_HARDWARE_MEMORY1: [
            'medium',
            'large',
            'xlarge'
        ]
    }

    VERSION_14_04 = '14.04'
    VERSION_CHOICES = (
        (VERSION_14_04, VERSION_14_04),
    )
    DEFAULT_VERSION = VERSION_14_04

    KERNEL_3_13 = '3.13'
    KERNEL_4_13 = '4.13'

    KERNEL_VERSION_CHOICES = (
        (KERNEL_3_13, KERNEL_3_13),
        (KERNEL_4_13, KERNEL_4_13)
    )
    DEFAULT_KERNEL_VERSION = KERNEL_4_13

    DISK_SIZE_32 = 32
    DISK_SIZE_64 = 64
    DISK_SIZE_128 = 128
    DISK_SIZE_256 = 256

    DISK_SIZE_CHOICES = (
        (DISK_SIZE_32, DISK_SIZE_32),
        (DISK_SIZE_64, DISK_SIZE_64),
        (DISK_SIZE_128, DISK_SIZE_128),
        (DISK_SIZE_256, DISK_SIZE_256)
    )
    DEFAULT_DISK_SIZE = DISK_SIZE_32

    # Amount of memory in root disk of AMI
    ROOT_DISK_SIZE_5GB = 5
    ROOT_DISK_SIZE_10GB = 10
    ROOT_DISK_SIZE_25GB = 25
    ROOT_DISK_SIZE_100GB = 100

    ROOT_DISK_SIZE_CHOICES = (
        (ROOT_DISK_SIZE_5GB, ROOT_DISK_SIZE_5GB),
        (ROOT_DISK_SIZE_10GB, ROOT_DISK_SIZE_10GB),
        (ROOT_DISK_SIZE_25GB, ROOT_DISK_SIZE_25GB),
        (ROOT_DISK_SIZE_100GB, ROOT_DISK_SIZE_100GB)
    )
    DEFAULT_ROOT_DISK_SIZE = ROOT_DISK_SIZE_5GB

    kernel_version = models.CharField(
        max_length=16,
        blank=False,
        choices=KERNEL_VERSION_CHOICES,
        help_text='Kernel version, one of %s'
                  % repr([choice[0] for choice in KERNEL_VERSION_CHOICES]),
        default=DEFAULT_KERNEL_VERSION
    )

    root_disk_size = models.IntegerField(
        choices=ROOT_DISK_SIZE_CHOICES,
        help_text='Root disk size in GB, one of %s'
                  % repr([choice[0] for choice in ROOT_DISK_SIZE_CHOICES]),
        default=DEFAULT_ROOT_DISK_SIZE
    )

    disk_size = models.IntegerField(
        choices=DISK_SIZE_CHOICES,
        help_text='Disk size in GB, one of %s'
                  % repr([choice[0] for choice in DISK_SIZE_CHOICES]),
        default=DEFAULT_DISK_SIZE
    )

    version = models.CharField(
        max_length=16,
        blank=False,
        choices=VERSION_CHOICES,
        help_text='Version, one of %s'
                  % repr([choice[0] for choice in VERSION_CHOICES]),
        default=DEFAULT_VERSION
    )

    model = models.CharField(
        max_length=64,
        blank=False,
        default=DEFAULT_MODEL)

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this UbuntuMachine.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this UbuntuMachine.')

    time_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_available_models(cls):
        available_models = []
        for typ, shapes in cls.VSPHERE_MODEL_CHOICES.items():
            for shape in shapes:
                model = 'vsphere-%s.%s' % (typ, shape)
                available_models.append(model)
        available_models.extend(cls.AWS_MODEL_CHOICES)
        return available_models

    @classmethod
    def get_available_root_sizes(cls):
        available_sizes = [choice[0] for choice in cls.ROOT_DISK_SIZE_CHOICES]
        return available_sizes

    @classmethod
    def get_available_kernel_versions(cls):
        available_versions = [choice[0] for
                              choice in cls.KERNEL_VERSION_CHOICES]
        return available_versions

    @classmethod
    def get_vcpu_and_memory_for_hardware_and_size(cls, hardware, size):
        if hardware not in cls.VSPHERE_MODEL_CHOICES:
            bodega_value_error(log,
                               '%s is not a supported hardware' % hardware)
        if size not in cls.VSPHERE_MODEL_CHOICES[hardware]:
            bodega_value_error(log,
                               '%s is not supported size for hardware %s '
                               'for this item type.'
                               % (size, hardware))
        return EsxHost.VSPHERE_MODELS_MAPPINGS[hardware][size]

    @property
    def _ingredient(self):
        ubuntu_machine_content_type = \
            ContentType.objects.get_for_model(UbuntuMachine)
        held_items = Item.objects.filter(
            held_by_content_type_id=ubuntu_machine_content_type.id,
            held_by_object_id=self.id)

        held_item = held_items.first()
        if held_item is None:
            return None

        if hasattr(held_item, 'ec2instance'):
            return held_item.ec2instance
        elif hasattr(held_item, "vspherevirtualmachine"):
            return held_item.vspherevirtualmachine
        else:
            bodega_value_error(log,
                               'UbuntuMachine instance %s is currently '
                               'holding an unsupported item %s.'
                               % (self, held_item))

    @property
    def name(self):
        ingredient = self._ingredient
        if not ingredient:
            return 'Not associated with an ingredient'
        return ingredient._name

    @property
    def ipv4(self):
        if Item.STATE_DESTROYED == self.state:
            return 'Item has been destroyed and has no IP Address'

        ingredient = self._ingredient
        if not ingredient:
            bodega_error(
                log,
                '%s is not currently tied to any ingredient.' % (self))

        if isinstance(ingredient, Ec2Instance):
            try:
                instance_ip = get_ec2_instance_private_ip(ingredient)
            except:
                log.warning('Could not get IP Address for %s but it is '
                            'currently in state %s with ingredient %s'
                            % (self, self.state, ingredient), exc_info=True)
                return ('Item is made from Ec2Instance %s but could not get IP'
                        % ingredient)
            return instance_ip
        elif isinstance(ingredient, VSphereVirtualMachine):
            try:
                instance_ip = get_virtual_machine_ipv4_address(ingredient)
            except:
                log.warning('Could not get IP Address for %s but it is '
                            'currently in state %s with ingredient %s'
                            % (self, self.state, ingredient), exc_info=True)
                return ('Item is made from VSphereVirtualMachine %s but '
                        'could not get IP.' % ingredient)
            return instance_ip

        return 'Could not retrieve IP address for this Item'

    @property
    def username(self):
        return 'ubuntu'

    @property
    def password(self):
        return 'qwerty'

    @property
    def item_destroyer(self):
        ingredient = self._ingredient
        if ingredient is None:
            log.warning('%s has no ingredient associated with it. Item will '
                        'be marked as destroyed but we may have leaked the '
                        'ingredient.'
                        % (self))
            return None
        elif ingredient.state == Item.STATE_DESTROYED:
            log.debug('%s has an ingredient %s that was marked as %s.'
                      % (self, ingredient, Item.STATE_DESTROYED))
            return None
        elif isinstance(ingredient, Ec2Instance):
            log.debug('%s has an Ec2Instance ingredient so use %s to destroy '
                      'it. ' % (self, DestroyEc2InstanceTask))
            return DestroyEc2InstanceTask.si(ingredient.sid)
        elif isinstance(ingredient, VSphereVirtualMachine):
            log.debug('%s has an VSphereVirtualMachine ingredient so use %s '
                      'to destroy it. '
                      % (self, DestroyVSphereVirtualMachineTask))
            return DestroyVSphereVirtualMachineTask.si(ingredient.sid)
        else:
            error_msg = ('No item_destroyer for %s with ingredient %s'
                         % (self, ingredient))
            bodega_error(log, error_msg)


class IpAddress(Item):
    """A validated, usable Ip Address."""

    def __str_additional_info_nvps__(self):
        """Get additional name-value pairs for the string representation."""
        return [
            ('ip', self.ip)
        ]

    ip = models.CharField(
        max_length=15,
        blank=False,
        unique=True,
        help_text='The IPv4 address')

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this IpAddress.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this IpAddress.')

    @property
    def name(self):
        return self.ip
