from rest_framework import serializers
from rest_framework.reverse import reverse
from urllib import urlencode
from .models import Ball, Doll, Stick, Toy


# This defines a custom field which dynamically determines a toy object's
# specific detail view URL. We need it because the basic URL fields statically
# choose the viewset.
class SpecificToyHyperlinkField(serializers.HyperlinkedRelatedField):
    # We won't be using this, but set it to a value to prevent the
    # HyperlinkedRelatedField constructor from complaining.
    view_name = 'unused'

    def get_url(self, obj, view_name, request, format):
        # Start with no view_name as we will try to look up different objects
        # in order to find the specific view.
        view_name = None

        # For each of the specific toy types that are possible, try to look
        # up the corresponding related object. If this toy is not of that type,
        # the lookup will fail with a DoesNotExist exception from that model
        # class, which we will ignore. If it doesn't fail, we will set
        # view_name to the detail view name for that REST endpoint.

        try:
            obj.ball
            view_name = 'ball-detail'
        except Ball.DoesNotExist:
            pass

        try:
            obj.doll
            view_name = 'doll-detail'
        except Doll.DoesNotExist:
            pass

        try:
            obj.stick
            view_name = 'stick-detail'
        except Stick.DoesNotExist:
            pass

        # If none of the lookups succeeded, we still won't have a view name so
        # just return None. The serialized URL will be null.
        if view_name is None:
            return None

        # Otherwise, take the view name we got and add the object ID as the
        # argument, plus forward the other keyword arguments to reverse a full
        # URL for that object.
        return reverse(
            view_name, args=[obj.id], request=request, format=format)

    # If we were supporting writes to this field, we would have to implement
    # this method for DRF to get the underlying model instance given its URL.
    # For simplicity, we won't support this.
    def get_object(self, queryset, view_name, view_args, view_kwargs):
        raise NotImplementedError(
            'Getting a toy object for writing is not supported.')


# This defines a custom field with slightly different behavior from the
# standard HyperlinkedRelatedField. Instead of linking to a related object
# through a path parameter, link through a query parameter.
class QueryParamHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    # Override the get_url behavior to use lookup_url_kwarg and lookup_field
    # in a query parameter instead of a path parameter.
    def get_url(self, obj, view_name, request, format):
        view_url = reverse(
            self.view_name, request=request, format=format)
        query = {
            self.lookup_url_kwarg: getattr(obj, self.lookup_field)
        }
        return '%s?%s' % (view_url, urlencode(query))

    # It's not generally possible to get an object out of a URL with a query
    # parameter as query parameters are usually for filtering lists of other
    # objects.
    def get_object(self, queryset, view_name, view_args, view_kwargs):
        raise NotImplementedError(
            'Getting an object for writing from a query param URL is not ' +
            'supported.')
