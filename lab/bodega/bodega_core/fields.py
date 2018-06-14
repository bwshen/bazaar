"""Bodega custom fields."""
import json
from rest_framework import serializers


class ItemsField(serializers.CharField):
    def to_representation(self, obj):
        """Serialize the underlying items value (a dict) as a string.

        This is to be consistent with the string that the client provides,
        as opposed to JSON.

        Do this by just dumping the items value as JSON. Ideally we should
        actually show any YAML formatting/features (especially comments) that
        the client included by computing it from the series of string (as
        opposed to dict) patches from the order updates. We'll do that later.
        """
        return super(ItemsField, self).to_representation(
            json.dumps(obj, sort_keys=True))

        # Skip overriding the superclass implementation of to_internal_value
        # to prevent errors. Callers to the method (serializers) will instead
        # deserialize and create the items field separately


class LocationField(serializers.CharField):
    def to_representation(self, obj):
        """Represent Location object as a string for backwards compatibility.

        The existing RktestYml and SdDevMachine api endpoints expect location
        to be a string with the name of the location. Since location is now
        represented as a ForeignKey, we should return location as a string but
        internally, when someone adds an object with a location specified,
        convert the location into the correct object.
        """
        return super(LocationField, self).to_representation(obj.name)

        # Skip overriding the superclass implementation of to_internal_value
        # to prevent errors. Callers to the method (serializers) will instead
        # deserialize and create the location field separately


class NetworkField(serializers.CharField):
    def to_representation(self, obj):
        """Serialize the Network field as a string."""
        return super(NetworkField, self).to_representation(obj.name)

        # Skip overriding the superclass implementation of to_internal_value
        # to prevent errors. Callers to the method (serializers) will instead
        # deserialize and create the location field separately
