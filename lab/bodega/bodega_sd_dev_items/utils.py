"""Lower level Bodega utility functions for SdDevMachines."""
import logging

from bodega_kubernetes.utils import get_docker_image_name

log = logging.getLogger(__name__)
CLUSTER = 'bodega-cluster'
CONTEXT = 'bodega-context'
USER = 'bodega-user'


def get_default_pod_specs():
    pod_specs = {}
    pod_specs['apiVersion'] = 'v1'
    pod_specs['kind'] = 'Pod'
    pod_specs['metadata'] = {}
    pod_specs['spec'] = {}
    pod_specs['spec']['containers'] = []
    pod_specs['spec']['restartPolicy'] = 'OnFailure'

    return pod_specs


def get_v1_object_metadata_dict(pod_name, pod_namespace):
    metadata_dict = {}
    metadata_dict['labels'] = {'name': 'sd_dev'}
    metadata_dict['name'] = pod_name
    metadata_dict['namespace'] = pod_namespace

    return metadata_dict


def get_v1_container_dict(container_name, docker_image_name, privileged_mode):
    container_dict = {}
    container_dict['command'] = ["/opt/sd-dev-init/init.sh"]
    container_dict['args'] = ['/usr/sbin/sshd', '-eD']
    container_dict['imagePullPolicy'] = 'IfNotPresent'
    container_dict['ports'] = [{'containerPort': 8000}]
    container_dict['name'] = container_name
    container_dict['image'] = docker_image_name
    container_dict['volumeMounts'] = [
        {
            'name': 'git-rubrik-sdmain',
            # Mount to the path currently used by Jenkins jobs. However, the
            # way https://github.com/kubernetes/git-sync/ works, the host path
            # is slightly different as /git/rubrik/sdmain/.git. To more easily
            # support multiple repos in /git that the pod can simply mount as
            # /git, we should update jobs to use /git/rubrik/sdmain/.git when
            # more of them are running on Bodega sd_dev machines.
            'mountPath': '/git/rubrik/sdmain.git',
            'readOnly': True
        },
        {
            'name': 'shared-memory',
            'mountPath': '/dev/shm'
        }
    ]

    security_context = {
        'capabilities': {
            'add': ['NET_ADMIN']
        },
        'privileged': privileged_mode
    }

    container_dict['securityContext'] = security_context

    return container_dict


def get_node_selector_dict(privileged_mode, network_name):
    node_selector_dict = {
        'for_dev_machines': 'true',
        # We intentionally always use the allow_privileged_mode label to keep
        # privileged and on-privileged use cases disjoint from each other.
        # That way non-privileged use cases are rewarded by only sharing a
        # host with other use cases that don't risk breaking the host.
        'allow_privileged_mode': 'true' if privileged_mode else 'false',
        'network': network_name if network_name else 'native'
    }
    return node_selector_dict


def get_v1_pod_configuration(container_name,
                             pod_name,
                             pod_namespace,
                             location,
                             version,
                             privileged_mode,
                             network_name):
    docker_image_name = get_docker_image_name(
        location,
        'sd_dev',
        version)

    pod_specs = get_default_pod_specs()
    pod_specs['metadata'] = get_v1_object_metadata_dict(pod_name,
                                                        pod_namespace)
    pod_specs['spec']['nodeSelector'] = get_node_selector_dict(privileged_mode,
                                                               network_name)
    pod_specs['spec']['containers'].append(get_v1_container_dict(
        container_name, docker_image_name, privileged_mode))
    pod_specs['spec']['volumes'] = [
        {
            'name': 'git-rubrik-sdmain',
            'hostPath': {
                'path': '/git/rubrik/sdmain/.git'
            }
        },
        # Kubernetes by default assigns 64 Mb of shm to each container
        # This causes failures for certain tests (INFRA-3917)

        # With the Kubernetes version we currently have, it is not possible
        # to specify a limit on the amount of space the mount can use
        # This will give shm access to half of total memory the container has
        # To specify a limit, kubernetes needs to be updated to at least 1.7
        # and have the feature-gate LocalStorageCapacityIsolation
        # More info at https://kubernetes.io/docs/reference/feature-gates/
        # Leaving the sizeLimit parameter currently doesn't do any harm and
        # will come into effect when Kubernetes is updated
        {
            'name': 'shared-memory',
            'emptyDir': {
                'medium': 'Memory',
                'sizeLimit': '256Mi'
            }
        }
    ]
    return pod_specs
