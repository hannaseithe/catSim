from django.test import override_settings
import pytest

from cats.models import SimulationRun
from cats.tasks import run_simulation_logic


@pytest.mark.django_db
@override_settings(SIMULATION_CHECKPOINT_INTERVAL=5)
def test_simulation_run_logic(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": 9, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run_simulation_logic(run.id,resume=False)
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
    run_simulation_logic(run.id,resume=False)
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
    run_simulation_logic(run.id,resume=False)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.PAUSED

    run_simulation_logic(run.id,resume=True)
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

    run_simulation_logic(run.id, resume=False)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FAILED
    assert run.error_message == "iterations must be greater than 0"
