from decimal import Decimal
from rest_framework import serializers

from cats.models import SimulationResults, SimulationRun

class SimulationParamsSerializer(serializers.Serializer):
    iterations = serializers.IntegerField(default=1000, min_value=1, max_value=10000)
    cat_amount = serializers.IntegerField(default=10, min_value=2, max_value= 200)
    node_amount = serializers.IntegerField(default=60, min_value=3, max_value=1000)
    mean_edges = serializers.IntegerField(default=4, min_value=2, max_value=20)
    var_edges = serializers.FloatField(default=1.0, min_value=0, max_value=5)
    mean_aggressive = serializers.FloatField(default=0.0, min_value=-1, max_value=1)
    var_aggressive = serializers.FloatField(default=0.1, min_value=0, max_value=0.5)
    mean_laziness = serializers.FloatField(default=0.5, min_value=0, max_value=1)
    var_laziness = serializers.FloatField(default=0.05, min_value=0, max_value=0.25)

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

        return data


class SimulationCreateSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(
        required=True,
        help_text="Client-generated UUID used for idempotent simulation creation."
        )
    params = SimulationParamsSerializer()

    

class SimulationStatusSerializer(serializers.ModelSerializer):
    params = serializers.SerializerMethodField()
    class Meta:
        model = SimulationRun
        fields = ["id", "uuid", "status", "created_at", "started_at", "finished_at", "params", "user"]
    
    def get_params(self, obj):
        # Recursively convert any Decimal in JSON to float
        def convert(value):
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert(v) for v in value]
            elif isinstance(value, Decimal):
                return float(value)
            return value

        return convert(obj.params)


class SimulationErrorSerializer(serializers.ModelSerializer):
    error = serializers.CharField(source="error_message", read_only=True)

    class Meta:
        model = SimulationRun
        fields = ["id", "uuid", "status", "error"]


class SimulationResultSerializer(serializers.ModelSerializer):
    run_id = serializers.PrimaryKeyRelatedField(source="run", read_only=True)

    class Meta:
        model = SimulationResults
        fields = ["id", "run_id", "metrics"]
