"""Item-specific managers."""
import logging
import subprocess
from datetime import timedelta

from bodega_core import ItemManager
from bodega_core.exceptions import bodega_validation_error
from bodega_core.models import Item
from django.contrib.contenttypes.models import ContentType
from rkelery import states
from rkelery.models import Task
from .filters import MssqlServerFilter, UbuntuMachineFilter
from .models import MssqlServer, UbuntuMachine
from .recipes import MssqlServerRecipe, UbuntuMachineRecipe
from .tasks import (CreateMssqlServerFromAwsTask,
                    CreateUbuntuMachineFromAwsTask,
                    CreateUbuntuMachineFromVSphereTask)

log = logging.getLogger(__name__)


class MssqlServerManager(ItemManager):

    def __init__(self, **kwargs):
        """Item manager for MssqlServer Item."""
        pass

    def get_item_creator(self, requirements):
        return None

    def get_item_price(self, requirements):
        """m4.large, MSSQL2012, US West (Oregon).

        $0.1 per Hour
        https://aws.amazon.com/ec2/pricing/on-demand/
        """
        return 0.1

    def get_item_recipe(self, requirements):
        return MssqlServerRecipe(requirements)

    def get_pending_items_queryset(self,
                                   item_queryset):
        acceptable_tasks_qs = Task.objects.filter(
            task=CreateMssqlServerFromAwsTask.name,
            task_result__status__in=states.UNREADY_STATES)
        tasks_content_type = \
            ContentType.objects.get_for_model(Task)

        acceptable_tasks_ids = [task.id for task in acceptable_tasks_qs]
        held_by_task_qs = item_queryset.filter(
            held_by_object_id__in=acceptable_tasks_ids,
            held_by_content_type_id=tasks_content_type)
        return held_by_task_qs

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta(hours=6)

    def get_status(self, mssql_server):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, mssql_server):
        item_destroyer = mssql_server.item_destroyer

        if item_destroyer:
            log.debug('Triggering %s for %s'
                      % (item_destroyer, mssql_server))
            item_destroyer.delay()
        else:
            log.info('%s does not have an item destroyer so mark it as %s.'
                     % (mssql_server, Item.STATE_DESTROYED))
            mssql_server.held_by = None
            mssql_server.state = Item.STATE_DESTROYED
            mssql_server.save()

    def taste_test(self, mssql_server, requirements):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = MssqlServerFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the mssql_server item type.'
                             % field)
                bodega_validation_error(log, error_msg)
            if field == 'model' and \
                    value not in MssqlServer.get_available_models():
                error_msg = ('Model "%s" is not valid for the mssql_server '
                             'item type.'
                             % value)
                bodega_validation_error(log, error_msg)


class UbuntuMachineManager(ItemManager):

    def __init__(self, **kwargs):
        """Item manager for UbuntuMachine Item."""
        pass

    def get_item_creator(self, requirements):
        return None

    def get_item_price(self, requirements):
        """m4.large, Linux, US West (Oregon).

        $0.1 per Hour
        https://aws.amazon.com/ec2/pricing/on-demand/
        """
        return 0.1

    def get_item_recipe(self, requirements):
        return UbuntuMachineRecipe(requirements)

    def get_pending_items_queryset(self,
                                   item_queryset):
        task_names = [CreateUbuntuMachineFromAwsTask.name,
                      CreateUbuntuMachineFromVSphereTask.name]
        acceptable_tasks_qs = Task.objects.filter(
            task__in=task_names,
            task_result__status__in=states.UNREADY_STATES)
        tasks_content_type = \
            ContentType.objects.get_for_model(Task)

        acceptable_tasks_ids = [task.id for task in acceptable_tasks_qs]
        held_by_task_qs = item_queryset.filter(
            held_by_object_id__in=acceptable_tasks_ids,
            held_by_content_type_id=tasks_content_type)
        return held_by_task_qs

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta(hours=8)

    def get_status(self, ubuntu_machine):
        return ItemManager.STATUS_SUCCESS

    def handle_cleanup(self, ubuntu_machine):
        item_destroyer = ubuntu_machine.item_destroyer

        if item_destroyer:
            log.debug('Triggering %s for %s'
                      % (item_destroyer, ubuntu_machine))
            item_destroyer.delay()
        else:
            log.info('%s does not have an item destroyer so mark it as %s.'
                     % (ubuntu_machine, Item.STATE_DESTROYED))
            ubuntu_machine.held_by = None
            ubuntu_machine.state = Item.STATE_DESTROYED
            ubuntu_machine.save()

    def taste_test(self, ubuntu_item, requirements):
        return True

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        for field, value in item_requirements.items():
            filters = UbuntuMachineFilter.get_filters()
            if field not in filters:
                error_msg = ('"%s" is not a recognized requirement name for '
                             'the ubuntu_machine item type.'
                             % field)
                bodega_validation_error(log, error_msg)
            if field == 'model' and \
                    (value not in UbuntuMachine.get_available_models()):
                error_msg = ('Model "%s" is not valid for the ubuntu_machine '
                             'item type.'
                             % value)
                bodega_validation_error(log, error_msg)
            if field == 'root_disk_size' and \
                    (int(value) not in
                        UbuntuMachine.get_available_root_sizes()):
                error_msg = ('Root disk size "%s" is not valid. '
                             'Currently only %s GB  are supported.'
                             % (value,
                                UbuntuMachine.get_available_root_sizes()))
                bodega_validation_error(log, error_msg)
            if field == 'kernel_version' and \
                    (value not in
                        UbuntuMachine.get_available_kernel_versions()):
                error_msg = ('Kernel "%s" is not valid for the ubuntu_machine '
                             'item type. Currently kernels 3.13 and 4.13 '
                             'are supported.'
                             % value)
                bodega_validation_error(log, error_msg)


class IpAddressManager(ItemManager):

    def __init__(self, **kwargs):
        """Item manager for IpAddress Item."""
        pass

    def get_item_creator(self, requirements):
        return None

    def get_item_price(self, requirements):
        return 1.0

    def get_item_recipe(self, requirements):
        return None

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        return timedelta()

    def get_status(self, ip_address):
        return ItemManager.STATUS_SUCCESS

    def get_pending_items_queryset(self,
                                   item_queryset):
        return item_queryset.none()

    def handle_cleanup(self, ip_address):
        ip_address.held_by = None
        ip_address.save()

    def taste_test(self, ip_address, requirements):
        """Ensure the IP address is not reachable."""
        # Ideally, there would be another IP address manager which
        # would validate if the IPv4 address is being used or not.
        # For now, we do a best-effort nmap scan
        # Note: This is not fool-proof. This kind of ping-scan
        # is susceptible to false negatives.
        # Note2: We use the -sn flag instead of -sO or -PO which require root
        # perms
        try:
            nmap_output = \
                subprocess.check_output(["nmap", "-sn", ip_address.ip])
            if '0 hosts up' in nmap_output.decode('utf-8'):
                return True
            else:
                log.warn('Could successfully connect to %s.'
                         'This is not expected and may indicate a problem with'
                         ' this IP address. Aborting' % repr(ip_address))
                return False
        except subprocess.CalledProcessError as nmap_exception:
            log.warn('Could not complete nmap scan. Got error %s' %
                     repr(nmap_exception))
        except Exception as e:
            log.warn('Unexpected exception %s' % e)
        return False

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        return
