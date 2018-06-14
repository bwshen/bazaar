"""Test Bodega permissions."""

from bodega_core.models import Location, Network
from bodega_legacy_items.models import RktestYml
from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class PermissionTests(APITestCase):

    def setUp(self):
        self.location_hq = Location.objects.get(name='HQ')
        self.location_colo = Location.objects.get(name='COLO')
        self.network_hq = Network.objects.get(location=self.location_hq)
        User.objects.create_user(
            username='Foo',
            password='Bar',
            email='john.doe@rubrik.com')
        User.objects.create_superuser(
            username='Jack',
            password='Bar',
            email='jack.doe@rubrik.com')

    def test_item_permissions_for_user(self):
        """Test item permissions logic.

        Users should be able to perform a GET request on Items
        but should not be able to POST any new ones. Regular users
        should not be allowed to change or delete Items.
        """
        self.client.login(username='Foo', password='Bar')

        response = self.client.post(
            '/api/items/')
        self.assertEquals(response.status_code, 405)

        item = RktestYml.objects.create(filename='item1.yml',
                                        location=self.location_hq,
                                        network=self.network_hq)

        response = self.client.get('/api/items/' + item.sid + '/')
        self.assertEquals(response.status_code, 200)

        response = self.client.patch('/api/items/' + item.sid + '/')
        self.assertEquals(response.status_code, 405)

        response = self.client.delete('/api/items/' + item.sid + '/')
        self.assertEquals(response.status_code, 405)

        # Test that superusers are able to delete and update
        self.client.login(username='Jack', password='Bar')
        response = self.client.post('/api/items/')
        self.assertEquals(response.status_code, 405)

        response = self.client.patch('/api/items/' + item.sid + '/')
        self.assertEquals(response.status_code, 405)

        response = self.client.delete('/api/items/' + item.sid + '/')
        self.assertEquals(response.status_code, 405)

    def test_order_permissions_for_user(self):
        """Test for Order permissions for regular User.

        A regular user should be able to create an Order and also
        perform a GET on the Order. However, they should not be
        able to change or delete the Order (outside of creating
        an OrderUpdate) once it has been created.
        """
        self.client.login(username='Foo', password='Bar')

        response = self.client.post(
            '/api/orders/',
            {'status': 'OPEN', 'items': '{}'},
            format='json')
        self.assertEquals(response.status_code, 201)

        order_sid = response.json()['sid']

        response = self.client.get('/api/orders/' + order_sid + '/',
                                   format='json')
        self.assertEquals(response.status_code, 200)

        response = self.client.patch(
            '/api/orders/' + order_sid + '/',
            {'status': 'CLOSED'},
            format='json')
        self.assertEquals(response.status_code, 405)

        response = self.client.delete('/api/orders/' + order_sid + '/',
                                      format='json')
        self.assertEquals(response.status_code, 405)

    def test_order_update_permissions_for_user(self):
        """Test for OrderUpdate permissions for regular User.

        A regular user should be able to create an Order and also
        subsequent OrderUpdates for that order. However, they should
        not be able to change or delete any existing OrderUpdates.
        Furthermore, they should not be able to create an OrderUpdate
        for any Orders that do not belong to them.
        """
        self.client.login(username='Foo', password='Bar')

        response = self.client.post('/api/orders/',
                                    {'status': 'OPEN', 'items': '{}'},
                                    format='json')
        self.assertEquals(response.status_code, 201)

        order_sid = response.json()['sid']

        response = self.client.post(
            '/api/order_updates/',
            {'order_sid': order_sid, 'items_delta': '{}'},
            format='json')
        self.assertEquals(response.status_code, 400)

        response = self.client.post(
            '/api/order_updates/',
            {'order_sid': order_sid, 'comment': 'UnitTest'},
            format='json')
        self.assertEquals(response.status_code, 201)

        order_update_sid = response.json()['sid']

        response = self.client.patch(
            '/api/order_updates/' + order_update_sid + '/',
            {'items_delta': '{test}'},
            format='json')
        self.assertEquals(response.status_code, 405)

        response = self.client.delete(
            '/api/order_updates/' + order_update_sid + '/',
            format='json')
        self.assertEquals(response.status_code, 405)

        # Make sure users cannot create updates for other people's orders
        User.objects.create_user(
            username='Jane',
            password='Bar',
            email='jane.doe@rubrik.com')

        self.client.login(username='Jane', password='Bar')

        response = self.client.post(
            '/api/order_updates/',
            {'order_sid': order_sid, 'items_delta': '{}'},
            format='json')
        self.assertEquals(response.status_code, 400)

        # Make sure superusers can create an update for other people
        self.client.login(username='Jack', password='Bar')

        response = self.client.post(
            '/api/order_updates/',
            {'order_sid': order_sid, 'comment': 'Test as admin'},
            format='json')
        self.assertEquals(response.status_code, 201)
