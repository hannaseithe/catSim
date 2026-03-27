import json
from unittest.mock import MagicMock, patch

from celery import states
from django.test import override_settings
import pytest

from cats.events import Source
from cats.models import SimulationRun
from cats.tasks import on_worker_ready, run_simulation_logic


@pytest.mark.django_db(transaction=True)
@patch("cats.tasks.AsyncResult")
@patch("cats.tasks.run_simulation.delay")
def test_on_worker_ready(mock_delay, mock_async_result, create_simulation):
    mock_task_instance = MagicMock()
    mock_async_result.return_value = mock_task_instance
    mock_task_instance.state = states.FAILURE

    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_delay.return_value = mock_task
    
    run = create_simulation(status=SimulationRun.Status.RUNNING)

    on_worker_ready(sender=None)

    run.refresh_from_db()

    mock_delay.assert_called_once_with(run.id)
    assert run.status == ""
    assert run.queued_for == SimulationRun.Queued.RUN
    assert run.celery_task_id == mock_task.id

@pytest.mark.django_db(transaction=True)
@patch("cats.tasks.AsyncResult")
@patch("cats.tasks.run_simulation.delay")
def test_on_worker_ready_with_checkpoint(mock_delay, mock_async_result, create_simulation):
    mock_task_instance = MagicMock()
    mock_async_result.return_value = mock_task_instance
    mock_task_instance.state = states.FAILURE

    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_delay.return_value = mock_task
    
    run = create_simulation(status=SimulationRun.Status.RUNNING, checkpoint_state=json.dumps({"state":"some state"}))

    on_worker_ready(sender=None)

    run.refresh_from_db()

    mock_delay.assert_called_once_with(run.id)
    assert run.status == SimulationRun.Status.FAILED
    assert run.queued_for == SimulationRun.Queued.RESUME
    assert run.celery_task_id == mock_task.id


@pytest.mark.django_db
@override_settings(SIMULATION_CHECKPOINT_INTERVAL=5)
def test_simulation_run_logic(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": 9, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run.mark_run_queued(source=Source.WORKER)
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FINISHED
    assert run.checkpoint_state is not None
    assert run.checkpoint_tick == 5

@pytest.mark.django_db
def test_simulation_run_pause_logic(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": 10, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run.pause_requested = True
    run.save(update_fields=['pause_requested'])
    run.mark_run_queued(source=Source.WORKER)
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.PAUSED
    assert run.checkpoint_state is not None
    assert run.checkpoint_tick == 1

@pytest.mark.django_db
@override_settings(SIMULATION_CHECKPOINT_INTERVAL=5)
def test_simulation_run_resume_logic(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": 9, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run.pause_requested = True
    run.save(update_fields=['pause_requested'])
    run.mark_run_queued(source=Source.WORKER)
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.PAUSED

    run.mark_resume_queued(source=Source.WORKER)
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FINISHED
    assert run.checkpoint_state is not None
    assert run.checkpoint_tick == 5


@pytest.mark.django_db
def test_simulation_run_logic_fail(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": -1, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run.mark_run_queued(source=Source.WORKER)
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FAILED
    assert run.error_message == "iterations must be greater than 0"
    assert run.checkpoint_state is None


@pytest.mark.django_db
def test_simulation_run_logic_fail_inside_sim_loop(create_user):
    
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": 9, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run.mark_run_queued(source=Source.WORKER)
    with patch("cats.tasks.SimulationRun.refresh_from_db") as mock_refresh:
        mock_refresh.side_effect = [None, Exception("mid-loop-failure")]
        run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FAILED
    assert run.error_message == "mid-loop-failure"
    assert run.checkpoint_state is not None
