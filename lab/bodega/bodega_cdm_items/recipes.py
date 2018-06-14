"""Recipes for Bodega CdmNode items."""
import logging
from bodega_core import exceptions, Recipe
from .models import CdmCluster, CdmNode
from .tasks import CreateCdmClusterFromAwsTask, CreateCdmNodeFromAwsTask

log = logging.getLogger(__name__)


class CdmNodeRecipe(Recipe):
    """Recipe for the CdmNode Item class."""

    @property
    def required_ingredients(self):
        # Currently we don't need any ingredients for a CdmNode since
        # we can drive the install from Bodega itself.
        return None

    def creator_task(self, requirements):
        model = self.requirements.get('model', None)

        if not model:
            log.debug('No model was specified so using default model '
                      '(%s) for CdmNodes.'
                      % CdmNode.DEFAULT_MODEL)
            model = CdmNode.DEFAULT_MODEL

        if model.lower().startswith('aws'):
            return CreateCdmNodeFromAwsTask
        else:
            exceptions.bodega_value_error(
                log,
                'The requested model (%s) is not supported for CdmNode items.'
                % model)


class CdmClusterRecipe(Recipe):
    """Recipe for the CdmCluster Item class."""

    @property
    def required_ingredients(self):
        # CdmCluster is made up of a specified number of nodes

        ingredients = {}
        for node_number in range(self.requirements.get(
                'node_count',
                CdmCluster.DEFAULT_NODE_COUNT)):
            nickname = 'cdm_node_%d' % node_number
            ingredients[nickname] = {
                'type': 'cdm_node',
                'requirements': {
                    'artifacts_url': self.requirements.get('artifacts_url',
                                                           None),
                    'location': self.requirements.get('location'),
                    'network': self.requirements.get('network', None),
                    'model': self.requirements.get('model',
                                                   CdmCluster.DEFAULT_MODEL)
                }
            }
        return ingredients

    def creator_task(self, requirements):
        model = self.requirements.get('model', None)

        if not model:
            log.debug('No model was specified so using default model '
                      '(%s) for CdmClusters.'
                      % CdmCluster.DEFAULT_MODEL)
            model = CdmCluster.DEFAULT_MODEL

        if model.lower().startswith('aws'):
            return CreateCdmClusterFromAwsTask
        else:
            exceptions.bodega_value_error(
                log,
                'The requested model (%s) is not supported for CdmCluster '
                'items.'
                % model)
