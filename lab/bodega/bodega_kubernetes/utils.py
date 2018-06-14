"""Bodega Kubernetes utility functions."""
import logging
import os
import subprocess
import tempfile
from datetime import timedelta

import kubernetes
from bodega_core import exceptions
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from memoize import memoize
from .models import KubernetesFarm

log = logging.getLogger(__name__)
CLUSTER = 'bodega-cluster'
CONTEXT = 'bodega-context'
USER = 'bodega-user'


def get_kubernetes_farm_for_location(location):
    """Get KubernetesFarm object based on location.

    Using the settings.KUBERNETES_NAMESPACE and
    settings.KUBERNETES_URL_FOR_LOCATION variables in our local_settings files,
    query for a given farm based on location.
    """
    try:
        kubernetes_farm = KubernetesFarm.objects.get(location=location)
        return kubernetes_farm
    except ObjectDoesNotExist:
        exceptions.bodega_value_error(
            log,
            ('Could not find KubernetesFarm object for location %s.'
             % location.name))


def _get_docker_registry_for_location(location):
    if location.name not in settings.DOCKER_REGISTRY_FOR_LOCATION:
        exceptions.BodegaValueError(
            'Location %s is not a valid location. Valid locations for the '
            'Docker registry are: %s'
            % (repr(location.name),
               repr(settings.DOCKER_REGISTRY_FOR_LOCATION.keys())))
    return settings.DOCKER_REGISTRY_FOR_LOCATION[location.name]


def get_docker_image_name(location, tag_name, version):
    registry = _get_docker_registry_for_location(location)
    image_name = '%s/%s:%s' % (registry, tag_name, version)
    return image_name


def _create_kubernetes_cluster_config_info(farm, kubeconfig_file):
    kubernetes_ca_cert = farm.ca_cert
    kubernetes_url = farm.url

    ca_cert_file = tempfile.mkstemp(suffix='.crt')[1]
    try:
        with open(ca_cert_file, 'w') as file:
            file.write(kubernetes_ca_cert)

        kubeconfig_opt = '--kubeconfig=%s' % kubeconfig_file
        certificate_authority_opt = '--certificate-authority=%s' % ca_cert_file
        server_opt = '--server=%s' % (kubernetes_url)
        subprocess.call(['kubectl', kubeconfig_opt, 'config', 'set-cluster',
                         CLUSTER, server_opt, certificate_authority_opt,
                         '--embed_certs=true'])
    finally:
        os.remove(ca_cert_file)


def _create_kubernetes_user_config_info(farm, kubeconfig_file):
    kubeconfig_opt = '--kubeconfig=%s' % kubeconfig_file
    token_opt = '--token=%s' % farm.token
    subprocess.call(['kubectl', kubeconfig_opt, 'config', 'set-credentials',
                     USER, token_opt])


def _create_and_set_kubernetes_context_config_info(farm, kubeconfig_file):
    kubernetes_namespace = farm.namespace

    kubeconfig_opt = '--kubeconfig=%s' % kubeconfig_file
    cluster_opt = '--cluster=%s' % CLUSTER
    user_opt = '--user=%s' % USER
    namespace_opt = '--namespace=%s' % kubernetes_namespace
    subprocess.call(['kubectl', kubeconfig_opt, 'config', 'set-context',
                     CONTEXT, cluster_opt, user_opt, namespace_opt])
    subprocess.call(['kubectl', kubeconfig_opt, 'config', 'use-context',
                     CONTEXT])


def create_kubernetes_config_file_for_location(location, farm=None):
    """Create a Kubernetes config file from given location.

    Use the 'kubectl' command to generate a kubeconfig file for Kubernetes.
    The following Kubernetes commands will be used.

    kubectl --kubeconfig=NAMESPACE.kubeconfig config set-cluster KUBERNETES_URL
        --server=https://KUBERNETES_URL:443
        --certificate-authority=/path/to/ca.crt
        --embed-certs=true
    kubectl --kubeconfig=NAMESPACE.kubeconfig config set-credentials USER
        --token=$(contents of token-rcmct)
    kubectl --kubeconfig=NAMESPACE.kubeconfig config set-context
        NAMESPACE.KUBERNETES_URL --cluster=KUBERNETES_URL --user=USER
        --namespace=NAMESPACE
    kubectl --kubeconfig=NAMESPACE.kubeconfig config use-context
        NAMESPACE.KUBERNETES_URL
    """
    if not farm:
        farm = get_kubernetes_farm_for_location(location)

    kubeconfig_file = tempfile.mkstemp()[1]
    _create_kubernetes_cluster_config_info(farm, kubeconfig_file)
    _create_kubernetes_user_config_info(farm, kubeconfig_file)
    _create_and_set_kubernetes_context_config_info(farm, kubeconfig_file)

    return kubeconfig_file


def delete_kubernetes_config(filepath):
    os.remove(filepath)
    log.debug('Successfully deleted %s.' % repr(filepath))


def get_kubernetes_client(location, farm=None):
    config_filepath = create_kubernetes_config_file_for_location(
        location,
        farm=farm)
    try:
        kubernetes_client = kubernetes.client.CoreV1Api(
            api_client=kubernetes.config.new_client_from_config(
                config_file=config_filepath))
    finally:
        delete_kubernetes_config(config_filepath)
    return kubernetes_client


@memoize(timeout=timedelta(minutes=5).total_seconds())
def get_kubernetes_pod_ip(kubernetes_pod):
    farm = kubernetes_pod.farm
    kubernetes_client = get_kubernetes_client(farm.location, farm)
    pod = kubernetes_client.read_namespaced_pod(
        kubernetes_pod._name, farm.namespace)
    return pod.status.pod_ip
