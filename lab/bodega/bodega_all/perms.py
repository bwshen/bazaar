"""Permissions for Bodega."""

import logging

from bodega_cdm_items.models import CdmCluster, CdmNode
from bodega_core.models import Item, Order, OrderUpdate
from bodega_crdb_dev_items.models import CockroachDBDepsMachine
from bodega_generic_items.models import IpAddress
from bodega_generic_items.models import UbuntuMachine
from bodega_legacy_items.models import (
    JenkinsTask, ReleaseQualBaton, RktestYml)
from bodega_sd_dev_items.models import SdDevMachine
from bodega_vsphere_items.models import EsxHost
from permission.logics.base import PermissionLogic

log = logging.getLogger(__name__)


class DynamicItemPermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('DynamicItemPermissionLogic.has_perm'
                  '(user=%s, perm=%s, obj=%s)'
                  % (repr(user), repr(perm), repr(obj)))
        # Users cannot add, create, or delete a dynamic item. This is handled
        # automatically by Bodega.
        return False


class ItemPermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('ItemPermissionLogic.has_perm(user=%s, perm=%s, obj=%s)' %
                  (repr(user), repr(perm), repr(obj)))
        if not user.is_authenticated():
            return False

        # We return True here so that we raise a 405 error in the ViewSets
        # on unsupported actions.
        return True


class JenkinsTaskPermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('JenkinsTaskPermissionLogic.has_perm'
                  '(user=%s, perm=%s, obj=%s)'
                  % (repr(user), repr(perm), repr(obj)))
        # User must be authenticated to do anything with JenkinsTasks
        if not user.is_authenticated():
            return False

        # Jenkins tasks are created automatically by Bodega and are used purely
        # for information for the user. Don't allow create, update, or delete.
        # Return True here to raise a 405 error on the ViewSets
        return True


class OrderPermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('OrderPermissionLogic.has_perm(user=%s, perm=%s, obj=%s)' %
                  (repr(user), repr(perm), repr(obj)))

        add_perm = self.get_full_permission_string('add')

        # User must be authenticated to do anything with Orders
        if not user.is_authenticated():
            return False

        # Allow adding Order objects.
        if perm == add_perm:
            return True

        # Don't allow deletion or update of Order objects. Return True here
        # so that we raise a 405 error in the ViewSets
        return True


class OrderUpdatePermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('OrderUpdatePermissionLogic.has_perm'
                  '(user=%s, perm=%s, obj=%s)'
                  % (repr(user), repr(perm), repr(obj)))

        add_perm = self.get_full_permission_string('add')

        # User must be authenticated to do anything with OrderUpdates
        if not user.is_authenticated():
            return False

        # Allow adding OrderUpdate objects. The validation to enforce that
        # the user is the owner of the Order object for this update will occur
        # in the input validation.
        if perm == add_perm:
            return True

        # Don't allow deletion or changing of OrderUpdate objects. Return True
        # here to raise a 405 error in the ViewSets
        return True


class ReleaseQualBatonPermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('ReleaseQualBatonPermissionLogic.has_perm'
                  '(user=%s, perm=%s, obj=%s)'
                  % (repr(user), repr(perm), repr(obj)))
        # User must be authenticated to do anything with ReleaseQualBaton
        if not user.is_authenticated():
            return False

        return user.is_superuser


class RktestYmlPermissionLogic(PermissionLogic):
    def has_perm(self, user, perm, obj=None):
        log.debug('RktestYmlPermissionLogic.has_perm'
                  '(user=%s, perm=%s, obj=%s)'
                  % (repr(user), repr(perm), repr(obj)))
        # User must be authenticated to do anything with RktestYmls
        if not user.is_authenticated():
            return False

        return user.is_superuser


# TODO: Use something other than wide open permissions for these models.
PERMISSION_LOGICS = (
    # The way django-permission and Django REST Framework work together for
    # model inheritance is a little quirky. Django REST Framework always
    # expects to require the permissions for the exact model (the subclass),
    # meaning that a user needs the change_rktestyml permission to PATCH a
    # RktestYml. django-permission on the other hand seems to assume that
    # having the permission for the superclass is fine so the user would only
    # need the change_item permission. So, django-permission skips registering
    # the permission logic if it detects that the model's superclass is already
    # registered.
    #
    # Either permission inheritance style could be argued as correct. Go ahead
    # with requiring the exact model's permissions since that's more flexible
    # in case we have a reason to use different policies for specific subtypes.
    # That means we have to register subclasses before their superclasses here
    # so django-permission doesn't skip the subclasses.
    #
    # If we change our minds on this style, the alternative is to create and
    # use a modified version of Django REST Framework's DjangoObjectPermissions
    # class which knows to require permissions for the superclass instead of
    # the exact model's class.
    (CdmCluster, DynamicItemPermissionLogic()),
    (CdmNode, DynamicItemPermissionLogic()),
    (CockroachDBDepsMachine, DynamicItemPermissionLogic()),
    (EsxHost, DynamicItemPermissionLogic()),
    (IpAddress, DynamicItemPermissionLogic()),
    (JenkinsTask, JenkinsTaskPermissionLogic()),
    (Order, OrderPermissionLogic()),
    (OrderUpdate, OrderUpdatePermissionLogic()),
    (ReleaseQualBaton, ReleaseQualBatonPermissionLogic()),
    (RktestYml, RktestYmlPermissionLogic()),
    (SdDevMachine, DynamicItemPermissionLogic()),
    (UbuntuMachine, DynamicItemPermissionLogic()),
)

PERMISSION_LOGICS += (
    # Register superclasses last. See comment above about permission
    # inheritance for why.
    (Item, ItemPermissionLogic()),
)
