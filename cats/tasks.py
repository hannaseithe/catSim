from celery import shared_task

from cats.models import SimulationResults, SimulationRun
from simulation.metrics import extract_metrics
from simulation.simulation import Simulation, SimulationParameters

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_simulation(self, run_id):
    return run_simulation_logic(run_id)


def run_simulation_logic(run_id):
    run = SimulationRun.objects.get(id=run_id)
    run.mark_running()

    logger.info(f"Simulation {run.id} started")

    try:
        params = SimulationParameters(**run.params)
        sim = Simulation(params=params)
        sim.generate_initial_state()
        sim.run()

        metrics = extract_metrics(sim)

        results = SimulationResults.objects.create(
            run=run,
            metrics=metrics,
        )
        run.mark_completed()
        logger.info(f"Simulation id:{run.id} finished with Results id:{results.id}")

    except Exception as e:
        run.mark_failed(str(e))
        logger.info(f"Simulation {run.id} failed. Error: {run.error_messages}")
