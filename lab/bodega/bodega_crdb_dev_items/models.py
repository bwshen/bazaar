"""Models representing Bodega generic items."""
import logging
from bodega_aws.models import AwsFarm, Ec2Instance
from bodega_aws.tasks import DestroyEc2InstanceTask
from bodega_aws.utils import get_ec2_instance_private_ip
from bodega_core.exceptions import bodega_error, bodega_value_error
from bodega_core.models import Item
from django.contrib.contenttypes.models import ContentType
from django.db import models

log = logging.getLogger(__name__)


class CockroachDBDepsMachine(Item):
    """
    CockroachDBDepsMachine.

    A machine with Ubuntu Linux distro and CockroachDB
    dependencies (git, docker, go) installed on it.
    """

    AWS_MODEL_CHOICES = [
        AwsFarm.MODEL_AWS_M4_LARGE,
        AwsFarm.MODEL_AWS_M4_XLARGE,
        AwsFarm.MODEL_AWS_M4_2XLARGE,
        AwsFarm.MODEL_AWS_T2_LARGE
    ]
    DEFAULT_MODEL = AwsFarm.MODEL_AWS_M4_LARGE

    VERSION_14_04 = '14.04'
    VERSION_CHOICES = (
        (VERSION_14_04, VERSION_14_04),
    )
    DEFAULT_VERSION = VERSION_14_04

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

    DEFAULT_IMAGE_VERSION = 'cockroachdb_deps_machine_base_image'
    image_version = models.CharField(
        max_length=64,
        blank=True,
        default=DEFAULT_IMAGE_VERSION,
        help_text='Version of the image to build '
                  'cockroachdb_deps_machine with.'
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
        help_text='The location of this CockroachDBDepsMachine.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this CockroachDBDepsMachine.')

    time_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_available_models(cls):
        available_models = []
        available_models.extend(cls.AWS_MODEL_CHOICES)
        return available_models

    @property
    def _ingredient(self):
        crdb_deps_machine_content_type = \
            ContentType.objects.get_for_model(CockroachDBDepsMachine)
        held_items = Item.objects.filter(
            held_by_content_type_id=crdb_deps_machine_content_type.id,
            held_by_object_id=self.id)

        held_item = held_items.first()
        if held_item is None:
            return None

        if hasattr(held_item, 'ec2instance'):
            return held_item.ec2instance
        else:
            bodega_value_error(log,
                               'CockroachDBDepsMachine instance %s '
                               'is currently '
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
        else:
            error_msg = ('No item_destroyer for %s with ingredient %s'
                         % (self, ingredient))
            bodega_error(log, error_msg)
