from django_filters import rest_framework as filters

from cats.models import SimulationRun

class SimulationFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    user = filters.CharFilter(field_name="user")
    created_at_min = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_max = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    iterations = filters.NumberFilter(field_name="iterations")
    iterations_min = filters.NumberFilter(field_name="iterations", lookup_expr="gte")
    iterations_max = filters.NumberFilter(field_name="iterations", lookup_expr="lte")
    cat_amount = filters.NumberFilter(field_name="cat_amount")
    cat_amount_min = filters.NumberFilter(field_name="cat_amount", lookup_expr="gte")
    cat_amount_max = filters.NumberFilter(field_name="cat_amount", lookup_expr="lte")
    node_amount = filters.NumberFilter(field_name="node_amount")
    node_amount_min = filters.NumberFilter(field_name="node_amount", lookup_expr="gte")
    node_amount_max = filters.NumberFilter(field_name="node_amount", lookup_expr="lte")

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