"""Validator test cases."""

from datetime import datetime, timedelta
from pytz import utc

from bodega_core.exceptions import BodegaValidationError
from bodega_core.models import Order, OrderUpdate
from django.contrib.auth.models import User
from django.test import TestCase
from sid_from_id.encoder import get_sid
from . import validators


class ValidatorTestCase(TestCase):

    def test_validate_correct_order_update_items_delta(self):

        items_delta_yml = """
        pod1:
          type: 'rktest_yml'
          requirements:
            platform: 'DYNAPOD'
            linux_agent: True
        """

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

        items_delta_empty = ""

        # Validating a correctly formed YML should succeed and
        # not throw any exceptions.
        validators.validate_order_update_items_delta(items_delta_yml)
        validators.validate_order_update_items_delta(items_delta_json)
        validators.validate_order_update_items_delta(items_delta_empty)

    def test_validate_incorrect_order_update_items_delta(self):
        # Scanner Error due to missing ':' after 'pod1'
        # which will cause BodegaValidationError to be thrown
        items_delta_incorrect_yaml = """
          pod1
            type: 'rktest_yml'
            requirements:
            - platform:
            - linux_agent: True
        """

        items_delta_items_is_string = """
          Foo Bar
        """

        items_delta_item_no_type = """
          pod1:
            requirements:
              platform: 'DYNAPOD'
              linux_agent: True
        """

        items_delta_item_no_requirements = """
          pod1:
            type: 'rktest_yml'
        """

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_update_items_delta,
                          items_delta_incorrect_yaml)

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_update_items_delta,
                          items_delta_items_is_string)

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_update_items_delta,
                          items_delta_item_no_type)

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_update_items_delta,
                          items_delta_item_no_requirements)

    def test_validate_order_new_status(self):
        admin_user = User.objects.get(id=1)
        admin_tab = admin_user.tabs.get()
        open_order = Order.objects.create(status=Order.STATUS_OPEN,
                                          owner=admin_user,
                                          tab=admin_tab)
        fulfilled_order = Order.objects.create(status=Order.STATUS_FULFILLED,
                                               owner=admin_user,
                                               tab=admin_tab)
        closed_order = Order.objects.create(status=Order.STATUS_CLOSED,
                                            owner=admin_user,
                                            tab=admin_tab)

        # Users can never (re)open orders.
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_OPEN, open_order)
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_OPEN, fulfilled_order)
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_OPEN, closed_order)

        # Users can never mark orders as fulfilled, since we do that.
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_FULFILLED, open_order)
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_FULFILLED, fulfilled_order)
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_FULFILLED, closed_order)

        # Users can close open or fulfilled orders. The former is like
        # canceling an order, which is simpler for now, but we might want to
        # represent cancel states explicitly in the future.
        validators.validate_order_new_status(
            Order.STATUS_CLOSED, open_order)
        validators.validate_order_new_status(
            Order.STATUS_CLOSED, fulfilled_order)

        # Users can't re-close an already closed order.
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_new_status,
                          Order.STATUS_CLOSED, closed_order)

    def test_validate_order_time_limit_delta(self):
        # Order time limit should always be zero or positive
        user = User.objects.create_user(username='Foo',
                                        password='Bar')
        user_tab = user.tabs.get()
        open_order = Order.objects.create(status=Order.STATUS_OPEN,
                                          owner=user,
                                          tab=user_tab)
        OrderUpdate.objects.create(
            items_delta="",
            order=open_order,
            creator=user,
            time_limit_delta=timedelta(hours=4),
            expiration_time_limit_delta=timedelta(minutes=60))

        curr_time = datetime.now(utc)
        validators.validate_order_time_limit_delta(timedelta(minutes=0),
                                                   curr_time,
                                                   open_order,
                                                   user)
        validators.validate_order_time_limit_delta(timedelta(minutes=60),
                                                   curr_time,
                                                   open_order,
                                                   user)
        validators.validate_order_time_limit_delta(
            timedelta(hours=43, minutes=59),
            curr_time,
            open_order,
            user)

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_time_limit_delta,
                          timedelta(minutes=-60), curr_time, open_order, user)

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_time_limit_delta,
                          timedelta(hours=49), curr_time, open_order, user)

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_time_limit_delta,
                          timedelta(hours=44, minutes=1), curr_time,
                          open_order, user)

        validators.validate_order_time_limit_delta(
            timedelta(hours=43, minutes=59),
            curr_time + timedelta(hours=48),
            open_order,
            user)

        superuser = User.objects.create_superuser(
            username='John',
            password='Doe',
            email='john.doe@rubrik.com')

        validators.validate_order_time_limit_delta(timedelta(minutes=-60),
                                                   curr_time,
                                                   open_order,
                                                   superuser)
        validators.validate_order_time_limit_delta(timedelta(minutes=1000),
                                                   curr_time,
                                                   open_order,
                                                   superuser)

    def test_validate_extending_fulfilled_order(self):
        # Order time limit should always be zero or positive
        user = User.objects.create_user(username='Foo',
                                        password='Bar')
        user_tab = user.tabs.get()
        fulfilled_order = Order.objects.create(status=Order.STATUS_FULFILLED,
                                               owner=user,
                                               tab=user_tab)
        OrderUpdate.objects.create(
            items_delta="",
            order=fulfilled_order,
            creator=user,
            time_limit_delta=timedelta(hours=4),
            expiration_time_limit_delta=timedelta(minutes=60),
            new_status=Order.STATUS_FULFILLED)

        curr_time = datetime.now(utc)
        validators.validate_order_time_limit_delta(
            timedelta(hours=43, minutes=59),
            curr_time,
            fulfilled_order,
            user)
        OrderUpdate.objects.create(
            items_delta="",
            order=fulfilled_order,
            creator=user,
            time_limit_delta=timedelta(hours=43, minutes=59))

        self.assertRaises(BodegaValidationError,
                          validators.validate_order_time_limit_delta,
                          timedelta(minutes=10), curr_time,
                          fulfilled_order, user)
        validators.validate_order_time_limit_delta(
            timedelta(hours=43, minutes=59),
            curr_time + timedelta(hours=48),
            fulfilled_order,
            user)
        OrderUpdate.objects.create(
            items_delta="",
            order=fulfilled_order,
            creator=user,
            time_limit_delta=timedelta(hours=43, minutes=59))
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_time_limit_delta,
                          timedelta(hours=5), curr_time + timedelta(hours=48),
                          fulfilled_order, user)

    def test_validate_order_ownership_transfer(self):
        admin_user = User.objects.get(id=1)
        user_1 = User.objects.create_user(username='Jane',
                                          password='foobar',
                                          email='jane.doe@rubrik.com')
        user_1_tab = user_1.tabs.get()
        user_2 = User.objects.create_user(username='John',
                                          password='foobar',
                                          email='john.doe@rubrik.com')

        open_order = Order.objects.create(status=Order.STATUS_OPEN,
                                          owner=user_1,
                                          tab=user_1_tab)

        # Superusers and Order owners can transfer the Order
        validators.validate_order_ownership_transfer(user_2.email,
                                                     get_sid(user_2),
                                                     open_order,
                                                     user_1)
        validators.validate_order_ownership_transfer(user_2.email,
                                                     get_sid(user_2),
                                                     open_order,
                                                     admin_user)

        # Either email or sid can be used to transfer the order
        validators.validate_order_ownership_transfer(None,
                                                     get_sid(user_2),
                                                     open_order,
                                                     user_1)
        validators.validate_order_ownership_transfer(user_2.email,
                                                     None,
                                                     open_order,
                                                     admin_user)

        # One of email or sid must be provided
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_ownership_transfer,
                          None, None, open_order, user_2)

        # Users cannot transfer an Order ownership from other users
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_ownership_transfer,
                          user_2.email, get_sid(user_2), open_order, user_2)

        # Provided email must be valid
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_ownership_transfer,
                          "fakeemail", None, open_order, user_1)
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_ownership_transfer,
                          "fakeemail", None, open_order, admin_user)

        # Provided user sid must be valid
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_ownership_transfer,
                          None, "234567-abcdefg", open_order, user_1)
        self.assertRaises(BodegaValidationError,
                          validators.validate_order_ownership_transfer,
                          None, "234567-abcdefg", open_order, admin_user)
