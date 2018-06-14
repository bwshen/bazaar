"""Temporary unittests for cleanupmanager.py."""

import os
import random
import string
from time import sleep
from unittest import skipUnless

from bodega_all.item_types import item_tools
from bodega_all.tasks import HandleItemCleanupTask
from bodega_core.cleanup import CleanupManager
from bodega_core.models import Location, Order, Network
from bodega_legacy_items.models import JenkinsTask, ReleaseQualBaton, RktestYml
from django.contrib.auth.models import User
from django.test import TestCase
from rkelery.models import Task


# This should be a bit longer than the recovery time, since Jenkins may have a
# slight delay before starting the build. The expectation is that unittests
# will run serially, whereas Jenkins may have concurrent builds.
RECOVERY_SLEEP = 90


def jenkins_flag():
    """Return True if 'jenkins' is in the BODEGA_TEST_FLAGS environ variable.

    This flag is used to indicate if the Jenkins tests (that require sandboxes)
    should be run. The environment variable is expected to be a comma-separated
    list of flags. Typically invoked from the command line via the following
    command: BODEGA_TEST_FLAGS=jenkins ./manage.py test
    """
    flags = os.environ.get('BODEGA_TEST_FLAGS', '').lower().split(',')
    return 'jenkins' in flags


def create_item_cleaner(item_sid):
    return Task.objects.create(
        task=HandleItemCleanupTask.name,
        args=[item_sid],
        kwargs={})


class CleanupManagerReleaseQualBatonTestCase(TestCase):
    def setUp(self):
        self.manager = CleanupManager(item_tools)
        self.user = User.objects.create_user(username='John',
                                             password='Bar',
                                             email='john.doe@rubrik.com')
        self.tab = self.user.tabs.get()

    def testBatonCleanup(self):
        order = Order.objects.create(status=Order.STATUS_CLOSED,
                                     owner=self.user,
                                     tab=self.tab)
        baton = ReleaseQualBaton.objects.create(held_by=order)
        self.assertEqual(baton.held_by, order,
                         msg='setup error: baton not assigned to order')
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        order.refresh_from_db()
        baton.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CLOSED,
                         msg='order status was not preserved')
        self.assertIsNone(baton.held_by,
                          msg='baton was not successfully freed')


class CleanupManagerRktestYmlTestCase(TestCase):
    def setUp(self):
        self.manager = CleanupManager(item_tools)
        self.user = User.objects.create_user(username='John',
                                             password='Bar',
                                             email='john.doe@rubrik.com')
        self.tab = self.user.tabs.get()
        self.location_hq = Location.objects.get(name='HQ')
        self.location_colo = Location.objects.get(name='COLO')
        self.network = \
            Network.objects.filter(location=self.location_colo).first()

    def create_open_order(self):
        return Order.objects.create(status=Order.STATUS_OPEN,
                                    owner=self.user,
                                    tab=self.tab)

    def create_fulfilled_order(self):
        return Order.objects.create(
            status=Order.STATUS_FULFILLED,
            tab=self.tab)

    def create_closed_order(self):
        return Order.objects.create(status=Order.STATUS_CLOSED,
                                    owner=self.user,
                                    tab=self.tab)

    def create_dynapod(self, name, held_by=None):
        return RktestYml.objects.create(held_by=held_by,
                                        filename=name,
                                        location=self.location_hq,
                                        network=self.network,
                                        platform='DYNAPOD')

    def get_random_name(self, length=10):
        return ''.join(random.choice(string.ascii_lowercase)
                       for _ in range(length))

    def testSanityAssignment(self):
        order = self.create_closed_order()
        dynapod = self.create_dynapod(self.get_random_name(), held_by=order)
        self.assertEqual(dynapod.held_by, order,
                         msg='setup error: dynapod not assigned to order')

    @skipUnless(jenkins_flag(), 'Skipping since \'jenkins\' test flag not set')
    def testUntouchables(self):
        order1 = self.create_open_order()
        order2 = self.create_fulfilled_order()
        dynapod1 = self.create_dynapod(self.get_random_name(), held_by=order1)
        dynapod2 = self.create_dynapod(self.get_random_name(), held_by=order2)
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        order1.refresh_from_db()
        order2.refresh_from_db()
        dynapod1.refresh_from_db()
        dynapod2.refresh_from_db()
        self.assertEqual(order1.status, Order.STATUS_OPEN,
                         msg='open order was not preserved')
        self.assertEqual(order2.status, Order.STATUS_FULFILLED,
                         msg='fulfilled order was not preserved')
        self.assertEqual(dynapod1.held_by, order1,
                         msg='dynapod of open order was not preserved')
        self.assertEqual(dynapod2.held_by, order2,
                         msg='dynapod of fulfilled order was not preserved')

    @skipUnless(jenkins_flag(), 'Skipping since \'jenkins\' test flag not set')
    def testRecoveryTaskCreation(self):
        order = self.create_closed_order()
        self.create_dynapod(self.get_random_name(), held_by=order)
        initial_task_count = JenkinsTask.objects.all().count()
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        new_task_count = JenkinsTask.objects.all().count()
        self.assertEqual(new_task_count - initial_task_count, 1,
                         msg='recovery task was not properly created')

    @skipUnless(jenkins_flag(), 'Skipping since \'jenkins\' test flag not set')
    def testHeldByTransitionToRecovery(self):
        order = self.create_closed_order()
        dynapod = self.create_dynapod(self.get_random_name(), held_by=order)
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        order.refresh_from_db()
        dynapod.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CLOSED,
                         msg='order status was not preserved')
        self.assertIsInstance(dynapod.held_by, JenkinsTask,
                              msg='unsuccessful transition to recovery task')

    # These are outdated and should be moved or removed.
    # def testHeldByUUIDUpdate(self):
    #     order = self.create_closed_order()
    #     dynapod = self.create_dynapod(self.get_random_name(), held_by=order)
    #     self.manager._start_recovery(dynapod)
    #     dynapod.refresh_from_db()
    #     uuid = dynapod.held_by.uuid
    #     self.manager._continue_recovery(dynapod)
    #     dynapod.refresh_from_db()
    #     self.assertNotEqual(dynapod.held_by.uuid, uuid,
    #                         msg='UUID was not updated on retry')

    # def testJenkinsBuildTrigger(self):
    #     order = self.create_closed_order()
    #     dynapod = self.create_dynapod(self.get_random_name(), held_by=order)
    #     self.manager.process_items_cleanup(create_item_cleaner)
    #     Task.objects.simulate_run_all()
    #     sleep(RECOVERY_SLEEP)
    #     dynapod.refresh_from_db()
    #     status = self.manager.get_status(dynapod)
    #     self.assertIsNotNone(status, msg='cound not find Jenkins build')

    @skipUnless(jenkins_flag(), 'Skipping since \'jenkins\' test flag not set')
    def testHeldByTransitionToFree(self):
        order = self.create_closed_order()
        dynapod = self.create_dynapod(self.get_random_name(), held_by=order)
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        sleep(RECOVERY_SLEEP)
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        order.refresh_from_db()
        dynapod.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CLOSED,
                         msg='order status was not preserved')
        self.assertIsNone(dynapod.held_by,
                          msg='dynapod was not successfully freed')

    @skipUnless(jenkins_flag(), 'Skipping since \'jenkins\' test flag not set')
    def testMultipleCases(self):
        order1 = self.create_open_order()
        order2 = self.create_fulfilled_order()
        order3 = self.create_closed_order()
        order4 = self.create_closed_order()
        dynapod5 = self.create_dynapod('dynapod5', order1)
        dynapod6 = self.create_dynapod('dynapod6', order2)
        dynapod7 = self.create_dynapod('dynapod7', order3)
        dynapod8 = self.create_dynapod('dynapod8', order4)
        dynapod9 = self.create_dynapod('dynapod9', order3)
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        sleep(RECOVERY_SLEEP)
        self.manager.process_items_cleanup(create_item_cleaner)
        Task.objects.simulate_run_all()
        dynapod5.refresh_from_db()
        dynapod6.refresh_from_db()
        dynapod7.refresh_from_db()
        dynapod8.refresh_from_db()
        dynapod9.refresh_from_db()
        self.assertIsNotNone(dynapod5.held_by,
                             msg='dynapod5 was mistakenly freed')
        self.assertIsNotNone(dynapod6.held_by,
                             msg='dynapod6 was mistakenly freed')
        self.assertIsNone(dynapod7.held_by,
                          msg='dynapod7 was not successfully freed')
        self.assertIsNone(dynapod8.held_by,
                          msg='dynapod8 was not successfully freed')
        self.assertIsNone(dynapod9.held_by,
                          msg='dynapod9 was not successfully freed')
