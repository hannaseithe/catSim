from dataclasses import asdict
import dataclasses
import pytest
from simulation.state import Cat, CatMetrics, Relationship, RelationshipMetrics


def test_cat_instantiation(sample_cat: Cat):
    assert sample_cat.traits.home == 0
    assert sample_cat.traits.name == "Thima"
    assert sample_cat.traits.aggressive == -0.5
    assert sample_cat.traits.lazy == 0.3
    assert sample_cat.traits.id == 0

    assert sample_cat.current_node == 0
    assert not sample_cat.needs_to_run
    assert sample_cat.target_node is None

    assert sample_cat.stats.iter_at_home == 0
    assert sample_cat.stats.iter_on_edge == 0
    assert sample_cat.stats.iter_at_friendly == 0
    assert sample_cat.stats.iter_at_neutral == 0
    assert sample_cat.stats.fights == 0
    assert sample_cat.stats.friendly_interaction == 0
    assert sample_cat.stats.sleeps == 0
    assert sample_cat.stats.times_at_home == 0
    assert sample_cat.stats.times_at_friendly == 0
    assert sample_cat.stats.times_at_neutral == 0
    assert sample_cat.stats.interacted_with == set()
    assert sample_cat.stats.nodes_visited == set([sample_cat.traits.home])

    assert sample_cat.metrics is None

    assert str(sample_cat) == "Thima (n: #0)"
    assert repr(sample_cat) == "Thima at node #0"

    assert sample_cat.is_at_home()


def test_cat_traits_are_frozen(sample_cat):
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_cat.traits.aggressive = -0.2


def test_cat_leave(sample_cat: Cat):
    sample_cat.leave(1)
    assert sample_cat.is_on_the_edge()
    assert str(sample_cat) == "Thima -> n #1"
    assert repr(sample_cat) == "Thima moving to node #1"


def test_cat_arrive(sample_cat: Cat):
    sample_cat.leave(1)
    sample_cat.arrive()

    assert sample_cat.current_node == 1
    assert not sample_cat.is_on_the_edge()
    assert sample_cat.stats.nodes_visited == set(
        [sample_cat.current_node, sample_cat.traits.home]
    )


def test_cat_cant_leave_for_where_she_is_at(sample_cat: Cat):
    with pytest.raises(ValueError):
        sample_cat.leave(0)


def test_relationship_instantiation(sample_rel: Relationship):
    assert sample_rel.value == 0
    assert sample_rel.traits.cat1 == 0
    assert sample_rel.traits.cat2 == 1
    assert sample_rel.stats.absolute_delta == 0.0
    assert sample_rel.metrics is None

    assert str(sample_rel) == "Relationship: Cat 0 - Cat 1"
    assert repr(sample_rel) == "Relationship between Cat 0 and Cat 1 - value: 0"


def test_relationship_traits_are_frozen(sample_rel):
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_rel.traits.cat1 = 2


def test_cat_metrics_instantiation():
    kwargs = {
        "percent_time_spent_home": 0.0,
        "percent_time_spent_on_edge": 0.0,
        "percent_time_spent_on_neutral_ground": 0.2,
        "percent_time_spent_at_friends_house": 0.35,
        "average_iter_spent_at_home": 3.2,
        "average_iter_spent_at_friends_home": 4.3,
        "average_iter_spent_on_neutral_node": 2,
        "percent_of_cats_interacted_with": 0.33,
        "percent_of_friends": 0.5,
        "percent_of_enemies": 0.2,
        "percent_of_aquaintances": 0.3,
        "percent_time_spent_fighting": 0.05,
        "percent_time_spent_friendly_interaction": 0.13,
        "percent_time_spent_sleeping": 0.33,
        "amount_friendgroups": 4,
        "average_size_friendgroup": 2.1,
        "exploration_index": 0.4,
        "relationship_entropy": 0.8,
    }
    metrics = CatMetrics(**kwargs)
    assert asdict(metrics) == kwargs


def test_relationship_method_other_cat(sample_rel: Relationship):
    assert sample_rel.other_cat(0) == 1
    assert sample_rel.other_cat(1) == 0


def test_relationship_method_is_relationship(sample_rel: Relationship):
    assert sample_rel.is_relationship(0, 1)
    assert sample_rel.is_relationship(1, 0)
    assert not sample_rel.is_relationship(1, 1)
    assert not sample_rel.is_relationship(2, 1)


def test_relationship_metrics_instantiation():
    kwargs = {
        "stability": 0.9,
        "volatility": 0.5,
        "min_value": 0.0,
        "max_value": 0.5,
        "number_of_sign_flips": 2,
    }
    metrics = RelationshipMetrics(**kwargs)
    assert asdict(metrics) == kwargs


def test_node_instantiation(sample_node):
    assert sample_node.id == 1
    assert sample_node.number_of_edges == 3


def test_node_is_frozen(sample_node):
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_node.id = 2


def test_edge_instantiation(sample_edge):
    assert sample_edge.node1 == 0
    assert sample_edge.node2 == 1


def test_edge_is_frozen(sample_edge):
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_edge.node1 = 2


def test_edge_method_node_in_edge(sample_edge):
    assert sample_edge.node_in_edge(0)
    assert sample_edge.node_in_edge(1)
    assert not sample_edge.node_in_edge(2)


def test_edge_method_other_node(sample_edge):
    assert sample_edge.other_node(0) == 1
    assert sample_edge.other_node(1) == 0
