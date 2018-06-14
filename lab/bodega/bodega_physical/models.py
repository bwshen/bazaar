"""Models representing Physical items."""
from bodega_core.models import Item, Stockroom
from django.db import models


class BrikStockroom(Stockroom):
    """For Prod briks, we only need the pxe_server_ip and identifiable name."""

    name = models.CharField(max_length=255, null=False, blank=False)
    pxe_server_ip = models.CharField(max_length=15, null=False, blank=False)


class PhysicalCdmNode(Item):
    """A physical CDM node's static infromation.

    Only serial number is required as we will use this to derive the
    information required to manufacture the node and bootstrap the
    cluster. The plan is to use Racktables api that IT manages to
    derive this information.
    """

    serial_number = models.CharField(max_length=255, null=False, blank=False)
    stockroom = models.ForeignKey('BrikStockroom',
                                  on_delete=models.CASCADE,
                                  null=False,
                                  help_text='Stockroom for this brik')
