"""Trigger tasks in response to signals.

This is where most of our root tasks should be triggered so that we are a
primarily event-driven and responsive system. Unlike scheduling tasks
periodically, we don't have a major tradeoff between satisfying user requests
quickly and spamming our logs when there's usually nothing to process. Unlike
large tasks or tasks that directly trigger each other, we quickly adapt to
changing situations such as new user requests or crashes / hardware failures
without wasting much work or having tasks queued for a long time.
"""
import sys

from bodega_core.models import Item, Order, OrderUpdate, Tab
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from rkelery import Group
from .tasks import (
    FulfillOpenOrdersTask, ProcessItemCleanupTask,
    SendOrderUpdateNotificationsTask)

# Detect whether we're running unit tests using technique suggested at
# http://stackoverflow.com/questions/6957016/detect-django-testing-mode
_running_unit_tests = 'test' in sys.argv


@receiver(post_save, sender=OrderUpdate)
def on_order_update_saved(sender, instance, created, *args, **kwargs):
    if _running_unit_tests:
        return

    # This function triggers each time an OrderUpdate is saved, whether
    # we are creating a new object or updating a new object
    # The created field is automatically set to True if we are creating
    # a new object. We want to send a slack notice only if we are
    # creating a new OrderUpdate
    if not created:
        return

    SendOrderUpdateNotificationsTask.delay(order_update_sid=instance.sid)

    if instance.items_delta:
        FulfillOpenOrdersTask.delay()
    elif instance.new_status == Order.STATUS_CLOSED:
        signatures = [ProcessItemCleanupTask.si(item.sid)
                      for item in instance.order.fulfilled_items.values()]
        Group(signatures).delay()


@receiver(post_save)
def on_item_saved(sender, instance, created, *args, **kwargs):
    if _running_unit_tests:
        return

    if not(issubclass(sender, Item)):
        return

    if instance.held_by is None and instance.state != Item.STATE_DESTROYED:
        FulfillOpenOrdersTask.delay()


@receiver(post_save, sender=User)
def on_user_saved(sender, instance, created, *args, **kwargs):
    """A receiver to create a new tab for each new user."""
    if not created:
        return

    Tab.objects.create(limit=Tab.DEFAULT_LIMIT, owner=instance)
