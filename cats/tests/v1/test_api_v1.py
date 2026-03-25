import json
import uuid
from unittest.mock import MagicMock, patch
from django.urls import reverse
import pytest

from cats.api.v1.serializers import (
    SimulationErrorSerializerV1,
    SimulationResultSerializerV1,
    SimulationStatusSerializerV1,
)
from cats.api.v1.views import NOT_COMPLETED_RESPONSE, NOT_FAILED_RESPONSE
from cats.models import SimulationRun

def test_login_works(create_user, api_client):
    password="CoolPassword"
    user = create_user(password=password)
    url = reverse('v1-token-obtain-pair')
    response = api_client.post(url,{"email": user.email, "password":password}, format="json")
    
    assert response.status_code == 200
    assert "access" in response.data.keys()
    assert "refresh" in response.data.keys()

def test_refresh_works(api_client, create_user, auth_client_with_refresh_v1):
    password="test1password"
    user = create_user(email="test1@email.com",password=password)
    _,refresh_token = auth_client_with_refresh_v1(user=user, password=password)
    url = reverse('v1-token-refresh')
    response = api_client.post(url, data={"refresh": refresh_token}, format="json")
    
    assert response.status_code == 200
    assert "access" in response.data.keys()

def test_simulation_list(create_simulation, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    sim1 = create_simulation(user = user)
    sim2 = create_simulation(params={"iterations": 5}, user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response = auth_client.get(url)
    sim1_data = SimulationStatusSerializerV1(sim1).data
    sim2_data = SimulationStatusSerializerV1(sim2).data

    assert response.status_code == 200
    sims = response.data.get("results")
    assert isinstance(sims, list)
    assert len(sims) == 2
    assert sims[1].get("id") == sim1_data.get("id")
    assert sims[0].get("id") == sim2_data.get("id")

def test_simulation_get_detail(api_client, create_simulation, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user=user)
    sim_data = SimulationStatusSerializerV1(sim).data

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-get-detail-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data


@pytest.mark.django_db
def test_simulation_get_error(create_simulation, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user = user)
    sim.mark_run_queued()
    sim.mark_running()
    sim.mark_failed("This is an error message")
    sim_data = SimulationErrorSerializerV1(sim).data

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-get-error-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data

@pytest.mark.django_db
def test_simulation_get_error_with_uuid(create_simulation, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user = user)
    sim.mark_run_queued()
    sim.mark_running()
    sim.mark_failed("This is an error message")
    sim_data = SimulationErrorSerializerV1(sim).data

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-get-error-uuid", args=[sim.uuid])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == sim_data

@pytest.mark.django_db
def test_simulation_get_error_if_not_failed(create_simulation, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    sim = create_simulation(user = user)
    sim.mark_run_queued()
    sim.mark_running()
    sim.mark_completed()

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-get-error-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 409
    data = response.data
    assert isinstance(data, dict)
    assert data == NOT_FAILED_RESPONSE


@pytest.mark.django_db
def test_simulation_get_results(create_results, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    results = create_results(user=user)
    sim = results.run
    sim.mark_run_queued()
    sim.mark_running()
    sim.mark_completed()
    results_data = SimulationResultSerializerV1(results).data

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-get-results-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.data
    assert isinstance(data, dict)
    assert data == results_data


@pytest.mark.django_db
def test_simulation_get_results_if_not_finished(create_results, create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")
    results = create_results(user=user)
    sim = results.run
    sim.mark_run_queued()
    sim.mark_running()

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-get-results-id", args=[sim.id])
    response = auth_client.get(url)

    assert response.status_code == 409
    data = response.data
    assert isinstance(data, dict)
    assert data == NOT_COMPLETED_RESPONSE

@pytest.mark.django_db
@patch("cats.api.v1.views.run_simulation.delay")
def test_simulation_start(mock_delay, create_user, auth_client_with_refresh_v1):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_delay.return_value = mock_task

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-start")
    uuid_val = str(uuid.uuid4())
    response = auth_client.post(
        url,
        data={"uuid": uuid_val, "params": {}},
        format="json"
    )

    assert response.status_code == 201

    data = response.data

    run = SimulationRun.objects.get(id = data["id"])
    assert run.status == data["status"]
    assert str(run.uuid) == uuid_val

    mock_delay.assert_called_once_with(run.id)

@pytest.mark.django_db
@patch("cats.api.v1.views.run_simulation.delay")
def test_simulation_start_idempotency(mock_delay, create_user, auth_client_with_refresh_v1):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_delay.return_value = mock_task

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-start")
    uuid_val = str(uuid.uuid4())
    response1 = auth_client.post(
        url,
        data={"uuid": uuid_val, "params": {}},
        format="json"
    )

    assert response1.status_code == 201

    data1 = response1.data

    response2 = auth_client.post(
        url,
        data={"uuid": uuid_val, "params": {}},
        format="json"
    )

    data2 = response2.data

    assert response2.status_code == 200
    assert data1["id"] == data2["id"]

    mock_delay.assert_called_once_with(data1["id"])

@pytest.mark.django_db
@patch("cats.models.AsyncResult")
def test_simulation_cancel(mock_async_result, create_user, auth_client_with_refresh_v1):

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.RUNNING,
        celery_task_id="fake-task-id-123",
        params=json.dumps({})
    )

    mock_task_instance = MagicMock()
    mock_async_result.return_value = mock_task_instance
    mock_task_instance.revoke.return_value = None 

    url_cancel = reverse("v1-simulation-cancel-id", args=[run.id])
    response_cancel = auth_client.post(
        url_cancel
    )

    assert response_cancel.status_code == 200
    assert response_cancel.data["id"] == run.id
    assert response_cancel.data["detail"] == "The SimulationRun has been canceled."

    run.refresh_from_db()

    assert run.status == SimulationRun.Status.CANCELED

    mock_async_result.assert_called_once_with("fake-task-id-123")
    mock_task_instance.revoke.assert_called_once_with(terminate=True)

@pytest.mark.django_db
@patch("cats.models.AsyncResult")
def test_simulation_cancel_finished(mock_async_result, create_user, auth_client_with_refresh_v1):

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.RUNNING,
        celery_task_id="fake-task-id-123",
        params=json.dumps({})
    )
    run.mark_completed()

    url_cancel = reverse("v1-simulation-cancel-id", args=[run.id])
    response_cancel = auth_client.post(
        url_cancel
    )

    assert response_cancel.status_code == 409
    assert response_cancel.data["id"] == run.id
    assert response_cancel.data["detail"] == "The SimulationRun is not pending nor running, and can therefore not be canceled."

    run.refresh_from_db()

    assert run.status == SimulationRun.Status.FINISHED

    assert not mock_async_result.called

@pytest.mark.django_db
def test_simulation_delete(create_user, auth_client_with_refresh_v1):

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.FINISHED,
        params=json.dumps({})
    )

    url = reverse("v1-simulation-delete-id", args=[run.id])
    response = auth_client.delete(
        url
    )

    assert response.status_code == 200
    assert response.data["id"] == run.id
    assert response.data["detail"] == "The SimulationRun has been deleted."

    assert not SimulationRun.objects.filter(id=run.id).exists()

@pytest.mark.django_db
def test_simulation_pause(create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.RUNNING,
        params=json.dumps({})
    )

    url = reverse("v1-simulation-pause-id", args=[run.id])
    response = auth_client.post(
        url
    )

    assert response.status_code == 200
    assert response.data["id"] == run.id
    assert response.data["detail"] == "The SimulationRun has been queued to be paused."

    run.refresh_from_db()

    assert run.pause_requested

@pytest.mark.django_db
def test_simulation_pause_fail(create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.FINISHED,
        params=json.dumps({})
    )

    url = reverse("v1-simulation-pause-id", args=[run.id])
    response = auth_client.post(
        url
    )

    assert response.status_code == 409
    assert response.data["id"] == run.id
    assert response.data["detail"] == "The SimulationRun is not running, and can therefore not be paused."

    run.refresh_from_db()

    assert not run.pause_requested


@pytest.mark.django_db
@patch("cats.api.v1.views.run_simulation.delay")
def test_simulation_resume(mock_delay,create_user, auth_client_with_refresh_v1):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_delay.return_value = mock_task

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.PAUSED,
        params=json.dumps({}),
        checkpoint_state=json.dumps({}),
    )

    url = reverse("v1-simulation-resume-id", args=[run.id])
    response = auth_client.post(
        url
    )

    assert response.status_code == 200
    assert response.data["id"] == run.id
    assert response.data["detail"] == "The SimulationRun has been queued to be resumed."

    mock_delay.assert_called_once_with(run.id)

@pytest.mark.django_db
def test_simulation_resume_fail_wrong_state(create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.RUNNING,
        params=json.dumps({}),
        checkpoint_state=json.dumps({})
    )

    url = reverse("v1-simulation-resume-id", args=[run.id])
    response = auth_client.post(
        url
    )

    assert response.status_code == 409
    assert response.data["id"] == run.id
    assert response.data["detail"] == "The SimulationRun has not been paused, cancelled or failed, and can therefore not be resumed."

@pytest.mark.django_db
def test_simulation_resume_fail_no_checkpoint(create_user, auth_client_with_refresh_v1):
    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.PAUSED,
        params=json.dumps({}),
    )

    url = reverse("v1-simulation-resume-id", args=[run.id])
    response = auth_client.post(
        url
    )

    assert response.status_code == 409
    assert response.data["id"] == run.id
    assert response.data["detail"] == "The SimulationRun has not been saved on a checkpoint state, and can therefore not be resumed."


@pytest.mark.django_db
@patch("cats.api.v1.views.run_simulation.delay")
def test_simulation_resume_idempotency(mock_delay,create_user, auth_client_with_refresh_v1):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_delay.return_value = mock_task

    user = create_user(email="test1@email.com",password="test1password")

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    run = SimulationRun.objects.create(
        user=user,
        status=SimulationRun.Status.PAUSED,
        params=json.dumps({}),
        checkpoint_state=json.dumps({})
    )

    url = reverse("v1-simulation-resume-id", args=[run.id])
    response1 = auth_client.post(
        url
    )

    print(response1.data["detail"])
    assert response1.status_code == 200
    assert response1.data["id"] == run.id
    assert response1.data["detail"] == "The SimulationRun has been queued to be resumed."

    response2 = auth_client.post(
        url
    )

    assert response2.status_code == 409
    assert response2.data["id"] == run.id
    assert response2.data["detail"] == "The resume of the SimulationRun has already been queued."

    mock_delay.assert_called_once_with(run.id)

