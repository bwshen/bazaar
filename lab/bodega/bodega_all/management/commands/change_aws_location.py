"""Change AWS location to AWS-US-WEST-1."""
# TODO(stefan): Delete this file from Git
# https://rubrik.atlassian.net/browse/INFRA-1758

import logging
from bodega_core.models import Location
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        log.debug('Changing AWS Location object to AWS-US-WEST-1 if it exists')
        try:
            location = Location.objects.get(name='AWS')
            location.name = 'AWS-US-WEST-1'
            location.save()
            log.debug('Done.')
        except ObjectDoesNotExist:
            log.warning('Could not find AWS Location object.')
