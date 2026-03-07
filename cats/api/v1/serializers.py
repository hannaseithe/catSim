from decimal import Decimal
from typing import Dict, List, Union
from rest_framework import serializers

from cats.models import SimulationResults, SimulationRun

JSONType = Union[
    Dict[str, "JSONType"],
    List["JSONType"],
    str,
    int,
    float,
    bool,
    None,
]

class StrictFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            raise serializers.ValidationError("Boolean is not allowed for this float field")
        return super().to_internal_value(data)

class SimulationParamsSerializerV1(serializers.Serializer):
    iterations = serializers.IntegerField(default=1000, min_value=1, max_value=10000)
    cat_amount = serializers.IntegerField(default=10, min_value=2, max_value= 200)
    node_amount = serializers.IntegerField(default=60, min_value=3, max_value=1000)
    mean_edges = serializers.IntegerField(default=4, min_value=2, max_value=20)
    var_edges = StrictFloatField(default=1.0, min_value=0.0, max_value=5)
    mean_aggressive = StrictFloatField(default=0.0, min_value=-1.0, max_value=1)
    var_aggressive = StrictFloatField(default=0.1, min_value=0.0, max_value=0.5)
    mean_laziness = StrictFloatField(default=0.5, min_value=0.0, max_value=1)
    var_laziness = StrictFloatField(default=0.05, min_value=0.0, max_value=0.25)

    def validate(self, data):
        if data["cat_amount"] * 3 >= data["node_amount"]:
            raise serializers.ValidationError(
                "Nodes must be at least thrice the amount of cats"
            )

        if data["mean_edges"] * 2 >= data["node_amount"]:
            raise serializers.ValidationError(
                "The mean of edges cant be more than half the amount of nodes"
            )

        if data["var_edges"] * 3 >= data["mean_edges"]:
            raise serializers.ValidationError(
                "The variance of edges cant be more than a third of the mean"
            )
        for field_name, value in data.items():
            field = self.fields[field_name]
            expected_type = float if isinstance(field, serializers.FloatField) else int
            if not isinstance(value, expected_type):
                raise serializers.ValidationError(
                    f"{field_name} must be of type {expected_type.__name__}"
                )
        return data


class SimulationCreateSerializerV1(serializers.Serializer):
    uuid = serializers.UUIDField(
        required=True,
        help_text="Client-generated UUID used for idempotent simulation creation."
        )
    params = SimulationParamsSerializerV1()

    

class SimulationStatusSerializerV1(serializers.ModelSerializer):
    params = serializers.SerializerMethodField()
    class Meta:
        model = SimulationRun
        fields = ["id", "uuid", "status", "created_at", "started_at", "finished_at", "params", "user"]
    

    def get_params(self, obj) -> JSONType:
        def convert(value: JSONType) -> JSONType:
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert(v) for v in value]
            elif isinstance(value, Decimal):
                return float(value)
            return value

        return convert(obj.params)


class SimulationErrorSerializerV1(serializers.ModelSerializer):
    error = serializers.CharField(source="error_message", read_only=True)

    class Meta:
        model = SimulationRun
        fields = ["id", "uuid", "status", "error"]


class SimulationResultSerializerV1(serializers.ModelSerializer):
    run_id = serializers.PrimaryKeyRelatedField(source="run", read_only=True)

    class Meta:
        model = SimulationResults
        fields = ["id", "run_id", "metrics"]

class TokenRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class TokenRefreshResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class LoginErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    email = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    password = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )

