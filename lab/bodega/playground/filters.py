import django_filters
from rest_framework import filters
from .models import Toy

# Read about Django REST Framework filtering at
# http://www.django-rest-framework.org/api-guide/filtering/
# in particular the DjangoFilterBackend section.

# This is a filter set defining the filters that can be used on a given toy
# view. Each filter defined in the body of the class becomes a query parameter
# in the REST API, with the query parameter value passed to a filter predicate.
# Most filter predicates perform some kind of check against a field. The
# special notation `__` means to drill into the field to use a subfield. So
# for example `owner__id` means to use `owner.id`.
class ToyFilter(filters.FilterSet):
    # owner_id matches on the toy owner's ID.
    owner_id = django_filters.NumberFilter(name='owner__id')

    # player_id matches on any toy player's ID.
    player_id = django_filters.NumberFilter(name='players__id')

    class Meta:
        model = Toy
        fields = ['owner_id', 'player_id']
