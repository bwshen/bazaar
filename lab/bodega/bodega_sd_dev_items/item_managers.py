"""Item-specific cleanup managers."""
import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType

# flake8: noqa I100 # Turn off broken import ordering check as flake8 have bug
from bodega_core import ItemManager
from bodega_core.exceptions import bodega_validation_error
from bodega_core.models import Item
from bodega_utils.ssh import check_ssh_availability
from rkelery import states
from rkelery.models import Task
from .filters import SdDevMachineFilter
from .models import SdDevMachine
from .recipes import SdDevMachineRecipe
from .tasks import CreateSdDevMachineFromAwsTask
from .tasks import CreateSdDevMachineFromKubernetesTask

log = logging.getLogger(__name__)


class SdDevMachineManager(ItemManager):

    def __init__(self, **kwargs):
        """Initialize SdDevMachineManager."""
        pass

    def get_item_recipe(self, requirements):
        return SdDevMachineRecipe(requirements)

    def get_item_price(self, requirements):
        # Dev machine on Kubernetes occupies ~0.1 Microcloud. We round up
        # the final price to $0.01. INFRA-1074.
        return 0.01

    def get_pending_items_queryset(self,
                                   item_queryset):
        acceptable_tasks_qs = Task.objects.filter(
            task__in=[
                CreateSdDevMachineFromKubernetesTask.name,
                CreateSdDevMachineFromAwsTask.name
            ],
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

    def get_status(self, sd_dev_machine):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, sd_dev_machine):
        item_destroyer = sd_dev_machine.item_destroyer

        if item_destroyer:
            log.info('Triggering %s for %s' % (item_destroyer, sd_dev_machine))
            item_destroyer.delay()
        else:
            log.info('%s does not have an item destroyer so mark it as %s.'
                     % (sd_dev_machine, Item.STATE_DESTROYED))
            sd_dev_machine.held_by = None
            sd_dev_machine.state = Item.STATE_DESTROYED
            sd_dev_machine.save()

    def taste_test(self, sd_dev_machine, requirements):
        log.debug('Taste testing %s on IP %s to make sure SSH is usable.'
                  % (sd_dev_machine, sd_dev_machine.ip_address))
        if check_ssh_availability(sd_dev_machine.ip_address,
                                  sd_dev_machine.username,
                                  sd_dev_machine.password,
                                  retries=1):
            return True
        else:
            log.info('Unable to SSH into %s with username %s'
                     % (sd_dev_machine.ip_address, sd_dev_machine.username))

        return False

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = SdDevMachineFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the sd_dev_machine item type.'
                             % field)
                bodega_validation_error(log, error_msg)
            if field == 'model' and \
                    value not in SdDevMachine.get_available_models():
                error_msg = ('Model "%s" is not valid for sd_dev_machine '
                             'item type.'
                             % value)
                bodega_validation_error(log, error_msg)
