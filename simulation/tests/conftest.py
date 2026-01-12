import pytest
from simulation.state import Cat, CatTraits

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
