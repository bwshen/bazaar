"""Item-specific managers."""
import logging
import os
import sys
from datetime import timedelta

SDMAIN_ROOT = os.path.abspath('/opt/sdmain')  # noqa
PY_ROOT = os.path.join(SDMAIN_ROOT, 'src', 'py')  # noqa
sys.path.append(PY_ROOT)  # noqa
import cdm_tivan  # noqa

from bodega_core import ItemManager
from bodega_core.exceptions import bodega_validation_error
from bodega_core.models import Item
from django.contrib.contenttypes.models import ContentType
from rkelery import Group, states
from rkelery.models import Task
from .filters import CdmClusterFilter, CdmNodeFilter
from .models import CdmCluster, CdmNode
from .recipes import CdmClusterRecipe, CdmNodeRecipe
from .tasks import CreateCdmClusterFromAwsTask, CreateCdmNodeFromAwsTask

log = logging.getLogger(__name__)


class CdmNodeManager(ItemManager):

    def __init__(self, **kwargs):
        """Item manager for CdmNode Item."""
        pass

    def get_item_creator(self, requirements):
        return None

    def get_item_recipe(self, requirements):
        return CdmNodeRecipe(requirements)

    def get_item_price(self, requirements):
        """m4.xlarge, Linux, US West (Oregon).

        $0.2 per Hour
        https://aws.amazon.com/ec2/pricing/on-demand/
        """
        return 0.2

    def get_pending_items_queryset(self,
                                   item_queryset):
        acceptable_tasks_qs = Task.objects.filter(
            task=CreateCdmNodeFromAwsTask.name,
            task_result__status__in=states.UNREADY_STATES)
        tasks_content_type = \
            ContentType.objects.get_for_model(Task)

        acceptable_tasks_ids = [task.id for task in acceptable_tasks_qs]
        held_by_task_qs = item_queryset.filter(
            held_by_object_id__in=acceptable_tasks_ids,
            held_by_content_type_id=tasks_content_type)
        return held_by_task_qs

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta(hours=6)

    def get_status(self, cdm_node):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, cdm_node):
        item_destroyer = cdm_node.item_destroyer

        if item_destroyer:
            log.debug('Triggering %s for %s' % (item_destroyer, cdm_node))
            item_destroyer.delay()
        else:
            log.info('%s does not have an item destroyer so mark it as %s.'
                     % (cdm_node, Item.STATE_DESTROYED))
            cdm_node.held_by = None
            cdm_node.state = Item.STATE_DESTROYED
            cdm_node.save()

    def taste_test(self, cdm_node, requirements):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = CdmNodeFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the cdm_node item type.'
                             % field)
                bodega_validation_error(log, error_msg)
            if field == 'model' and \
                    value not in CdmNode.get_available_models():
                error_msg = ('Model "%s" is not valid for the cdm_node '
                             'item_type.'
                             % value)
                bodega_validation_error(log, error_msg)

        if 'artifacts_url' not in item_requirements:
            error_msg = ('Required field "artifacts_url" not specified.'
                         % value)
            bodega_validation_error(log, error_msg)
        else:
            try:
                artifacts_url = item_requirements['artifacts_url']
                cdm_tivan.Artifacts(artifacts_url)
            except Exception as e:
                error_msg = ('Failed to parse artifacts_url from %s with error'
                             ' of %s.' % (item_requirements, str(e)))
                bodega_validation_error(log, error_msg)


class CdmClusterManager(ItemManager):

    def __init__(self, **kwargs):
        """Item manager for CdmCluster Item."""
        pass

    def get_item_creator(self, requirements):
        return None

    def get_item_recipe(self, requirements):
        return CdmClusterRecipe(requirements)

    def get_item_price(self, requirements):
        # TODO: Calculate a realistic price.
        return 1.0

    def get_pending_items_queryset(self,
                                   item_queryset):
        acceptable_tasks_qs = Task.objects.filter(
            task=CreateCdmClusterFromAwsTask.name,
            task_result__status__in=states.UNREADY_STATES)
        tasks_content_type = \
            ContentType.objects.get_for_model(Task)

        acceptable_tasks_ids = [task.id for task in acceptable_tasks_qs]
        held_by_task_qs = item_queryset.filter(
            held_by_object_id__in=acceptable_tasks_ids,
            held_by_content_type_id=tasks_content_type)
        return held_by_task_qs

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta(hours=12)

    def get_status(self, cdm_cluster):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, cdm_cluster):
        item_destroyers = cdm_cluster.item_destroyers

        if len(item_destroyers) > 0:
            log.debug('Triggering %s for %s' % (item_destroyers, cdm_cluster))
            Group(item_destroyers).delay()
        else:
            log.info('%s does not have any item destroyers so mark it as %s.'
                     % (cdm_cluster, Item.STATE_DESTROYED))
            cdm_cluster.held_by = None
            cdm_cluster.state = Item.STATE_DESTROYED
            cdm_cluster.save()

    def taste_test(self, cdm_cluster, requirements):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = CdmClusterFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the cdm_cluster item type.'
                             % field)
                bodega_validation_error(log, error_msg)
            if field == 'model' and \
                    value not in CdmCluster.get_available_models():
                error_msg = ('Model "%s" is not valid for the cdm_cluster '
                             'item type.'
                             % value)
                bodega_validation_error(log, error_msg)
            if field == 'node_count' and \
                    value != 1 and value < 3:
                error_msg = 'Invalid node_count value. Valid values: ' \
                            'node_count = 1 or node_count >= 3'
                bodega_validation_error(log, error_msg)
        if 'artifacts_url' not in item_requirements:
            error_msg = ('Required field "artifacts_url" not specified.'
                         % value)
            bodega_validation_error(log, error_msg)
        else:
            try:
                artifacts_url = item_requirements['artifacts_url']
                cdm_tivan.Artifacts(artifacts_url)
            except Exception as e:
                error_msg = ('Failed to parse artifacts_url from %s with error'
                             ' of %s.' % (item_requirements, str(e)))
                bodega_validation_error(log, error_msg)
