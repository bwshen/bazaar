"""Models representing Bodega Sd Dev items."""
import logging

from django.contrib.contenttypes.models import ContentType
from django.db import models

# flake8: noqa I100 # Turn off broken import ordering check as flake8 have bug
from bodega_aws.models import AwsFarm, Ec2Instance
from bodega_aws.tasks import DestroyEc2InstanceTask
from bodega_aws.utils import get_ec2_instance_private_ip
from bodega_core.exceptions import bodega_error
from bodega_core.exceptions import bodega_value_error
from bodega_core.models import Item
from bodega_kubernetes.models import KubernetesPod
from bodega_kubernetes.tasks import DestroyKubernetesPodTask
from bodega_kubernetes.utils import get_kubernetes_pod_ip

log = logging.getLogger(__name__)


class SdDevMachine(Item):
    """A dev machine Docker container bootstrapped to the specified version."""

    MODEL_KUBERNETES = 'kubernetes'
    AWS_MODEL_CHOICES = [
        AwsFarm.MODEL_AWS_M4_LARGE,
        AwsFarm.MODEL_AWS_M4_2XLARGE
    ]
    DEFAULT_MODEL = MODEL_KUBERNETES

    model = models.CharField(
        max_length=16,
        blank=False)

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this SdDevMachine')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this SdDevMachine.')

    version = models.CharField(
        default="",
        blank=True,
        max_length=64,
        help_text=('Contents of .sd_dev_bootstrap_hash to determine '
                   'bootstrap version.'))

    privileged_mode = models.BooleanField(
        default=False,
        help_text='Has full root/kernel capabilities.')

    time_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_available_models(cls):
        available_models = []
        available_models.extend(cls.AWS_MODEL_CHOICES)
        available_models.append(cls.MODEL_KUBERNETES)
        return available_models

    @property
    def _ingredient(self):
        sd_dev_machine_content_type = \
            ContentType.objects.get_for_model(SdDevMachine)
        held_items = Item.objects.filter(
            held_by_content_type_id=sd_dev_machine_content_type.id,
            held_by_object_id=self.id)

        held_item = held_items.first()
        if held_item is None:
            return None

        if hasattr(held_item, 'kubernetespod'):
            return held_item.kubernetespod
        elif hasattr(held_item, 'ec2instance'):
            return held_item.ec2instance
        else:
            bodega_value_error(log,
                               'SdDevMachine instance %s is currently '
                               'holding an unsupported item %s.'
                               % (self, held_item))

    @property
    def name(self):
        ingredient = self._ingredient
        if not ingredient:
            return "Not associated with an ingredient"
        return ingredient._name

    @property
    def ip_address(self):
        ingredient = self._ingredient
        if Item.STATE_DESTROYED == self.state:
            return 'Item has been destroyed and has no IP Address'
        elif ingredient is None:
            return 'Item has no ingredient associated with it'
        elif isinstance(ingredient, Ec2Instance):
            try:
                return get_ec2_instance_private_ip(self._ingredient)
            except:
                log.warning(
                    'Could not get IP address for %s but it is currently '
                    'in state %s with ingredient %s'
                    % (self, self.state, ingredient), exc_info=True)
                return 'Could not retrieve IP address for this Item'
        elif isinstance(ingredient, KubernetesPod):
            try:
                return get_kubernetes_pod_ip(self._ingredient)
            except:
                log.warning(
                    'Could not get IP Address for %s but it is currently '
                    'in state %s with ingredient %s'
                    % (self, self.state, ingredient), exc_info=True)
                return 'Could not retrieve IP address for this Item'
        else:
            bodega_value_error(log,
                               'Unrecognized ingredient %s for SdDevMachine' %
                               repr(self._ingredient))

    @property
    def username(self):
        """TODO: Use a more secure method for accessing each SdDevMachine."""
        return 'ubuntu'

    @property
    def password(self):
        """TODO: Use a more secure method for accessing each SdDevMachine."""
        return 'qwerty'

    @property
    def item_destroyer(self):
        ingredient = self._ingredient
        if ingredient is None:
            log.warning('%s has no ingredient associated with it. Item will '
                        'be marked as destroyed but we may have leaked the '
                        'ingredient.'
                        % self)
            return None
        elif ingredient.state == Item.STATE_DESTROYED:
            log.debug('%s has an ingredient %s that was marked as %s.'
                      % (self, ingredient, Item.STATE_DESTROYED))
            return None
        elif isinstance(ingredient, KubernetesPod):
            log.info('%s has a KubernetesPod ingredient so use %s to destroy '
                     'it.' % (self.name, DestroyKubernetesPodTask))
            return DestroyKubernetesPodTask.si(ingredient.sid)
        elif isinstance(ingredient, Ec2Instance):
            log.info('%s has a Ec2Instance ingredient so use %s to destroy '
                     'it.' % (self.name, DestroyEc2InstanceTask))
            return DestroyEc2InstanceTask.si(ingredient.sid)
        else:
            error_msg = ('No item_destroyer for %s with ingredient %s'
                         % (self, ingredient))
            bodega_error(log, error_msg)
