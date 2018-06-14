"""Item type definitions of Bodega generic items."""
from bodega_core import ItemType
from .filters import (IpAddressFilter,
                      MssqlServerFilter,
                      UbuntuMachineFilter)
from .item_managers import (IpAddressManager,
                            MssqlServerManager,
                            UbuntuMachineManager)
from .models import IpAddress, MssqlServer, UbuntuMachine
from .serializers import (IpAddressSerializer,
                          MssqlServerSerializer,
                          UbuntuMachineSerializer)


definitions = [
    ItemType(
        name='mssql_server',
        plural_name='mssql_servers',
        model=MssqlServer,
        queryset=MssqlServer.objects.all(),
        filter_class=MssqlServerFilter,
        serializer_class=MssqlServerSerializer,
        manager_class=MssqlServerManager),
    ItemType(
        name='ubuntu_machine',
        plural_name='ubuntu_machines',
        model=UbuntuMachine,
        queryset=UbuntuMachine.objects.all(),
        filter_class=UbuntuMachineFilter,
        serializer_class=UbuntuMachineSerializer,
        manager_class=UbuntuMachineManager),
    ItemType(
        name='ip_address',
        plural_name='ip_addresses',
        model=IpAddress,
        queryset=IpAddress.objects.all(),
        filter_class=IpAddressFilter,
        serializer_class=IpAddressSerializer,
        manager_class=IpAddressManager),
]
