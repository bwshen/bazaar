"""Fulfill Bodega orders."""
import json
import logging
import random
import statistics
import time
from collections import Counter
from datetime import datetime, timedelta
from math import floor
from bodega_core.exceptions import bodega_value_error
from django.conf import settings
from django.db import transaction
from instrumentation.utils import instrumentation_context
from pytz import utc
from sid_from_id.encoder import get_sid

from .models import Item, ItemFulfillment, Order, OrderUpdate

log = logging.getLogger(__name__)
MAX_RECURSION_LIMIT = 10


class FulfillmentManager(object):
    def __init__(self, item_tools):
        """Initialize FulfillmentManager."""
        self.item_tools = item_tools

    def _expire_order(self, order, order_update_creator):
        comment = ('This order started at %s has gone past its expiration '
                   'time limit of %s has automatically been closed.'
                   % (order.time_created, order.expiration_time_limit))
        OrderUpdate.objects.create(
            order=order,
            comment=comment,
            creator=order_update_creator,
            new_status=Order.STATUS_CLOSED)
        order.status = Order.STATUS_CLOSED
        order.tab_based_priority = Order.PRIORITY_CLOSED
        order.save(update_fields=['status', 'tab_based_priority'])
        log.info(comment)

    def _close_order_if_past_expiration_time(self, order, order_update_creator,
                                             curr_time):
        """Check the expiration time of the order and expires as needed."""
        log.debug('Checking %s to see if it has passed its expiration time'
                  % order)
        if curr_time > order.expiration_time:
            with instrumentation_context('expired_order_closures'):
                self._expire_order(order, order_update_creator)
            return True
        return False

    def _pop_item_from_queryset(self, items_queryset, item):
        return items_queryset.exclude(id=item.id)

    def _pop_item_from_all_querysets(self, items_querysets, item):
        """Remove from querysets the given item."""
        for nickname in items_querysets:
            item_queryset = items_querysets[nickname]
            # This is safe if the Item does not exist within the queryset
            items_querysets[nickname] = self._pop_item_from_queryset(
                item_queryset, item)

    def _get_item_from_queryset(self, item_queryset):
        """Return an item from the given queryset.

        We will first attempt to find an item with a held_by of None since
        the queryset contains a mix of Items which are held by None and
        items which are held by a creator_task.
        """
        held_by_none_qs = item_queryset.filter(held_by_object_id=None)
        if held_by_none_qs:
            return random.choice(list(held_by_none_qs))

        return random.choice(list(item_queryset))

    def _filter_item_state_for_queryset(self, item_queryset,
                                        requires_maintenance_items):
        if requires_maintenance_items:
            state = Item.STATE_MAINTENANCE
        else:
            state = Item.STATE_ACTIVE
        return item_queryset.filter(state=state)

    def _get_prefiltered_item_queryset(self,
                                       item_type,
                                       assigned_items_ids,
                                       held_by_any,
                                       requires_maintenance_items):
        item_queryset = (self.item_tools
                             .get_queryset_for_item_type(item_type)
                             .exclude(id__in=assigned_items_ids))

        item_state_filtered_queryset = \
            self._filter_item_state_for_queryset(
                item_queryset,
                requires_maintenance_items)

        if held_by_any:
            return item_state_filtered_queryset

        held_by_none_queryset = \
            item_state_filtered_queryset.filter(held_by_object_id=None)
        item_manager = self.item_tools.item_types[item_type].manager_class()
        pending_item_queryset = item_manager.get_pending_items_queryset(
            item_state_filtered_queryset)

        return (pending_item_queryset | held_by_none_queryset)

    def _select_items(self, order_items, assigned_items_ids,
                      held_by_any=False,
                      requires_maintenance_items=False,
                      ignore_rare=False):
        """Assign an eligible item to each nickname in an Order.

        Return None if any nickname is un-assignable. Otherwise, return a
        dictionary of selected items.

        ignore_rare can be set to True to only select from non-rare items. If
        the order is inherently looking for rare items, selection will fail.
        """
        log.debug('Selecting for order items: %s', json.dumps(order_items,
                                                              indent=4,
                                                              sort_keys=True))

        prefiltered_items_querysets = {}
        for nickname, order_item in order_items.items():
            item_type = order_item['type']
            if item_type not in prefiltered_items_querysets:
                prefiltered_items_querysets[item_type] = \
                    self._get_prefiltered_item_queryset(
                        item_type,
                        assigned_items_ids,
                        held_by_any,
                        requires_maintenance_items)

        items_querysets = self.item_tools.find_eligible_items_for_order_items(
            order_items=order_items,
            prefiltered_items_querysets=prefiltered_items_querysets)

        if ignore_rare:
            log.debug('Ignoring rare items in querysets of eligible items')
            for nickname, queryset in items_querysets.items():
                item_type = order_items[nickname]['type']
                non_rare_requirements = self.item_tools \
                                            .item_types[item_type] \
                                            .manager_class() \
                                            .get_non_rare_requirements()
                items_querysets[nickname] = \
                    queryset.filter(**non_rare_requirements)

        selected_items = {}
        for nickname in order_items:
            if not items_querysets[nickname].exists():
                log.debug('Did not find item in queryset for %s - '
                          'assigned None for this nickname'
                          % repr(nickname))
                selected_items[nickname] = None
                continue

            selected_item = self._get_item_from_queryset(
                items_querysets[nickname])
            self._pop_item_from_all_querysets(items_querysets,
                                              selected_item)

            log.debug('Tentatively selecting item %s to fulfill %s'
                      % (repr(selected_item), repr(nickname)))
            selected_items[nickname] = selected_item
        return selected_items

    def _get_creator_tasks_for_item(self,
                                    item_requirements,
                                    item_type,
                                    assigned_items_ids,
                                    recursion_depth=0):
        """Try to create an Item from a recipe.

        Returns a set of tasks that creates the item based on the given
        recipe. If a recipe is defined, we will either return a task to
        create the item or recursively check its required ingredients
        for tasks to create those as well if needed.
        """
        if recursion_depth > MAX_RECURSION_LIMIT:
            # If we haven't determined all the ingredients that we need
            # by now, chances are the recipe we're using is bad (i.e. it
            # contains a circular dependency) or it is too complex.
            # A limit of 10 is arbitrary for now and can revisit this if
            # the situation for such complexity in our recipes arises.
            log.error('MAX_RECURSION_LIMIT of %d reached while trying to '
                      'process item of type %s.'
                      % (MAX_RECURSION_LIMIT, item_type))
            return []

        item_manager = self.item_tools.item_types[item_type].manager_class()
        recipe = item_manager.get_item_recipe(item_requirements)
        if not recipe:
            # The item_type we are processing doesn't have a recipe defined
            # so we cannot create it on the fly.
            log.debug('item_type %s does not have a recipe to use so unable '
                      'to create an item of this type.'
                      % item_type)
            return []

        required_ingredients = recipe.required_ingredients
        if not required_ingredients:
            # The item_type we are processing is a dynamic item and doesn't
            # have any required ingredients. Return the creator_task signature
            # for this item_type so a Celery worker can create this item.
            item_creator_task = recipe.creator_task(item_requirements)
            log.debug('item_type %s does not have any required ingredients '
                      'so create task signature of type %s.'
                      % (item_type, item_creator_task))
            item_creator = item_creator_task.si(
                ingredients={},
                requirements=item_requirements)
            return [item_creator]

        selected_items = self._select_items(
            order_items=required_ingredients,
            assigned_items_ids=assigned_items_ids,
            held_by_any=False,
            requires_maintenance_items=False,
            ignore_rare=False)

        unfulfilled_nicknames = \
            [nickname for nickname, item in selected_items.items()
             if item is None]

        if 0 == len(unfulfilled_nicknames):
            # The item_type we are processing has required_ingredients and
            # we were able to find the items to satisfy them.
            selected_item_currently_held = False
            selected_item_sids = {}
            for nickname, item in selected_items.items():
                selected_item_sids[nickname] = item.sid
                assigned_items_ids.append(item.id)

                if item.held_by is not None:
                    # We can select items that are held by None or held by
                    # a creator task to fulfill the required ingredients.
                    # In the case of the latter, the item is not yet usable
                    # so don't fulfill anything with it yet but also don't
                    # create more creator tasks.
                    log.debug('Found %s to fulfill %s for item type %s but '
                              'it is currently being held by %s.'
                              % (item, nickname, item_type, item.held_by))
                    selected_item_currently_held = True

            if selected_item_currently_held:
                return []

            # All the items we found to satisfy our required_ingredients are
            # usable. Return the creator_task signature for this item_type so
            # a Celery worker can create this item
            item_creator_task = recipe.creator_task(item_requirements)
            item_creator = item_creator_task.si(
                ingredients=selected_item_sids,
                requirements=item_requirements)
            return [item_creator]
        else:
            # We were unable to find an item to satisfy one or more of our
            # required ingredients. Therefore we will recurse on the item_types
            # where we could not satisfy our requirements and run through the
            # same logic to create those item_types. After multiple passes
            # of the fulfiller, we will be able to gradually build up the items
            # that we need.
            log.debug('Unable to fulfill item requests for nicknames %s for '
                      'item_type %s'
                      % (unfulfilled_nicknames, item_type))
            item_creators = []
            for nickname in unfulfilled_nicknames:
                item = required_ingredients[nickname]
                item_creators += self._get_creator_tasks_for_item(
                    item['requirements'],
                    item['type'],
                    assigned_items_ids,
                    recursion_depth + 1)

            return item_creators

    def _compute_order_priorities(self, orders):
        """Compute a dictionary mapping order SIDs to processing priority.

        For now, an order's priority is just the time_created with a slight
        addition to pretend orders from the same user are throttled. This is a
        cheap way to effectively throttle orders mainly so that the release
        pipeline doesn't aggressively hog all available items even though it
        places 100s of orders at a time.

        In https://rubrik.atlassian.net/browse/INFRA-670 we'll turn this into
        a more carefully designed notion of integer priorities.
        """
        order_priorities = {}
        times_last_created = {}

        if len(orders) == 0:
            return order_priorities

        time_last_order_created = orders[-1].time_created
        # We'll analyze all orders created in the
        # bodega_all.serializers.DEFAULT_ORDER_EXPIRATION_TIME_LIMIT window
        # before the last order that we're computing priorities for. In
        # practice that covers virtually all orders that hadn't expired. It's
        # not worth refactoring to move that constant somewhere else for this
        # hack, and since it's only an approximation anyway it's okay if the
        # values don't match up exactly.
        ordering_start_time = time_last_order_created + timedelta(hours=-24)
        all_orders = Order.objects.filter(
            time_created__gt=ordering_start_time,
            time_created__lte=time_last_order_created)
        for order in all_orders.order_by('time_created'):
            owner_sid = get_sid(order.owner)
            time_last_created = times_last_created.get(owner_sid, None)
            if time_last_created is None:
                # First order is not throttled.
                throttled_time_created = order.time_created
            else:
                # Hard-coded throttle amount since this is only a hack.
                # At about 200 jobs per release pipeline run, throttling them
                # at 4 minutes each will spread them evenly over ~13 hours.
                # Any orders placed by other individual users during those ~13
                # hours will be in the middle rather than the back of the
                # queue.
                throttled_time_created = max(
                    time_last_created + timedelta(minutes=4),
                    order.time_created)
            times_last_created[owner_sid] = throttled_time_created
            order_priorities[order.sid] = throttled_time_created.isoformat()

        return order_priorities

    def _get_open_orders_by_price(self):
        """Get the list of open orders sorted by price-based priority."""
        log.debug("Getting open orders sorted by price-based priority")

        # time_created ordering will be preserved as the secondary sort key.
        unprioritized_open_orders = list(Order.objects.filter(
            status=Order.STATUS_OPEN).order_by('time_created'))
        fulfilled_orders = list(Order.objects.filter(
            status=Order.STATUS_FULFILLED))

        sorted_orders_dict = self._sort_open_orders_by_price(
            unprioritized_open_orders,
            fulfilled_orders)
        return sorted_orders_dict['sorted_open_orders']

    def _get_open_orders_by_time_created(self):
        """Get an in-memory list of open orders to process.

        We work with frozen list instead of a queryset to avoid potential edge
        cases where we process a new open order that was placed while we were
        still computing priorities and therefore wasn't taken into account.
        """
        log.debug("Getting open orders sorted by time-created priority")

        def get_priority(order):
            return order_priorities.get(order.sid,
                                        order.time_created.isoformat())

        unprioritized_open_orders = list(Order.objects.filter(
            status=Order.STATUS_OPEN).order_by('time_created'))
        order_priorities = self._compute_order_priorities(
            unprioritized_open_orders)
        open_orders = sorted(unprioritized_open_orders, key=get_priority)
        for order in open_orders:
            log.debug(('%s by user %s at %s has priority %s.' %
                      (order, order.owner, order.time_created.isoformat(),
                       get_priority(order))))
        return open_orders

    def _get_open_orders(self):
        """Get an ordered list of open orders to process for fulfillment."""
        # When using ORDER_PRICE_PRIORITY, the get_priority function has a
        # side-effect of doing a database write for the tab_based_priority
        # field of each open order. More details documented on the function
        if settings.ENABLE_ORDER_PRICE_PRIORITY:
            return self._get_open_orders_by_price()
        return self._get_open_orders_by_time_created()

    def _sort_open_orders_by_price(self,
                                   open_orders,
                                   fulfilled_orders):
        """Compute each open order's price-based priority.

        Returns a dictionary containing:
          - the sorted open orders
          - a dictionary mapping order sid to its priority value
            used for testing and debugging

        Price-based priority depends on the order price, the total
        price from all of the owner's fulfilled orders, and the
        current average demand.
        """
        priorities_stats = self._compute_order_priorities_stats(
            open_orders + fulfilled_orders)
        median_demand, order_prices, tab_limits, total_fulfilled_prices = \
            (priorities_stats['median_demand'],
             priorities_stats['order_prices'],
             priorities_stats['tab_limits'],
             priorities_stats['total_fulfilled_prices'])

        # The get_priority function also does a write to the database to update
        # tab_based_priority field for each order. This is because we use that
        # as a cached field to show the user the order's last known priority.
        # This is a side-effect of the function
        def get_priority(open_order):
            """Compute an open order's price-based priority.

            The floor and 20% fudge keep FIFO as a small component of priority
            instead of severely penalizing people who ordered early but want
            just a bit more than average demand.

            Maintenance orders are a special case and always priced at 0.0
            to be processed early.
            """
            priority = 0.0
            if not open_order.maintenance:
                order_price = order_prices[open_order.sid]
                tab = open_order.tab
                owner_total_fulfilled_price = \
                    total_fulfilled_prices.get(tab.id, 0.0)
                tab_limit = tab_limits[tab.sid]
                priority = floor(
                    ((order_price + owner_total_fulfilled_price) / tab_limit) /
                    (1.2 * median_demand))

            open_order.tab_based_priority = priority
            open_order.save(update_fields=['tab_based_priority'])

            return priority

        order_priorities = {
            order.sid: get_priority(order) for order in open_orders
        }

        log.debug('Open order price-based priorities: %s' % order_priorities)

        sorted_open_orders = \
            sorted(open_orders,
                   key=lambda o: order_priorities[o.sid])

        return {
            'sorted_open_orders': sorted_open_orders,
            'open_order_priorities': order_priorities
        }

    def _compute_order_priorities_stats(self, orders):
        """Compute the statistics required to calculate order priorities.

        Returns a dictionary containing:
          - median demand (median of all tab_demand/tab_limit)
          - dictionary mapping order sid to order price
          - dictionary mapping tab sid to tab limit
          - dictionary mapping user ids to their total fulfilled price

        Maintenance orders are a special case. We price these orders at 0.0
        and they are not included in the total price, total tab limit, nor
        their owners' total fulfilled prices.
        """
        order_prices = {}
        tab_limits = {}
        tab_demands = {}
        total_fulfilled_prices = Counter()
        valid_statuses = set([Order.STATUS_OPEN, Order.STATUS_FULFILLED])

        for order in orders:
            if order.status not in valid_statuses:
                bodega_value_error(
                    log,
                    ('Order %s status %s is not valid for computing '
                     'price-based priority') % (order, order.status))

            order_price = 0.0
            if not order.maintenance:
                # We currently assume that each user has a single tab,
                # but this may change in the future.
                if order.tab.sid not in tab_limits:
                    tab_limits[order.tab.sid] = order.tab.limit

                if order.tab.sid not in tab_demands:
                    tab_demands[order.tab.sid] = 0.0

                # Compute order price as a sum of its items' prices.
                item_prices = \
                    self.item_tools.get_prices_for_items(order.items.items())
                order_price = sum(item_prices.values())

                if order.status == Order.STATUS_FULFILLED:
                    total_fulfilled_prices[order.tab.id] += order_price

                tab_demands[order.tab.sid] += order_price

            log.debug('Order %s has a price of %s' % (order, order_price))
            order_prices[order.sid] = order_price

        total_tab_limit = sum(tab_limits.values())

        # Generate a list of tab_demands / tab_limit to compute the median
        # demand
        tab_demand_per_limit = sorted(
            [tab_demands[key] / tab_limits[key]
             for key in tab_demands])

        if total_tab_limit < 0:
            bodega_value_error(
                log,
                'Total tab limit is negative: %s' % total_tab_limit)
        elif total_tab_limit == 0:
            if orders:
                bodega_value_error(
                    log,
                    ('Total tab limit is 0 for non-empty list of orders. '
                     'This may be due to a race condition in between the time '
                     'we collect the tab ids and fetch their limits.'))
            median_demand = None
        else:
            median_demand = statistics.median(tab_demand_per_limit)

        order_priority_stats = {
            'median_demand': median_demand,
            'order_prices': order_prices,
            'tab_limits': tab_limits,
            'total_fulfilled_prices': dict(total_fulfilled_prices)
        }

        log.debug('Order priority stats: %s' % order_priority_stats)
        return order_priority_stats

    def fulfill_open_orders(self, get_order_fulfillers,
                            create_order_fulfiller,
                            create_item_maintenance_setter,
                            order_update_creator):
        """Loop through all OPEN Orders try to fulfill all item requests.

        The strategy to fulfill orders will be an all-or-nothing strategy.
        Partially fulfilling orders at this time is not supported to avoid
        the possibility of deadlock on items.

        Fulfillment will prioritize non-rare items, falling back to the full
        set when prioritization is not possible.
        """
        open_orders = self._get_open_orders()
        open_maintenance_orders = [order for order in open_orders
                                   if order.maintenance]
        assigned_items_ids = []
        signatures = []

        for maintenance_order in open_maintenance_orders:
            log.debug('Processing maintenance order %s' % maintenance_order)

            if maintenance_order.changed_item_state_to_maintenance:
                log.debug('Items were already marked for maintenance so no '
                          'need for further action.')
                continue

            maintenance_items = self._select_items(
                order_items=maintenance_order.items,
                assigned_items_ids=assigned_items_ids,
                held_by_any=True,
                requires_maintenance_items=False)
            unfulfilled_nicknames = \
                [nickname for nickname, item in maintenance_items.items()
                 if item is None]
            if 0 == len(unfulfilled_nicknames):
                comment = ('These items have been changed to maintenance '
                           'state: %s' %
                           ", ".join(['`%s` => `%s`' %
                                      (nickname, str(item.name))
                                      for nickname, item
                                      in sorted(maintenance_items.items())]))

                time.sleep(1)
                OrderUpdate.objects.create(
                    order=maintenance_order,
                    comment=comment,
                    creator=order_update_creator,
                    maintenance=True)
                for nickname in maintenance_items:
                    maintenance_item = maintenance_items[nickname]
                    signatures.append(
                        create_item_maintenance_setter(maintenance_item.sid))
                    assigned_items_ids.append(maintenance_item.id)

                log.info(comment)

        for order in open_orders:
            curr_time = datetime.now(utc)
            if order.maintenance:
                log.debug(('%s is a maintenance order so will not check '
                           'expiration time on this order.') % order)
            elif self._close_order_if_past_expiration_time(
                    order,
                    order_update_creator,
                    curr_time):
                continue

            order_fulfillers = get_order_fulfillers(order.sid)
            # If there is already a fulfiller for this order, we don't want to
            # do anything with it. In particular this avoids creating
            # additional order fulfillers which is potentially wasteful of
            # items not only by assigning extras to the order, but even before
            # that as the extra fulfillers hold items that could have been
            # used to fulfill other orders.
            if order_fulfillers.exists():
                log.debug(
                    ('Will not process %s because it already ' % order) +
                    ('has order fulfillers: %s' % repr(order_fulfillers)))
                continue

            try:
                task_signatures = self.process_open_order(
                    order, create_order_fulfiller, assigned_items_ids)
            except Exception:
                log.warning('Caught Exception for %s. Not creating '
                            'any tasks for this order.'
                            % order,
                            exc_info=True)
            else:
                signatures += task_signatures

        return signatures

    def process_open_order(self, order, create_order_fulfiller,
                           assigned_items_ids):
        log.debug('Processing OPEN order %s' % order)
        order_items = order.items
        requires_maintenance_items = order.maintenance

        selected_items = {}
        if not requires_maintenance_items:
            log.debug('Attempting assignment with \'ignore_rare=True\'')
            selected_items = self._select_items(
                order_items=order.items,
                assigned_items_ids=assigned_items_ids,
                held_by_any=False,
                requires_maintenance_items=requires_maintenance_items,
                ignore_rare=True)

        unfulfilled_nicknames = \
            [nickname for nickname, item in selected_items.items()
             if item is None]
        if len(unfulfilled_nicknames) > 0 or order.maintenance:
            log.debug('Attempting assignment with \'ignore_rare=False\'')
            selected_items = self._select_items(
                order_items=order.items,
                assigned_items_ids=assigned_items_ids,
                held_by_any=False,
                requires_maintenance_items=requires_maintenance_items,
                ignore_rare=False)

        unfulfilled_nicknames = \
            [nickname for nickname, item in selected_items.items()
             if item is None]
        if 0 == len(unfulfilled_nicknames):
            log.debug('Able to assign item requests in %s' % order)

            selected_item_currently_held = False
            selected_item_sids = {}
            for nickname, item in selected_items.items():
                selected_item_sids[nickname] = item.sid
                assigned_items_ids.append(item.id)

                if item.held_by is not None:
                    log.info('%s is currently held by %s so do not use it to '
                             'fulfill any orders.'
                             % (item, item.held_by))
                    selected_item_currently_held = True

            if selected_item_currently_held:
                # We can select items that are held by None or held by
                # a creator task to fulfill the required ingredients.
                # In the case of the latter, the item is not yet usable
                # so don't fulfill anything with it yet but also don't
                # create more creator tasks.
                log.debug('Selected items for fulfilling all items in %s but '
                          'an item is currently being held so will not '
                          'fulfill this Order.' % order)
                return []

            order_fulfiller = create_order_fulfiller(
                order.sid, selected_item_sids)
            return [order_fulfiller]
        else:
            log.debug('Unable to fulfill item requests for nicknames %s in %s.'
                      ' Will not assign any items to this Order.'
                      % (unfulfilled_nicknames, str(order)))

            item_creators = []
            for nickname in unfulfilled_nicknames:
                item = order_items[nickname]
                item_creators += self._get_creator_tasks_for_item(
                    item['requirements'],
                    item['type'],
                    assigned_items_ids)

            return item_creators

        return []

    def fulfill_order(self, order, selected_items, order_update_creator):
        log.debug('Fulfilling order %s with items %s' %
                  (order, repr(selected_items)))
        usable_items = set()
        spoiled_items = set()
        fulfilled_items = {}

        if order.maintenance:
            log.debug(
                ('Skipping taste tests for order %s ' % str(order)) +
                ('since it is a maintenance order.'))
        else:
            for (nickname, item) in selected_items.items():
                specific_item = self.item_tools.get_specific_item(item)
                manager_class = self.item_tools.get_manager_class(item)
                item_manager = manager_class()

                requirements = order.items[nickname]
                log.debug('Taste testing %s with %s for order %s.' %
                          (specific_item, item_manager, order))
                if item_manager.taste_test(specific_item, requirements):
                    usable_items.add(specific_item)
                else:
                    log.debug(
                        ('Item %s failed taste test ' % str(item)) +
                        ('against requirements %s.' % repr(requirements)))
                    spoiled_items.add(specific_item)

                # Track the specific (instead of generic) item to generate
                # the comment below with a more useful description of the item.
                fulfilled_items[nickname] = specific_item

            if len(spoiled_items) > 0:
                log.debug(
                    ('%d items failed their taste ' % len(spoiled_items)) +
                    ('tests, so cannot fulfill %s. ' % str(order)) +
                    ('%d other items are still usable.' % len(usable_items)))
                return usable_items

        comment = ('These order items have been fulfilled and are '
                   'ready to consume: %s' %
                   ", ".join(['`%s` => `%s`' %
                              (nickname, str(item.name))
                              for nickname, item
                              in sorted(fulfilled_items.items())]))
        # Ensure that this OrderUpdate does not have the same
        # timestamp as the initial update.
        time.sleep(1)
        with transaction.atomic():
            order_update = OrderUpdate.objects.create(
                order=order,
                comment=comment,
                creator=order_update_creator,
                new_status=Order.STATUS_FULFILLED)

            for nickname in selected_items:
                selected_item = selected_items[nickname]
                ItemFulfillment.objects.create(
                    order_update=order_update,
                    nickname=nickname,
                    item=selected_item)
                log.debug('Assigned Item %s to fulfill %s for %s'
                          % (repr(selected_item), repr(nickname), order))
                selected_item.held_by = order
                selected_item.save()

            log.info('Fulfilled all item requests for %s and setting '
                     'status to %s.'
                     % (str(order), Order.STATUS_FULFILLED))
            order.status = Order.STATUS_FULFILLED
            order.tab_based_priority = Order.PRIORITY_FULFILLED
            order.save(update_fields=['status', 'tab_based_priority'])
        log.info(comment)
        return set()
