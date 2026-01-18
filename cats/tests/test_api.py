from unittest.mock import patch
from django.urls import reverse
import pytest

from cats.api.serializers import (
    SimulationErrorSerializer,
    SimulationResultSerializer,
    SimulationStatusSerializer,
)
from cats.api.views import NOT_COMPLETED_RESPONSE, NOT_FAILED_RESPONSE
from cats.models import SimulationRun


@pytest.mark.django_db
def test_simulation_list(api_client, create_simulation):
    sim1 = create_simulation()
    sim2 = create_simulation(params={"iterations": 5})
    url = reverse("simulation-list")
    response = api_client.get(url)
    sim1_data = SimulationStatusSerializer(sim1).data
    sim2_data = SimulationStatusSerializer(sim2).data

    assert response.status_code == 200
    sims = response.data
    assert isinstance(sims, list)
    assert len(sims) == 2
    assert sims[0] == sim1_data
    assert sims[1] == sim2_data


@pytest.mark.django_db
def test_simulation_get_detail(api_client, create_simulation):
    sim = create_simulation()
    sim_data = SimulationStatusSerializer(sim).data
    url = reverse("simulation-get-detail", args=[sim.id])
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data


@pytest.mark.django_db
def test_simulation_get_error(api_client, create_simulation):
    sim = create_simulation()
    sim.mark_running()
    sim.mark_failed("This is an error message")
    sim_data = SimulationErrorSerializer(sim).data
    url = reverse("simulation-get-error", args=[sim.id])
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data


@pytest.mark.django_db
def test_simulation_get_error_if_not_failed(api_client, create_simulation):
    sim = create_simulation()
    sim.mark_running()
    sim.mark_completed()
    url = reverse("simulation-get-error", args=[sim.id])
    response = api_client.get(url)

    assert response.status_code == 409
    data = response.data
    assert isinstance(data, dict)
    assert data == NOT_FAILED_RESPONSE


@pytest.mark.django_db
def test_simulation_get_results(api_client, create_results):
    results = create_results()
    sim = results.run
    sim.mark_running()
    sim.mark_completed()
    results_data = SimulationResultSerializer(results).data
    url = reverse("simulation-get-results", args=[sim.id])
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == results_data


@pytest.mark.django_db
def test_simulation_get_results_if_not_finished(api_client, create_results):
    results = create_results()
    sim = results.run
    sim.mark_running()
    url = reverse("simulation-get-results", args=[sim.id])
    response = api_client.get(url)

    assert response.status_code == 409
    data = response.data
    assert isinstance(data, dict)
    assert data == NOT_COMPLETED_RESPONSE

@pytest.mark.django_db
@patch("cats.management.commands.run_simulation.run_simulation.delay")
def test_simulation_start(mock_delay,api_client):
    url = reverse("simulation-start")
    response = api_client.post(url)

    assert response.status_code == 201

    data = response.data

    run = SimulationRun.objects.get(id = data["id"])
    assert run.status == data["status"]

    mock_delay.assert_called_once_with(run.id)