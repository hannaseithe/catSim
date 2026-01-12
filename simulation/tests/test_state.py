import pytest
from simulation.state import Cat

def test_cat(sample_cat:Cat):
    assert sample_cat.traits.home == 0
    assert sample_cat.traits.name == "Thima"
    assert sample_cat.traits.aggressive == -0.5
    assert sample_cat.traits.lazy == 0.3
    assert sample_cat.traits.id ==0

    assert sample_cat.current_node == 0
    assert sample_cat.needs_to_run == False
    assert sample_cat.target_node == None

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

    assert sample_cat.metrics == None