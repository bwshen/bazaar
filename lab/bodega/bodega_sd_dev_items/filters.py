"""Filters for Bodega Sd Dev items."""
from django_filters import CharFilter

# flake8: noqa I100 # Turn off broken import ordering check as flake8 have bug
from bodega_core.filters import ExtendedBooleanFilter
from sid_from_id.filters import SidFromIdFilterSet
from .models import SdDevMachine


class SdDevMachineFilter(SidFromIdFilterSet):
    """Filter for the SdDevMachine model."""

    location = CharFilter(name='location__name', method='filter_location')
    network = CharFilter(name='network__name')
    privileged_mode = ExtendedBooleanFilter(name='privileged_mode')
    version = CharFilter(name='version')

    def filter_location(self, queryset, name, value):
        """Filter location with and without underscores.

        This supports more human-intuitive locations on top of the
        underscore-prefixed locations defined in the models. Ignore the 'name'
        parameter here - we know we're filtering on location.
        """
        if value == '_COLO':
            return queryset.filter(location__name='COLO')
        elif value == '_HQ':
            return queryset.filter(location__name='HQ')
        return queryset.filter(location__name=value)

    class Meta:
        model = SdDevMachine
        fields = ['sid',
                  'model',
                  'location',
                  'network',
                  'privileged_mode',
                  'version',
                  'state']
