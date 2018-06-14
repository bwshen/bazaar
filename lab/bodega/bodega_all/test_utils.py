"""Bodega utils.py tests."""

from unittest import skip

from bodega_all.item_types import item_tools
from bodega_core.exceptions import BodegaValueError
from bodega_core.models import Location, Network, Order, OrderUpdate
from bodega_legacy_items.models import RktestYml
from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.test import TestCase


class RktestYmlTestCase(TestCase):
    def setUp(self):
        self.item_type = 'rktest_yml'
        self.location_hq = Location.objects.get(name='HQ')
        self.location_colo = Location.objects.get(name='COLO')
        self.network = \
            Network.objects.filter(location=self.location_colo).first()
        RktestYml.objects.create(filename='dynapod1.yml',
                                 location=self.location_hq,
                                 network=self.network,
                                 platform='DYNAPOD',
                                 linux_agent=True,
                                 vcenter_6_0=True)

        RktestYml.objects.create(filename='dynapod2.yml',
                                 location=self.location_hq,
                                 network=self.network,
                                 platform='DYNAPOD',
                                 vcenter_5_5=True)

        RktestYml.objects.create(filename='dynapod3.yml',
                                 location=self.location_colo,
                                 network=self.network,
                                 platform='DYNAPOD',
                                 linux_agent=True,
                                 vcenter_6_0=True,
                                 vcenter_5_5=True)

        RktestYml.objects.create(filename='dynapod4.yml',
                                 location=self.location_colo,
                                 network=self.network,
                                 platform='DYNAPOD',
                                 linux_agent=True,
                                 vcenter_6_0=True,
                                 vcenter_5_5=True)

        RktestYml.objects.create(filename='dynapod5.yml',
                                 location=self.location_colo,
                                 network=self.network,
                                 platform='DYNAPOD',
                                 vcenter_5_1=True)

        # Some predicates to reuse
        self.unsatisfiable_p = {'platform': 'X'}
        self.simple_p = {'location': 'COLO'}
        self.complex_p = {'location': 'COLO', 'vcenter_5_1': True}

    # Some functions to reuse
    def checkRktestYmlsInQuerySet(self, qs, rktestyml_filenames):
        self.assertEqual(qs.count(), len(rktestyml_filenames),
                         msg='resulting queryset has incorrect size')
        filenames = map(lambda x: x.filename, qs)
        for filename in rktestyml_filenames:
            self.assertIn(filename, filenames,
                          msg='resulting queryset is missing item')

    def checkUnsatisfiableFiltering(self, qs):
        self.assertEqual(qs.count(), 0,
                         msg='resulting queryset should be empty but is not')

    def checkSimpleFiltering(self, qs):
        expected_result = ['dynapod3.yml', 'dynapod4.yml', 'dynapod5.yml']
        self.checkRktestYmlsInQuerySet(qs, expected_result)

    def checkComplexFiltering(self, qs):
        expected_result = ['dynapod5.yml']
        self.checkRktestYmlsInQuerySet(qs, expected_result)

    def checkCompleteQuerySet(self, qs):
        self.assertEqual(qs.count(), 5,
                         msg='resulting queryset is not exactly complete')
        expected_result = ['dynapod1.yml', 'dynapod2.yml', 'dynapod3.yml',
                           'dynapod4.yml', 'dynapod5.yml']
        self.checkRktestYmlsInQuerySet(qs, expected_result)


class ProcessOrderTestCase(RktestYmlTestCase):
    def setUp(self):
        super(ProcessOrderTestCase, self).setUp()
        self.user = User.objects.create_user(username='test',
                                             password='qwerty')
        self.single_item_template = """
        {
          "pod1": {
            "type": %s,
            "requirements":
              %s
          },
        }
        """

        self.double_item_template = """
        {
          "pod1": {
            "type": %s,
            "requirements":
              %s
          },
          "pod2": {
            "type": %s,
            "requirements":
              %s
          },
        }
        """

    def createOpenOrderWithItems(self, items_json):
        order = Order.objects.create(status='OPEN',
                                     owner=self.user,
                                     tab=self.user.tabs.get())
        OrderUpdate.objects.create(items_delta=items_json,
                                   order=order,
                                   creator=self.user)
        return order

    def testUnsatisfiableItem(self):
        order = self.createOpenOrderWithItems(
            self.single_item_template % (self.item_type, self.unsatisfiable_p))
        result = item_tools.find_eligible_items_for_order_items(order.items)
        self.assertEqual(len(result), 1,
                         msg='did not receive exactly one queryset')
        self.assertIsNotNone(result.get('pod1'),
                             msg='missing queryset for item \'pod1\'')
        self.checkUnsatisfiableFiltering(result.get('pod1'))

    def testSingleItem(self):
        order = self.createOpenOrderWithItems(
            self.single_item_template % (self.item_type, self.simple_p))
        result = item_tools.find_eligible_items_for_order_items(order.items)
        self.assertEqual(len(result), 1,
                         msg='did not receive exactly one queryset')
        self.assertIsNotNone(result.get('pod1'),
                             msg='missing queryset for item \'pod1\'')
        self.checkSimpleFiltering(result.get('pod1'))

    def testMultipleItems(self):
        order = self.createOpenOrderWithItems(
            self.double_item_template %
            (self.item_type, self.simple_p, self.item_type, self.complex_p))
        result = item_tools.find_eligible_items_for_order_items(order.items)
        self.assertEqual(len(result), 2,
                         msg='did not receive exactly two querysets')
        self.assertIsNotNone(result.get('pod1'),
                             msg='missing queryset for item \'pod1\'')
        self.checkSimpleFiltering(result['pod1'])
        self.assertIsNotNone(result.get('pod2'),
                             msg='missing queryset for item \'pod2\'')
        self.checkComplexFiltering(result['pod2'])


class DiscoverQuerySetTestCase(RktestYmlTestCase):
    def testInvalidItemType(self):
        self.assertRaises(BodegaValueError,
                          item_tools.find_eligible_items_for_requirements,
                          'kittens')
        self.assertRaises(BodegaValueError,
                          item_tools.find_eligible_items_for_requirements,
                          RktestYml)

    def testReturnType(self):
        self.assertIsInstance(
            item_tools.find_eligible_items_for_requirements(self.item_type),
            QuerySet)
        self.assertIsInstance(
            item_tools.find_eligible_items_for_requirements(self.item_type,
                                                            self.simple_p),
            QuerySet)

    def testNoRequirements(self):
        qs = item_tools.find_eligible_items_for_requirements(self.item_type)
        self.checkCompleteQuerySet(qs)

    @skip("This is currently unsupported and thus untestable")
    def testInvalidRequirementKeys(self):
        pass

    def testUnsatisfiableRequirementValues(self):
        qs = item_tools.find_eligible_items_for_requirements(
            self.item_type, self.unsatisfiable_p)
        self.checkUnsatisfiableFiltering(qs)

    def testSingleRequirement(self):
        qs = item_tools.find_eligible_items_for_requirements(
            self.item_type, self.simple_p)
        self.checkSimpleFiltering(qs)

    def testMultipleRequirements(self):
        qs = item_tools.find_eligible_items_for_requirements(
            self.item_type, self.complex_p)
        self.checkComplexFiltering(qs)


class ExtendedBooleanFilterTestCase(RktestYmlTestCase):
    """Test filtering with the ExtendedBooleanFilter/Widget."""

    def setUp(self):
        super(ExtendedBooleanFilterTestCase, self).setUp()
        self.true_values = \
            ['1', 'y', 't', 'yes', 'true', 'Y', 'T', 'Yes', 'True', 1, True]
        self.false_values = \
            ['0', 'n', 'f', 'no', 'false', 'N', 'F', 'No', 'False', 0, False]
        self.non_values = \
            ['hello_world', 'None', 2, 3, None]

    def testTrueValues(self):
        for val in self.true_values:
            qs = item_tools.find_eligible_items_for_requirements(
                self.item_type, {'linux_agent': val})
            expected_result = ['dynapod1.yml', 'dynapod3.yml', 'dynapod4.yml']
            self.checkRktestYmlsInQuerySet(qs, expected_result)

    def testFalseValues(self):
        for val in self.false_values:
            qs = item_tools.find_eligible_items_for_requirements(
                self.item_type, {'linux_agent': val})
            expected_result = ['dynapod2.yml', 'dynapod5.yml']
            self.checkRktestYmlsInQuerySet(qs, expected_result)

    # Nonsensical/unsupported values should be ignored when filtering
    def testNonValues(self):
        for val in self.non_values:
            qs = item_tools.find_eligible_items_for_requirements(
                self.item_type, {'linux_agent': val})
            self.checkCompleteQuerySet(qs)

    def testComplexCombination(self):
        qs = item_tools.find_eligible_items_for_requirements(
            self.item_type, {'linux_agent': 'Y', 'vcenter_5_5': 'F'})
        expected_result = ['dynapod1.yml']
        self.checkRktestYmlsInQuerySet(qs, expected_result)
