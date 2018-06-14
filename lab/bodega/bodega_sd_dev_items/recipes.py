"""Recipes for Bodega SdDev items."""
import logging

# flake8: noqa I100 # Turn off broken import ordering check as flake8 have bug
from bodega_core import Recipe
from bodega_core import exceptions
from .models import SdDevMachine
from .tasks import CreateSdDevMachineFromAwsTask
from .tasks import CreateSdDevMachineFromKubernetesTask

log = logging.getLogger(__name__)


class SdDevMachineRecipe(Recipe):
    """Recipe for the SdDevMachine Item class."""

    DEFAULT_MODEL = SdDevMachine.MODEL_KUBERNETES

    @property
    def required_ingredients(self):
        return None

    def creator_task(self, requirements):
        model = self.requirements.get('model', None)

        if not model:
            log.debug('No model was specified so using default model '
                      '(%s) for SdDevMachines.'
                      % SdDevMachineRecipe.DEFAULT_MODEL)
            model = SdDevMachineRecipe.DEFAULT_MODEL

        if model.lower() == SdDevMachine.MODEL_KUBERNETES.lower():
            return CreateSdDevMachineFromKubernetesTask
        elif model.lower().startswith('aws'):
            return CreateSdDevMachineFromAwsTask
        else:
            exceptions.bodega_value_error(
                log,
                'The requested model (%s) is not supported for SdDevMachine '
                'items.' % model)
