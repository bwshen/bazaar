"""Test Bodega Legacy Items' item_manager."""
from bodega_core.models import Location, Network
from django.test import TestCase
from .item_managers import (get_item_price_by_platform,
                            PLATFORM_TO_ITEM_PRICE,
                            UNKNOWN_PLATFORM_DEFAULT_PRICE)
from .models import RktestYml


class ItemManagerTestCase(TestCase):
    def setUp(self):
        self.filename = 'Item1.yml'
        self.location = Location.objects.get(name='HQ')
        self.network = Network.objects.get(location=self.location)
        self.platform = 'PROD_BRIK'
        self.item1 = RktestYml.objects.create(filename=self.filename,
                                              location=self.location,
                                              network=self.network,
                                              platform=self.platform)
        self.prod_brik_price = PLATFORM_TO_ITEM_PRICE.get(self.platform)

    def test_requirements_no_platform(self):
        """Test price for item when resource specified directly.

        When a user specifies a resource directly, the item price should be
        based on the resource's platform.
        """
        requirements = {'filename': self.filename}
        price = get_item_price_by_platform(requirements)

        self.assertEqual(self.prod_brik_price, price)

    def test_unfulfillable_requirement_price(self):
        """Test price for an item when not possible to fulfill.

        It is sometimes possible to modify an item's requirements
        once the order is placed. It is possible the modified requirements
        makes the order unfulfillable. Need to ensure that the item manager
        returns a default price and not crash the fulfiller. The fulfiller
        will handle the logic around unfulfillable items.
        """
        requirements = {'filename': 'item20.yml'}
        price = get_item_price_by_platform(requirements)

        self.assertEqual(UNKNOWN_PLATFORM_DEFAULT_PRICE, price)

    def test_requirements_with_platform(self):
        """Test price for an item when platform is specified.

        When platform is specified, the item manager should return the price
        in the dictionary.
        """
        requirements = {'platform': self.platform}
        price = get_item_price_by_platform(requirements)

        self.assertEqual(self.prod_brik_price, price)
