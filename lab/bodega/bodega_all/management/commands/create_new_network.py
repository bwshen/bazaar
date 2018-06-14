"""Create a new Network in Bodega."""

import logging
from bodega_core.models import Location, Network
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('location', type=str)
        parser.add_argument('name', type=str)

    def handle(self, *args, **options):
        location_name = options['location']
        name = options['name']

        log.debug('Creating new network with location of %s and name %s.'
                  % (location_name, name))
        location = Location.objects.get(name=location_name)
        Network.objects.create(location=location, name=name)
        log.debug('Done.')
