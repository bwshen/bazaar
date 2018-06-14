"""All supported Bodega item types."""
import bodega_cdm_items.item_types
import bodega_crdb_dev_items.item_types
import bodega_generic_items.item_types
import bodega_legacy_items.item_types
import bodega_sd_dev_items.item_types
import bodega_vsphere_items.item_types
from bodega_core.models import Item, Order
from bodega_core.utils import ItemTools
from bodega_legacy_items.models import JenkinsTask
from generic_relations.relations import GenericRelatedField
from rest_framework import mixins
from rest_framework.reverse import reverse
from rest_framework.serializers import HyperlinkedRelatedField
from rkelery.models import Task
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from sid_from_id.views import SidFromIdGenericViewSet
from .utils import get_related_url_fields


class SpecificItemHyperlinkField(HyperlinkedRelatedField):
    """Dynamically determines the item-specific detailed view URL."""

    view_name = 'unused'  # Prevents super-class constructor from complaining

    def get_url(self, obj, view_name, request, format):
        view_name = 'item-detail'

        field_name = item_tools.get_specific_item_field_name(obj)
        if field_name is not None:
            view_name = '%s-detail' % field_name

        # Create a specialized URL for this item
        return reverse(
            view_name, args=[obj.sid], request=request, format=format)

    # If we were supporting writes to this field, we would have to implement
    # this method for DRF to get the underlying model instance given its URL.
    # For simplicity, we won't support this.
    def get_object(self, queryset, view_name, view_args, view_kwargs):
        raise NotImplementedError(
            'Getting a resource object for writing is not supported.')


class ItemBaseSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Base serializer for the Item models."""

    # Virtual field for resource-specific view
    specific_item = SpecificItemHyperlinkField(
        source='*',
        read_only=True)

    held_by = GenericRelatedField(
        get_related_url_fields(Item, Order, JenkinsTask, Task),
        read_only=True)

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Meta class."""

        model = Item
        item_fields = ('sid', 'url', 'name', 'held_by', 'time_held_by_updated',
                       'state')
        fields = item_fields + ('specific_item',)

        read_only_fields = ('state', 'time_held_by_updated',)


class ItemBaseViewSet(mixins.CreateModelMixin,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      SidFromIdGenericViewSet):
    pass


definitions = (
    bodega_cdm_items.item_types.definitions +
    bodega_crdb_dev_items.item_types.definitions +
    bodega_generic_items.item_types.definitions +
    bodega_legacy_items.item_types.definitions +
    bodega_sd_dev_items.item_types.definitions +
    bodega_vsphere_items.item_types.definitions
)

item_tools = ItemTools(definitions,
                       ItemBaseSerializer,
                       ItemBaseViewSet)
