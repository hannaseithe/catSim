from rest_framework import serializers

from cats.models import SimulationResults, SimulationRun


class SimulationCreateSerializer(serializers.Serializer):
    iterations = serializers.IntegerField(default=1000)
    cat_amount = serializers.IntegerField(default=10)
    node_amount = serializers.IntegerField(default=60)
    mean_edges = serializers.IntegerField(default=4)
    var_edges = serializers.FloatField(default=1.0)
    mean_aggressive = serializers.FloatField(default=0.0)
    var_aggressive = serializers.FloatField(default=0.1)
    mean_laziness = serializers.FloatField(default=0.5)
    var_laziness = serializers.FloatField(default=0.05)

    def validate_iterations(self, value):
        if not 1 <= value <= 10000:
            raise serializers.ValidationError("Must be between 1 and 10000")

        return value

    def validate_cat_amount(self, value):
        if not 2 <= value <= 200:
            raise serializers.ValidationError("Must be between 2 and 200")

        return value

    def validate_node_amount(self, value):
        if not 3 <= value <= 1000:
            raise serializers.ValidationError("Must be between 3 and 1000")

        return value

    def validate_mean_edges(self, value):
        if not 2 <= value <= 20:
            raise serializers.ValidationError("Must be between 2 and 20")

        return value

    def validate_var_edges(self, value):
        if not 0 <= value <= 5:
            raise serializers.ValidationError("Must be between 0 and 5")

        return value

    def validate_mean_aggressive(self, value):
        if not -1 <= value <= 1:
            raise serializers.ValidationError("Must be between -1 and 1")

        return value

    def validate_var_aggressive(self, value):
        if not 0 <= value <= 0.5:
            raise serializers.ValidationError("Must be between 0 and 0.5")

        return value

    def validate_mean_laziness(self, value):
        if not 0 <= value <= 1:
            raise serializers.ValidationError("Must be between 0 and 1")

        return value

    def validate_var_laziness(self, value):
        if not 0 <= value <= 0.25:
            raise serializers.ValidationError("Must be between 0 and 0.25")

        return value

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
                "The variance of edges can be more than a third of the mean"
            )

        return data


class SimulationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationRun
        fields = ["id", "status", "created_at", "started_at", "finished_at", "params", "user"]


class SimulationErrorSerializer(serializers.ModelSerializer):
    error = serializers.CharField(source="error_message", read_only=True)

    class Meta:
        model = SimulationRun
        fields = ["id", "status", "error"]


class SimulationResultSerializer(serializers.ModelSerializer):
    run_id = serializers.PrimaryKeyRelatedField(source="run", read_only=True)

    class Meta:
        model = SimulationResults
        fields = ["id", "run_id", "metrics"]
