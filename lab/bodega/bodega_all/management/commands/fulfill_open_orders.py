"""Trigger one off FulfillOpenOrdersTask."""
import logging
from bodega_all.tasks import FulfillOpenOrdersTask
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        log.debug('Triggering one off FulfillOpenOrders task.')
        FulfillOpenOrdersTask.delay()
