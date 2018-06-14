import logging
from permission.logics.base import PermissionLogic
from .models import Ball, Doll, Stick, Toy

log = logging.getLogger(__name__)


class ToyPermissionLogic(PermissionLogic):
    def __init__(self):
        pass

    def has_perm(self, user, perm, obj=None):
        log.debug('ToyPermissionLogic.has_perm(user=%s, perm=%s, obj=%s)' %
                  (repr(user), repr(perm), repr(obj)))

        add_perm = self.get_full_permission_string('add')
        change_perm = self.get_full_permission_string('change')
        delete_perm = self.get_full_permission_string('delete')

        # When obj isn't passed, this is Django checking whether the user has
        # the permission at all, before checking whether the user has the
        # permission on a specific object. Always return True so that Django
        # will proceed to the permission check on the specific object.
        if obj is None:
            return True

        if not(isinstance(obj, Toy)):
            raise TypeError('%s is not a Toy object' % repr(obj))

        # Administrators can do anything.
        if user.is_superuser:
            return True

        # Any authenticated user can add a toy.
        if perm == add_perm:
            return user.is_authenticated()

        # The owner of the toy has full permissions. Everybody else has
        # none.
        return obj.owner == user


PERMISSION_LOGICS = (
    # The way django-permission and Django REST Framework work together for
    # model inheritance is a little quirky. Django REST Framework always
    # expects to require the permissions for the exact model (the subclass),
    # meaning that a user needs the change_ball permission to PATCH a
    # Ball. django-permission on the other hand seems to assume that having the
    # permission for the superclass is fine so the user would only need the
    # change_toy permission. So, django-permission skips registering the
    # permission logic if it detects that the model's superclass is already
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
    (Ball, ToyPermissionLogic()),
    (Doll, ToyPermissionLogic()),
    (Stick, ToyPermissionLogic()),

    # Register superclasses last. See comment above about permission
    # inheritance for why.
    (Toy, ToyPermissionLogic()),
)
