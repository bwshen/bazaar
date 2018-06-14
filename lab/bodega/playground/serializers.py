from django.contrib.auth.models import User
from rest_framework import serializers
from .fields import (
    SpecificToyHyperlinkField, QueryParamHyperlinkedRelatedField)
from .models import Ball, Doll, Stick, Toy

# Serializers are one of the major concepts in Django REST Framework. Although
# REST APIs are mainly for offering CRUD operations on our models, it's
# generally a good idea to take control of how this is exposed. In most cases
# this comes in the form of choosing which fields to include in the JSON
# representations. Other times it can include translating between the API
# representation of field and the underlying model's representation, or
# creating virtual fields which exist only at the API layer and are backed by
# some combination or computation of underlying model fields.

# Read about serializers at
# http://www.django-rest-framework.org/api-guide/serializers/


# Create a toy serializer. We generally choose to inherit from
# HyperlinkedModelSerializer because it gives us a handy "url" field that is a
# more HTTP-friendly substitute for our model's ID (primary key), and both the
# browsable API and other REST clients can very conveniently navigate between
# different objects in our app.
class ToySerializer(serializers.HyperlinkedModelSerializer):
    # This is a custom field that we defined to dynamically determine a toy
    # object's specific detail view URL. The source being '*' means that the
    # entire toy object is passed in as the obj argument for
    # SpecificToyHyperlinkField.get_url. Otherwise the default would have been
    # to try passing in the contents of a field with the same name
    # (specific_toy) which in this case does not exist.
    #
    # The specific_toy URL is only for clients to conveniently find the URL
    # of the toy. Writing it is not supported, so we set read_only to True.
    specific_toy = SpecificToyHyperlinkField(source='*', read_only=True)

    def create(self, validated_data):
        owner = self.context['request'].user
        validated_data['owner'] = owner
        return super(ToySerializer, self).create(validated_data)

    class Meta:
        # This tells DRF what the underlying model is for this serializer.
        model = Toy

        # Define some base fields that all toy serializers will expose. No
        # translation is necessary for these. For the 'owner' and 'players'
        # fields, DRF will represent the underlying foreign keys as URLs to
        # User objects. This includes support for PUT and POST so that clients
        # can set owners/players by URL.
        base_fields = ('id', 'url', 'name', 'owner', 'players')

        # For the generic toy serializer, include a link to the specific toy
        # type's detail view.
        fields = base_fields + ('specific_toy',)

        read_only_fields = ('owner',)


# Create a base class for specific toy serializers to define things that we
# want in common for them all.
class SpecificToySerializer(serializers.HyperlinkedModelSerializer):
    # Every specific toy serializer should include a URL to the generic toy
    # detail view.
    toy = serializers.HyperlinkedRelatedField(
        source='toy_ptr', view_name='toy-detail', read_only=True)

    def create(self, validated_data):
        owner = self.context['request'].user
        validated_data['owner'] = owner
        return super(SpecificToySerializer, self).create(validated_data)

    class Meta:
        base_fields = ToySerializer.Meta.base_fields + ('toy',)
        read_only_fields = ToySerializer.Meta.read_only_fields


# A ball serializer, adding the ball-specific fields.
class BallSerializer(SpecificToySerializer):
    class Meta:
        model = Ball
        fields = SpecificToySerializer.Meta.base_fields + ('radius',)
        read_only_fields = SpecificToySerializer.Meta.read_only_fields


# A stick serializer, adding the stick-specific fields.
class StickSerializer(SpecificToySerializer):
    class Meta:
        model = Stick
        fields = SpecificToySerializer.Meta.base_fields + ('length',)
        read_only_fields = SpecificToySerializer.Meta.read_only_fields


# A doll serializer, adding the doll-specific fields.
class DollSerializer(SpecificToySerializer):
    class Meta:
        model = Doll
        fields = SpecificToySerializer.Meta.base_fields + ('sex', 'race',)
        read_only_fields = SpecificToySerializer.Meta.read_only_fields


# Create a user serializer as well, backed by Django's built in user model.
# It's not uncommon to expose the user objects through the REST API so that
# the UI can present directory listings, object ownership, activity logs, etc
# which all relate to the users in the application.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    # Convenience URL to a query for the toys this user owns.
    toys = QueryParamHyperlinkedRelatedField(
        source='*',
        view_name='toy-list',
        lookup_field='id',
        lookup_url_kwarg='owner_id',
        read_only=True)

    # Convenience URL to a query for the toys this user is playing with.
    playing_with_toys = QueryParamHyperlinkedRelatedField(
        source='*',
        view_name='toy-list',
        lookup_field='id',
        lookup_url_kwarg='player_id',
        read_only=True)

    class Meta:
        model = User

        # Note that we choose the fields to expose, in particular NOT exposing
        # the password.
        fields = ('id', 'url', 'username', 'first_name', 'last_name', 'email',
                  'is_superuser', 'toys', 'playing_with_toys')

        # For Google logins these fields are just local caches of what's stored
        # in Google. Don't support updating them since that would be confusing.
        read_only_fields = ('username', 'first_name', 'last_name', 'email')


# Create a profile serializer which includes a superset of the fields in the
# user serializer. This is a way to show sensitive fields only to the user
# themselves and not to other users.
class ProfileSerializer(UserSerializer):
    auth_token = serializers.CharField(source='auth_token.key')

    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + ('auth_token',)
        read_only_fields = UserSerializer.Meta.read_only_fields + \
            ('auth_token',)
