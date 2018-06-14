from django.contrib.auth.models import User
import logging
from permission.logics.base import PermissionLogic

log = logging.getLogger(__name__)


class UserPermissionLogic(PermissionLogic):
    def __init__(self):
        pass

    def has_perm(self, user, perm, obj=None):
        log.debug('UserPermissionLogic.has_perm(user=%s, perm=%s, obj=%s)' %
                  (repr(user), repr(perm), repr(obj)))

        add_perm = self.get_full_permission_string('add')
        change_perm = self.get_full_permission_string('change')
        delete_perm = self.get_full_permission_string('delete')

        # Return True when there's no specific object so Django will move on to
        # checking the permission for the specific object.
        if obj is None:
            return True

        if not(isinstance(obj, User)):
            raise TypeError('%s is not a User object' % repr(obj))

        # Administrators can do anything.
        if user.is_superuser:
            return True

        # Nobody else can do anything. The only useful operation we support is
        # turning users into administrators, and administrators already have
        # that permission above.
        return False


PERMISSION_LOGICS = (
    (User, UserPermissionLogic()),
)
