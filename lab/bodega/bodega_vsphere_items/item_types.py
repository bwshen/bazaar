"""ItemType definitions for vsphere items."""
from bodega_core import ItemType
from .filters import EsxHostFilter
from .item_managers import EsxHostManager
from .models import EsxHost
from .serializers import EsxHostSerializer

definitions = [
    ItemType(
        name='esx_host',
        plural_name='esx_hosts',
        model=EsxHost,
        queryset=EsxHost.objects.all(),
        filter_class=EsxHostFilter,
        serializer_class=EsxHostSerializer,
        manager_class=EsxHostManager)
]
