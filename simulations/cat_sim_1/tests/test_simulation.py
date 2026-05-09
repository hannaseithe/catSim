from dataclasses import asdict
import json

from simulations.cat_sim_1.simulation import SimulationState


def test_simulation_instantiation(sample_sim):
    kwargs = {
        "iterations": 30,
        "seed": 1,
        "cat_amount": 3,
        "node_amount": 7,
        "mean_edges": 3,
        "var_edges": 1,
        "mean_aggressive": 0.0,
        "var_aggressive": 0.1,
        "mean_laziness": 0.5,
        "var_laziness": 0.05,
    }
    assert asdict(sample_sim.params) == kwargs
    assert sample_sim.state.cats == []
    assert sample_sim.state.nodes == []
    assert sample_sim.state.edges == []
    assert sample_sim.state.relationships == {}
    assert sample_sim.metrics is None


def test_simulation_method_generate_initial_state(sample_sim):
    sample_sim.generate_initial_state()

    assert len(sample_sim.state.cats) == 3
    assert len(sample_sim.state.nodes) == 7
    assert len(sample_sim.state.edges) == 10
    assert len(sample_sim.state.relationships) == 3

    assert sample_sim.state.cats[0].current_node == 3
    assert sample_sim.state.cats[1].current_node == 5
    assert sample_sim.state.cats[2].current_node == 3

    assert sample_sim.state.relationships[(0, 1)].value == 0.0
    assert sample_sim.state.relationships[(0, 2)].value == 0.0
    assert sample_sim.state.relationships[(1, 2)].value == 0.0


def test_simulation_method_movement_step(sample_sim):
    sample_sim.generate_initial_state()
    sample_sim.movement_step()

    assert sample_sim.state.cats[0].current_node is None
    assert sample_sim.state.cats[1].current_node is None
    assert sample_sim.state.cats[2].current_node == 3

    assert sample_sim.state.cats[0].stats.iter_at_home == 1
    assert sample_sim.state.cats[1].stats.iter_at_home == 1
    assert sample_sim.state.cats[2].stats.iter_at_home == 1

    assert sample_sim.state.cats[0].stats.times_at_home == 1
    assert sample_sim.state.cats[1].stats.times_at_home == 1
    assert sample_sim.state.cats[2].stats.times_at_home == 0

    sample_sim.movement_step()
    sample_sim.movement_step()

    assert sample_sim.state.cats[0].current_node is None
    assert sample_sim.state.cats[1].current_node is None
    assert sample_sim.state.cats[2].current_node is None

    assert sample_sim.state.cats[0].stats.iter_at_home == 1
    assert sample_sim.state.cats[1].stats.iter_at_home == 1
    assert sample_sim.state.cats[2].stats.iter_at_home == 3

    assert sample_sim.state.cats[0].stats.iter_at_neutral == 1
    assert sample_sim.state.cats[1].stats.iter_at_neutral == 1
    assert sample_sim.state.cats[2].stats.iter_at_neutral == 0

    assert sample_sim.state.cats[0].stats.iter_at_friendly == 0
    assert sample_sim.state.cats[1].stats.iter_at_friendly == 0
    assert sample_sim.state.cats[2].stats.iter_at_friendly == 0

    assert sample_sim.state.cats[0].stats.iter_on_edge == 1
    assert sample_sim.state.cats[1].stats.iter_on_edge == 1
    assert sample_sim.state.cats[2].stats.iter_on_edge == 0

    assert sample_sim.state.cats[0].stats.times_at_home == 1
    assert sample_sim.state.cats[1].stats.times_at_home == 1
    assert sample_sim.state.cats[2].stats.times_at_home == 1


def test_simulation_method_engagement_step(sample_sim):
    sample_sim.generate_initial_state()
    sample_sim.movement_step()
    sample_sim.engagement_step()

    assert sample_sim.state.cats[0].stats.fights == 0
    assert sample_sim.state.cats[1].stats.fights == 0
    assert sample_sim.state.cats[2].stats.fights == 0

    assert sample_sim.state.cats[0].stats.friendly_interaction == 0
    assert sample_sim.state.cats[1].stats.friendly_interaction == 0
    assert sample_sim.state.cats[2].stats.friendly_interaction == 0

    assert sample_sim.state.cats[0].stats.sleeps == 0
    assert sample_sim.state.cats[1].stats.sleeps == 0
    assert sample_sim.state.cats[2].stats.sleeps == 1


def test_simulation_method_run(sample_sim):
    sample_sim.generate_initial_state()
    for _ in sample_sim.run():
        pass

    assert sample_sim.metrics.friendgroups_total == 0
    assert sample_sim.metrics.average_size_friendgroups == 0
    assert sample_sim.metrics.interaction_density == 0.06666666666666667
    assert sample_sim.metrics.isolated_cats_count == 0
    assert sample_sim.metrics.largest_group_size == 0
    assert sample_sim.metrics.mean_relationship_value == -0.05

    assert sample_sim.state.cats[0].stats.fights == 0
    assert sample_sim.state.cats[0].stats.friendly_interaction == 1
    assert sample_sim.state.cats[0].stats.sleeps == 14
    assert sample_sim.state.cats[0].stats.iter_at_home == 1
    assert sample_sim.state.cats[0].stats.iter_at_neutral == 12
    assert sample_sim.state.cats[0].stats.iter_at_friendly == 2
    assert sample_sim.state.cats[0].stats.iter_on_edge == 15
    assert sample_sim.state.cats[0].stats.times_at_home == 1

    assert sample_sim.state.cats[0].metrics.average_iter_spent_at_friends_home == 1.0
    assert sample_sim.state.cats[0].metrics.average_iter_spent_at_home == 1.0
    assert sample_sim.state.cats[0].metrics.average_iter_spent_on_neutral_node == 1.0
    assert sample_sim.state.cats[0].metrics.percent_of_cats_interacted_with == 0.5
    assert sample_sim.state.cats[0].metrics.percent_of_friends == 1
    assert sample_sim.state.cats[0].metrics.percent_of_enemies == 0
    assert sample_sim.state.cats[0].metrics.percent_of_aquaintances == 0
    assert sample_sim.state.cats[0].metrics.amount_friendgroups == 0
    assert sample_sim.state.cats[0].metrics.average_size_friendgroup == 0
    assert sample_sim.state.cats[0].metrics.exploration_index == 0.8571428571428571
    assert sample_sim.state.cats[0].metrics.relationship_entropy == 0
    assert (
        sample_sim.state.cats[0].metrics.percent_time_spent_at_friends_house
        == 0.06666666666666667
    )
    assert sample_sim.state.cats[0].metrics.percent_time_spent_fighting == 0
    assert (
        sample_sim.state.cats[0].metrics.percent_time_spent_friendly_interaction
        == 0.03333333333333333
    )
    assert sample_sim.state.cats[0].metrics.percent_time_spent_home == 0.03333333333333333
    assert sample_sim.state.cats[0].metrics.percent_time_spent_on_edge == 0.5
    assert sample_sim.state.cats[0].metrics.percent_time_spent_on_neutral_ground == 0.4
    assert sample_sim.state.cats[0].metrics.percent_time_spent_sleeping == 0.4666666666666667

    assert sample_sim.state.relationships[(0, 1)].value == -0.05
    assert sample_sim.state.relationships[(0, 1)].metrics.stability == 0.9523809523809523
    assert sample_sim.state.relationships[(0, 1)].metrics.volatility == 0.0016666666666666668
    assert sample_sim.state.relationships[(0, 1)].metrics.max_value == 0
    assert sample_sim.state.relationships[(0, 1)].metrics.min_value == -0.05
    assert sample_sim.state.relationships[(0, 1)].metrics.number_of_sign_flips == 1

def test_serialize_deserialize_state(sample_sim):
    sample_sim.generate_initial_state()
    for sim in sample_sim.run():
        if sim.state.run.tick > 5:
            break
    serialized_state = sim.serialize_state()
    de_serialized_state = SimulationState.from_dict(json.loads(serialized_state))

    assert asdict(sim.state) == asdict(de_serialized_state)

def test_weights_above_zero_bug(sample_aggressive_sim):
    sample_aggressive_sim.generate_initial_state()
    for _ in sample_aggressive_sim.run():
        pass