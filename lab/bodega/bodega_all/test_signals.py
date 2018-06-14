"""Test signals."""
import logging

from bodega_core.models import Tab
from django.contrib.auth.models import User
from django.test import TestCase

log = logging.getLogger(__name__)


class OnUserSavedTestCase(TestCase):

    def test_tab_creation(self):
        """Test tab creation on user creation."""
        # The admin user should already have a tab.
        self.assertEquals(Tab.objects.count(), 1)

        # When a new user is created, a new tab should be created
        # for the user with the default limit.
        new_employee = User.objects.create_user(username='NewEmployee')
        self.assertEquals(Tab.objects.count(), 2)
        self.assertEquals(new_employee.tabs.count(), 1)
        new_employee_tab = new_employee.tabs.get()
        self.assertEquals(new_employee_tab.limit, Tab.DEFAULT_LIMIT)

        # No new tab should be created when the employee is saved but
        # not created.
        new_employee.save()
        self.assertEquals(Tab.objects.count(), 2)
        self.assertEquals(new_employee.tabs.count(), 1)
        self.assertEquals(new_employee_tab.sid, new_employee.tabs.get().sid)
