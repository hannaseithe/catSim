import pytest

from cats.models import SimulationRun
from cats.tasks import run_simulation_logic


@pytest.mark.django_db
def test_simulation_run_logic(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": 10, "cat_amount": 3, "node_amount": 10},
        user=user
    )
    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FINISHED


@pytest.mark.django_db
def test_simulation_run_logic_fail(create_user):
    user = create_user()
    run = SimulationRun.objects.create(
        params={"iterations": -1, "cat_amount": 3, "node_amount": 10},
        user=user
    )

    run_simulation_logic(run.id)
    run.refresh_from_db()
    assert run.status == SimulationRun.Status.FAILED
    assert run.error_message == "iterations must be greater than 0"
