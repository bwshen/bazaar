"""Recipes for Bodega generic items."""
import logging
from bodega_core import exceptions, Recipe
from .models import CockroachDBDepsMachine
from .tasks import CreateCockroachDBDepsMachineFromAwsTask

log = logging.getLogger(__name__)


class CockroachDBDepsMachineRecipe(Recipe):
    """Recipe for the CockroachDBDepsMachine Item class."""

    @property
    def required_ingredients(self):
        return None

    def creator_task(self, requirements):
        model = self.requirements.get('model', None)

        if not model:
            log.debug('No model was specified so using default model '
                      '(%s) for CockroachDBDepsMachine.'
                      % CockroachDBDepsMachine.DEFAULT_MODEL)
            model = CockroachDBDepsMachine.DEFAULT_MODEL

        if model.lower().startswith('aws'):
            return CreateCockroachDBDepsMachineFromAwsTask
        else:
            exceptions.bodega_value_error(
                log,
                'The requested model (%s) is not supported '
                'for CockroachDBDepsMachine items.'
                % model)
