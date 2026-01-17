import pytest

from cats.models import InvalidSimulationState, SimulationResults, SimulationRun
from cats.tasks import run_simulation_logic

from django.core.management import call_command
from unittest.mock import patch


@pytest.mark.django_db
def test_model_simulation_run():
    sim = SimulationRun.objects.create(params={"iterations": 10})
    assert sim.status == SimulationRun.Status.PENDING
    assert sim.created_at is not None
    assert sim.started_at is None
    assert sim.finished_at is None


@pytest.mark.django_db
def test_model_simulation_run_success_lifecycle():
    sim = SimulationRun.objects.create(params={"iterations": 10})

    sim.mark_running()
    assert sim.started_at is not None
    assert sim.status == SimulationRun.Status.RUNNING

    sim.mark_completed()
    assert sim.finished_at is not None
    assert sim.status == SimulationRun.Status.FINISHED


@pytest.mark.django_db
def test_model_simulation_run_fail_lifecycle():
    sim = SimulationRun.objects.create(params={"iterations": 10})

    sim.mark_running()
    assert sim.started_at is not None
    assert sim.status == SimulationRun.Status.RUNNING

    sim.mark_failed("This simulation has failed")
    assert sim.finished_at is not None
    assert sim.status == SimulationRun.Status.FAILED
    assert sim.error_messages == "This simulation has failed"


@pytest.mark.django_db
def test_cannot_complete_without_running():
    sim = SimulationRun.objects.create(params={})

    with pytest.raises(InvalidSimulationState):
        sim.mark_completed()


@pytest.mark.django_db
def test_cannot_fail_without_running():
    sim = SimulationRun.objects.create(params={})

    with pytest.raises(InvalidSimulationState):
        sim.mark_failed("error message")


@pytest.mark.django_db
def test_cannot_start_if_not_pending():
    sim = SimulationRun.objects.create(params={"iterations": 10})

    sim.mark_running()
    sim.mark_completed()

    with pytest.raises(InvalidSimulationState):
        sim.mark_running()


@pytest.mark.django_db
def test_simulation_results_link_to_run():
    run = SimulationRun.objects.create(params={"iterations": 10})
    results = SimulationResults.objects.create(run=run, metrics={"foo": "bar"})

    assert results.run == run


@pytest.mark.django_db
def test_simulation_run_logic():
    run = SimulationRun.objects.create(
        params={"iterations": 10, "cat_amount": 3, "node_amount": 10}
    )
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FINISHED


@pytest.mark.django_db
def test_simulation_run_logic_fail():
    run = SimulationRun.objects.create(
        params={"iterations": -1, "cat_amount": 3, "node_amount": 10}
    )

    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FAILED
    assert run.error_messages == "iterations must be greater than 0"


@pytest.mark.django_db
@patch("cats.management.commands.run_simulation.run_simulation.delay")
def test_run_simulation_command_creates_run_and_queues_task(mock_delay):
    call_command(
        "run_simulation",
        iterations=42,
        cat_amount=3,
        node_amount=10,
    )

    run = SimulationRun.objects.get()
    assert run.params["iterations"] == 42
    assert run.params["cat_amount"] == 3
    assert run.params["node_amount"] == 10

    assert "seed" in run.params
    assert isinstance(run.params["seed"], int)

    mock_delay.assert_called_once_with(run.id)
