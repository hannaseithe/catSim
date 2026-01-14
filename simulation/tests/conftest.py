import pytest
from simulation.simulation import Simulation, SimulationParameters
from simulation.state import Cat, CatTraits, Edge, Node, Relationship, RelationshipTraits

@pytest.fixture
def sample_cat():
    return Cat(CatTraits(id=0, name="Thima", home=0, aggressive=-0.5, lazy=0.3))


@pytest.fixture
def sample_cats():
    return [
        Cat(CatTraits(id=1, name="Tom", home=1, aggressive=0.5, lazy=0.3)),
        Cat(CatTraits(id=2, name="Mittens", home=2, aggressive=-0.2, lazy=0.5)),
        Cat(CatTraits(id=3, name="Whiskers", home=3, aggressive=0.0, lazy=0.7)),
    ]

@pytest.fixture
def sample_rel():
    return Relationship(RelationshipTraits(0,1))

@pytest.fixture
def sample_node():
    return Node(id=1,number_of_edges=3)

@pytest.fixture
def sample_edge():
    return Edge(0,1)

@pytest.fixture
def sample_sim():
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
    params=SimulationParameters(**kwargs)
    return Simulation(params=params)

