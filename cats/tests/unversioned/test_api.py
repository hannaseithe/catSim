from unittest.mock import patch
from django.urls import reverse
import pytest

from cats.api.unversioned.serializers import (
    SimulationErrorSerializer,
    SimulationResultSerializer,
    SimulationStatusSerializer,
)
from cats.api.unversioned.views import NOT_COMPLETED_RESPONSE, NOT_FAILED_RESPONSE
from cats.events import Source
from cats.models import SimulationRun

def test_login_works(create_user, api_client):
    password="CoolPassword"
    user = create_user(password=password)
    url = reverse('token-obtain-pair')
    response = api_client.post(url,{"email": user.email, "password":password}, format="json")
    
    assert response.status_code == 200
    assert "access" in response.data.keys()
    assert "refresh" in response.data.keys()

def test_refresh_works(api_client, create_user, auth_client_with_refresh_unversioned):
    password="test1password"
    user = create_user(email="test1@email.com",password=password)
    _,refresh_token = auth_client_with_refresh_unversioned(user=user, password=password)
    url = reverse('token-refresh')
    response = api_client.post(url, data={"refresh": refresh_token}, format="json")
    
    assert response.status_code == 200
    assert "access" in response.data.keys()

def test_simulation_list(create_simulation, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")
    sim1 = create_simulation(user = user)
    sim2 = create_simulation(params={"iterations": 5}, user = user)

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-list")
    response = auth_client.get(url)
    sim1_data = SimulationStatusSerializer(sim1).data
    sim2_data = SimulationStatusSerializer(sim2).data

    assert response.status_code == 200
    sims = response.data.get("results")
    assert isinstance(sims, list)
    assert len(sims) == 2
    assert sims[1].get("id") == sim1_data.get("id")
    assert sims[0].get("id") == sim2_data.get("id")

def test_simulation_get_detail(api_client, create_simulation, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user=user)
    sim_data = SimulationStatusSerializer(sim).data

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-get-detail-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data


@pytest.mark.django_db
def test_simulation_get_error(create_simulation, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user = user)
    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    sim.mark_failed(error_message="This is an error message", source=Source.WORKER, tick=0)
    sim_data = SimulationErrorSerializer(sim).data

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-get-error-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data


@pytest.mark.django_db
def test_simulation_get_error_if_not_failed(create_simulation, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user = user)
    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    sim.mark_completed(source=Source.WORKER, tick=0)

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-get-error-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 409
    data = response.data
    assert isinstance(data, dict)
    assert data == NOT_FAILED_RESPONSE


@pytest.mark.django_db
def test_simulation_get_results(create_results, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")
    results = create_results(user=user)
    sim = results.run
    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    sim.mark_completed(source=Source.WORKER, tick=0)
    results_data = SimulationResultSerializer(results).data

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-get-results-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == results_data


@pytest.mark.django_db
def test_simulation_get_results_if_not_finished(create_results, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")
    results = create_results(user=user)
    sim = results.run
    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-get-results-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 409
    data = response.data
    assert isinstance(data, dict)
    assert data == NOT_COMPLETED_RESPONSE

@pytest.mark.django_db
@patch("cats.management.commands.run_simulation.run_simulation.delay")
def test_simulation_start(mock_delay, create_user, auth_client_with_refresh_unversioned):
    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_unversioned(user=user, password="test1password")
    url = reverse("simulation-start")
    response = auth_client.post(url)

    assert response.status_code == 201

    data = response.data

    run = SimulationRun.objects.get(id = data["id"])
    assert run.status == data["status"]

    mock_delay.assert_called_once_with(run.id)

