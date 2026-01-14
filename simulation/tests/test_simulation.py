from dataclasses import asdict


def test_simulation_instantiation(sample_sim):
    kwargs= {
        "iterations": 30,
        "seed":1,
        "cat_amount":3,
        "node_amount":7,
        "mean_edges":3,
        "var_edges":1,
        "mean_aggressive": 0.0,
        "var_aggressive": 0.1,
        "mean_laziness": 0.5,
        "var_laziness":0.05
    }
    assert asdict(sample_sim.params) == kwargs
    assert sample_sim.cats == []
    assert sample_sim.nodes == []
    assert sample_sim.edges == []
    assert sample_sim.relationships == {}
    assert sample_sim.metrics == None

def test_simulation_method_generate_initial_state(sample_sim):
    sample_sim.generate_initial_state()

    assert len(sample_sim.cats) == 3
    assert len(sample_sim.nodes) == 7
    assert len(sample_sim.edges) == 9
    assert len(sample_sim.relationships) == 3

    assert sample_sim.cats[0].current_node == 4
    assert sample_sim.cats[1].current_node == 5
    assert sample_sim.cats[2].current_node == 0

    assert sample_sim.relationships[(0,1)].value == 0.0
    assert sample_sim.relationships[(0,2)].value == 0.0
    assert sample_sim.relationships[(1,2)].value == 0.0

def test_simulation_method_movement_step(sample_sim):
    sample_sim.generate_initial_state()
    sample_sim.movement_step()

    assert sample_sim.cats[0].current_node == 4
    assert sample_sim.cats[1].current_node == None
    assert sample_sim.cats[2].current_node == None

    assert sample_sim.cats[0].stats.iter_at_home == 1
    assert sample_sim.cats[1].stats.iter_at_home == 1
    assert sample_sim.cats[2].stats.iter_at_home == 1

    assert sample_sim.cats[0].stats.times_at_home == 0
    assert sample_sim.cats[1].stats.times_at_home == 1
    assert sample_sim.cats[2].stats.times_at_home == 1

    sample_sim.movement_step()
    sample_sim.movement_step()

    assert sample_sim.cats[0].current_node == 4
    assert sample_sim.cats[1].current_node == None
    assert sample_sim.cats[2].current_node == None

    assert sample_sim.cats[0].stats.iter_at_home == 3
    assert sample_sim.cats[1].stats.iter_at_home == 1
    assert sample_sim.cats[2].stats.iter_at_home == 1

    assert sample_sim.cats[0].stats.iter_at_neutral == 0
    assert sample_sim.cats[1].stats.iter_at_neutral == 1
    assert sample_sim.cats[2].stats.iter_at_neutral == 0

    assert sample_sim.cats[0].stats.iter_at_friendly == 0
    assert sample_sim.cats[1].stats.iter_at_friendly == 0
    assert sample_sim.cats[2].stats.iter_at_friendly == 1

    assert sample_sim.cats[0].stats.iter_on_edge == 0
    assert sample_sim.cats[1].stats.iter_on_edge == 1
    assert sample_sim.cats[2].stats.iter_on_edge == 1

    assert sample_sim.cats[0].stats.times_at_home == 0
    assert sample_sim.cats[1].stats.times_at_home == 1
    assert sample_sim.cats[2].stats.times_at_home == 1

def test_simulation_method_engagement_step(sample_sim):
    sample_sim.generate_initial_state()
    sample_sim.movement_step()
    sample_sim.engagement_step()


    assert sample_sim.cats[0].stats.fights == 0
    assert sample_sim.cats[1].stats.fights == 0
    assert sample_sim.cats[2].stats.fights == 0

    assert sample_sim.cats[0].stats.friendly_interaction == 0
    assert sample_sim.cats[1].stats.friendly_interaction == 0
    assert sample_sim.cats[2].stats.friendly_interaction == 0

    assert sample_sim.cats[0].stats.sleeps == 1
    assert sample_sim.cats[1].stats.sleeps == 0
    assert sample_sim.cats[2].stats.sleeps == 0

def test_simulation_method_run(sample_sim):
    sample_sim.generate_initial_state()
    sample_sim.run()

    assert sample_sim.cats[0].stats.fights == 0
    assert sample_sim.cats[1].stats.fights == 1
    assert sample_sim.cats[2].stats.fights == 1

    assert sample_sim.cats[0].stats.friendly_interaction == 1
    assert sample_sim.cats[1].stats.friendly_interaction == 1
    assert sample_sim.cats[2].stats.friendly_interaction == 0

    assert sample_sim.cats[0].stats.sleeps == 20
    assert sample_sim.cats[1].stats.sleeps == 15
    assert sample_sim.cats[2].stats.sleeps == 15

    assert sample_sim.cats[0].stats.iter_at_home == 10
    assert sample_sim.cats[1].stats.iter_at_home == 2
    assert sample_sim.cats[2].stats.iter_at_home == 5

    assert sample_sim.cats[0].stats.iter_at_neutral == 9
    assert sample_sim.cats[1].stats.iter_at_neutral == 10
    assert sample_sim.cats[2].stats.iter_at_neutral == 5

    assert sample_sim.cats[0].stats.iter_at_friendly == 1
    assert sample_sim.cats[1].stats.iter_at_friendly == 4
    assert sample_sim.cats[2].stats.iter_at_friendly == 5

    assert sample_sim.cats[0].stats.iter_on_edge == 10
    assert sample_sim.cats[1].stats.iter_on_edge == 14
    assert sample_sim.cats[2].stats.iter_on_edge == 15

    assert sample_sim.cats[0].stats.times_at_home == 4
    assert sample_sim.cats[1].stats.times_at_home == 2
    assert sample_sim.cats[2].stats.times_at_home == 5

    assert sample_sim.metrics.friendgroups_total == 0
    assert sample_sim.metrics.average_size_friendgroups == 0

    assert sample_sim.cats[0].metrics.average_iter_spent_at_friends_home == 1.0
    assert sample_sim.cats[1].metrics.average_iter_spent_at_friends_home == 1.0
    assert sample_sim.cats[2].metrics.average_iter_spent_at_friends_home == 1.0

    assert sample_sim.cats[0].metrics.average_iter_spent_at_home == 2.5
    assert sample_sim.cats[1].metrics.average_iter_spent_at_home == 1.0
    assert sample_sim.cats[2].metrics.average_iter_spent_at_home == 1.0

    assert sample_sim.cats[0].metrics.average_iter_spent_on_neutral_node == 1.8
    assert sample_sim.cats[1].metrics.average_iter_spent_on_neutral_node == 1.1111111111111112
    assert sample_sim.cats[2].metrics.average_iter_spent_on_neutral_node == 1.0

    assert sample_sim.cats[0].metrics.amount_of_cats_interacted_with == 1
    assert sample_sim.cats[0].metrics.amount_of_friends == 1
    assert sample_sim.cats[0].metrics.amount_of_enemies == 0
    
    assert sample_sim.relationships[(0,1)].value == -0.05
    assert sample_sim.relationships[(0,1)].metrics.stability == 0.9983333333333333