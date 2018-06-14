from rest_framework import serializers

from .encoder import get_sid


class HyperlinkedRelatedFieldUsingSid(serializers.HyperlinkedRelatedField):
    lookup_field = 'sid'
    lookup_url_kwarg = 'sid'

    def get_url(self, obj, view_name, request, format):
        """Reimplementation of serializers.HyperlinkedRelatedField.get_url to
        get the lookup value using get_sid instead of as an attribute. The
        attribute doesn't always exist on models we don't control such as User.
        """

        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk in (None, ''):
            return None

        lookup_value = get_sid(obj)
        kwargs = {self.lookup_url_kwarg: lookup_value}
        return self.reverse(
            view_name, kwargs=kwargs, request=request, format=format)


class HyperlinkedIdentityFieldUsingSid(HyperlinkedRelatedFieldUsingSid,
                                       serializers.HyperlinkedIdentityField):
    """Take the implementation of HyperlinkedIdentityField with overrides from
    HyperlinkedRelatedFieldUsingSid.
    """
    pass
