"""Test order ejection."""
import time
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from pytz import utc
from .ejection import EjectionManager
from .models import Order, OrderUpdate


class EjectionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='Foo')
        self.tab = self.user.tabs.get()
        self.order = Order.objects.create(
            status=Order.STATUS_FULFILLED,
            owner=self.user,
            tab=self.tab)
        OrderUpdate.objects.create(
            order=self.order,
            creator=self.user,
            time_limit_delta=timedelta(minutes=240),
            new_status=Order.STATUS_FULFILLED)

        self.curr_time = datetime.now(utc)
        # Sleep here so this is guaranteed to be the earliest update
        time.sleep(1)

    def set_latest_order_update_time_created(self, order, time):
        order_update = order.updates.last()
        order_update.time_created = time
        order_update.save()

    def test_order_ejection_4_hours(self):
        """Test order ejections for a four hour order.

        We expect to have a periodic notices at the 1 hr and 2 hour mark.
        We should then have final notices at 3 hrs and 20 minutes,
        3 hrs and 40 minutes, and 4 hours.
        """
        manager = EjectionManager(self.user)
        curr_time = self.curr_time

        manager.process_order_time_limit(self.order, curr_time)
        self.assertEqual(self.order.number_of_ejection_notices, 1)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time)

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=61))
        self.assertEqual(self.order.number_of_ejection_notices, 1)

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=121))
        self.assertEqual(self.order.number_of_ejection_notices, 2)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=121))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=181))
        self.assertEqual(self.order.number_of_ejection_notices, 3)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=181))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=211))
        self.assertEqual(self.order.number_of_ejection_notices, 4)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=211))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=226))
        self.assertEqual(self.order.number_of_ejection_notices, 5)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=226))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=230))
        self.assertEqual(self.order.number_of_ejection_notices, 5)

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=241))
        self.assertEqual(self.order.number_of_ejection_notices, 5)
        self.assertEqual(self.order.status, Order.STATUS_CLOSED)

    def test_order_ejection_4_hours_extended_24(self):
        """Test order ejections for a four hour order.

        We expect to have a periodic notices at the 1 hr and 2 hour mark.
        We should then have final notices at 3 hrs and 20 minutes,
        3 hrs and 40 minutes, and 4 hours.
        """
        manager = EjectionManager(self.user)
        curr_time = self.curr_time

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=61))
        self.assertEqual(self.order.number_of_ejection_notices, 1)

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=121))
        self.assertEqual(self.order.number_of_ejection_notices, 2)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=121))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=181))
        self.assertEqual(self.order.number_of_ejection_notices, 3)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=181))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=211))
        self.assertEqual(self.order.number_of_ejection_notices, 4)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=211))

        OrderUpdate.objects.create(
            order=self.order,
            creator=self.user,
            time_limit_delta=timedelta(hours=24))
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=211, seconds=1))

        curr_time = curr_time + timedelta(minutes=211, seconds=1)
        # Now that we've extended the Order by 24 hours left to go, we should
        # start getting periodic notifications
        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=31))
        self.assertEqual(self.order.number_of_ejection_notices, 5)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=31))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=511))
        self.assertEqual(self.order.number_of_ejection_notices, 6)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=511))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=991))
        self.assertEqual(self.order.number_of_ejection_notices, 7)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=991))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=1231))
        self.assertEqual(self.order.number_of_ejection_notices, 8)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=1231))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=1351))
        self.assertEqual(self.order.number_of_ejection_notices, 9)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=1351))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=1411))
        self.assertEqual(self.order.number_of_ejection_notices, 10)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=1411))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=1441))
        self.assertEqual(self.order.number_of_ejection_notices, 11)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=1441))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=1456))
        self.assertEqual(self.order.number_of_ejection_notices, 12)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=1456))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=1471))
        self.assertEqual(self.order.number_of_ejection_notices, 12)
        self.assertEqual(self.order.status, Order.STATUS_CLOSED)

    def test_stuck_ejection_manager_task(self):
        """Test order ejections for a four hour order with a stuck task.

        We start processing the order after it has surpassed its time
        limit but expect to have three notifications equally spaced apart
        before ejection.
        """
        manager = EjectionManager(self.user)
        curr_time = self.curr_time

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=241))
        self.assertEqual(self.order.number_of_ejection_notices, 1)
        self.set_latest_order_update_time_created(
            self.order,
            curr_time + timedelta(minutes=241))

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=255))
        self.assertEqual(self.order.number_of_ejection_notices, 1)
        self.assertEqual(self.order.status, Order.STATUS_FULFILLED)

        manager.process_order_time_limit(self.order,
                                         curr_time + timedelta(minutes=257))
        self.assertEqual(self.order.number_of_ejection_notices, 1)
        self.assertEqual(self.order.status, Order.STATUS_CLOSED)
