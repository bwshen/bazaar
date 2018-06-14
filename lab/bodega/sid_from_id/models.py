from __future__ import unicode_literals

import copy
from django.db import models

from .encoder import get_sid, SidEncoder


class SidFromIdManager(models.Manager):
    """A manager which translates basic queries for SIDs so that
    objects.filter(sid='Q8qkS-EXWem1') would behave like
    objects.filter(id=1). This is just more convenient syntax so that in
    many cases we can use SIDs like IDs. For more complicated queries like
    traversing relationships, we still need do something like
    objects.filter(child__id=sidEncoder.decode('Q8qkS-EXWem1'))
    """

    def _translate_q(self, q_args, q_kwargs):
        new_args = copy.deepcopy(q_args)
        new_kwargs = copy.deepcopy(q_kwargs)

        if 'sid' in new_kwargs.keys():
            sid = new_kwargs.pop('sid')
            encoder = SidEncoder(self.model)
            pk = encoder.decode(sid)
            new_kwargs['pk'] = pk

        return (new_args, new_kwargs)

    def get(self, *args, **kwargs):
        (new_args, new_kwargs) = self._translate_q(args, kwargs)
        return super(SidFromIdManager, self).get(*new_args, **new_kwargs)

    def filter(self, *args, **kwargs):
        (new_args, new_kwargs) = self._translate_q(args, kwargs)
        return super(SidFromIdManager, self).filter(*new_args, **new_kwargs)

    def exclude(self, *args, **kwargs):
        (new_args, new_kwargs) = self._translate_q(args, kwargs)
        return super(SidFromIdManager, self).exclude(*new_args, **new_kwargs)


class ModelWithSidFromId(models.Model):
    """A base class for models that will use SIDs from integer IDs. Models that
    we control can use this base class to get conveniences such as the default
    manager defined above and a sid property.
    """

    objects = SidFromIdManager()

    class Meta:
        abstract = True

    @property
    def sid(self):
        return get_sid(self)
