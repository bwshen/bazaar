import django_filters
from rest_framework import filters

from .encoder import SidEncoder


class SidFromIdFilter(django_filters.CharFilter):
    """A CharFilter that decodes the input filter value as a SID before
    doing the filtering."""

    def __init__(self, *args, **kwargs):
        self.sid_from_id_model = kwargs.pop('sid_from_id_model', None)
        super(SidFromIdFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        # For types we don't handle or empty values, just use the parent
        # implementation.
        if (not(isinstance(value, str) or isinstance(value, unicode)) or
           value in django_filters.filters.EMPTY_VALUES):
            return super(SidFromIdFilter, self).filter(qs, value)

        # Get a SidEncoder for the appropriate model.
        if self.sid_from_id_model is not None:
            sid_from_id_model = self.sid_from_id_model
        else:
            sid_from_id_model = qs.model
        encoder = SidEncoder(sid_from_id_model)

        # Decode the SID value, returning no results if it's an invalid value.
        try:
            decoded_value = encoder.decode(value)
        except ValueError:
            return qs.none()

        # Use the parent implementation with the now decoded value.
        return super(SidFromIdFilter, self).filter(qs, decoded_value)


class SidFromIdFilterSet(filters.FilterSet):
    """A FilterSet that automatically defines an sid filter."""
    sid = SidFromIdFilter(name='pk')
