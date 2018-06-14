"""Item type definitions of Bodega Sd Dev items."""
from bodega_core import ItemType
from .filters import SdDevMachineFilter
from .item_managers import SdDevMachineManager
from .models import SdDevMachine
from .serializers import SdDevMachineSerializer


definitions = [
    ItemType(
        name='sd_dev_machine',
        plural_name='sd_dev_machines',
        model=SdDevMachine,
        queryset=SdDevMachine.objects.all(),
        filter_class=SdDevMachineFilter,
        serializer_class=SdDevMachineSerializer,
        manager_class=SdDevMachineManager),
]
