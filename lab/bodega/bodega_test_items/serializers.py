"""Test item serializers."""
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from .models import BasicItem, ComplexItem


class BasicItemSerializer(HyperlinkedModelWithSidFromIdSerializer):
    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = BasicItem
        fields = ('sid', 'url', 'boolean', 'string', 'choice')


class ComplexItemSerializer(HyperlinkedModelWithSidFromIdSerializer):
    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        model = ComplexItem
        fields = ('sid', 'number')
