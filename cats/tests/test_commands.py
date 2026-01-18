from unittest.mock import patch
import pytest

from django.core.management import call_command

from cats.models import SimulationRun


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
