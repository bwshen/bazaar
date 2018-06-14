"""RKelery filters."""
from django.db.models import Q
from django_filters import CharFilter, ChoiceFilter
from rest_framework.filters import FilterSet
from . import states
from .models import Task
from .utils import json_dump


class TaskFilter(FilterSet):
    id = CharFilter(name='task_id')

    type = CharFilter(name='task')

    state = ChoiceFilter(
        name='task_result__status', choices=states.choices(states.ALL_STATES))

    root = CharFilter(name='root_id')

    parent = CharFilter(name='parent_id')

    group = CharFilter(name='group_id')

    arg = CharFilter(method='filter_arg')

    def filter_arg(self, queryset, name, value):
        return queryset.filter(
            Q(args_json__contains=json_dump(value)) |
            Q(kwargs_json__contains=json_dump(value)))

    class Meta:
        model = Task
        fields = ['id', 'type', 'state', 'root', 'parent', 'group', 'origin',
                  'arg']
