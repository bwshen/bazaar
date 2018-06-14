"""Tasks for Bodega generic items."""
import json
import logging
from bodega_aws.models import Ec2Instance
from bodega_aws.utils import (create_ec2_instance_on_aws,
                              get_aws_farm,
                              get_ec2_instance_type_for_model,
                              get_or_create_aws_network)
from bodega_core.models import Location, Network
from bodega_core.tasks import ThrottledTask
from bodega_vsphere.models import VSphereVirtualMachine
from bodega_vsphere.utils import (create_virtual_machine_on_vsphere,
                                  get_esx_host,
                                  get_hardware_and_size_for_model)
from rkelery import register_task

from .models import MssqlServer, UbuntuMachine
from .utils import (change_hostname_on_ubuntu_machine,
                    get_ami_id_for_mssql_server_version,
                    get_ami_id_for_ubuntu_version)

TEMPLATES_LOCATION = 'http://files-master.colo.rubrik-lab.com/Templates/'
UBUNTU_SOURCE_VM_TEMPLATE = TEMPLATES_LOCATION + \
    'UbuntuSource/UbuntuSource.ova'
UBUNTU_TEMPLATE_NAME = 'BodegaUbuntuTemplate'
log = logging.getLogger(__name__)


@register_task
class CreateMssqlServerFromAwsTask(ThrottledTask):

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get AWS MssqlServer with requirements of %s.'
            % (json.dumps(requirements)))

    def max_concurrent_tasks(self, ingredients, requirements):
        return 10

    def run(self, ingredients, requirements):
        version = requirements.get('version', MssqlServer.DEFAULT_VERSION)
        model = requirements.get('model', MssqlServer.DEFAULT_MODEL)
        location = Location.objects.get(name=requirements['location'])

        network_name = requirements.get('network', 'default')
        network = Network.objects.get(name=network_name,
                                      location=location)

        aws_farm = get_aws_farm(location)
        ami_id = get_ami_id_for_mssql_server_version(version, aws_farm)
        instance_type = get_ec2_instance_type_for_model(model)

        mssql_server = MssqlServer.objects.create(
            version=version,
            model=model,
            location=location,
            network=network,
            held_by=self.model_instance
        )
        instance_name = 'mssql-server-%s' % mssql_server.sid

        ec2_instance = Ec2Instance.objects.create(
            _name=instance_name,
            instance_id="",
            ami_id=ami_id,
            instance_type=instance_type,
            farm=aws_farm,
            held_by=mssql_server)
        instance = create_ec2_instance_on_aws(ec2_instance)

        vpc_id = instance['NetworkInterfaces'][0]['VpcId']
        if network_name != vpc_id:
            network = get_or_create_aws_network(vpc_id, location)
            mssql_server.network = network
            mssql_server.save()

        mssql_server.held_by = None
        mssql_server.save()


@register_task
class CreateUbuntuMachineFromAwsTask(ThrottledTask):

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get AWS UbuntuMachine with requirements of %s.'
            % (json.dumps(requirements)))

    def max_concurrent_tasks(self, ingredients, requirements):
        return 10

    def run(self, ingredients, requirements):
        disk_size = requirements.get('disk_size',
                                     UbuntuMachine.DEFAULT_DISK_SIZE)
        version = requirements.get('version', UbuntuMachine.DEFAULT_VERSION)
        model = requirements.get('model', UbuntuMachine.DEFAULT_MODEL)
        location = Location.objects.get(name=requirements['location'])
        root_disk_size = requirements.get('root_disk_size',
                                          UbuntuMachine.DEFAULT_ROOT_DISK_SIZE)
        kernel_version = requirements.get('kernel_version',
                                          UbuntuMachine.DEFAULT_KERNEL_VERSION)

        network_name = requirements.get('network', 'default')
        network = Network.objects.get(name=network_name,
                                      location=location)

        aws_farm = get_aws_farm(location)
        ami_id = get_ami_id_for_ubuntu_version(version,
                                               kernel_version,
                                               aws_farm,
                                               root_disk_size)
        instance_type = get_ec2_instance_type_for_model(model)
        ubuntu_machine = UbuntuMachine.objects.create(
            version=version,
            disk_size=disk_size,
            model=model,
            location=location,
            network=network,
            root_disk_size=root_disk_size,
            kernel_version=kernel_version,
            held_by=self.model_instance
        )
        instance_name = 'ubuntu-%s' % ubuntu_machine.sid
        log.info('Creating Ec2Instance')
        ec2_instance = Ec2Instance.objects.create(
            _name=instance_name,
            instance_id="",
            ami_id=ami_id,
            instance_type=instance_type,
            farm=aws_farm,
            held_by=ubuntu_machine)
        instance = create_ec2_instance_on_aws(
            ec2_instance,
           additional_disk_size=disk_size)

        vpc_id = instance['NetworkInterfaces'][0]['VpcId']
        if network_name != vpc_id:
            network = get_or_create_aws_network(vpc_id, location)
            ubuntu_machine.network = network
            ubuntu_machine.save()

        change_hostname_on_ubuntu_machine(ubuntu_machine)
        ubuntu_machine.held_by = None
        ubuntu_machine.save()


@register_task
class CreateUbuntuMachineFromVSphereTask(ThrottledTask):

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get VSphere UbuntuMachine with requirements of %s.'
            % (json.dumps(requirements)))

    def max_concurrent_tasks(self, ingredients, requirements):
        return 50

    def run(self, ingredients, requirements):
        disk_size = requirements.get('disk_size',
                                     UbuntuMachine.DEFAULT_DISK_SIZE)
        version = requirements.get('version', UbuntuMachine.DEFAULT_VERSION)
        model = requirements.get('model', UbuntuMachine.DEFAULT_MODEL)
        location = Location.objects.get(name=requirements['location'])
        network = Network.objects.get(name=requirements['network'])

        hardware, size = get_hardware_and_size_for_model(model)
        esx_host = get_esx_host(location, hardware)
        vcpu, memory = \
            UbuntuMachine.get_vcpu_and_memory_for_hardware_and_size(hardware,
                                                                    size)

        log.info('Using host %s with hardware %s, vcpu %s and memory %s'
                 % (esx_host, hardware, vcpu, memory))

        ubuntu_machine = UbuntuMachine.objects.create(
            version=version,
            disk_size=disk_size,
            model=model,
            location=location,
            network=network,
            held_by=self.model_instance
        )
        instance_name = 'ubuntu-%s' % ubuntu_machine.sid

        virtual_machine = VSphereVirtualMachine.objects.create(
            _name=instance_name,
            instance_uuid="",
            vcenter=esx_host.vcenter,
            held_by=ubuntu_machine)
        create_virtual_machine_on_vsphere(virtual_machine,
                                          esx_host,
                                          UBUNTU_TEMPLATE_NAME,
                                          cpu_count=vcpu,
                                          ram_size_GB=memory)
        change_hostname_on_ubuntu_machine(ubuntu_machine)
        ubuntu_machine.held_by = None
        ubuntu_machine.save()
