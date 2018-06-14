"""Tasks for Bodega AWS."""
import logging
from bodega_core.models import Item
from bodega_core.tasks import SingleItemTask
from botocore.exceptions import ClientError
from rkelery import register_task
from .models import Ec2Instance
from .utils import delete_ec2_instance

log = logging.getLogger(__name__)


@register_task
class DestroyEc2InstanceTask(SingleItemTask):

    @classmethod
    def get_summary(cls, item_sid):
        return ('Destroy Ec2Instance with sid of %s' % item_sid)

    def run(self, item_sid):
        ec2_instance = Ec2Instance.objects.get(sid=item_sid)

        if ec2_instance.state == Item.STATE_DESTROYED:
            log.warning('Attempting to destroy an Ec2Instance that already '
                        'has a state of %s.'
                        % Item.STATE_DESTROYED)
            return

        try:
            delete_ec2_instance(ec2_instance)
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                log.warning('Attempted to delete %s which no longer exists '
                            'in AWS. Marking this item as DESTROYED.'
                            % ec2_instance,
                            exc_info=True)
                ec2_instance.state = Item.STATE_DESTROYED
                ec2_instance.save()
            else:
                # We were not able to clean up the Ec2Instance on AWS and
                # cannot be sure that it no longer exists. Throw an error
                # and do not change the state of the Ec2Instance so that
                # we attempt clean up on it again.
                log.error('Failed to delete ec2 instance (%s).'
                          % ec2_instance.instance_id)
                raise
