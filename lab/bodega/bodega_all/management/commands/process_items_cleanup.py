"""Trigger one off ProcessItemsCleanupTask."""
import logging
from bodega_all.tasks import ProcessItemsCleanupTask
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        log.debug('Triggering one off ProcessItemsCleanup task.')
        ProcessItemsCleanupTask.delay()
