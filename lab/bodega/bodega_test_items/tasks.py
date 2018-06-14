"""Tasks for Bodega CdmNode items."""
import logging
from rkelery import register_task, Task

log = logging.getLogger(__name__)


@register_task
class CreateBasicItemTask(Task):
    @classmethod
    def get_summary(cls, requirements):
        pass

    def run(self, requirements):
        pass


@register_task
class CreateComplexItemTask(Task):
    @classmethod
    def get_summary(cls, requirements):
        pass

    def run(self, requirements):
        pass
