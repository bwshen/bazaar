"""Bodega Sd Dev Items tasks."""
import datetime
import json
import logging
from time import sleep

from django.db import transaction
from kubernetes.client.rest import ApiException

# flake8: noqa I100 # Turn off broken import ordering check as flake8 have bug
from bodega_aws.models import AwsFarm, Ec2Instance
from bodega_aws.utils import create_ec2_instance_on_aws
from bodega_aws.utils import get_aws_farm
from bodega_aws.utils import get_or_create_aws_network
from bodega_aws.utils import search_for_ami_id_by_name
from bodega_core.exceptions import bodega_error
from bodega_core.exceptions import bodega_value_error
from bodega_core.models import Location, Network
from bodega_kubernetes.models import KubernetesPod
from bodega_kubernetes.utils import get_kubernetes_client
from bodega_kubernetes.utils import get_kubernetes_farm_for_location
from bodega_utils.ssh import check_ssh_availability
from rkelery import Task
from rkelery import register_task
from .models import SdDevMachine
from .utils import get_v1_pod_configuration

log = logging.getLogger(__name__)
PHASE_RUNNING = 'Running'


@register_task
class CreateSdDevMachineFromKubernetesTask(Task):
    """Get Dev Machine from Kubernetes with a namespace and version hash.

    This task will request an image from the registry with a specified
    sd_dev_bootstrap_hash. We currently do not support build images on demand
    and if a matching image is not found within the registry, we will simply
    fail.
    """

    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get SdDevMachine from Kubernetes with requirements of %s' %
            (json.dumps(requirements)))

    def run(self, ingredients, requirements):
        version = requirements['version']
        location = Location.objects.get(name=requirements['location'])

        network_name = requirements.get('network', 'native')
        network = Network.objects.get(name=network_name,
                                      location=location)
        privileged_mode = requirements.get('privileged_mode', False)
        sd_dev_machine = SdDevMachine.objects.create(
            model=SdDevMachine.MODEL_KUBERNETES,
            location=location,
            network=network,
            version=version,
            privileged_mode=privileged_mode,
            held_by=self.model_instance)

        pod_name = 'sd-dev-%s' % sd_dev_machine.sid
        kubernetes_farm = get_kubernetes_farm_for_location(location)
        pod_namespace = kubernetes_farm.namespace

        kubernetes_pod = KubernetesPod.objects.create(
            _name=pod_name,
            uid="",
            farm=kubernetes_farm,
            held_by=sd_dev_machine)
        pod_config = get_v1_pod_configuration(container_name=pod_name,
                                              pod_name=pod_name,
                                              pod_namespace=pod_namespace,
                                              location=location,
                                              version=version,
                                              privileged_mode=privileged_mode,
                                              network_name=network_name)
        log.info('Specs for pod %s: %s' % (repr(pod_name), pod_config))

        kubernetes_client = get_kubernetes_client(location)
        try:
            pod = kubernetes_client.create_namespaced_pod(pod_namespace,
                                                          pod_config)
        except ApiException as e:
            log.error('Hit error while trying to create pod %s. Normal '
                      'clean up will take care of destroying this item.')
            raise e

        log.info('Waiting for pod %s to have phase of %s.'
                 % (repr(pod_name), repr(PHASE_RUNNING)))
        while PHASE_RUNNING != pod.status.phase:
            sleep(1)
            pod = kubernetes_client.read_namespaced_pod(pod_name,
                                                        pod_namespace)
        if not check_ssh_availability(sd_dev_machine.ip_address,
                                      sd_dev_machine.username,
                                      sd_dev_machine.password):
            msg = ('SSH was not available for %s with IP %s'
                   % (sd_dev_machine, sd_dev_machine.ip_address))
            bodega_error(log, msg)

        with transaction.atomic():
            kubernetes_pod.uid = pod.metadata.uid
            kubernetes_pod.save()
            sd_dev_machine.held_by = None
            sd_dev_machine.save()


@register_task
class CreateSdDevMachineFromAwsTask(Task):
    @classmethod
    def get_summary(cls, ingredients, requirements):
        return (
            'Get SdDevMachine from AWS with requirements of %s' %
            (json.dumps(requirements)))

    @classmethod
    def get_soft_timeout(cls, ingredients, requirements):
        return datetime.timedelta(minutes=30).total_seconds()

    def run(self, ingredients, requirements):
        model = requirements.get('model')
        version = requirements['version']
        location = Location.objects.get(name=requirements['location'])

        network_name = requirements.get('network', 'default')
        network = Network.objects.get(name=network_name,
                                      location=location)
        privileged_mode = requirements.get('privileged_mode', False)
        sd_dev_machine = SdDevMachine.objects.create(
            model=model,
            location=location,
            network=network,
            version=version,
            privileged_mode=privileged_mode,
            held_by=self.model_instance)

        log.debug('Created %s' % sd_dev_machine)

        instance_name = 'sd-dev-%s' % sd_dev_machine.sid
        aws_farm = get_aws_farm(location)
        ami_name = "sd_dev_{0}".format(version)
        ami_id = search_for_ami_id_by_name(aws_farm, ami_name)
        if model.lower() == AwsFarm.MODEL_AWS_M4_2XLARGE:
            instance_type = 'm4.2xlarge'
        elif model.lower() == AwsFarm.MODEL_AWS_M4_LARGE:
            instance_type = 'm4.large'
        else:
            bodega_value_error(
                log,
                'Unrecognized sd_dev_machine AWS model %s' % repr(model))

        ec2_instance = Ec2Instance.objects.create(
            _name=instance_name,
            instance_id="",
            ami_id=ami_id,
            instance_type=instance_type,
            farm=aws_farm,
            held_by=sd_dev_machine)
        instance = create_ec2_instance_on_aws(ec2_instance,
                                              sda1_volume_size=100)

        vpc_id = instance['NetworkInterfaces'][0]['VpcId']
        if network_name != vpc_id:
            network = get_or_create_aws_network(vpc_id, location)
            sd_dev_machine.network = network
            sd_dev_machine.save()

        sd_dev_machine.held_by = None
        sd_dev_machine.save()
