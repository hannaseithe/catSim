from django.utils import timezone
from celery import shared_task

from cats.models import SimulationResults, SimulationRun
from simulation.metrics import extract_metrics
from simulation.simulation import Simulation, SimulationParameters

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_simulation(self,run_id):
    run = SimulationRun.objects.get(id=run_id)
    run.status = SimulationRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save()
    logger.info(f"Simulation {run.id} started")
    logger.info(run.params)

    try:
        params= SimulationParameters(**run.params)
        sim = Simulation(params=params)
        sim.generate_initial_state()
        sim.run()
        
        metrics = extract_metrics(sim)

        results = SimulationResults.objects.create(
            run=run,
            metrics=metrics,
        )

        run.status = "completed"
        run.finished_at = timezone.now()
        logger.info(f"Simulation {run.id} finished with Results: {results.id}")

    except Exception as e:
        run.status = "failed"
        run.error_messages = str(e)
        logger.info(f"Simulation {run.id} failed. Error: {run.error_messages}")

    run.save()
