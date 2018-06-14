"""Global Bodega tasks."""
import logging
import os
import sys

SDMAIN_ROOT = os.path.abspath('/opt/sdmain')  # noqa
sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'py', 'communication'))  # noqa
from rklab_slacker import RkSlacker  # noqa

import rkelery.models
from bodega_core.cleanup import CleanupManager
from bodega_core.ejection import EjectionManager
from bodega_core.fulfillment import FulfillmentManager
from bodega_core.models import Item, Order, OrderUpdate
from bodega_core.tasks import GlobalTask, SingleItemTask
from django.conf import settings
from requests.exceptions import HTTPError
from rkelery import Group, register_task, states, Task
from rkelery.utils import json_dump
from .item_types import item_tools
from .utils import absolute_reverse, get_url_and_display_name

log = logging.getLogger(__name__)

rkslacker = RkSlacker(bot_token=getattr(settings, 'SLACK_TOKEN', None))
DEFAULT_NOTIFICATION_RETRY_SECONDS = 1
MAX_EXPONENTIAL_BACKOFF_SECONDS = 60
MAX_NOTIFICATION_RETRY_ATTEMPTS = 10


# TODO(kenny) This function, and in general the mixture of task
# manipulation and order fulfillment logic, is kind of ugly. As we get
# more experience working with tasks, should come up with cleaner ways
# to keep core logic separate from tasks.
def get_order_fulfillers(order_sid):
    return rkelery.models.Task.objects.filter(
        task=FulfillOrderTask.name,
        args_json__contains=json_dump(order_sid),
        task_result__status__in=(
            states.PRE_RUNNING_STATES.union(frozenset(states.RUNNING))))


@register_task
class FulfillOpenOrdersTask(GlobalTask):
    @classmethod
    def get_summary(cls, *args, **kwargs):
        return 'Fulfill open orders.'

    def run(self, *args, **kwargs):
        fulfillment_manager = FulfillmentManager(item_tools)
        signatures = fulfillment_manager.fulfill_open_orders(
            get_order_fulfillers,
            FulfillOrderTask.si,
            SetItemToMaintenanceTask.si,
            self.model_instance)
        Group(signatures).delay()


@register_task
class FulfillOrderTask(Task):
    @classmethod
    def get_summary(cls, order_sid, selected_item_sids):
        item_sids = [str(sid) for sid in selected_item_sids.values()]
        return (
            'Fulfill order %s using items %s.' %
            (repr(str(order_sid)), repr(item_sids)))

    def get_blockage_cause(self, order_sid, selected_item_sids):
        # TODO: https://rubrik.atlassian.net/browse/INFRA-1634
        # The task needs to make sure it is holding the selected items
        # before it can proceed. This is our way of simulating a lock on the
        # item but is still imperfect as different tasks can still manipulate
        # the item at the same time. We'll need to explore a more robust way
        # of ensuring only one Task at a time can manipulate an item but try
        # to avoid actual locks for better responsiveness.
        not_held_item_sids = set()
        for item_sid in selected_item_sids.values():
            item = Item.objects.get(sid=item_sid)
            if item.held_by != self.model_instance:
                not_held_item_sids.add(item_sid)
                if item.held_by is None:
                    item.held_by = self.model_instance
                    item.save()

        if len(not_held_item_sids) == 0:
            return None
        return 'This task does not hold items %s.' % repr(not_held_item_sids)

    def run(self, order_sid, selected_item_sids):
        fulfillment_manager = FulfillmentManager(item_tools)
        order = Order.objects.get(sid=order_sid)

        selected_items = {nickname: Item.objects.get(sid=item_sid)
                          for (nickname, item_sid)
                          in selected_item_sids.items()}
        usable_items = fulfillment_manager.fulfill_order(
            order, selected_items, self.model_instance)

        # Free any usable but not used items that fulfill_order returned.
        # This would happen if a taste test failed on a subset of the selected
        # items but the rest were okay. Let them be used for other orders.
        for item in usable_items:
            item.held_by = None
            item.save()


@register_task
class SetItemToMaintenanceTask(SingleItemTask):
    @classmethod
    def get_summary(cls, item_sid):
        return 'Set state of %s to %s' % (repr(item_sid),
                                          repr(Item.STATE_MAINTENANCE))

    def run(self, item_sid):
        item = Item.objects.get(sid=item_sid)
        item.state = Item.STATE_MAINTENANCE
        item.save()


@register_task
class ProcessItemsCleanupTask(GlobalTask):
    @classmethod
    def get_summary(cls):
        return 'Initiate cleanup process for all items.'

    def run(self):
        cleanup_manager = CleanupManager(item_tools)
        signatures = cleanup_manager.process_items_cleanup(
            HandleItemCleanupTask.si)
        Group(signatures).delay()


@register_task
class ProcessItemCleanupTask(SingleItemTask):
    @classmethod
    def get_summary(cls, item_sid):
        return 'Initiate cleanup process for %s.' % repr(str(item_sid))

    def run(self, item_sid):
        cleanup_manager = CleanupManager(item_tools)
        signature = cleanup_manager.process_item_cleanup(
            Item.objects.get(sid=item_sid),
            HandleItemCleanupTask.si)
        signature.delay()


@register_task
class HandleItemCleanupTask(SingleItemTask):
    @classmethod
    def get_summary(cls, item_sid):
        return 'Handle cleanup of item %s.' % repr(str(item_sid))

    def run(self, item_sid):
        cleanup_manager = CleanupManager(item_tools)
        item = Item.objects.get(sid=item_sid)
        cleanup_manager.handle_item_cleanup(item)


@register_task
class ProcessOrderTimeLimitsTask(GlobalTask):
    @classmethod
    def get_summary(cls):
        return 'Process order time limits.'

    def run(self):
        ejection_manager = EjectionManager(self.model_instance)
        ejection_manager.process_orders_time_limits()


@register_task
class SendOrderUpdateNotificationsTask(Task):
    """Send notifications for an order update.

    Although this task is currently specific to Slack notifications, it's
    named generically and lives here because conceptually it is a top level
    task. In the future we could be adding other notification types
    implemented in their individual apps, and this task would trigger those
    tasks.
    """

    @classmethod
    def get_summary(cls, order_update_sid=None, **kwargs):
        return (
            'Send notifications for order update %s.' %
            repr(str(order_update_sid)))

    def run(self, order_update_sid=None, retry_attempts=0, **kwargs):
        order_update = OrderUpdate.objects.get(sid=order_update_sid)
        order = order_update.order
        msg = self.__get_order_update_slack_message(order_update)

        if order.owner.email == "":
            log.warning("Email of owner (%s) of %s is blank."
                        % (order.owner, order))
            return

        try:
            slackuser = rkslacker.find_user_details_from_email_id(
                order.owner.email)
            slack_handle = rkslacker.find_slack_handle_from_user(slackuser)
            log.info('Sending (%s) to user %s with email %s.'
                     % (repr(msg), repr(slack_handle),
                        repr(order.owner.email)))
            rkslacker.send_message(message=msg,
                                   recipients=[slack_handle])
        except HTTPError as e:
            if e.response.status_code == 429:
                log.warning('Failed to send Slack notice for %s due to rate '
                            'limiting.' % order_update_sid,
                            exc_info=True)
                if retry_attempts > MAX_NOTIFICATION_RETRY_ATTEMPTS:
                    log.info('Exceeded the retry limit of %s so not '
                             'triggering any new tasks.'
                             % MAX_NOTIFICATION_RETRY_ATTEMPTS)
                    raise e
                else:
                    retry_after_secs = int(e.response.headers.get(
                        'Retry-After',
                        DEFAULT_NOTIFICATION_RETRY_SECONDS))
                    countdown = self.__get_countdown_time(retry_after_secs,
                                                          retry_attempts)
                    log.debug('There have been %d retries for sending this '
                              'update which is less than the limit of %d. '
                              'Triggering new task with a delay '
                              'of %d seconds'
                              % (retry_attempts,
                                 MAX_NOTIFICATION_RETRY_ATTEMPTS,
                                 countdown))
                    SendOrderUpdateNotificationsTask.apply_async(
                        kwargs={
                            'order_update_sid': order_update_sid,
                            'retry_attempts': retry_attempts + 1
                        },
                        countdown=countdown)
            # TODO: https://rubrik.atlassian.net/browse/INFRA-2237
            # Since we are not raising an error when we retry, it will look
            # like this task succeeded when it really failed. We should set the
            # state of this task accordingly in this case.

    def __get_order_update_slack_message(self, order_update):
        order = order_update.order
        (creator_url, creator_display_name) = get_url_and_display_name(
            order_update.creator)
        order_update_url = absolute_reverse('orderupdate-detail',
                                            {'sid': order_update.sid})
        order_url = absolute_reverse('order-detail', {'sid': order.sid})

        msg = ('<%s|Order %s> `(%s)` was <%s|updated> by <%s|%s>.\n'
               % (order_url, order.sid, order.status, order_update_url,
                  creator_url, creator_display_name))

        items = order.items
        fulfilled_items = order.fulfilled_items
        msg += ('> %d item(s) in order:\n' % len(items))
        for nickname, item in items.items():
            requirements = ', '.join(['%s=%s' %
                                      (name, value)
                                      for name, value
                                      in item['requirements'].items()])
            if fulfilled_items:
                fulfilled_item = \
                    item_tools.get_specific_item(fulfilled_items[nickname])
                fulfilled_item_str = ('=> `%s`\n' % str(fulfilled_item.name))
            else:
                fulfilled_item_str = '\n'
            item_str = ('>  `%s`: `%s(%s)` %s'
                        % (nickname, item['type'], requirements,
                           fulfilled_item_str))
            msg += item_str
        msg += order_update.comment

        return msg

    def __get_countdown_time(self, retry_after_seconds, retry_attempts):
        exp_backoff_seconds = min(pow(2, retry_attempts),
                                  MAX_EXPONENTIAL_BACKOFF_SECONDS)
        return retry_after_seconds + exp_backoff_seconds
