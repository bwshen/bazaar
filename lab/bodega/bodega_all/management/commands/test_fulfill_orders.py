"""Bodega order fulfillment tests."""
from datetime import timedelta
from bodega_all.item_types import item_tools
from bodega_all.tasks import (FulfillOrderTask, get_order_fulfillers,
                              SetItemToMaintenanceTask)
from bodega_core.fulfillment import FulfillmentManager
from bodega_core.models import Item, Location, Order, OrderUpdate, Network
from bodega_legacy_items.models import RktestYml
from django.contrib.auth.models import User
from django.test import TestCase
from rkelery.models import Task


class FulfillOrdersTestCase(TestCase):
    def setUp(self):
        self.order_update_creator = User.objects.get(id=1)
        self.user = User.objects.create_user(username='Foo',
                                             password='Bar')
        self.tab = self.user.tabs.get()
        self.location_hq = Location.objects.get(name='HQ')
        self.location_colo = Location.objects.get(name='COLO')
        self.network_hq = \
            Network.objects.filter(location=self.location_hq).first()
        self.network_colo = \
            Network.objects.filter(location=self.location_colo).first()

        self.dynapod1 = RktestYml.objects.create(
            filename='dynapod1.yml',
            location=self.location_hq,
            network=self.network_hq,
            platform='DYNAPOD',
            linux_agent=True)

        self.dynapod2 = RktestYml.objects.create(
            filename='dynapod2.yml',
            location=self.location_hq,
            network=self.network_hq,
            platform='DYNAPOD')

        self.dynapod3 = RktestYml.objects.create(
            filename='dynapod3.yml',
            location=self.location_colo,
            network=self.network_colo,
            platform='DYNAPOD')

    def create_order_fulfiller(self, order_sid, selected_item_sids):
        return Task.objects.create(
            task=FulfillOrderTask.name,
            args=[order_sid, selected_item_sids],
            kwargs={})

    def create_item_maintenance_setter(self, item_sid):
        return Task.objects.create(
            task=SetItemToMaintenanceTask.name,
            args=[item_sid],
            kwargs={})


class SingleOrderSingleItemTestCase(FulfillOrdersTestCase):
    def setUp(self):
        super(SingleOrderSingleItemTestCase, self).setUp()

        items_delta_json = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
                "linux_agent": true
              }
          },
        }
        """

        self.order = Order.objects.create(
            status=Order.STATUS_OPEN,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json,
            order=self.order,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

    def testSingleOrderSingleItem(self):

        manager = FulfillmentManager(item_tools)
        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()

        order = Order.objects.get(id=self.order.id)
        self.assertEqual(order.status, Order.STATUS_FULFILLED)

        fulfilled_items = order.fulfilled_items
        self.assertEqual(fulfilled_items['pod1'].id, self.dynapod1.id)


class SingleOrderMultipleItemsTestCase(FulfillOrdersTestCase):
    def setUp(self):
        super(SingleOrderMultipleItemsTestCase, self).setUp()

        items_delta_json = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          },
          "pod2": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          }
        }
        """

        self.order = Order.objects.create(status=Order.STATUS_OPEN,
                                          owner=self.user,
                                          tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json,
            order=self.order,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

    def testSingleOrderMultipleItems(self):
        manager = FulfillmentManager(item_tools)
        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()

        order = Order.objects.get(id=self.order.id)
        self.assertEqual(order.status, Order.STATUS_FULFILLED)

        fulfilled_items = order.fulfilled_items
        self.assertTrue(fulfilled_items['pod1'].id)
        self.assertTrue(fulfilled_items['pod2'].id)


class MultipleOrderTestCase(FulfillOrdersTestCase):
    def setUp(self):
        super(MultipleOrderTestCase, self).setUp()

        items_delta_json_1 = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
                "linux_agent": true
              }
          },
        }
        """

        self.order_1 = Order.objects.create(status=Order.STATUS_OPEN,
                                            owner=self.user,
                                            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json_1,
            order=self.order_1,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

        items_delta_json_2 = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
                "linux_agent": true
              }
          },
          "pod2": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          }
        }
        """

        self.order_2 = Order.objects.create(status=Order.STATUS_OPEN,
                                            owner=self.user,
                                            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json_2,
            order=self.order_2,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

    def testMultipleOrders(self):
        manager = FulfillmentManager(item_tools)
        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()

        order = Order.objects.get(id=self.order_1.id)
        self.assertEqual(order.status, Order.STATUS_FULFILLED)

        fulfilled_items = order.fulfilled_items
        self.assertEqual(fulfilled_items['pod1'].id, self.dynapod1.id)

        order = Order.objects.get(id=self.order_2.id)
        self.assertEqual(order.status, Order.STATUS_OPEN)

        fulfilled_items = order.fulfilled_items
        self.assertRaises(KeyError, lambda: fulfilled_items['pod1'])
        self.assertRaises(KeyError, lambda: fulfilled_items['pod2'])


class MaintenanceOrderTestCase(FulfillOrdersTestCase):
    def setUp(self):
        super(MaintenanceOrderTestCase, self).setUp()

        items_delta_json_1 = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
                "linux_agent": true
              }
          },
        }
        """

        self.order_1 = Order.objects.create(status=Order.STATUS_OPEN,
                                            owner=self.user,
                                            tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json_1,
            order=self.order_1,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

    def testMaintenanceOrder(self):
        manager = FulfillmentManager(item_tools)
        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()

        order = Order.objects.get(id=self.order_1.id)
        self.assertEqual(order.status, Order.STATUS_FULFILLED)

        items_delta_json = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          },
          "pod2": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          },
          "pod3": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          }
        }
        """

        order_2 = Order.objects.create(status=Order.STATUS_OPEN,
                                       maintenance=True,
                                       owner=self.user,
                                       tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json,
            order=order_2,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))
        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()
        self.dynapod1.refresh_from_db()
        self.dynapod2.refresh_from_db()
        self.dynapod3.refresh_from_db()

        self.assertEqual(self.dynapod1.state, Item.STATE_MAINTENANCE)
        self.assertEqual(self.dynapod2.state, Item.STATE_MAINTENANCE)
        self.assertEqual(self.dynapod3.state, Item.STATE_MAINTENANCE)

        self.assertEqual(self.dynapod1.held_by.sid, self.order_1.sid)
        self.assertEqual(self.dynapod2.held_by, None)

        items_delta_json = """
        {
          "pod1": {
            "type": "rktest_yml",
            "requirements":
              {
                "platform": "DYNAPOD",
              }
          },
        }
        """

        order_3 = Order.objects.create(status=Order.STATUS_OPEN,
                                       owner=self.user,
                                       tab=self.tab)
        OrderUpdate.objects.create(
            items_delta=items_delta_json,
            order=order_3,
            creator=self.user,
            expiration_time_limit_delta=timedelta(minutes=60))

        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()
        order_3.refresh_from_db()
        self.assertEqual(order_3.status, Order.STATUS_OPEN)

        self.dynapod1.held_by = None
        self.dynapod1.save()

        manager.fulfill_open_orders(
            get_order_fulfillers, self.create_order_fulfiller,
            self.create_item_maintenance_setter, self.order_update_creator)
        Task.objects.simulate_run_all()
        self.dynapod1.refresh_from_db()
        self.dynapod2.refresh_from_db()
        self.dynapod3.refresh_from_db()

        self.assertEqual(self.dynapod1.held_by.sid, order_2.sid)
        self.assertEqual(self.dynapod2.held_by.sid, order_2.sid)
        self.assertEqual(self.dynapod3.held_by.sid, order_2.sid)
