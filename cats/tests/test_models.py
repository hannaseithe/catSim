
from dataclasses import asdict

import pytest

from cats.events import Action, QueueEvent, Source
from cats.models import InvalidSimulationState, SimulationEvent, SimulationRun
from cats.tests.conftest import DUMMY_METRICS


@pytest.mark.django_db
def test_model_simulation_run(create_simulation):
    sim = create_simulation()
    assert sim.uuid is not None
    assert sim.status == SimulationRun.Status.PENDING
    assert sim.created_at is not None
    assert not sim.pause_requested


@pytest.mark.django_db
def test_model_simulation_run_success_lifecycle(create_simulation):
    sim = create_simulation()

    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    assert sim.started_at is not None
    assert sim.status == SimulationRun.Status.RUNNING

    sim.mark_completed(source=Source.WORKER, tick=0)
    assert sim.finished_at is not None
    assert sim.status == SimulationRun.Status.FINISHED


@pytest.mark.django_db
def test_model_simulation_run_fail_lifecycle(create_simulation):
    sim = create_simulation()

    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    assert sim.started_at is not None
    assert sim.status == SimulationRun.Status.RUNNING

    sim.mark_failed(error_message="This simulation has failed", source=Source.WORKER, tick=0)
    assert sim.finished_at is not None
    assert sim.status == SimulationRun.Status.FAILED
    assert sim.error_message == "This simulation has failed"


@pytest.mark.django_db
def test_cannot_complete_without_running(create_simulation):
    sim = create_simulation()

    with pytest.raises(InvalidSimulationState):
        sim.mark_completed(source=Source.WORKER, tick=0)


@pytest.mark.django_db
def test_cannot_fail_without_running(create_simulation):
    sim = create_simulation()

    with pytest.raises(InvalidSimulationState):
        sim.mark_failed(error_message="error message",source=Source.WORKER, tick=0)


@pytest.mark.django_db
def test_cannot_start_if_not_pending(create_simulation):
    sim = create_simulation()

    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    sim.mark_completed(source=Source.WORKER, tick=0)

    with pytest.raises(InvalidSimulationState):
        sim.mark_running(source=Source.WORKER, tick=0)


@pytest.mark.django_db
def test_mark_paused(create_simulation):
    sim = create_simulation()

    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)

    sim.pause_requested = True

    sim.mark_paused(source=Source.WORKER, tick=0)
    assert sim.pause_requested is False
    assert sim.status == SimulationRun.Status.PAUSED
    assert sim.stopped_at is not None

@pytest.mark.django_db
def test_fail_mark_paused(create_simulation):
    sim = create_simulation()

    sim.mark_run_queued(source=Source.WORKER)
    sim.mark_running(source=Source.WORKER, tick=0)
    sim.mark_completed(source=Source.WORKER, tick=0)

    sim.pause_requested = True

    with pytest.raises(InvalidSimulationState):
        sim.mark_paused(source=Source.WORKER, tick=0)


@pytest.mark.django_db
def test_simulation_results_link_to_run(create_results):
    results = create_results()

    assert results.run
    assert results.metrics == DUMMY_METRICS

@pytest.mark.django_db
def test_simulation_event_emit_event(create_simulation):
    run = create_simulation()
    queue_event = QueueEvent(source=Source.WORKER, action=Action.PAUSE)
    SimulationEvent.emit_event(run=run, event_type=SimulationEvent.Type.PROGRESS, content=queue_event)
    event = SimulationEvent.objects.get(run=run)
    assert event.event_type == SimulationEvent.Type.PROGRESS
    assert event.content == asdict(queue_event)
    