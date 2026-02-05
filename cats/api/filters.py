from django_filters import rest_framework as filters

from cats.models import SimulationRun

class SimulationFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = SimulationRun
        fields = [
            'status',
            'created_after',
            'created_before',
        ]