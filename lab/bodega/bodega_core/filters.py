"""Reference: http://www.django-rest-framework.org/api-guide/filtering/.

In particular, see the DjangoFilterBackend section.
"""
from django import forms
from django.contrib.auth.models import User
from django.utils.six import string_types
from django.utils.translation import ugettext
from django_filters import (BooleanFilter, CharFilter, filters)
from sid_from_id.filters import (SidFromIdFilter, SidFromIdFilterSet)
from . import models


class ExtendedBooleanWidget(forms.Select):
    """Convert applicable values into Python's True/False.

    This is heavily based off of django_filters.widgets.BooleanWidget, and adds
    a few customizations to support convenient filtering with non-standard
    True/False values. This should be passed as a widget for BooleanFilter.
    """

    def __init__(self, attrs=None):
        choices = (('', ugettext('Unspecified')),
                   ('true', ugettext('Yes')),
                   ('false', ugettext('No')))
        super(ExtendedBooleanWidget, self).__init__(attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, string_types):
            value = value.lower()

        return {
            '1': True,
            '0': False,
            'y': True,
            'n': False,
            't': True,
            'f': False,
            'yes': True,
            'no': False,
            'true': True,
            'false': False,
            1: True,
            0: False,
            True: True,
            False: False,
        }.get(value, None)


class ExtendedBooleanFilter(BooleanFilter):
    """Extend the default BooleanFilter with ExtendedBooleanWidget.

    This is a convenience class, to be used for friendlier filtering. Keyword
    arguments are passed onwards (excepting 'widget' which should error).
    """

    def __init__(self, **kwargs):
        super(ExtendedBooleanFilter, self) \
            .__init__(widget=ExtendedBooleanWidget(), **kwargs)


class OrderStatusLiveFilter(ExtendedBooleanFilter):
    """Filter Orders based on predefined status sets for user convenience."""

    def __init__(self, *args, **kwargs):
        self.live_statuses = [
            models.Order.STATUS_FULFILLED,
            models.Order.STATUS_OPEN,
        ]

        super(OrderStatusLiveFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):

        if value in filters.EMPTY_VALUES:
            return super(OrderStatusLiveFilter, self).filter(qs, value)

        if value is True:
            return qs.filter(status__in=self.live_statuses)
        elif value is False:
            return qs.exclude(status__in=self.live_statuses)
        else:
            return qs.none()


class ItemFilter(SidFromIdFilterSet):
    """Filter for the generic Item model."""

    class Meta:
        model = models.Item
        fields = ['sid', 'state']


class OrderFilter(SidFromIdFilterSet):
    """Filter for the Order model."""

    # Filter for orders that were (partially) fulfilled by a given item SID.
    fulfilled_item = SidFromIdFilter(
        name='updates__item_fulfillments__item__id',
        sid_from_id_model=models.Item)

    owner_email = CharFilter(name='owner__email')
    owner_sid = SidFromIdFilter(name='owner__id', sid_from_id_model=User)
    tab_sid = SidFromIdFilter(name='tab__id', sid_from_id_model=models.Tab)

    status_live = OrderStatusLiveFilter(name='status')

    class Meta:
        model = models.Order
        fields = {
            'sid': ['exact'],
            'status': ['exact'],
            'fulfilled_item': ['exact'],
            'owner_email': ['exact'],
            'owner_sid': ['exact'],
            'time_created': ['exact', 'range', 'lt', 'lte', 'gt', 'gte'],
            'tab_sid': ['exact'],
            'tab_based_priority': ['exact', 'range', 'lt', 'lte', 'gt', 'gte']
        }


class OrderUpdateFilter(SidFromIdFilterSet):
    """Filter for the OrderUpdate model."""

    class Meta:
        model = models.OrderUpdate
        fields = ['sid', 'order', 'time_created']


class UserFilter(SidFromIdFilterSet):
    """Filter for the User model."""

    class Meta:
        model = User
        fields = ['sid', 'email']


class TabFilter(SidFromIdFilterSet):
    """Filter for the Tab model."""

    owner_sid = SidFromIdFilter(name='owner__id', sid_from_id_model=User)

    class Meta:
        model = models.Tab
        fields = ['sid', 'owner_sid']
