"""Tasks for Bodega CdmNode items."""
import datetime
import json
import logging
from bodega_aws.models import Ec2Instance
from bodega_aws.utils import (create_ec2_instance_on_aws,
                              get_aws_farm,
                              get_ec2_instance_type_for_model,
                              get_or_create_aws_network)
from bodega_core.models import Location, Network
from bodega_core.tasks import ThrottledTask
from rkelery import register_task, Task
from .models import CdmCluster, CdmNode
from .utils import (bootstrap_cdm_cluster,
                    get_ami_id_for_code_version,
                    setup_cdm_node_with_build,
                    tag_cdm_node_with_network_info,
                    tag_cluster_nodes)

log = logging.getLogger(__name__)


@register_task
class CreateCdmNodeFromAwsTask(ThrottledTask):
    """Create a CdmNode in AWS with the given requirements."""

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get AWS CdmNode with requirements of %s using %s as ingredients.'
            % (json.dumps(requirements), json.dumps(ingredients)))

    @classmethod
    def get_soft_timeout(cls, ingredients, requirements):
        return datetime.timedelta(minutes=60).total_seconds()

    def max_concurrent_tasks(self, ingredients, requirements):
        return 20

    @classmethod
    def get_timeout(cls, *args, **kwargs):
        return datetime.timedelta(minutes=65).total_seconds()

    def run(self, ingredients, requirements):
        artifacts_url = requirements.get('artifacts_url', None)
        model = requirements.get('model', CdmNode.DEFAULT_MODEL)
        location = Location.objects.get(name=requirements['location'])

        network_name = requirements.get('network', None)
        if not network_name:
            # It's possible for 'network' to be present in the requirements
            # but have a value of None. The "get" function will return None
            # instead of a chosen default value which is why we need this check
            network_name = 'default'
        network = Network.objects.get(name=network_name,
                                      location=location)

        cdm_node = CdmNode.objects.create(
            model=model,
            artifacts_url=artifacts_url,
            location=location,
            network=network,
            held_by=self.model_instance
        )
        log.debug('Created %s' % cdm_node)

        instance_name = 'cdm-node-%s' % cdm_node.sid
        aws_farm = get_aws_farm(location)
        ami_id = get_ami_id_for_code_version(aws_farm, artifacts_url)
        instance_type = get_ec2_instance_type_for_model(model)

        ec2_instance = Ec2Instance.objects.create(
            _name=instance_name,
            instance_id="",
            ami_id=ami_id,
            instance_type=instance_type,
            farm=aws_farm,
            held_by=cdm_node)

        # INFRA-2207: Remove these NoDevice entries once our AMIs do not have
        #             data disks in them (CDM-77081). Additionally, rename
        #             sdd and sde to sdb and sdc.
        block_device_mappings = []
        block_device_mappings.append({
            'DeviceName': '/dev/sdb',
            'NoDevice': ''
        })
        block_device_mappings.append({
            'DeviceName': '/dev/sdc',
            'NoDevice': ''
        })
        block_device_mappings.append({
            'DeviceName': '/dev/sdd',
            'Ebs': {
                'VolumeSize': 512,
                'VolumeType': 'gp2',
                'Encrypted': True,
                'DeleteOnTermination': True
            }
        })
        block_device_mappings.append({
            'DeviceName': '/dev/sde',
            'Ebs': {
                'VolumeSize': 512,
                'VolumeType': 'gp2',
                'Encrypted': True,
                'DeleteOnTermination': True
            }
        })

        instance = create_ec2_instance_on_aws(
            ec2_instance=ec2_instance,
            instance_block_device_mappings=block_device_mappings,
            ebs_optimized=True)

        vpc_id = instance['NetworkInterfaces'][0]['VpcId']
        if network_name != vpc_id:
            network = get_or_create_aws_network(vpc_id, location)
            cdm_node.network = network
            cdm_node.save()

        tag_cdm_node_with_network_info(cdm_node)
        setup_cdm_node_with_build(cdm_node, artifacts_url)

        cdm_node.held_by = None
        cdm_node.save()


@register_task
class CreateCdmClusterFromAwsTask(Task):
    """Create a CdmCluster in AWS with the given requirements."""

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get AWS CdmCluster with requirements of %s using %s as '
            'ingredients.'
            % (json.dumps(requirements), json.dumps(ingredients)))

    @classmethod
    def get_soft_timeout(cls, ingredients, requirements):
        return datetime.timedelta(minutes=30).total_seconds()

    @classmethod
    def get_timeout(cls, *args, **kwargs):
        return datetime.timedelta(minutes=35).total_seconds()

    def run(self, ingredients, requirements):
        artifacts_url = requirements.get('artifacts_url', None)
        model = requirements.get('model', CdmCluster.DEFAULT_MODEL)
        location = Location.objects.get(name=requirements['location'])

        cdm_nodes_sids = list(ingredients.values())
        network_name = requirements.get('network', None)
        if not network_name:
            cdm_node = CdmNode.objects.get(sid=cdm_nodes_sids[0])
            network_name = cdm_node.network.name
            log.debug('No network given so using the network %s from the '
                      'ingredients.' % network_name)
        network = Network.objects.get(name=network_name,
                                      location=location)

        cdm_cluster = CdmCluster.objects.create(
            node_count=len(cdm_nodes_sids),
            model=model,
            artifacts_url=artifacts_url,
            location=location,
            network=network,
            held_by=self.model_instance
        )
        log.debug('Created %s and using %s as ingredients'
                  % (cdm_cluster, cdm_nodes_sids))
        for cdm_node_sid in cdm_nodes_sids:
            cdm_node = CdmNode.objects.get(sid=cdm_node_sid)
            cdm_node.held_by = cdm_cluster
            cdm_node.save()

        # Update AWS CdmNodes with tags saying they belong to this cluster
        tag_cluster_nodes(cdm_cluster)

        # Perform CLI bootstrap of the CdmCluster
        bootstrap_cdm_cluster(cdm_cluster)

        cdm_cluster.held_by = None
        cdm_cluster.save()
