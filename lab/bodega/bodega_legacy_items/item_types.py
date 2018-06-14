"""Item type definitions of legacy items."""
from bodega_core import ItemType
from .filters import ReleaseQualBatonFilter, RktestYmlFilter
from .item_managers import ReleaseQualBatonManager, RktestYmlManager
from .models import ReleaseQualBaton, RktestYml
from .serializers import ReleaseQualBatonSerializer, RktestYmlSerializer


definitions = [
    ItemType(
        name='release_qual_baton',
        plural_name='release_qual_batons',
        model=ReleaseQualBaton,
        queryset=ReleaseQualBaton.objects.all(),
        filter_class=ReleaseQualBatonFilter,
        serializer_class=ReleaseQualBatonSerializer,
        manager_class=ReleaseQualBatonManager),
    ItemType(
        name='rktest_yml',
        plural_name='rktest_ymls',
        model=RktestYml,
        queryset=RktestYml.objects.all().order_by('filename'),
        filter_class=RktestYmlFilter,
        serializer_class=RktestYmlSerializer,
        manager_class=RktestYmlManager)
]
