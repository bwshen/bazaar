"""Populate Reserved IP addresses into Bodega database"""

import logging
import socket
import struct
from bodega_core.models import Location, Network
from bodega_generic_items.models import IpAddress
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def _get_start_and_end_ip(self, possible_range):
        split_ip = possible_range.split('-')
        if len(split_ip) == 1:
            return (split_ip[0].strip(), split_ip[0].strip())
        else:
            return (split_ip[0].strip(), split_ip[1].strip())

    def _convert_ranges_to_individual_ips(self, ip_range):
        ip_addresses = []
        start, end = self._get_start_and_end_ip(ip_range)
        start_i = struct.unpack('>I', socket.inet_aton(start))[0]
        end_i = struct.unpack('>I', socket.inet_aton(end))[0] + 1
        for i in range(start_i, end_i):
            ip_str = socket.inet_ntoa(struct.pack('>I', i))
            ip_addresses.append(ip_str)
        return ip_addresses

    def _store_ip_addresses_in_db(self, location_str, ip_addresses,
                                  network_str):
        log.debug('Retrieving location entry from db for %s' % location_str)
        location_entry = Location.objects.get(name=location_str)
        network_entry = Network.objects.get(name=network_str,
                                            location=location_entry)
        for ip_address in ip_addresses:
            self._store_ip_address_in_db(location_entry, ip_address,
                                         network_entry)

    def _store_ip_address_in_db(self, location_entry, ip_address,
                                network_entry):
        try:
            IpAddress.objects.get(ip=ip_address)
            log.debug('An entry for %s already exists in db.'
                      'So skip adding it again' % ip_address)
            return None
        except IpAddress.DoesNotExist:
            log.debug('Adding ip address %s to db' % ip_address)
        IpAddress.objects.create(ip=ip_address, location=location_entry,
                                 network=network_entry)

    def handle(self, *args, **options):
        ip_address_range = options['ip_range']
        ip_range_location_str = options['location']
        ip_range_network_str = options['network']
        self._store_ip_addresses_in_db(
            ip_range_location_str,
            self._convert_ranges_to_individual_ips(ip_address_range),
            ip_range_network_str)

    def add_arguments(self, parser):
        ip_range_help_text = (
            'Range of IP addresses. Examples:'
            '\'10.0.0.1-10.0.0.3\' or 10.0.0.1 or \'10.0.2.1-10.0.3.255\'')
        parser.add_argument(
            'ip_range',
            type=str,
            help=ip_range_help_text)
        parser.add_argument(
            'location',
            type=str,
            choices=Location.objects.values_list('name', flat=True))
        parser.add_argument(
            'network',
            type=str,
            choices=Location.objects.values_list('name', flat=True))
