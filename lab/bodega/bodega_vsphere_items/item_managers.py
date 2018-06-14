"""Managers for vsphere items."""
import logging

from datetime import timedelta

from bodega_core import ItemManager
from bodega_utils.ssh import send_remote_command


log = logging.getLogger(__name__)


class EsxHostManager(ItemManager):

    def get_item_creator(self, requirements):
        return None

    def get_item_price(self, requirements):
        return 0.09

    def get_item_recipe(self, requirements):
        return None

    def get_status(self, ip_address):
        return ItemManager.STATUS_SUCCESS

    def get_pending_items_queryset(self,
                                   item_queryset):
        return item_queryset.none()

    def get_shelf_life(self, esx_host_item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta()

    def handle_cleanup(self, esx_item):
        log.info("Triggering EsxHost item_destroyer")
        # For now we are not doing anything in item destroyer. Once we
        # have native cleanup workflow in bodega (kt, stefan), then we can
        # add clean up code here.
        esx_item.held_by = None
        esx_item.save()

    def taste_test(self, esx_host_item, requirements):
        """Check host is reachable."""
        cmd = "ls"
        send_remote_command(ip_address=esx_host_item.ipv4,
                            cmd=cmd,
                            username=esx_host_item.username,
                            password=esx_host_item.password)
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        # TODO: (Rohit) Recent change needs this function. Will get back to
        # adding logic for this once we have the yaml converter code in. For
        # now not validating anything.
        return
