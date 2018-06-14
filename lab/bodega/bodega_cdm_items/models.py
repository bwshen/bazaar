"""Models representing Bodega CDM items."""
import logging
from bodega_aws.models import AwsFarm, Ec2Instance
from bodega_aws.tasks import DestroyEc2InstanceTask
from bodega_aws.utils import get_ec2_instance_private_ip
from bodega_core.exceptions import bodega_error, bodega_value_error
from bodega_core.models import Item
from django.contrib.contenttypes.models import ContentType
from django.db import models
from .utils import (get_dns_nameservers,
                    get_dns_search_domains,
                    get_management_gateway,
                    get_management_subnet_mask,
                    get_ntp_servers)

log = logging.getLogger(__name__)


class CdmNode(Item):
    """A CdmNode with a specific version of software installed."""

    AWS_MODEL_CHOICES = [
        AwsFarm.MODEL_AWS_M4_XLARGE,
    ]
    DEFAULT_MODEL = AwsFarm.MODEL_AWS_M4_XLARGE

    model = models.CharField(
        max_length=16,
        blank=False)

    artifacts_url = models.CharField(
        default="",
        blank=True,
        max_length=255,
        help_text=('Tivan style artifacts metadata containing information '
                   'about the build to install on this CdmNode.'))

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this CdmNode.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this CdmNode.')

    time_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_available_models(cls):
        available_models = []
        available_models.extend(cls.AWS_MODEL_CHOICES)
        return available_models

    @property
    def _ingredient(self):
        cdm_node_content_type = \
            ContentType.objects.get_for_model(CdmNode)
        held_items = Item.objects.filter(
            held_by_content_type_id=cdm_node_content_type.id,
            held_by_object_id=self.id)

        held_item = held_items.first()
        if held_item is None:
            return None

        if hasattr(held_item, 'ec2instance'):
            return held_item.ec2instance
        else:
            bodega_value_error(log,
                               'CdmNode instance %s is currently '
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
                instance_ip = \
                    get_ec2_instance_private_ip(ingredient)
            except:
                log.warning('Could not get IP Address for %s but it is '
                            'currently in state %s with ingredient %s'
                            % (self, self.state, ingredient), exc_info=True)
                return ('Item is made from Ec2Instance %s but could not get IP'
                        % ingredient)
            return instance_ip

        return 'Could not retrieve IP address for this Item'

    @property
    def gateway(self):
        if Item.STATE_DESTROYED == self.state:
            return 'Item has been destroyed and has no gateway'

        ingredient = self._ingredient
        if not ingredient:
            bodega_error(
                log,
                '%s is not currently tied to any ingredient.' % (self))

        try:
            gateway = get_management_gateway(self)
        except:
            log.warning('Could not get gateway for %s but it is '
                        'currently in state %s with ingredient %s'
                        % (self, self.state, ingredient), exc_info=True)
            return ('Item is made from Ec2Instance %s but couldnt get gateway'
                    % ingredient)
        return gateway

    @property
    def netmask(self):
        if Item.STATE_DESTROYED == self.state:
            return 'Item has been destroyed and has no netmask'

        ingredient = self._ingredient
        if not ingredient:
            bodega_error(
                log,
                '%s is not currently tied to any ingredient.' % (self))

        try:
            netmask = get_management_subnet_mask(self)
        except:
            log.warning('Could not get netmask for %s but it is '
                        'currently in state %s with ingredient %s'
                        % (self, self.state, ingredient), exc_info=True)
            return ('Item is made from Ec2Instance %s but couldnt get netmask'
                    % ingredient)
        return netmask

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


class CdmCluster(Item):
    """A CdmCluster containing N nodes with a specified version."""

    AWS_MODEL_CHOICES = [
        AwsFarm.MODEL_AWS_M4_XLARGE,
    ]
    DEFAULT_MODEL = AwsFarm.MODEL_AWS_M4_XLARGE
    DEFAULT_NODE_COUNT = 3

    artifacts_url = models.CharField(
        default="",
        blank=True,
        max_length=255,
        help_text=('Tivan style artifacts metadata containing information '
                   'about the build to install and bootstrap on this '
                   'CdmCluster.'))

    node_count = models.IntegerField(
        blank=False,
        default=DEFAULT_NODE_COUNT,
        help_text='Number of nodes in this CdmCluster')

    model = models.CharField(
        max_length=16,
        blank=False)

    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this CdmCluster.')

    network = models.ForeignKey(
        'bodega_core.Network', on_delete=models.CASCADE,
        help_text='The network of this CdmCluster.')

    time_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_available_models(cls):
        available_models = []
        available_models.extend(cls.AWS_MODEL_CHOICES)
        return available_models

    @property
    def name(self):
        return 'cdm-cluster-%s' % self.sid

    @property
    def nodes(self):
        cdm_cluster_content_type = \
            ContentType.objects.get_for_model(CdmCluster)
        held_items = Item.objects.filter(
            held_by_content_type_id=cdm_cluster_content_type.id,
            held_by_object_id=self.id)

        cdm_nodes = []
        for held_item in held_items:
            if hasattr(held_item, 'cdmnode'):
                cdm_nodes.append(held_item.cdmnode)
            else:
                bodega_value_error(log,
                                   'CdmCluster instance %s is currently '
                                   'holding an unsupported item %s.'
                                   % (self, held_item))

        if len(cdm_nodes) != self.node_count:
            log.warning(
                'Expected %s to hold %d CdmNodes but found %d. Currently '
                'holding nodes: %s' %
                (self,
                 self.node_count,
                 len(cdm_nodes),
                 ". ".join(['%s' % node for node in cdm_nodes])))
        return cdm_nodes

    @property
    def ntp_servers(self):
        return get_ntp_servers(self)

    @property
    def dns_search_domains(self):
        return get_dns_search_domains(self)

    @property
    def dns_nameservers(self):
        return get_dns_nameservers(self)

    @property
    def item_destroyers(self):
        log.debug('Checking if all nodes for %s have been cleaned up.'
                  % self)
        cdm_node_destroyers = []

        for node in self.nodes:
            node_item_destroyer = node.item_destroyer
            if node_item_destroyer is None:
                log.debug('%s has no item_destroyer so marked it as %s'
                          % (node, Item.STATE_DESTROYED))
                node.state = Item.STATE_DESTROYED
                node.save()
            else:
                log.debug('%s has an item_destroyer of %s.'
                          % (node, node_item_destroyer))
                cdm_node_destroyers.append(node_item_destroyer)
        return cdm_node_destroyers
