"""Lower level Bodega utilities."""
from bodega_core.models import Item
from rest_framework import serializers
from . import exceptions


def get_remote_field_name(item_type):
    return item_type.model._meta.parents[Item].remote_field.name


def create_item_serializer_class(base_class, item_type_def):
    class ItemSerializer(base_class, item_type_def.serializer_class):

        item_type = serializers.SerializerMethodField()

        def get_item_type(self, item):
            return item_type_def.name

        class Meta(item_type_def.serializer_class.Meta):
            model = item_type_def.model
            fields = (
                getattr(base_class.Meta, 'item_fields', ()) +
                getattr(item_type_def.serializer_class.Meta, 'fields', ()) +
                ('item_type',))
            read_only_fields = (
                getattr(base_class.Meta, 'read_only_fields', ()) +
                getattr(item_type_def.serializer_class.Meta,
                        'read_only_fields', ()) +
                ('item_type',))

    ItemSerializer.__name__ = '%sSerializer' % item_type_def.model.__name__
    return ItemSerializer


def create_item_view_set_class(base_class, item_type, item_serializer_class):
    class ItemViewSet(base_class):
        queryset = item_type.queryset
        serializer_class = item_serializer_class
        filter_class = item_type.filter_class

        def get_queryset(self):
            queryset = super(ItemViewSet, self).get_queryset()
            if self.action == 'list':
                return queryset.exclude(state=Item.STATE_DESTROYED)
            else:
                return queryset

    ItemViewSet.__name__ = '%sViewSet' % item_type.model.__name__
    return ItemViewSet


class ItemTools(object):
    def __init__(self, item_types, base_serializer_class, base_view_set_class):
        """Create item tools."""
        self.item_types = {
            item_type.name: item_type for item_type in item_types
        }
        self.item_types_by_field_name = {
            get_remote_field_name(item_type): item_type
            for item_type in item_types
        }
        self.serializer_classes = {
            item_type.name:
                create_item_serializer_class(base_serializer_class, item_type)
            for item_type in item_types
        }
        self.view_set_classes = {
            item_type.name: create_item_view_set_class(
                base_view_set_class, item_type,
                self.serializer_classes[item_type.name])
            for item_type in item_types
        }

    def register_routes(self, router):
        for item_type in self.item_types.values():
            view = self.view_set_classes[item_type.name]
            router.register(item_type.plural_name, view)

    def find_eligible_items_for_order_items(self, order_items,
                                            prefiltered_items_querysets=None):
        """Get all QuerySets corresponding to the order_items.

        Takes an order and, if the order is OPEN, returns a QuerySet for each
        item stored in a dictionary under its corresponding nickname.
        """
        querysets = {}
        for nickname, item in order_items.items():
            if prefiltered_items_querysets \
                    and item['type'] in prefiltered_items_querysets:
                prefiltered_items_queryset = \
                    prefiltered_items_querysets[item['type']]
            else:
                prefiltered_items_queryset = None

            querysets[nickname] = \
                self.find_eligible_items_for_requirements(
                    item['type'],
                    item['requirements'],
                    prefiltered_items_queryset)

        return querysets

    def find_eligible_items_for_requirements(self, item_type,
                                             item_requirements={},
                                             prefiltered_items_queryset=None):
        """Get a QuerySet of an item type filtered by requirements.

        This expects an item_type name corresponding to one of the ItemType
        definitions along with a dictionary/JSON mapping of item requirements.
        Currently, only inclusive equality requirements are supported.

        No validation is performed on the input, as we expect validation to be
        handled at the serializer level.

        TODO: This currently ignores requirements on fields that don't exist
        (i.e.  item_requirements={"notafield": "_COLO"} returns the full set).
        We could validate with filter_class.filters...

        >>> type = "rktest_yml"
        >>> requirements = {"location": "_COLO"}
        >>> item_tools.find_eligible_items_for_requirements(type, requirements)
        <QuerySet [<RktestYml: RktestYml(sid=Dp1iE-Y7cLLK,
                                         filename=dynapod-colo-16.yml)>, ...]>
        """
        item_type_def = self.item_types.get(item_type, None)
        if item_type_def is None:
            raise exceptions.BodegaValueError(
                'item_type=%s was not recognized. Expecting one of: %s' %
                (repr(item_type), repr(self.item_types.keys())))
        if prefiltered_items_queryset is None:
            prefiltered_items_queryset = item_type_def.queryset.all()

        return item_type_def.filter_class(item_requirements,
                                          prefiltered_items_queryset).qs

    def get_generic_queryset_for_all_item_types(self):
        generic_item_qs = Item.objects.none()
        for item_type in self.item_types.keys():
            specific_item_qs = self.get_queryset_for_item_type(item_type)
            item_ids = [item.id for item in specific_item_qs]
            generic_item_qs = \
                generic_item_qs | Item.objects.filter(id__in=item_ids)

        return generic_item_qs

    def get_queryset_for_item_type(self, item_type):
        item_type_def = self.item_types.get(item_type, None)
        if item_type_def is None:
            raise exceptions.BodegaValueError(
                'item_type=%s was not recognized. Expecting one of: %s' %
                (repr(item_type), repr(self.item_types.keys())))
        return item_type_def.queryset.all()

    def get_specific_item_field_name(self, generic_item):
        for field_name in self.item_types_by_field_name.keys():
            if hasattr(generic_item, field_name):
                return field_name

        return None

    def get_specific_item(self, generic_item):
        field_name = self.get_specific_item_field_name(generic_item)
        if field_name is None:
            return None

        return getattr(generic_item, field_name)

    def get_manager_class(self, generic_item):
        field_name = self.get_specific_item_field_name(generic_item)
        if field_name is None:
            return None

        return self.item_types_by_field_name[field_name].manager_class

    def get_serializer_class(self, generic_item):
        field_name = self.get_specific_item_field_name(generic_item)
        if field_name is None:
            return None

        item_type = self.item_types_by_field_name[field_name]
        return self.serializer_classes[item_type.name]

    # Return a dictionary of price per item in the list of items passed
    def get_prices_for_items(self, items):
        item_prices = {}
        for (nickname, item) in items:
            item_type = item['type']
            item_requirements = item['requirements']
            item_manager = \
                self.item_types[item_type].manager_class()
            item_price = \
                item_manager.get_item_price(item_requirements)
            item_prices[nickname] = item_price

        return item_prices
