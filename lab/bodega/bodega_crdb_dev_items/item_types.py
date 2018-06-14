"""Item type definitions of Bodega generic items."""
from bodega_core import ItemType
from .filters import CockroachDBDepsMachineFilter
from .item_managers import CockroachDBDepsMachineManager
from .models import CockroachDBDepsMachine
from .serializers import CockroachDBDepsMachineSerializer

definitions = [
    ItemType(
        name='cockroachdb_deps_machine',
        plural_name='cockroachdb_deps_machines',
        model=CockroachDBDepsMachine,
        queryset=CockroachDBDepsMachine.objects.all(),
        filter_class=CockroachDBDepsMachineFilter,
        serializer_class=CockroachDBDepsMachineSerializer,
        manager_class=CockroachDBDepsMachineManager
    )
]
