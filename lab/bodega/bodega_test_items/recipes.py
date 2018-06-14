"""Recipes for Bodega CdmNode items."""
import logging
from bodega_core import Recipe
from rkelery.models import Task
from .models import BasicItem, ComplexItem
from .tasks import CreateBasicItemTask, CreateComplexItemTask

log = logging.getLogger(__name__)

CREATE_BASIC_ITEM_TASK = 'CreateBasicItem'
CREATE_COMPLEX_ITEM_TASK = 'CreateComplexItem'


class BasicItemRecipe(Recipe):
    @property
    def required_ingredients(self):
        return None

    def creator_task(self, requirements):
        BasicItem.objects.create(**requirements)
        Task.objects.create(task=CREATE_BASIC_ITEM_TASK,
                            args=[requirements],
                            kwargs={})
        return CreateBasicItemTask


class ComplexItemRecipe(Recipe):
    @property
    def required_ingredients(self):
        ingredients = {
            'basic_item_1': {
                'type': 'basic_item',
                'requirements': {
                    'choice': 'B',
                    'boolean': False
                }
            },
            'basic_item_2': {
                'type': 'basic_item',
                'requirements': {
                    'choice': 'A',
                    'boolean': False
                }
            }
        }

        return ingredients

    def creator_task(self, requirements):
        ComplexItem.objects.create(**requirements)
        Task.objects.create(task=CREATE_COMPLEX_ITEM_TASK,
                            args=[requirements],
                            kwargs={})

        return CreateComplexItemTask
