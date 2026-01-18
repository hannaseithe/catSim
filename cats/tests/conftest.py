import pytest
from cats.models import SimulationResults, SimulationRun
from rest_framework.test import APIClient

DUMMY_METRICS = {"foo": "bar"}

@pytest.fixture
def create_simulation():
    def _create_simulation(params={"iterations": 10}):
        return SimulationRun.objects.create(params = params)
    return _create_simulation

@pytest.fixture
def create_results(create_simulation):
    run = create_simulation()
    def _create_results(run = run, metrics = DUMMY_METRICS):
        return SimulationResults.objects.create(run = run, metrics = metrics)
    return _create_results

@pytest.fixture
def api_client():
    return APIClient()