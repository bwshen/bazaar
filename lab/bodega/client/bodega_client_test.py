"""Bodega Client tests."""
from bodega.client.bodega_client import BodegaClient


def test_orders():
    client = BodegaClient()
    orders = client.get('/orders')
    assert orders
