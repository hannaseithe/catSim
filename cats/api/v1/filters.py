from django_filters import rest_framework as filters
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import make_aware
from django.core.validators import MaxValueValidator, MinValueValidator
import datetime

from cats.models import SimulationRun

#custom filter to be able to both filter for date and datetime
class DateOrDateTimeFilter(filters.IsoDateTimeFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        # If value is already a datetime, pass it through
        if isinstance(value, datetime.datetime):
            dt = value
        # If value is already a date (but not datetime), convert to datetime start-of-day
        elif isinstance(value, datetime.date):
            dt = make_aware(datetime.datetime.combine(value, datetime.time.min))
        # Otherwise assume string and try to parse
        elif isinstance(value, str):
            dt = parse_datetime(value)
            if dt is None:
                date = parse_date(value)
                if date:
                    dt = make_aware(datetime.datetime.combine(date, datetime.time.min))
                else:
                    # invalid string, don't apply any filter
                    return qs
        else:
            # unsupported type of filter value, don't apply any filter
            return qs

        # pass datetime to normal IsoDateTimeFilter
        return super().filter(qs, dt)

class SimulationFilter(filters.FilterSet):
    status = filters.ChoiceFilter(field_name="status", choices= SimulationRun.Status.choices)
    user = filters.NumberFilter(field_name="user",validators=[MinValueValidator(1), MaxValueValidator(1e18)])
    created_at_min = DateOrDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_max = DateOrDateTimeFilter(field_name="created_at", lookup_expr="lte")
    iterations = filters.NumberFilter(field_name="iterations", validators=[MinValueValidator(1)])
    iterations_min = filters.NumberFilter(field_name="iterations", lookup_expr="gte", validators=[MinValueValidator(1)])
    iterations_max = filters.NumberFilter(field_name="iterations", lookup_expr="lte", validators=[MinValueValidator(1)])
    cat_amount = filters.NumberFilter(field_name="cat_amount", validators=[MinValueValidator(1)])
    cat_amount_min = filters.NumberFilter(field_name="cat_amount", lookup_expr="gte", validators=[MinValueValidator(1)])
    cat_amount_max = filters.NumberFilter(field_name="cat_amount", lookup_expr="lte", validators=[MinValueValidator(1)])
    node_amount = filters.NumberFilter(field_name="node_amount", validators=[MinValueValidator(1)])
    node_amount_min = filters.NumberFilter(field_name="node_amount", lookup_expr="gte", validators=[MinValueValidator(1)])
    node_amount_max = filters.NumberFilter(field_name="node_amount", lookup_expr="lte", validators=[MinValueValidator(1)])

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