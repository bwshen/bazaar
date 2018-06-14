"""Item-specific managers."""
import logging
from datetime import timedelta

from bodega_core import ItemManager
from bodega_core.exceptions import bodega_validation_error
from bodega_core.models import Item
from django.contrib.contenttypes.models import ContentType
from rkelery import states
from rkelery.models import Task
from .filters import CockroachDBDepsMachineFilter
from .models import CockroachDBDepsMachine
from .recipes import CockroachDBDepsMachineRecipe
from .tasks import CreateCockroachDBDepsMachineFromAwsTask

log = logging.getLogger(__name__)


class CockroachDBDepsMachineManager(ItemManager):

    def __init__(self, **kwargs):
        """Item manager for CockroachDBDepsMachine Item."""
        pass

    def get_item_creator(self, requirements):
        return None

    def get_item_price(self, requirements):
        """m4.large, Linux, US West (Oregon).

        $0.1 per Hour
        https://aws.amazon.com/ec2/pricing/on-demand/
        """
        return 1.0

    def get_item_recipe(self, requirements):
        return CockroachDBDepsMachineRecipe(requirements)

    def get_pending_items_queryset(self,
                                   item_queryset):
        task_names = [CreateCockroachDBDepsMachineFromAwsTask.name]
        acceptable_tasks_qs = Task.objects.filter(
            task__in=task_names,
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
        return timedelta(hours=8)

    def get_status(self, deps_machine):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, deps_machine):
        item_destroyer = deps_machine.item_destroyer

        if item_destroyer:
            log.debug('Triggering %s for %s'
                      % (item_destroyer, deps_machine))
            item_destroyer.delay()
        else:
            log.info('%s does not have an item destroyer so mark it as %s.'
                     % (deps_machine, Item.STATE_DESTROYED))
            deps_machine.held_by = None
            deps_machine.state = Item.STATE_DESTROYED
            deps_machine.save()

    def taste_test(self, crdb_item, requirements):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = CockroachDBDepsMachineFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the cockroachdb_deps_machine item type.'
                             % field)
                bodega_validation_error(log, error_msg)
            if field == 'model' and \
               (value not in CockroachDBDepsMachine.get_available_models()):
                error_msg = ('Model "%s" is not valid for '
                             'the cockroachdb_deps_machine item type.'
                             % value)
                bodega_validation_error(log, error_msg)
