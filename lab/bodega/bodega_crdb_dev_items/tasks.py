"""Tasks for Bodega CockroachDBDepsMachine items."""
import json
from bodega_aws.models import Ec2Instance
from bodega_aws.utils import (create_ec2_instance_on_aws,
                              get_aws_farm,
                              get_ec2_instance_type_for_model,
                              get_or_create_aws_network)
from bodega_core.models import Location, Network
from bodega_core.tasks import ThrottledTask
from bodega_generic_items.utils import change_hostname_on_ubuntu_machine
from rkelery import register_task

from .models import CockroachDBDepsMachine
from .utils import get_ami_id_for_cockroachdb_deps_machine


@register_task
class CreateCockroachDBDepsMachineFromAwsTask(ThrottledTask):

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get AWS CockroachDBDepsMachine with requirements of %s.'
            % (json.dumps(requirements)))

    def max_concurrent_tasks(self, ingredients, requirements):
        return 10

    def run(self, ingredients, requirements):
        disk_size = requirements.get('disk_size',
                                     CockroachDBDepsMachine.DEFAULT_DISK_SIZE)
        version = requirements.get('version',
                                   CockroachDBDepsMachine.DEFAULT_VERSION)
        model = requirements.get('model',
                                 CockroachDBDepsMachine.DEFAULT_MODEL)
        location = Location.objects.get(name=requirements['location'])
        image_version = requirements.get(
            'image_version',
            CockroachDBDepsMachine.DEFAULT_IMAGE_VERSION)

        network_name = requirements.get('network', 'default')
        network = Network.objects.get(name=network_name,
                                      location=location)

        aws_farm = get_aws_farm(location)
        ami_id = get_ami_id_for_cockroachdb_deps_machine(aws_farm,
                                                         image_version)
        instance_type = get_ec2_instance_type_for_model(model)
        deps_machine = CockroachDBDepsMachine.objects.create(
            version=version,
            disk_size=disk_size,
            model=model,
            image_version=image_version,
            location=location,
            network=network,
            held_by=self.model_instance
        )
        instance_name = 'cockroachdb-deps-%s' % deps_machine.sid

        ec2_instance = Ec2Instance.objects.create(
            _name=instance_name,
            instance_id="",
            ami_id=ami_id,
            instance_type=instance_type,
            farm=aws_farm,
            held_by=deps_machine)
        instance = create_ec2_instance_on_aws(
            ec2_instance,
            additional_disk_size=disk_size)

        vpc_id = instance['NetworkInterfaces'][0]['VpcId']
        if network_name != vpc_id:
            network = get_or_create_aws_network(vpc_id, location)
            deps_machine.network = network
            deps_machine.save()

        change_hostname_on_ubuntu_machine(deps_machine)
        deps_machine.held_by = None
        deps_machine.save()
