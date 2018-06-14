"""Bodega top level utilities."""
from bodega_core.exceptions import BodegaTypeError
from bodega_core.models import Item, Order
from bodega_legacy_items.models import JenkinsTask
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.serializers import HyperlinkedRelatedField
from rkelery.models import Task
from sid_from_id.encoder import get_sid
from sid_from_id.fields import HyperlinkedRelatedFieldUsingSid

BASE_URL = 'https://%s' % settings.ALLOWED_HOSTS[0]


def absolute_reverse(view_name, url_kwargs={}):
    # reverse returns a URL with a leading '/' character.
    return ("%s%s" % (BASE_URL, reverse(view_name, kwargs=url_kwargs)))


# Classes for representing various view-related info of models. They have a
# fair amount of redundancy with stuff that's already in views, serializers,
# and routes. This info can't just live in those classes because use cases of
# these lower level utilities often can't import the actual views or
# serializers because that would introduce circular dependencies. This is kind
# of ugly, and the correct solution is probably to make views, serializers,
# and routes automatically pull their info from these classes. We can revisit
# this once we have a better idea of how all this info is used by various
# parts of the stack.

class ModelViewInfo(object):
    # Subclasses must override.
    view_name = None
    queryset = None

    url_field_class = HyperlinkedRelatedFieldUsingSid
    lookup_field = 'sid'
    lookup_url_kwarg = 'sid'

    @classmethod
    def get_display_name(cls, obj):
        raise NotImplementedError(
            'Model instances must provide a `display_name` attribute or ' +
            'subclasses must override `get_display_name`.')


class ItemViewInfo(ModelViewInfo):
    view_name = 'item-detail'
    queryset = Item.objects.all()

    @classmethod
    def get_display_name(cls, item):
        return 'Item %s' % item.sid


class JenkinsTaskViewInfo(ModelViewInfo):
    view_name = 'jenkinstask-detail'
    queryset = JenkinsTask.objects.all()

    @classmethod
    def get_display_name(cls, jenkins_task):
        return 'Recovery task'


class OrderViewInfo(ModelViewInfo):
    view_name = 'order-detail'
    queryset = Order.objects.all()

    @classmethod
    def get_display_name(cls, order):
        return 'Order %s' % order.sid


class TaskViewInfo(ModelViewInfo):
    view_name = 'task-detail'
    queryset = Task.objects.all()
    url_field_class = HyperlinkedRelatedField
    lookup_field = 'task_id'
    lookup_url_kwarg = 'id'

    @classmethod
    def get_display_name(cls, task):
        return '%s task' % task.task_class.get_task_display_name()


class UserViewInfo(ModelViewInfo):
    view_name = 'user-detail'
    queryset = User.objects.all()

    @classmethod
    def get_display_name(cls, user):
        return user.username


_model_view_info = {
    Item: ItemViewInfo,
    JenkinsTask: JenkinsTaskViewInfo,
    Order: OrderViewInfo,
    Task: TaskViewInfo,
    User: UserViewInfo
}


def get_related_url_field(model):
    info = _model_view_info[model]
    return info.url_field_class(
        queryset=info.queryset,
        view_name=info.view_name,
        lookup_field=info.lookup_field,
        lookup_url_kwarg=info.lookup_url_kwarg)


def get_related_url_fields(*models):
    return {model: get_related_url_field(model) for model in models}


def get_url_and_display_name(obj):
    model = obj.__class__
    if model not in _model_view_info.keys():
        raise BodegaTypeError(
            '%s is not one of the models with registered view info.' %
            (repr(model)))

    info = _model_view_info[model]
    if info.lookup_field == 'sid':
        lookup_field_value = get_sid(obj)
    else:
        lookup_field_value = getattr(obj, info.lookup_field)
    url = absolute_reverse(
        info.view_name, {info.lookup_url_kwarg: lookup_field_value})
    display_name = info.get_display_name(obj)
    return (url, display_name)
