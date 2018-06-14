from rest_framework import viewsets

from .encoder import SidEncoder


class SidFromIdGenericViewSet(viewsets.GenericViewSet):
    """A viewset for models with SID from ID field."""

    # Indicate the model field name used to look up an instance and the
    # URL keyword argument that goes with it. These need to match the
    # values chosen in HyperlinkedModelWithSidFromIdSerializer.
    lookup_field = 'sid'
    lookup_url_kwarg = 'sid'

    def get_object(self):
        # Figure out the URL keyword argument that GenericViewSet.get_object
        # will be using.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if self.lookup_field == 'sid':
            # Get the value passed in for the URL keyword argument.
            sid = self.kwargs[lookup_url_kwarg]

            # Explicitly set lookup_url_kwarg so that Django REST Framework
            # still uses that instead of lookup_field, which we're about to
            # change.
            self.lookup_url_kwarg = lookup_url_kwarg

            # Translate lookup_field to the underlying decoded field name.
            self.lookup_field = 'pk'

            # Decode the SID to get the ID, and pass that as the value for
            # the URL keyword argument so that GenericViewSet.get_object
            # will use it as the value for the model lookup.
            self.kwargs[lookup_url_kwarg] = (
                SidEncoder(self.serializer_class.Meta.model).decode(sid))

        # Defer to the parent implementation.
        return super(SidFromIdGenericViewSet, self).get_object()
