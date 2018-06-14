"""Register new RkTestYml Item."""

import logging
from bodega_core.models import Location, Order
from bodega_legacy_items.models import RktestYml
from django.core.management.base import BaseCommand
from django.db import transaction

log = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):

        parser.add_argument("-l", "--location", required=True,
                            help="Item location",
                            choices=["COLO", "HQ"])
        parser.add_argument('-p', "--platform", required=True,
                            help="Platform type",
                            choices=[_[0] for _ in RktestYml.PLATFORM_CHOICES])
        parser.add_argument('spec_files', nargs='+',
                            help=("Specification file in YAML format defining"
                                  "the RktestYml"))

    def handle(self, **options):

        location = Location.objects.get(name=options["location"])
        order = Order.objects.filter(status="CLOSED")[0]
        for spec_file in options["spec_files"]:
            log.info("Registering %s of platform type %s at location %s" %
                     (spec_file, options["platform"], options["location"]))

            with transaction.atomic():
                RktestYml.objects.create(held_by_object=order,
                                         platform=options["platform"],
                                         filename=spec_file,
                                         location=location)
            log.info("Done")
