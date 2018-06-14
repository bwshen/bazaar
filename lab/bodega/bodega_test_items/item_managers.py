"""Test item managers."""
from datetime import timedelta
from bodega_core import ItemManager
from django.contrib.contenttypes.models import ContentType
from rkelery import states
from rkelery.models import Task
from .recipes import BasicItemRecipe, ComplexItemRecipe

CREATE_BASIC_ITEM_TASK = 'CreateBasicItem'
CREATE_COMPLEX_ITEM_TASK = 'CreateComplexItem'


class BasicItemManager(ItemManager):
    def __init__(self):
        pass

    def get_item_recipe(self, requirements):
        return BasicItemRecipe(requirements)

    def get_item_price(self, requirements):
        # Simple price of 1.0 to allow easy calculations in unit tests.
        return 1.0

    def get_pending_items_queryset(self,
                                   item_queryset):
        acceptable_tasks_qs = Task.objects.filter(
            task=CREATE_BASIC_ITEM_TASK,
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
        return timedelta(hours=1)

    def get_status(self, basic_item):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, basic_item):
        basic_item.held_by = None
        basic_item.save()

    def taste_test(self, basic_item):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        return


class ComplexItemManager(ItemManager):
    def __init__(self):
        pass

    def get_item_recipe(self, requirements):
        return ComplexItemRecipe(requirements)

    def get_item_price(self, requirements):
        # Simple price of 1.0 to allow easy calculations in unit tests.
        return 1.0

    def get_pending_items_queryset(self,
                                   item_queryset):
        acceptable_tasks_qs = Task.objects.filter(
            task=CREATE_COMPLEX_ITEM_TASK,
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
        return timedelta(hours=1)

    def get_status(self, complex_item):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, complex_item):
        complex_item.held_by = None
        complex_item.save()

    def taste_test(self, complex_item):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        return
