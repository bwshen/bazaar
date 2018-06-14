"""Manages cleanup of all items in Bodega."""

import logging
from datetime import datetime
from pytz import utc

from rkelery import states
from rkelery.models import Task
from .models import Item, Order

log = logging.getLogger(__name__)


class CleanupManager(object):
    def __init__(self, item_tools):
        self.item_tools = item_tools

    def process_items_cleanup(self, create_item_cleaner):
        existing_items = Item.objects.exclude(state=Item.STATE_DESTROYED)
        held_items = existing_items.exclude(held_by_object_id=None)
        cleaners = []
        for item in held_items:
            log.debug('Attempting cleanup on %s' % item)
            cleaner = self.process_item_cleanup(item, create_item_cleaner)
            if cleaner is not None:
                cleaners.append(cleaner)

        not_held_items = existing_items.filter(held_by_object_id=None,
                                               state=Item.STATE_ACTIVE)

        for item in not_held_items:
            log.debug('Checking if %s has passed its shelf life.' % item)
            cleaner = self.process_item_shelf_life(item, create_item_cleaner)
            if cleaner is not None:
                cleaners.append(cleaner)

        return cleaners

    def process_item_cleanup(self, item, create_item_cleaner):
        specific_item = self.item_tools.get_specific_item(item)
        manager_class = self.item_tools.get_manager_class(item)

        if not manager_class:
            log.debug('Could not find a manager_class for %s so will not '
                      'cleanup on this item.' % item)
            return None
        manager = manager_class()

        # We don't want to attempt cleanup for any item that we're not totally
        # confident is held by something in its final state. Prematurely
        # triggering cleanup would take the item away while something is still
        # using or working on it.
        #
        # The only exception to this is for legacy style cleanup which is
        # is checked by the manager.is_managing method.
        if not (item.held_by_object_in_final_state or
                manager.is_managing(specific_item)):
            log.debug(('%s is not conclusively held by an object ' % item) +
                      ('in a final state, so not processing it for cleanup.'))
            return None

        held_by_closed_order = False
        held_by_closed_maintenance_order = False
        held_by_ready_task = False

        if isinstance(item.held_by, Order):
            order = item.held_by
            log.debug('%s is currently held by an Order: %s. This Order '
                      'currently has a status of %s and maintenance '
                      'set to %s.'
                      % (item, order, repr(order.status), order.maintenance))

            if order.status == Order.STATUS_CLOSED:
                if order.maintenance:
                    held_by_closed_maintenance_order = True
                held_by_closed_order = True
        elif isinstance(item.held_by, Task):
            task = item.held_by
            log.debug('%s is currently held by a Task: %s. This Task '
                      'currently has a state of %s.'
                      % (item, task, repr(task.state)))
            # The assumption is that a successful task should make its items
            # held by something else or nothing. So if the task is in a ready
            # state (meaning it's completed and the state won't be changing),
            # then either the task failed or it had a bug so any items it's
            # still holding need to be cleaned up.
            #
            # This protocol is true and makes sense for the tasks that we
            # currently have, but we can revisit this if it doesn't make sense
            # for other tasks.
            if task.state in states.READY_STATES:
                held_by_ready_task = True

        if held_by_closed_maintenance_order:
            specific_item.state = Item.STATE_ACTIVE
            specific_item.save()

        if (held_by_closed_order and
           specific_item.state == Item.STATE_MAINTENANCE):
            specific_item.held_by = None
            specific_item.save()
        elif (held_by_closed_order or
              held_by_ready_task or
              manager.is_managing(specific_item)):
            return create_item_cleaner(specific_item.sid)
        else:
            return None

    def process_item_shelf_life(self, item, create_item_cleaner):
        specific_item = self.item_tools.get_specific_item(item)
        manager_class = self.item_tools.get_manager_class(item)

        if not manager_class:
            log.debug('Could not find a manager_class for %s so will not '
                      'cleanup on this item.' % specific_item)
            return None
        manager = manager_class()

        shelf_life = manager.get_shelf_life(item)
        if not shelf_life:
            log.debug('%s has no shelf life so this item is unperishable.'
                      % specific_item)
            return None

        log.debug('%s has a shelf_life of %s and was last held at %s.'
                  % (specific_item, shelf_life, item.time_held_by_updated))

        curr_time = datetime.now(utc)
        time_since_last_held_by = curr_time - item.time_held_by_updated
        if time_since_last_held_by > shelf_life:
            log.info('%s has passed since %s was last held which is greater '
                     'than the shelf life. Will perform cleanup on this Item.'
                     % (time_since_last_held_by, specific_item))

            # TODO: https://rubrik.atlassian.net/browse/INFRA-1634
            # This logic, even though we minimize the risk by doing
            # a refresh_from_db(), is prone to race conditions if the
            # fulfiller and cleanup task respectively try to assign the
            # item to an order or clean it up since it has passed its
            # shelf life. The cleaner task should hold the selected
            # item before it performs any actions on it.
            item.refresh_from_db()
            if item.held_by is None:
                return create_item_cleaner(specific_item.sid)
            else:
                log.warning('%s is now being held by %s so skip cleanup.'
                            % (specific_item, item.held_by))
                return None

        log.debug('%s has passed since %s was last held which is less '
                  'than the shelf life. Will not take any action.'
                  % (time_since_last_held_by, specific_item))
        return None

    def handle_item_cleanup(self, item):
        specific_item = self.item_tools.get_specific_item(item)
        manager_class = self.item_tools.get_manager_class(item)
        manager = manager_class()

        log.debug('Handling cleanup for item %s currently held by %s.' %
                  (specific_item, repr(specific_item.held_by)))
        manager.handle_cleanup(specific_item)
