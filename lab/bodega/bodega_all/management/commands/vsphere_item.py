"""Populate Esx/Vcenter info in Bodega database."""

import logging
from pprint import pformat

from bodega_core.models import Location
from bodega_vsphere_items.models import EsxHost
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):
    ESX = "esx"

    def handle(self, *args, **options):
        host_type = options['subparser']
        options['location'] = Location.objects.get(name=options['location'])

        if host_type == self.ESX:
            self.process_esx(options)
        else:
            raise Exception("Cannot handle host type: %s" % host_type)

    def __create_item_args(self, valid_keys, options):
        item_args = dict()

        # Args to EsxHost property name map
        for opt_key, prop_key in valid_keys.items():
            if options[opt_key] is not None:
                item_args[prop_key] = options[opt_key]

        return item_args

    def process_esx(self, options):
        # We should define this separately for esx and vcenter because
        # models can change in terms of their properties. So easier to
        # just change one item and not impact the other
        valid_keys = dict(
            vcenter="vcenter",
            version="version",
            hostname="hostname",
            username="username",
            password="password",
            location="location"
        )

        item_args = self.__create_item_args(valid_keys, options)

        args = dict(
            ipv4=options['ipv4_address'],
            defaults=item_args
        )

        update_flag = True if options['action'] == "update" else False
        keyword = "Updating" if update_flag else "Adding"
        log.info("%s ESX host with following info:\n%s" %
                 (keyword, pformat(args)))

        self.process_item(EsxHost, args, update_flag, self.ESX)

    def process_item(self, model_obj, args, update_flag, host_type):
        action = "Updating" if update_flag else "Adding"

        p_args = pformat(args)
        log.debug("{action} {model_obj.__name__} with following "
                  "info:\n{p_args}".format(**locals()))
        if update_flag:
            item_obj, created = model_obj.objects.update_or_create(**args)
            item_obj.save()
            if created:
                log.debug("%s item successfully created" % host_type)
            else:
                log.debug("%s item successfully updated" % host_type)
        else:
            item_obj, created = model_obj.objects.get_or_create(**args)

            if not created:
                raise Exception("%s item is already present in database. "
                                "Use 'update' instead of 'add'"
                                % host_type)

            item_obj.save()
            log.debug("%s item successfully created" % host_type)

        return item_obj, created

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subparser")
        esx_parser = subparsers.add_parser(self.ESX,
                                           cmd=self.ESX,
                                           help="ESX info")

        esx_parser.add_argument('action', choices=["add", "update"])
        req_group = esx_parser.add_argument_group('required named arguments')

        req_group.add_argument('-i', '--ipv4_address',
                               required=True,
                               help="Ipv4 address of item")

        req_group.add_argument('-l', '--location',
                               required=True,
                               help="Network location of the item",
                               choices=Location.objects.values_list(
                                   'name', flat=True)
                               )
        req_group.add_argument('-vc', '--vcenter',
                               required=True,
                               help="VCenter where this item is located"
                               )

        esx_version_choices = [choice[0] for choice in EsxHost.VERSION_CHOICES]
        req_group.add_argument('-v', '--version',
                               required=True,
                               help="Version of the item",
                               choices=esx_version_choices)

        req_group.add_argument('-u', '--username', help="root/admin username")

        req_group.add_argument('-p', '--password', help="root/admin password")

        esx_parser.add_argument('-H', '--hostname',
                                help="resolvable hostname of item")
