from simulation.metrics import extract_metrics


def test_extract_metrics(sample_sim):
    sample_sim.generate_initial_state()
    sample_sim.run()
    metrics = extract_metrics(sample_sim)

    keys = metrics.keys()
    assert "simulation" in keys
    assert "relationships" in keys
    assert "cats" in keys

    simulation_keys = metrics["simulation"].keys()

    assert "friendgroups_total" in simulation_keys
    assert "average_size_friendgroups" in simulation_keys

    assert len(metrics["relationships"]) == 3
    assert len(metrics["cats"]) == 3
