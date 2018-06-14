"""Test item filters."""
from bodega_core.filters import ExtendedBooleanFilter
from sid_from_id.filters import SidFromIdFilterSet
from .models import BasicItem, ComplexItem


class BasicItemFilter(SidFromIdFilterSet):
    boolean = ExtendedBooleanFilter()

    class Meta:
        model = BasicItem
        fields = ['sid', 'boolean', 'string', 'choice']


class ComplexItemFilter(SidFromIdFilterSet):
    boolean = ExtendedBooleanFilter()

    class Meta:
        model = ComplexItem
        fields = ['sid', 'number']
