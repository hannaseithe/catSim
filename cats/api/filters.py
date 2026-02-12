from django_filters import rest_framework as filters

from cats.models import SimulationRun


class SimulationFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    user = filters.CharFilter(field_name="user")
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    iterations = filters.NumberFilter(field_name="params__iterations", method="filter_int_params")
    cat_amount = filters.NumberFilter(field_name="params__cat_amount", method="filter_int_params")
    node_amount = filters.NumberFilter(field_name="params__node_amount", method="filter_int_params")

    def filter_int_params(self, queryset, name, value):
        value = int(value)
        matching_filter = next((filter for filter in self.filters.values() if filter.field_name == name), None)
        if not matching_filter:
            return queryset
        lookup = getattr(matching_filter, "lookup_expr", "exact")
        return queryset.filter(**{f"{name}__{lookup}": value})

    class Meta:
        model = SimulationRun
        fields = [
            'status',
            'user',
            'created_after',
            'created_before',
            'iterations',
            'cat_amount',
            'node_amount',
        ]