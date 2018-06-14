"""Tasks for Bodega AWS."""
import logging
from bodega_core.models import Item
from bodega_core.tasks import SingleItemTask
from rkelery import register_task
from .models import VSphereVirtualMachine
from .utils import delete_virtual_machine

log = logging.getLogger(__name__)


@register_task
class DestroyVSphereVirtualMachineTask(SingleItemTask):

    @classmethod
    def get_summary(cls, item_sid):
        return ('Destroy VSphereVirtualMachine with sid of %s' % item_sid)

    def run(self, item_sid):
        virtual_machine = VSphereVirtualMachine.objects.get(sid=item_sid)

        if virtual_machine.state == Item.STATE_DESTROYED:
            log.warning('Attempting to destroy a VSphereVirtualMachine '
                        'that already has a state of %s.'
                        % Item.STATE_DESTROYED)
            return
        delete_virtual_machine(virtual_machine)
