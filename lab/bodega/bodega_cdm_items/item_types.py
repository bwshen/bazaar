"""Item type definitions of Bodega Cdmitems."""
from bodega_core import ItemType
from .filters import CdmClusterFilter, CdmNodeFilter
from .item_managers import CdmClusterManager, CdmNodeManager
from .models import CdmCluster, CdmNode
from .serializers import CdmClusterSerializer, CdmNodeSerializer

definitions = [
    ItemType(
        name='cdm_node',
        plural_name='cdm_nodes',
        model=CdmNode,
        queryset=CdmNode.objects.all(),
        filter_class=CdmNodeFilter,
        serializer_class=CdmNodeSerializer,
        manager_class=CdmNodeManager),
    ItemType(
        name='cdm_cluster',
        plural_name='cdm_clusters',
        model=CdmCluster,
        queryset=CdmCluster.objects.all(),
        filter_class=CdmClusterFilter,
        serializer_class=CdmClusterSerializer,
        manager_class=CdmClusterManager),
]
