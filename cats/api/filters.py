from functools import partial
from django_filters import rest_framework as filters

from cats.models import SimulationRun

#this custom method fucntion is needed because when applying NumberFilter to Json fields the filter request value gets cast as Decimal which in turn clashes with 
#an internal call to the JSONEncoder when filtering the JsonField, therefore we cast the filter value to int here
def filter_int_params(queryset, name, value, lookup="exact"):
    value = int(value)
    return queryset.filter(**{f"{name}__{lookup}": value})

class SimulationFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    user = filters.CharFilter(field_name="user")
    created_at_min = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_max = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    iterations = filters.NumberFilter(field_name="params__iterations", method=filter_int_params)
    iterations_min = filters.NumberFilter(field_name="params__iterations", method=partial(filter_int_params, lookup="gte"))
    iterations_max = filters.NumberFilter(field_name="params__iterations", method=partial(filter_int_params, lookup="lte"))
    cat_amount = filters.NumberFilter(field_name="params__cat_amount", method=filter_int_params)
    cat_amount_min = filters.NumberFilter(field_name="params__cat_amount", method=partial(filter_int_params, lookup="gte"))
    cat_amount_max = filters.NumberFilter(field_name="params__cat_amount", method=partial(filter_int_params, lookup="lte"))
    node_amount = filters.NumberFilter(field_name="params__node_amount", method=filter_int_params)
    node_amount_min = filters.NumberFilter(field_name="params__node_amount", method=partial(filter_int_params, lookup="gte"))
    node_amount_max = filters.NumberFilter(field_name="params__node_amount", method=partial(filter_int_params, lookup="lte"))



    class Meta:
        model = SimulationRun
        fields = [
            'status',
            'user',
            'created_at_min',
            'created_at_max',
            'iterations',
            'iterations_min',
            'iterations_max',
            'cat_amount',
            'cat_amount_min',
            'cat_amount_max',
            'node_amount',
            'node_amount_min',
            'node_amount_max',
        ]