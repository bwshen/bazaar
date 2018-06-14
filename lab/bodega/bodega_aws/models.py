"""Models representing AWS items."""
from bodega_core.models import Farm, Item
from django.db import models


class AwsFarm(Farm):

    MODEL_AWS_M4_LARGE = 'aws-m4.large'
    MODEL_AWS_M4_XLARGE = 'aws-m4.xlarge'
    MODEL_AWS_M4_2XLARGE = 'aws-m4.2xlarge'
    MODEL_AWS_T2_LARGE = 'aws-t2.large'

    region_name = models.CharField(max_length=255, null=False, blank=False)
    aws_access_key_id = models.CharField(max_length=255, null=False,
                                         blank=False)
    aws_secret_access_key = models.CharField(max_length=255, null=False,
                                             blank=False)
    subnet_id = models.CharField(max_length=32, null=False, blank=False)
    security_group_id = models.CharField(
        max_length=32, null=False, blank=False)

    class Meta:
        """Metadata for AwsFarm."""

        unique_together = ('region_name',
                           'aws_access_key_id',
                           'aws_secret_access_key')

    def can_grow(self, item):
        # TODO: Need more detailed logic on whether or not we can provide
        # an Ec2Instance
        if isinstance(item, Ec2Instance):
            return True

        return False


class Ec2Instance(Item):
    _name = models.CharField(max_length=255, null=False)
    instance_id = models.CharField(max_length=255, blank=False, null=False)
    ami_id = models.CharField(max_length=255, blank=False, null=False)
    instance_type = models.CharField(max_length=255, blank=False, null=False)
    farm = models.ForeignKey('AwsFarm',
                             null=False,
                             on_delete=models.CASCADE)
