"""Test order fulfillment."""
import json
import logging
from datetime import datetime, timedelta

from bodega_test_items.item_types import item_tools
from bodega_test_items.models import BasicItem
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from pytz import utc
from rkelery import states
from rkelery.models import Task
from rkelery.utils import json_dump
from .fulfillment import FulfillmentManager
from .models import Item, Order, OrderUpdate

log = logging.getLogger(__name__)

CREATE_BASIC_ITEM_TASK = 'CreateBasicItem'
CREATE_COMPLEX_ITEM_TASK = 'CreateComplexItem'
ORDER_FULFILLER_TASK = 'FulfillOrder'
SET_ITEM_TO_MAINTENANCE_TASK = 'SetItemToMaintenance'


class FulfillmentTestCase(TestCase):
    def setUp(self):
        self.order_update_creator = User.objects.get(id=1)
        self.user = User.objects.create_user(username='Foo')
        self.tab = self.user.tabs.get()
        self.item1 = BasicItem.objects.create(
            boolean=False,
            string="string1",
            choice=BasicItem.CHOICE_A)
        self.item2 = BasicItem.objects.create(
            boolean=False,
            string="string2",
            choice=BasicItem.CHOICE_B)
        self.item3 = BasicItem.objects.create(
            boolean=True,
            string="string3",
            choice=BasicItem.CHOICE_C)

    def get_order_fulfillers(self, order_sid):
        return Task.objects.filter(
            task=ORDER_FULFILLER_TASK,
            args_json__contains=json_dump(order_sid),
            task_result__status__in=(
                states.PRE_RUNNING_STATES.union(frozenset(states.RUNNING))))

    def create_order_fulfiller(self, order_sid, selected_item_sids):
        return Task.objects.create(
            task=ORDER_FULFILLER_TASK,
            args=[order_sid, selected_item_sids],
            kwargs={})

    def fulfill_open_orders(self):
        manager = FulfillmentManager(item_tools)
        manager.fulfill_open_orders(
            self.get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)

    def get_order_fulfiller(self, order_sid):
        order_fulfillers = self.get_order_fulfillers(order_sid)
        self.assertEqual(
            order_fulfillers.count(), 1,
            'There should be exactly one order fulfiller for order %s' %
            repr(order_sid))
        return order_fulfillers.first()

    def assert_order_fulfiller_args(self, order_fulfiller,
                                    order_sid, item_nicknames):
        self.assertEqual(order_fulfiller.task, ORDER_FULFILLER_TASK)
        self.assertEqual(len(order_fulfiller.args), 2)

        self.assertEqual(order_fulfiller.args[0], order_sid)
        self.assertIsInstance(order_fulfiller.args[1], dict)
        self.assertEqual(list(order_fulfiller.args[1].keys()),
                         item_nicknames)

    def get_selected_item(self, order_fulfiller, nickname):
        selected_item_sids = order_fulfiller.args[1]
        self.assertIn(nickname, selected_item_sids.keys())
        return item_tools.get_specific_item(
            Item.objects.get(sid=selected_item_sids[nickname]))

    def get_item_creators(self):
        return Task.objects.filter(
            task=CREATE_BASIC_ITEM_TASK,
            task_result__status__in=(
                states.PRE_RUNNING_STATES.union(frozenset(states.RUNNING))))

    def get_complex_item_creators(self):
        return Task.objects.filter(
            task=CREATE_COMPLEX_ITEM_TASK,
            task_result__status__in=(
                states.PRE_RUNNING_STATES.union(frozenset(states.RUNNING))))

    def create_item_maintenance_setter(self, item_sid):
        return Task.objects.create(
            task=SET_ITEM_TO_MAINTENANCE_TASK,
            args=[item_sid],
            kwargs={})


class OneFulfillmentTestCase(FulfillmentTestCase):
    def setUp(self):
        super(OneFulfillmentTestCase, self).setUp()

        items_delta = json.dumps({
            'item1': {
                'type': 'basic_item',
                'requirements': {
                    'boolean': False
                }
            }
        })

        self.order = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=self.order,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

    def assert_selected_item(self):
        order_fulfiller = self.get_order_fulfiller(self.order.sid)
        self.assert_order_fulfiller_args(order_fulfiller,
                                         self.order.sid,
                                         ['item1'])

        selected_item = self.get_selected_item(order_fulfiller, 'item1')
        self.assertIsInstance(selected_item, BasicItem)
        self.assertEqual(selected_item.boolean, False)

    def test_one_fulfiller(self):
        """Test for one fulfiller.

        In this basic case, one attempt to fulfill open orders should result
        in one order fulfiller with a correctly selected item.
        """
        self.fulfill_open_orders()
        self.assert_selected_item()

    def test_one_fulfiller_repeated(self):
        """Test for one fulfiller with repeated attempts.

        If multiple attempts to fulfill open orders occur before the first
        order fulfiller has completed, there should still only be one order
        fulfiller active. This is to prevent
        https://rubrik.atlassian.net/browse/CDM-52090
        """
        self.fulfill_open_orders()
        self.assert_selected_item()

        self.fulfill_open_orders()
        self.assert_selected_item()


class CreateItemFulfillmentTestCase(FulfillmentTestCase):
    def setUp(self):
        super(CreateItemFulfillmentTestCase, self).setUp()

        items_delta = json.dumps({
            'item1': {
                'type': 'basic_item',
                'requirements': {
                    'boolean': False
                }
            }
        })

        self.order = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=self.order,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

        fulfilled_order = Order.objects.create(
            status=Order.STATUS_FULFILLED,
            owner=self.user,
            tab=self.tab)
        self.item1.held_by = fulfilled_order
        self.item1.save()
        self.item2.held_by = fulfilled_order
        self.item2.save()
        self.item3.held_by = fulfilled_order
        self.item3.save()

    def assert_item_creator_count(self, count):
        item_creators = self.get_item_creators()
        self.assertEqual(
            item_creators.count(), count,
            'Found %d item creators but expected %d'
            % (item_creators.count(), count))

    def assert_complex_item_creator_count(self, count):
        item_creators = self.get_complex_item_creators()
        self.assertEqual(
            item_creators.count(), count,
            'Found %d item creators but expected %d'
            % (item_creators.count(), count))

    def test_item_does_not_exist(self):
        """Test for one fulfiller.

        In this basic case, one attempt to fulfill open orders should result
        in one order fulfiller with a task.
        """
        self.fulfill_open_orders()
        self.assert_item_creator_count(1)

        self.fulfill_open_orders()
        self.assert_item_creator_count(1)

    def test_multiple_orders_need_item_creators(self):
        self.fulfill_open_orders()
        self.assert_item_creator_count(1)

        items_delta = json.dumps({
            'item1': {
                'type': 'basic_item',
                'requirements': {
                    'boolean': False
                }
            }
        })

        order = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=order,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))
        self.fulfill_open_orders()
        self.assert_item_creator_count(2)

    def test_recipe_requires_items(self):
        self.fulfill_open_orders()
        self.assert_item_creator_count(1)

        items_delta = json.dumps({
            'item1': {
                'type': 'complex_item',
                'requirements': {
                    'number': 1
                }
            }
        })

        order = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=order,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))
        self.fulfill_open_orders()
        self.assert_item_creator_count(3)
        self.assert_complex_item_creator_count(0)

        self.fulfill_open_orders()
        self.assert_item_creator_count(3)
        self.assert_complex_item_creator_count(1)

    def test_prioritize_items_held_by_none(self):
        items_delta = json.dumps({
            'item1': {
                'type': 'complex_item',
                'requirements': {
                    'number': 1
                }
            }
        })

        self.order.status = Order.STATUS_FULFILLED
        self.order.save()

        order2 = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=order2,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

        task = Task.objects.create(task=CREATE_BASIC_ITEM_TASK,
                                   args=[],
                                   kwargs={})

        self.item4 = BasicItem.objects.create(
            boolean=False,
            string="string2",
            choice=BasicItem.CHOICE_B)

        self.item5 = BasicItem.objects.create(
            boolean=False,
            string="string2",
            choice=BasicItem.CHOICE_B,
            held_by=task)

        self.item6 = BasicItem.objects.create(
            boolean=False,
            string="string2",
            choice=BasicItem.CHOICE_B,
            held_by=task)

        self.item7 = BasicItem.objects.create(
            boolean=False,
            string="string2",
            choice=BasicItem.CHOICE_B)

        self.item8 = BasicItem.objects.create(
            boolean=False,
            string="string2",
            choice=BasicItem.CHOICE_A)

        task_result = task.task_result
        task_result.status = states.RUNNING
        task_result.save()

        self.fulfill_open_orders()
        self.assert_complex_item_creator_count(1)


class ExpirationTestCase(TestCase):
    def setUp(self):
        items_delta = json.dumps({
            'item1': {
                'type': 'basic_item',
                'requirements': {
                    'boolean': False
                }
            }
        })
        self.user = User.objects.create_user(username='Foo')
        self.tab = self.user.tabs.get()
        self.order_1 = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=self.order_1,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=1))

        self.order_2 = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta,
            order=self.order_2,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=10))

    def close_order_if_past_expiration_time(self, order, curr_time):
        manager = FulfillmentManager(item_tools)
        manager._close_order_if_past_expiration_time(order, self.user,
                                                     curr_time)

    def test_close_order_if_past_expiration_time(self):
        curr_time_plus_five_minutes = datetime.now(utc) + timedelta(minutes=5)

        self.close_order_if_past_expiration_time(self.order_1,
                                                 curr_time_plus_five_minutes)
        self.close_order_if_past_expiration_time(self.order_2,
                                                 curr_time_plus_five_minutes)
        self.order_1.refresh_from_db()
        self.order_2.refresh_from_db()

        self.assertEqual(self.order_1.status, Order.STATUS_CLOSED)
        self.assertEqual(self.order_2.status, Order.STATUS_OPEN)


class OrderPrioritizationTestCase(TestCase):
    def create_order(self, time_created, creator,
                     num_items=1, order_status=Order.STATUS_OPEN,
                     maintenance=False):
        items_delta = json.dumps({
            'item%d' % item_num: {
                'type': 'basic_item',
                'requirements': {
                    'boolean': False
                }
            } for item_num in range(num_items)
        })

        order = Order.objects.create(
            status=order_status,
            owner=creator,
            maintenance=maintenance,
            tab=creator.tabs.get())
        order_update = OrderUpdate.objects.create(
            items_delta=items_delta,
            order=order,
            creator=creator,
            expiration_time_limit_delta=timedelta(hours=24))
        order.time_created = time_created
        order.save()
        order_update.time_created = time_created
        order_update.save()
        return order

    def get_order_queue_position(self, open_orders, order):
        for queue_position in range(0, len(open_orders)):
            if open_orders[queue_position].sid == order.sid:
                return queue_position
        return None

    def test_creation_time_throttling(self):
        settings.ENABLE_ORDER_PRICE_PRIORITY = False
        pipeline_user = User.objects.create_user(username='pipeline')
        individual_user1 = User.objects.create_user(username='individual1')
        individual_user2 = User.objects.create_user(username='individual2')
        manager = FulfillmentManager(item_tools)

        # Simulate orders starting as early as 23 hours ago, so they wouldn't
        # have expired under the default 24 hour expiration time.
        simulated_time = datetime.now(utc) + timedelta(hours=-23)

        # Simulate a release pipeline creating 200 orders all at the same time.
        for i in range(0, 200):
            self.create_order(simulated_time, pipeline_user)

        # Simulate an individual user creating 1 order a couple hours after the
        # release pipeline's orders.
        simulated_time = simulated_time + timedelta(hours=2)
        order1 = self.create_order(simulated_time, individual_user1)

        # Simulate an individual user creating 1 order many hours after the
        # release pipeline's orders.
        simulated_time = simulated_time + timedelta(hours=8)
        order2 = self.create_order(simulated_time, individual_user2)

        # Determine the initial queue positions.
        initial_open_orders = manager._get_open_orders()
        initial_order1_position = self.get_order_queue_position(
            initial_open_orders, order1)
        initial_order2_position = self.get_order_queue_position(
            initial_open_orders, order2)
        # The first individual order shouldn't be at the front of the queue,
        # but at least somewhere fairly early.
        log.debug('Initially, %s by %s at %s is in queue position %d.' %
                  (order1, order1.owner, order1.time_created,
                   initial_order1_position))
        self.assertGreater(initial_order1_position, 0)
        self.assertLessEqual(initial_order1_position, 50)
        # The second individual order shouldn't be at the very back of the
        # queue, but still somewhere fairly late.
        log.debug('Initially, %s by %s at %s is in queue position %d.' %
                  (order2, order2.owner, order2.time_created,
                   initial_order2_position))
        self.assertGreater(initial_order2_position, 100)
        self.assertLessEqual(initial_order2_position, 200)

        # Simulate a large chunk of pipeline orders getting fulfilled just
        # before individual users start placing orders.
        for i in range(0, 100):
            order = initial_open_orders[i]
            if order.owner == pipeline_user:
                order.status = Order.STATUS_FULFILLED
                order.save()

        # Determine the queue positions midway through fulfillment.
        midway_open_orders = manager._get_open_orders()
        midway_order1_position = self.get_order_queue_position(
            midway_open_orders, order1)
        midway_order2_position = self.get_order_queue_position(
            midway_open_orders, order2)
        # The first individual order should be at the front of the queue since
        # it came early enough, and the pipeline has consumed a lot of items
        # already.
        log.debug('Midway, %s by %s at %s is in queue position %d.' %
                  (order1, order1.owner, order1.time_created,
                   midway_order1_position))
        self.assertEqual(midway_order1_position, 0)
        # The second individual order should have moved up somewhat and still
        # not be at the very back of the queue.
        log.debug('Midway, %s by %s at %s is in queue position %d.' %
                  (order2, order2.owner, order2.time_created,
                   midway_order2_position))
        self.assertLessEqual(midway_order2_position, 100)

    def assert_order_priority_stats(self,
                                    priority_stats,
                                    expected_median_demand,
                                    expected_order_prices,
                                    expected_fulfilled_prices):
        self.assertEquals(expected_median_demand,
                          priority_stats['median_demand'])
        self.assertEquals(expected_order_prices,
                          priority_stats['order_prices'])
        self.assertEquals(expected_fulfilled_prices,
                          priority_stats['total_fulfilled_prices'])

    def assert_sorted_open_orders_by_price(self,
                                           sorted_orders_dict,
                                           expected_sorted_orders,
                                           expected_priorities):
        self.assertEquals(expected_sorted_orders,
                          sorted_orders_dict['sorted_open_orders'])
        self.assertEquals(expected_priorities,
                          sorted_orders_dict['open_order_priorities'])

    def test_price_based_priority(self):
        settings.ENABLE_ORDER_PRICE_PRIORITY = True
        # Note that the admin user has a higher tab limit of 2.0.
        admin = User.objects.get(id=1)
        admin_tab = admin.tabs.get()
        admin_tab.limit = 2.0
        admin_tab.save()

        happy_user = User.objects.create_user(username='HappyBodegaUser')
        time_created = datetime.now(utc)
        manager = FulfillmentManager(item_tools)

        # Create the orders with items that we'll compute statistics from.
        fulfilled_order_one = self.create_order(
            time_created,
            happy_user,
            num_items=1,
            order_status=Order.STATUS_FULFILLED)
        fulfilled_order_two = self.create_order(
            time_created,
            admin,
            num_items=2,
            order_status=Order.STATUS_FULFILLED)
        fulfilled_order_three = self.create_order(
            time_created,
            happy_user,
            num_items=3,
            order_status=Order.STATUS_FULFILLED)
        open_order_two = self.create_order(
            time_created,
            admin,
            num_items=2)
        open_order_seven = self.create_order(
            time_created,
            happy_user,
            num_items=7)

        # No orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([]),
            expected_median_demand=None,
            expected_order_prices={},
            expected_fulfilled_prices={})

        # 1 fulfilled order with 1 item. No open orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one
            ]),
            expected_median_demand=1.0,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0
            },
            expected_fulfilled_prices={
                happy_user.id: 1.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[],
                fulfilled_orders=[fulfilled_order_one]),
            expected_sorted_orders=[],  # No open orders to sort.
            expected_priorities={})

        # 1 fulfilled order with 3 items. No open orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_three
            ]),
            expected_median_demand=3.0,
            expected_order_prices={
                fulfilled_order_three.sid: 3.0
            },
            expected_fulfilled_prices={
                happy_user.id: 3.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[],
                fulfilled_orders=[fulfilled_order_three]),
            expected_sorted_orders=[],
            expected_priorities={})

        # 2 fulfilled orders with 4 total items, same owner. No open orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one,
                fulfilled_order_three
            ]),
            expected_median_demand=4.0,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0,
                fulfilled_order_three.sid: 3.0
            },
            expected_fulfilled_prices={
                happy_user.id: 4.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[],
                fulfilled_orders=[
                    fulfilled_order_one,
                    fulfilled_order_three
                ]),
            expected_sorted_orders=[],
            expected_priorities={})

        # 3 fulfilled orders with 6 total items, 2 owners. No open orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one,
                fulfilled_order_two,
                fulfilled_order_three
            ]),
            expected_median_demand=2.5,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0,
                fulfilled_order_two.sid: 2.0,
                fulfilled_order_three.sid: 3.0
            },
            expected_fulfilled_prices={
                happy_user.id: 4.0,
                admin.id: 2.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[],
                fulfilled_orders=[
                    fulfilled_order_one,
                    fulfilled_order_two,
                    fulfilled_order_three
                ]),
            expected_sorted_orders=[],
            expected_priorities={})

        # 1 open order with 2 items, owner is admin. No fulfilled orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                open_order_two
            ]),
            expected_median_demand=1.0,
            expected_order_prices={
                open_order_two.sid: 2.0
            },
            expected_fulfilled_prices={})

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[open_order_two],
                fulfilled_orders=[]),
            expected_sorted_orders=[open_order_two],
            expected_priorities={
                # floor(((2.0 + 0.0) / 2.0) / (1.2 * 1.0))
                open_order_two.sid: 0.0
            })

        # 2 open order with 9 items, both owners. No fulfilled orders.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                open_order_two,
                open_order_seven
            ]),
            expected_median_demand=4.0,
            expected_order_prices={
                open_order_two.sid: 2.0,
                open_order_seven.sid: 7.0
            },
            expected_fulfilled_prices={})

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[
                    open_order_two,
                    open_order_seven
                ],
                fulfilled_orders=[]),
            expected_sorted_orders=[
                open_order_two,
                open_order_seven
            ],
            expected_priorities={
                # floor(((2.0 + 0.0) / 2.0) / (1.2 * 4.0))
                open_order_two.sid: 0.0,
                # floor(((7.0 + 0.0) / 1.0) / (1.2 * 4.0))
                open_order_seven.sid: 1.0
            })

        # All current orders in the db.
        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one,
                fulfilled_order_two,
                fulfilled_order_three,
                open_order_two,
                open_order_seven
            ]),
            expected_median_demand=6.5,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0,
                fulfilled_order_two.sid: 2.0,
                fulfilled_order_three.sid: 3.0,
                open_order_two.sid: 2.0,
                open_order_seven.sid: 7.0
            },
            expected_fulfilled_prices={
                happy_user.id: 4.0,
                admin.id: 2.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[
                    open_order_two,
                    open_order_seven
                ],
                fulfilled_orders=[
                    fulfilled_order_one,
                    fulfilled_order_two,
                    fulfilled_order_three
                ]),
            expected_sorted_orders=[
                open_order_two,
                open_order_seven
            ],
            expected_priorities={
                # floor(((2.0 + 2.0) / 2.0) / (1.2 * 6.5))
                open_order_two.sid: 0.0,
                # floor(((7.0 + 4.0) / 1.0) / (1.2 * 6.5))
                open_order_seven.sid: 1.0
            })

        self.assertEquals(
            manager._get_open_orders(),
            [open_order_two, open_order_seven])

        # Now add a fulfilled order for admin user to increase admin's total
        # fulfilled price such that open_order_seven is prioritized before
        # open_order_two.
        fulfilled_order_57 = self.create_order(
            time_created,
            admin,
            num_items=57,
            order_status=Order.STATUS_FULFILLED)

        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one,
                fulfilled_order_two,
                fulfilled_order_three,
                fulfilled_order_57,
                open_order_two,
                open_order_seven
            ]),
            expected_median_demand=20.75,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0,
                fulfilled_order_two.sid: 2.0,
                fulfilled_order_three.sid: 3.0,
                fulfilled_order_57.sid: 57.0,
                open_order_two.sid: 2.0,
                open_order_seven.sid: 7.0
            },
            expected_fulfilled_prices={
                happy_user.id: 4.0,
                admin.id: 59.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[
                    open_order_two,
                    open_order_seven
                ],
                fulfilled_orders=[
                    fulfilled_order_one,
                    fulfilled_order_two,
                    fulfilled_order_three,
                    fulfilled_order_57
                ]),
            expected_sorted_orders=[
                open_order_seven,
                open_order_two
            ],
            expected_priorities={
                # floor(((7.0 + 4.0) / 1.0) / (1.2 * 20.75))
                open_order_seven.sid: 0.0,
                # floor(((2.0 + 59.0) / 2.0) / (1.2 * 20.75))
                open_order_two.sid: 1.0
            })

        self.assertEquals(
            manager._get_open_orders(),
            [open_order_seven, open_order_two])

        # Now add another open order for admin. While it will have the same
        # priority value as the admin's other open order, it will be ordered
        # behind the other order because of the later creation time, hence
        # retaining some element of FIFO that was desired in INFRA-670.
        open_order_zero = self.create_order(
            time_created,
            admin,
            num_items=0,
            order_status=Order.STATUS_OPEN)

        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one,
                fulfilled_order_two,
                fulfilled_order_three,
                fulfilled_order_57,
                open_order_zero,
                open_order_two,
                open_order_seven
            ]),
            expected_median_demand=20.75,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0,
                fulfilled_order_two.sid: 2.0,
                fulfilled_order_three.sid: 3.0,
                fulfilled_order_57.sid: 57.0,
                open_order_zero.sid: 0.0,
                open_order_two.sid: 2.0,
                open_order_seven.sid: 7.0
            },
            expected_fulfilled_prices={
                happy_user.id: 4.0,
                admin.id: 59.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[
                    open_order_zero,
                    open_order_two,
                    open_order_seven
                ],
                fulfilled_orders=[
                    fulfilled_order_one,
                    fulfilled_order_two,
                    fulfilled_order_three,
                    fulfilled_order_57
                ]),
            expected_sorted_orders=[
                open_order_seven,
                # Here, open_order_zero is ahead of open_order_two despite
                # having equal priority values because open_order_zero is
                # ordered ahead in the open_orders input list sent to
                # _sort_open_orders_by_price.
                open_order_zero,
                open_order_two
            ],
            expected_priorities={
                # floor(((7.0 + 4.0) / 1.0) / (1.2 * 20.75))
                open_order_seven.sid: 0.0,
                # floor(((0.0 + 59.0) / 2.0) / (1.2 * 20.75))
                open_order_zero.sid: 1.0,
                # floor(((2.0 + 59.0) / 2.0) / (1.2 * 20.75))
                open_order_two.sid: 1.0
            })

        # Here, open_order_zero is behind open_order_two because
        # _get_open_orders first sorts by creation time and open_order_zero
        # was created after open_order_two.
        self.assertEquals(
            manager._get_open_orders(),
            [open_order_seven, open_order_two, open_order_zero])

        # Verify that open and fulfilled maintenance orders are priced at 0.0
        # but are not involved in median demand nor owner fulfilled price.
        fulfilled_maint_order = self.create_order(
            time_created,
            admin,
            num_items=1,
            order_status=Order.STATUS_FULFILLED,
            maintenance=True)
        open_maint_order = self.create_order(
            time_created,
            happy_user,
            num_items=1,
            order_status=Order.STATUS_OPEN,
            maintenance=True)

        self.assert_order_priority_stats(
            priority_stats=manager._compute_order_priorities_stats([
                fulfilled_order_one,
                fulfilled_order_two,
                fulfilled_order_three,
                fulfilled_order_57,
                fulfilled_maint_order,
                open_order_zero,
                open_order_two,
                open_order_seven,
                open_maint_order
            ]),
            expected_median_demand=20.75,
            expected_order_prices={
                fulfilled_order_one.sid: 1.0,
                fulfilled_order_two.sid: 2.0,
                fulfilled_order_three.sid: 3.0,
                fulfilled_order_57.sid: 57.0,
                fulfilled_maint_order.sid: 0.0,
                open_order_zero.sid: 0.0,
                open_order_two.sid: 2.0,
                open_order_seven.sid: 7.0,
                open_maint_order.sid: 0.0
            },
            expected_fulfilled_prices={
                happy_user.id: 4.0,
                admin.id: 59.0
            })

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=[
                    open_order_zero,
                    open_order_two,
                    open_order_seven,
                    open_maint_order
                ],
                fulfilled_orders=[
                    fulfilled_order_one,
                    fulfilled_order_two,
                    fulfilled_order_three,
                    fulfilled_order_57,
                    fulfilled_maint_order
                ]),
            expected_sorted_orders=[
                open_order_seven,
                # Although the maintenance order has priority 0.0 it is ordered
                # behind open_order_seven because it was created later. This is
                # fine because maintenance orders will only process items that
                # are marked as maintenance, so it will only compete with other
                # maintenance orders.
                open_maint_order,
                open_order_zero,
                open_order_two
            ],
            expected_priorities={
                # All open orders will have priority 0.0.
                open_maint_order.sid: 0.0,
                # floor(((7.0 + 4.0) / 1.0) / (1.2 * 24.0))
                open_order_seven.sid: 0.0,
                # floor(((0.0 + 59.0) / 2.0) / (1.2 * 24.0))
                open_order_zero.sid: 1.0,
                # floor(((2.0 + 59.0) / 2.0) / (1.2 * 24.0))
                open_order_two.sid: 1.0
            })

    def test_order_tab_change_scenario(self):
        """Test the scenario where we want to change the tab of the order.

        The user will create multiple orders, one of which will be higher
        than the user's tab limit. We will change that order to use a tab
        that has a higher limit and test the user is not penalized for the
        order that is costly.

        The purpose of this is there are scenarios in which an order is held
        for a long time for testing purposes of a group. We don't want to
        penalize the owner of that order as it is a shared resource.
        """
        settings.ENABLE_ORDER_PRICE_PRIORITY = True
        admin = User.objects.get(id=1)
        admin_tab = admin.tabs.get()
        admin_tab.limit = 2.0
        admin_tab.save()
        jane = User.objects.create_user(username='Jane')
        steve = User.objects.create_user(username='Steve')
        manager = FulfillmentManager(item_tools)

        jane_group_order = self.create_order(
            time_created=datetime.now(utc),
            creator=jane,
            num_items=15,
            order_status=Order.STATUS_FULFILLED)

        jane_individual_order = self.create_order(
            time_created=datetime.now(utc),
            creator=jane,
            num_items=1,
            order_status=Order.STATUS_OPEN)

        steve_order = self.create_order(
            time_created=datetime.now(utc),
            creator=steve,
            num_items=3,
            order_status=Order.STATUS_OPEN)

        all_open_orders = [steve_order] + \
            [jane_individual_order]

        fulfilled_orders = [jane_group_order]

        # Steve's order has higher priority as Jane's expensive
        # order has been fulfilled
        expected_priorities = {steve_order.sid: 0.0,
                               jane_individual_order.sid: 1.0}

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=all_open_orders,
                fulfilled_orders=fulfilled_orders),
            expected_sorted_orders=all_open_orders,
            expected_priorities=expected_priorities)

        # Change the tab of the group order and now we should expect
        # Jane's individual order to have same priority as both
        # orders are relatively cheap to the expensive group order
        # and both have no fulfilled orders
        jane_group_order.tab = admin_tab
        jane_group_order.save()

        fulfilled_orders = [jane_group_order]

        expected_priorities = {steve_order.sid: 0.0,
                               jane_individual_order.sid: 0.0}

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=all_open_orders,
                fulfilled_orders=fulfilled_orders),
            expected_sorted_orders=all_open_orders,
            expected_priorities=expected_priorities)

    def test_nightly_pipeline_price_scenario(self):
        """Test the nightly jenkins pipeline scenario.

        The user kicking off the pipeline will have a tab limit higher
        than that of a normal user to be able to hold more resources.

        Note that the admin user tab limit doesn't have to be much
        higher than that of the normal user to be able to order many
        more orders. In this test the admin tab limit is just 2x the
        normal tab limit.
        """
        settings.ENABLE_ORDER_PRICE_PRIORITY = True
        admin = User.objects.get(id=1)
        admin_tab = admin.tabs.get()
        admin_tab.limit = 7.0
        admin_tab.save()
        bob = User.objects.create_user(username='Bob')
        alice = User.objects.create_user(username='Alice')
        joe = User.objects.create_user(username='Joe')
        manager = FulfillmentManager(item_tools)

        # Bob orders before the rush of the orders from the nightly pipeline.
        bob_order = self.create_order(
            time_created=datetime.now(utc),
            creator=bob,
            num_items=1,
            order_status=Order.STATUS_OPEN)

        # The pipeline creates 15 orders and then Alice opens an order.
        pipeline_orders_1 = [
            self.create_order(
                time_created=datetime.now(utc),
                creator=admin,
                num_items=1,
                order_status=Order.STATUS_OPEN)
            for _ in range(15)
        ]
        alice_order = self.create_order(
            time_created=datetime.now(utc),
            creator=alice,
            num_items=1,
            order_status=Order.STATUS_OPEN)

        # The pipeline creates another 15 orders and then Joe opens an order.
        pipeline_orders_2 = [
            self.create_order(
                time_created=datetime.now(utc),
                creator=admin,
                num_items=1,
                order_status=Order.STATUS_OPEN)
            for _ in range(15)
        ]
        joe_order = self.create_order(
            time_created=datetime.now(utc),
            creator=joe,
            num_items=1,
            order_status=Order.STATUS_OPEN)

        # Verify that the open orders are sorted by time_created initially
        # because they have the same price and no user has fulfilled items.
        # In this scenario, normal users will have to compete with the
        # pipeline based on their order creation time.
        all_open_orders = [bob_order] + pipeline_orders_1 + [alice_order] + \
            pipeline_orders_2 + [joe_order]
        expected_priorities = {
            order.sid: 0.0 for order in all_open_orders
        }

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=all_open_orders,
                fulfilled_orders=[]),
            expected_sorted_orders=all_open_orders,
            expected_priorities=expected_priorities)

        # Fulfill 15 of the pipeline's open orders and verify the open
        # orders from Bob, Alice, and Joe are then ordered ahead of
        # the remaining nightly open orders.
        for order in pipeline_orders_1:
            order.status = Order.STATUS_FULFILLED
            order.save()

        all_open_orders = \
            [bob_order, alice_order] + pipeline_orders_2 + [joe_order]
        expected_priorities = {
            # The remaining pipeline orders now have priority 1.0:
            #   order price = 1.0
            #   admin total fulfilled price = 15.0
            #   median_demand = 1.0 (median of [1,1,1,4.28])
            #   floor(((1.0 + 15.0) / 7.0) / (1.2 * 1)) = 1.0
            order.sid: 1.0 if order.owner == admin else 0.0
            for order in all_open_orders
        }
        expected_sorted_orders = \
            [bob_order, alice_order, joe_order] + pipeline_orders_2

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=all_open_orders,
                fulfilled_orders=pipeline_orders_1),
            expected_sorted_orders=expected_sorted_orders,
            expected_priorities=expected_priorities)
        self.assertEquals(manager._get_open_orders(), expected_sorted_orders)

        # Fulfill Bob's order it will not bump the open pipeline orders
        # back down to 0.0 because one order doesn't drive the median down.
        # Need atleast 50% of the orders to be fulfilled to have an impact on
        # the pipeline orders or need to bump up the tab limit of the pipeline
        # tab to drive down the median
        bob_order.status = Order.STATUS_FULFILLED
        bob_order.save()
        all_open_orders.remove(bob_order)

        expected_priorities = {
            # The remaining open pipeline orders go back to 0.0:
            #   order price = 1.0
            #   admin total fulfilled price = 15.0
            #   median_demand = 1.0 (median of [1,1,1,4.28])
            #   floor(((1.0 + 15.0) / 7.0) / (1.2 * 1.0)) = 0.0
            order.sid: 1.0 if order.owner == admin else 0.0
            for order in all_open_orders
        }
        expected_sorted_orders = \
            [alice_order, joe_order] + pipeline_orders_2

        self.assert_sorted_open_orders_by_price(
            sorted_orders_dict=manager._sort_open_orders_by_price(
                open_orders=all_open_orders,
                fulfilled_orders=pipeline_orders_1 + [bob_order]),
            expected_sorted_orders=expected_sorted_orders,
            expected_priorities=expected_priorities)
        self.assertEquals(manager._get_open_orders(), expected_sorted_orders)
