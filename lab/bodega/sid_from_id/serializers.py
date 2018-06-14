from rest_framework import serializers

from .encoder import get_sid
from .fields import (
    HyperlinkedIdentityFieldUsingSid, HyperlinkedRelatedFieldUsingSid)


class HyperlinkedModelWithSidFromIdSerializer(serializers
                                              .HyperlinkedModelSerializer):
    """Hyperlinked model serializer supporting SID from ID field."""

    # Indicate that we want these serializers to use the SID versions of
    # the URL fields.
    serializer_related_field = HyperlinkedRelatedFieldUsingSid
    serializer_url_field = HyperlinkedIdentityFieldUsingSid

    # Define an sid field in the serializer. In many cases this is unnecessary
    # because models using ModelWithSidFromId as a base class have the sid
    # property. However, making the sid a SerializerMethodField here makes it
    # work even for models that don't have the sid property such as User.
    sid = serializers.SerializerMethodField()

    def get_sid(self, obj):
        return get_sid(obj)

    class Meta:
        extra_kwargs = {
            # Indicate the model field name used to look up an instance and the
            # URL keyword argument that goes with it. These need to match the
            # values chosen in SidFromIdGenericViewSet.
            'url': {
                'lookup_field': 'sid',
                'lookup_url_kwarg': 'sid'
            }
        }
