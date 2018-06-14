"""Test item types."""
from bodega_core import ItemType
from bodega_core.utils import ItemTools
from rest_framework import mixins
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from sid_from_id.views import SidFromIdGenericViewSet
from .filters import BasicItemFilter, ComplexItemFilter
from .item_managers import BasicItemManager, ComplexItemManager
from .models import BasicItem, ComplexItem
from .serializers import BasicItemSerializer, ComplexItemSerializer


class ItemBaseSerializer(HyperlinkedModelWithSidFromIdSerializer):
    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        item_fields = ('sid', 'url')


class ItemBaseViewSet(mixins.CreateModelMixin,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      SidFromIdGenericViewSet):
    pass


definitions = [
    ItemType(
        name='basic_item',
        plural_name='basic_items',
        model=BasicItem,
        queryset=BasicItem.objects.all(),
        filter_class=BasicItemFilter,
        serializer_class=BasicItemSerializer,
        manager_class=BasicItemManager),
    ItemType(
        name='complex_item',
        plural_name='complex_items',
        model=ComplexItem,
        queryset=ComplexItem.objects.all(),
        filter_class=ComplexItemFilter,
        serializer_class=ComplexItemSerializer,
        manager_class=ComplexItemManager)
]


item_tools = ItemTools(definitions,
                       ItemBaseSerializer,
                       ItemBaseViewSet)
