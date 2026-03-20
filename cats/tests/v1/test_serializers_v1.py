from cats.api.v1.serializers import SimulationCreateSerializerV1, SimulationErrorSerializerV1, SimulationResultSerializerV1, SimulationStatusSerializerV1
import pytest


def test_simulation_create_valid(valid_create_sim_args):
    serializer = SimulationCreateSerializerV1(data=valid_create_sim_args)
    assert serializer.is_valid(), serializer.errors

@pytest.mark.parametrize(
    "invalid_field, invalid_value",
    [
        ("iterations", 0),
        ("iterations", 10001),
        ("cat_amount", 1),
        ("cat_amount", 201),
        ("node_amount", 2),
        ("node_amount", 1001),
        ("mean_edges", 1),
        ("mean_edges", 21),
        ("var_edges", -0.1),
        ("var_edges", 5.1),
        ("mean_aggressive", -1.1),
        ("mean_aggressive", 1.1),
        ("var_aggressive", -0.1),
        ("var_aggressive", 0.6),
        ("mean_laziness", -0.1),
        ("mean_laziness", 1.1),
        ("var_laziness", -0.1),
        ("var_laziness", 0.26),
    ]
)
def test_simulation_create_invalid(valid_create_sim_args, invalid_field, invalid_value):
    args = valid_create_sim_args.copy()
    args["params"][invalid_field] = invalid_value
    serializer = SimulationCreateSerializerV1(data=args)
    assert not serializer.is_valid(), f"Serializer unexpectedly valid for field {invalid_field} with value {invalid_value}"
    assert invalid_field in serializer.errors.get("params"), f"Serializer is invalid, but not for field {invalid_field} with value {invalid_value}, which it should be invalid for"

def test_cat_amount_too_high_for_nodes(valid_create_sim_args):
    args = valid_create_sim_args.copy()
    args["params"]["cat_amount"] = 3
    args["params"]["node_amount"] = 9
    serializer = SimulationCreateSerializerV1(data=args)

    assert not serializer.is_valid(), "Serializer unexpectedly valid for 'cat_amount':3 and 'node_amount':9"
    assert "Nodes must be at least thrice the amount of cats" in [str(msg) for msgs in serializer.errors.get("params").values() for msg in msgs]

def test_mean_edges_too_high_for_nodes(valid_create_sim_args):
    args = valid_create_sim_args.copy()
    args["params"]["mean_edges"] = 20
    args["params"]["node_amount"] = 40
    serializer = SimulationCreateSerializerV1(data=args)

    assert not serializer.is_valid(), "Serializer unexpectedly valid for 'mean_edges':50 and 'node_amount':100"
    assert "The mean of edges cant be more than half the amount of nodes" in [str(msg) for msgs in serializer.errors.get("params").values() for msg in msgs]

def test_var_edges_too_high_for_mean_edges(valid_create_sim_args):
    args = valid_create_sim_args.copy()
    args["params"]["var_edges"] = 3
    args["params"]["mean_edges"] = 9
    serializer = SimulationCreateSerializerV1(data=args)

    assert not serializer.is_valid(), "Serializer unexpectedly valid for 'var_edges':3 and 'mean_edges':9"
    assert "The variance of edges cant be more than a third of the mean" in [str(msg) for msgs in serializer.errors.get("params").values() for msg in msgs]

@pytest.mark.django_db
def test_simulation_status(create_simulation):
    sim = create_simulation()
    serializer = SimulationStatusSerializerV1(sim)

    assert serializer.data["id"] == sim.id, "Serializer id unexpectedly does not equal simulation id"
    assert serializer.data["status"] == sim.status, "Serializer status unexpectedly does not equal simulation status"
    assert serializer.data["user"] == sim.user.id, "Serializer user unexpectedly does not equal simulation user"
    assert serializer.data["params"] == sim.params, "Serializer params unexpectedly does not equal simulation params"
    assert all(f in serializer.data for f in ["created_at", "finished_at", "started_at", "stopped_at"])

@pytest.mark.django_db
def test_simulation_error(create_simulation):
    sim = create_simulation()
    sim.mark_running()
    sim.mark_failed("Failed for Test")
    serializer = SimulationErrorSerializerV1(sim)

    assert serializer.data["id"] == sim.id, "Serializer id unexpectedly does not equal simulation id"
    assert serializer.data["status"] == sim.status, "Serializer status unexpectedly does not equal simulation status"
    assert serializer.data["error"] ==sim.error_message, "Serializer error unexpectedly does not equal simulation error_messages"

@pytest.mark.django_db
def test_simulation_result(create_results):
    res = create_results()
    serializer = SimulationResultSerializerV1(res)

    assert serializer.data["id"] == res.id, "Serializer id unexpectedly does not equal result id"
    assert serializer.data["run_id"] == res.run.id, "Serializer run_id unexpectedly does not equal result.run.id"
    assert serializer.data["metrics"] == res.metrics, "Serializer metrics unexpectedly does not equal result metrics"



