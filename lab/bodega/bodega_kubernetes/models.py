"""Models representing Kubernetes items."""
from bodega_core.models import Farm, Item
from django.db import models


class KubernetesFarm(Farm):
    url = models.CharField(max_length=255, null=False)
    ca_cert = models.TextField(null=False, blank=False)
    namespace = models.CharField(max_length=255, null=False)
    token = models.TextField(null=False, blank=False)
    location = models.ForeignKey(
        'bodega_core.Location', on_delete=models.CASCADE,
        help_text='The location of this KubernetesFarm')

    class Meta:
        unique_together = ('url', 'namespace',)

    def can_grow(self, item):
        # TODO: Need more detailed logic on whether or not we can provide
        # a KubernetesPod
        if isinstance(item, KubernetesPod):
            return True

        return False


class KubernetesPod(Item):
    _name = models.CharField(max_length=255, null=False)
    uid = models.CharField(max_length=255, null=False)
    farm = models.ForeignKey('KubernetesFarm',
                             null=False,
                             on_delete=models.CASCADE)
