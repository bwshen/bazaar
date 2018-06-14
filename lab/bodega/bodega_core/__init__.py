"""Core generic functionality of Bodega."""
import logging

log = logging.getLogger(__name__)

default_app_config = 'bodega_core.apps.BodegaAppConfig'


class ItemManager(object):
    """Abstract base class for item managers."""

    # Cleanup statuses
    STATUS_NOT_MANAGING = 'NOT_MANAGING'
    STATUS_WAITING = 'WAITING'
    STATUS_FAILURE = 'FAILURE'
    STATUS_SUCCESS = 'SUCCESS'

    def get_non_rare_requirements(self):
        """Return a dictionary of requirements that filter out rare items.

        These requirements allow for order fulfillment to serve non-rare items
        whenever possible.
        """
        return {}

    def get_pending_items_queryset(self,
                                   item_queryset):
        """Return a queryset containing pending items.

        Pending items are items that are actively being created or recycled
        and are expected to be held by nothing in the future.
        """
        raise NotImplementedError(
            "Child classes need to implement get_pending_items_queryset.")

    def get_item_recipe(self, requirements):
        """Return the Recipe class for this Item."""
        raise NotImplementedError(
            "Child classes need to implement get_item_recipe.")

    def get_item_price(self, requirements):
        """Return the price of this Item based on its requirements.

        The price should aim to reflect the actual cost of the underlying
        infrastructure. The units are the estimated TCO dollars per hour
        of the infrastructure.

        For cloud items already using a rental model, this is straightforward.
        For on-prem items, we should include both the share of electricity,
        cooling, and rent costs for operating the hardware and also a share of
        the capital for acquiring the hardware. For tax purposes it's standard
        to depreciate computer hardware over 5 years, so the share of capital
        would be 0.0022815% per hour.

        Numbers from finance:
        ~$3700 monthly colo OPEX per rack, let's round up to $4000 = $5.55/hour
        ~$1750 CAPEX per Microcloud host, let's round up to $2000. The new
        hosts were going to get are actually ~$1450 per equivalent, but the
        vast majority is on the old hosts for now.

        Estimate conservatively that we fit ~10 Microcloud units of 12 hosts
        each per rack, so the OPEX per host is ~$30.83 or ~$0.043 per hour.

        Please read INFRA-1074 for more details.
        """
        raise NotImplementedError(
            "Child classes need to implement get_item_price.")

    def get_status(self, item):
        """Return one of the cleanup statuses from above."""
        raise NotImplementedError(
            "Child classes need to implement get_status.")

    def handle_cleanup(self, item):
        """Handle cleanup of an item."""
        raise NotImplementedError(
            "Child classes need to implement handle_cleanup.")

    def get_shelf_life(self, item):
        """Return the shelf life of the item.

        The shelf life of an Item represents how long we want to wait for to
        clean up an Item if it is created but never used. The default timedelta
        means the Item never perishes and we should not clean it up until it is
        used.
        """
        raise NotImplementedError(
            "Child classes need to implement get_shelf_life.")

    def taste_test(self, item, requirements):
        raise NotImplementedError(
            "Child classes need to implement taste_test.")

    def is_managing(self, item):
        """Indicate whether this manager is currently managing this item.

        Only one manager should ever claim responsibility for any given
        item. Only legacy item managers that outsource their work to
        JenkinsTask should override this. Other item managers should leave
        the default implementation.
        """
        return False

    def validate_item_requirements(self, item_requirements, user_sid,
                                   is_maintenance_order):
        """Check if the given item requirements are valid for this Item."""
        raise NotImplementedError(
            "Child classes need to implement validate_item_requirements.")


class ItemType:
    def __init__(self, name=None, plural_name=None, model=None,
                 queryset=None, filter_class=None, serializer_class=None,
                 manager_class=None):
        # Local imports to avoid polluting the module namespace and having
        # risk of conflicts / circular dependencies.
        from django.db.models.query import QuerySet
        from .exceptions import bodega_type_error

        if not isinstance(name, str):
            bodega_type_error(log, 'ItemType name must be a str')
        self.name = name

        if not isinstance(plural_name, str):
            bodega_type_error(log, 'ItemType plural_name must be a str')
        self.plural_name = plural_name

        if not isinstance(model, type):
            bodega_type_error(log, 'ItemType model must be a class')
        self.model = model

        if not isinstance(queryset, QuerySet):
            bodega_type_error(log, 'ItemType queryset must be a QuerySet')
        self.queryset = queryset

        if not isinstance(filter_class, type):
            bodega_type_error(log, 'ItemType filter_class must be a class')
        self.filter_class = filter_class

        if not isinstance(serializer_class, type):
            bodega_type_error(log, 'ItemType serializer_class must be a class')
        self.serializer_class = serializer_class

        if not isinstance(manager_class, type):
            bodega_type_error(log, 'ItemType manager_class must be a class')
        self.manager_class = manager_class


class Recipe(object):
    def __init__(self, requirements):
        self.requirements = requirements

    @property
    def required_ingredients(self):
        """Return a dictionary of required items for this item."""
        raise NotImplementedError(
            'Child classes need to implement required_ingredients')

    @property
    def creator_task(self):
        """Return the task class used to create this item.

        This task will be passed the requirements and the required items.
        """
        raise NotImplementedError(
            'Child classes need to implement creator_task.')
