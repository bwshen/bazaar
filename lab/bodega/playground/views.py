from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import mixins, viewsets
from .filters import ToyFilter
from .models import Ball, Doll, Stick, Toy
from .serializers import (
    BallSerializer, DollSerializer, ProfileSerializer, ToySerializer,
    StickSerializer, UserSerializer)

# Create your views here.

# In traditional Django apps, we would define views which are responsible for
# applying business logic to the models and using that to render HTML templates
# on the server side so that the client sees an HTML page with different
# contents depending on the current application data. However, we are building
# a more modern app based on REST APIs and a a single page application for the
# UI, so our HTML will be dynamic on the client side instead of the server
# side. In the server side views, we will focus on dynamically creating REST
# API responses.

# Read about Django REST Framework views at
# http://www.django-rest-framework.org/api-guide/views/


# Create a toy view. We use the fullest feature form of DRF's views, which are
# viewsets. These generate views using the most common REST API conventions for
# GET, PUT, POST, DELETE, etc and map them to intuitive CRUD operations on
# models, all while needing very little code. We only write code where we want
# our REST API to behave differently from common conventions.
#
# Read about viewsets at
# http://www.django-rest-framework.org/api-guide/viewsets/
#
# Most viewsets use ModelViewSet, but for the generic toys listing use a
# viewset which supports everything except creation. This forces all toy
# creation through the specific toy viewsets.
class ToyViewSet(mixins.DestroyModelMixin,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.UpdateModelMixin,
                 viewsets.GenericViewSet):
    # A viewset presents a collection of resources with GET, PUT, POST, DELETE
    # operations. The queryset setting is required and tells DRF what the
    # underlying collection of model objects is. In more advanced cases
    # (particularly when an app has some form of RBAC), the queryset may be
    # restricted using some filter. In other cases, simply getting all objects
    # is appropriate.
    queryset = Toy.objects.all()

    # The other required setting is the serializer_class, which just tells DRF
    # what serializer class we use for this viewset.
    serializer_class = ToySerializer

    # Use these toy-specific filters with this view.
    filter_class = ToyFilter


# Create the specific toy type viewsets. These are pretty simple, just linking
# the specific toy models with their specific serializers.


class BallViewSet(viewsets.ModelViewSet):
    queryset = Ball.objects.all()
    serializer_class = BallSerializer
    filter_class = ToyFilter


class StickViewSet(viewsets.ModelViewSet):
    queryset = Stick.objects.all()
    serializer_class = StickSerializer
    filter_class = ToyFilter


class DollViewSet(viewsets.ModelViewSet):
    queryset = Doll.objects.all()
    serializer_class = DollSerializer
    filter_class = ToyFilter


# Create a user viewset that only supports getting users and updating them.
# We don't support adding/removing users through the REST API because we mainly
# use Google authentication and automatate adding/removing the local user
# objects associated with a Google login.
class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    queryset = User.objects.all()

    serializer_class = UserSerializer


# Create a profile viewset which shows the currently logged in user's profile.
class ProfileViewSet(mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    queryset = User.objects.all()

    serializer_class = ProfileSerializer

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
