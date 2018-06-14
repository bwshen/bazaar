"""Recipes for Bodega generic items."""
import logging
from bodega_core import exceptions, Recipe
from .models import MssqlServer, UbuntuMachine
from .tasks import (CreateMssqlServerFromAwsTask,
                    CreateUbuntuMachineFromAwsTask,
                    CreateUbuntuMachineFromVSphereTask)

log = logging.getLogger(__name__)


class MssqlServerRecipe(Recipe):
    """Recipe for the MssqlServer Item class."""

    @property
    def required_ingredients(self):
        return None

    def creator_task(self, requirements):
        model = self.requirements.get('model', None)

        if not model:
            log.debug('No model was specified so using default model '
                      '(%s) for MssqlServer.'
                      % MssqlServer.DEFAULT_MODEL)
            model = MssqlServer.DEFAULT_MODEL

        if model.lower().startswith('aws'):
            return CreateMssqlServerFromAwsTask
        else:
            exceptions.bodega_value_error(
                log,
                'The requested model (%s) is not supported for MssqlServer '
                'items.'
                % model)


class UbuntuMachineRecipe(Recipe):
    """Recipe for the UbuntuMachine Item class."""

    @property
    def required_ingredients(self):
        return None

    def creator_task(self, requirements):
        model = self.requirements.get('model', None)

        if not model:
            log.debug('No model was specified so using default model '
                      '(%s) for Ubuntu.'
                      % UbuntuMachine.DEFAULT_MODEL)
            model = UbuntuMachine.DEFAULT_MODEL

        if model.lower().startswith('aws'):
            return CreateUbuntuMachineFromAwsTask
        elif model.lower().startswith('vsphere'):
            return CreateUbuntuMachineFromVSphereTask
        else:
            exceptions.bodega_value_error(
                log,
                'The requested model (%s) is not supported for Ubuntu items.'
                % model)
