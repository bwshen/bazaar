"""Reference: http://www.django-rest-framework.org/api-guide/viewsets/."""

import bodega_core
import bodega_legacy_items
import rkelery
import rkelery.filters

from bodega_core.pagination import SmallResultsSetPagination
from django.contrib.auth.models import User
from rest_framework import mixins, viewsets
from sid_from_id.views import SidFromIdGenericViewSet
from . import serializers
from .item_types import item_tools, ItemBaseSerializer


class ItemViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  SidFromIdGenericViewSet):
    """A viewset for items."""

    serializer_class = ItemBaseSerializer
    filter_class = bodega_core.filters.ItemFilter

    # By specifying a queryset here, the basename for the Item route is
    # automatically set when we register the route. The queryset that is
    # actually used comes from the get_queryset() function.
    queryset = bodega_core.models.Item.objects.all()

    def get_queryset(self):
        return item_tools.get_generic_queryset_for_all_item_types()


class JenkinsTaskViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         SidFromIdGenericViewSet):
    """A viewset for Jenkins tasks."""

    queryset = bodega_legacy_items.models.JenkinsTask.objects.all().order_by(
        '-time_uuid_updated')
    serializer_class = bodega_legacy_items.serializers.JenkinsTaskSerializer
    filter_class = bodega_legacy_items.filters.JenkinsTaskFilter


class OrderViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   SidFromIdGenericViewSet):
    """A viewset for orders."""

    queryset = bodega_core.models.Order.objects.all().order_by(
        'tab_based_priority', 'time_created')
    detail_serializer_class = serializers.OrderDetailSerializer
    serializer_class = serializers.OrderSerializer
    filter_class = bodega_core.filters.OrderFilter
    pagination_class = SmallResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return self.serializer_class
        else:
            return self.detail_serializer_class


class OrderUpdateViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         SidFromIdGenericViewSet):
    """A viewset for updating orders."""

    queryset = bodega_core.models.OrderUpdate.objects.all().order_by(
        '-time_created')
    serializer_class = serializers.OrderUpdateSerializer
    filter_class = bodega_core.filters.OrderUpdateFilter


# Create a user viewset that only supports getting users and updating them.
# We don't support adding/removing users through the REST API because we mainly
# use Google authentication and automate adding/removing the local user
# objects associated with a Google login.
class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  SidFromIdGenericViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = serializers.UserSerializer
    filter_class = bodega_core.filters.UserFilter


# Create a profile viewset which shows the currently logged in user's profile.
class ProfileViewSet(mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    queryset = User.objects.all()

    serializer_class = serializers.ProfileSerializer

    # Override get_object (which will be called by RetrieveModelMixin) to
    # simply return the current user for the request. Normally this
    # implementation would use a dynamic component from the request URL to
    # identify the object instance to get, but we don't have a dynamic
    # component for the user's profile URL.
    def get_object(self):
        return self.request.user

    # This is the trick to make /profile return the profile instance instead of
    # trying to list profiles. It's a bit of a hack which works by making the
    # list method delegate to the retrieve method which is for getting a single
    # object instance. The reason for this hack is that Django REST Framework's
    # default router (and all of its niceness in generating a root API view) is
    # meant for API endpoints representing plural collections, not singletons
    # as the user profile is. The correct way to add a singleton endpoint to
    # the router is by creating a custom router derived from the default
    # router, but that effort isn't really worthwhile for this one-off use
    # case.
    def list(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).retrieve(request, *args, **kwargs)


class TaskViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = rkelery.models.Task.objects.all().order_by(
        '-time_published')
    serializer_class = serializers.TaskSerializer
    detail_serializer_class = serializers.TaskDetailSerializer
    filter_class = rkelery.filters.TaskFilter
    lookup_field = 'task_id'
    lookup_url_kwarg = 'id'

    def get_serializer_class(self):
        if self.action == 'list':
            return self.serializer_class
        else:
            return self.detail_serializer_class


class TabViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.UpdateModelMixin,
                 SidFromIdGenericViewSet):
    """A viewset for tabs."""

    queryset = bodega_core.models.Tab.objects.all()
    detail_serializer_class = serializers.TabDetailSerializer
    serializer_class = serializers.TabSerializer
    filter_class = bodega_core.filters.TabFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return self.serializer_class
        else:
            return self.detail_serializer_class
