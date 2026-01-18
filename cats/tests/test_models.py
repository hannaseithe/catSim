import pytest

from cats.models import InvalidSimulationState, SimulationResults, SimulationRun
from cats.tests.conftest import DUMMY_METRICS


@pytest.mark.django_db
def test_model_simulation_run(create_simulation):
    sim = create_simulation()
    assert sim.status == SimulationRun.Status.PENDING
    assert sim.created_at is not None
    assert sim.started_at is None
    assert sim.finished_at is None


@pytest.mark.django_db
def test_model_simulation_run_success_lifecycle(create_simulation):
    sim = create_simulation()

    sim.mark_running()
    assert sim.started_at is not None
    assert sim.status == SimulationRun.Status.RUNNING

    sim.mark_completed()
    assert sim.finished_at is not None
    assert sim.status == SimulationRun.Status.FINISHED


@pytest.mark.django_db
def test_model_simulation_run_fail_lifecycle(create_simulation):
    sim = create_simulation()

    sim.mark_running()
    assert sim.started_at is not None
    assert sim.status == SimulationRun.Status.RUNNING

    sim.mark_failed("This simulation has failed")
    assert sim.finished_at is not None
    assert sim.status == SimulationRun.Status.FAILED
    assert sim.error_messages == "This simulation has failed"


@pytest.mark.django_db
def test_cannot_complete_without_running(create_simulation):
    sim = create_simulation()

    with pytest.raises(InvalidSimulationState):
        sim.mark_completed()


@pytest.mark.django_db
def test_cannot_fail_without_running(create_simulation):
    sim = create_simulation()

    with pytest.raises(InvalidSimulationState):
        sim.mark_failed("error message")


@pytest.mark.django_db
def test_cannot_start_if_not_pending(create_simulation):
    sim = create_simulation()

    sim.mark_running()
    sim.mark_completed()

    with pytest.raises(InvalidSimulationState):
        sim.mark_running()


@pytest.mark.django_db
def test_simulation_results_link_to_run(create_results):
    results = create_results()

    assert results.run
    assert results.metrics == DUMMY_METRICS

