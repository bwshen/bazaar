"""Test models."""
import logging

from bodega_test_items.models import BasicItem
from django.contrib.auth.models import User
from django.test import TestCase
from rkelery import states
from rkelery.models import Task
from .models import Order

log = logging.getLogger(__name__)

CREATE_BASIC_ITEM_TASK = 'CreateBasicItem'


class ItemTestCase(TestCase):
    def test_held_by_object_in_final_state(self):
        # Create the task and item handles that we'll consider to be the
        # source of truth. All writes go through these handles. Start in a
        # state where the item is held by a running task that's still creating
        # the item.
        task = Task.objects.create(
            task=CREATE_BASIC_ITEM_TASK,
            args=[],
            kwargs={})
        task.task_result.status = states.RUNNING
        task.task_result.save()
        item = BasicItem.objects.create(held_by_object=task)

        # Simulate another task such as the cleanup processor reading the item
        # while it's still held by the first task.
        initial_item = BasicItem.objects.get(sid=item.sid)

        # Simulate the task holding the item completing and making the item
        # available for fulfilling orders.
        item.held_by = None
        item.save()
        task.task_result.status = states.SUCCESS
        task.task_result.save()

        # Simulate the item being assigned to fulfill an order.
        user = User.objects.create_user(username='User')
        tab = user.tabs.get()
        order = Order.objects.create(
            status=Order.STATUS_FULFILLED,
            owner=user,
            tab=tab)
        item.held_by = order
        item.save()

        # Simulate another task such as a later attempt of the cleanup
        # processor reading the item in its current fulfilled state.
        current_item = BasicItem.objects.get(sid=item.sid)

        # The initial cleanup attempt sees a stale item that's apparently still
        # held by the task which is now complete. This is the case we hit in
        # https://rubrik.atlassian.net/browse/INFRA-860 and we should not
        # consider the item to be held by an object in its final state because
        # it's now actually held by an order.
        self.assertFalse(initial_item.held_by_object_in_final_state)

        # A current cleanup attempt sees the item as it truly is: held by a
        # fulfilled order, which is not a final state.
        self.assertFalse(current_item.held_by_object_in_final_state)

        # Simulate the order being closed.
        order.status = Order.STATUS_CLOSED
        order.save()

        # Now a cleanup attempt on the latest item sees it held by a closed
        # order, which is a final state.
        final_item = BasicItem.objects.get(sid=item.sid)
        self.assertTrue(final_item.held_by_object_in_final_state)
