"""Bodega Kubernetes tasks."""

import logging
import kubernetes

from bodega_core.models import Item
from bodega_core.tasks import SingleItemTask
from kubernetes.client.rest import ApiException
from rkelery import register_task
from .models import KubernetesPod
from .utils import get_kubernetes_client

log = logging.getLogger(__name__)


@register_task
class DestroyKubernetesPodTask(SingleItemTask):

    @classmethod
    def get_summary(cls, pod_sid):
        return ('Destroy KubernetesPod with sid of %s'
                % (repr(pod_sid)))

    def run(self, pod_sid):
        kubernetes_pod = KubernetesPod.objects.get(sid=pod_sid)

        if kubernetes_pod.state == Item.STATE_DESTROYED:
            log.warning('Attempting to destroy an Ec2Instance that already '
                        'has a state of %s.'
                        % Item.STATE_DESTROYED)
            return

        kubernetes_farm = kubernetes_pod.farm
        pod_namespace = kubernetes_farm.namespace
        pod_name = kubernetes_pod._name
        log.debug('Destroying %s from %s' % (kubernetes_pod, kubernetes_farm))

        kubernetes_client = get_kubernetes_client(
            kubernetes_farm.location,
            farm=kubernetes_farm)
        try:
            kubernetes_client.delete_namespaced_pod(
                pod_name,
                pod_namespace,
                kubernetes.client.V1DeleteOptions())
            log.info('Successfully destroyed pod %s' % pod_name)
            kubernetes_pod.state = Item.STATE_DESTROYED
            kubernetes_pod.save()
        except ApiException as e:
            if e.status == 404:
                log.warning(('Unable to find corresponding pod for %s on the '
                             'Kubernetes cluster. Marking it as %s.')
                            % (kubernetes_pod, Item.STATE_DESTROYED),
                            exc_info=True)
                kubernetes_pod.state = Item.STATE_DESTROYED
                kubernetes_pod.save()
            else:
                raise
