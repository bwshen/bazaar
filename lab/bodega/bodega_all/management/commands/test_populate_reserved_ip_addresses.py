"""Unit tests for populate_reserved_ip_addresses command"""

from bodega_all.management.commands.populate_reserved_ip_addresses \
    import Command
from bodega_core.models import Location, Network
from bodega_generic_items.models import IpAddress
from django.test import TestCase


class PopulateReservedIpAddressesCommandTestCase(TestCase):

    def testPopulateReservedIpAddressCommandE2E_givenARange(self):
        command = Command()
        command.handle(**{'ip_range': '10.0.0.1-10.0.0.3', 'location': 'COLO',
                          'network': 'vlan1'})
        stored_ip_addresses = list(
            IpAddress.objects.values_list('ip', 'location__name'))
        self.assertEqual(stored_ip_addresses,
                         [('10.0.0.1', 'COLO'),
                          ('10.0.0.2', 'COLO'),
                          ('10.0.0.3', 'COLO')])

    def testPopulateReservedIpAddressCommandE2E_givenASingleIp(self):
        command = Command()
        command.handle(**{'ip_range': '10.0.0.1', 'location': 'COLO',
                          'network': 'vlan1'})
        stored_ip_addresses = list(
            IpAddress.objects.values_list('ip', 'location__name'))
        self.assertEqual(stored_ip_addresses, [('10.0.0.1', 'COLO')])

    def testStoreIpAddressInDbWithExistingAddress(self):
        location_entry = Location.objects.get(name='HQ')
        network_entry = Network.objects.get(location=location_entry,
                                            name='vlan1')
        IpAddress.objects.create(ip='1.1.1.1', location=location_entry,
                                 network=network_entry)
        self.assertEqual(IpAddress.objects.count(), 1)
        command = Command()
        command._store_ip_address_in_db(location_entry, '1.1.1.1',
                                        network_entry)
        self.assertEqual(IpAddress.objects.count(), 1)

    def testStoreIpAddressInDbWithNewAddress(self):
        location_entry = Location.objects.get(name='HQ')
        network_entry = Network.objects.get(location=location_entry,
                                            name='vlan1')
        command = Command()
        command._store_ip_address_in_db(location_entry, '1.1.1.1',
                                        network_entry)
        self.assertEqual(IpAddress.objects.count(), 1)

    def testStoreIpAddressWithInvalidLocation(self):
        command = Command()
        with self.assertRaises(Location.DoesNotExist) as expected_exception:
            command._store_ip_addresses_in_db('BLAH', ['192.168.1.1'], 'vlan1')
        self.assertIsNotNone(expected_exception)  # else lint will complain
