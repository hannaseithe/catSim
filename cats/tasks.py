import json

from celery import shared_task

from cats.models import SimulationResults, SimulationRun
from django.conf import settings
from simulation.metrics import extract_metrics
from simulation.simulation import Simulation, SimulationParameters, SimulationState

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_simulation(self, run_id):
    return run_simulation_logic(run_id)


def run_simulation_logic(run_id):
    run = SimulationRun.objects.get(id=run_id)
    resume = run.queued_for == SimulationRun.Queued.RESUME
    run.mark_running()
    try:
        params = SimulationParameters(**run.params)
        sim = Simulation(params=params)
        if resume:
            logger.info(f"Simulation {run.id} resumed")
            sim.state = SimulationState.from_dict(json.loads(run.checkpoint_state))
        else:
            logger.info(f"Simulation {run.id} started")
            sim.generate_initial_state()
        for sim in sim.run():
            run.refresh_from_db(fields=['pause_requested'])
            if run.pause_requested:
                run.checkpoint_tick = sim.state.run.tick
                run.checkpoint_state = sim.serialize_state()
                run.save(update_fields=["checkpoint_tick", "checkpoint_state"])
                run.mark_paused()
                logger.info(f"Simulation id:{run.id} has been paused on tick: {run.checkpoint_tick}")
                return
            if sim.state.run.tick % settings.SIMULATION_CHECKPOINT_INTERVAL == 0:
                run.checkpoint_tick = sim.state.run.tick
                run.checkpoint_state = sim.serialize_state()
                run.save(update_fields=["checkpoint_tick", "checkpoint_state"])

        metrics = extract_metrics(sim)

        results = SimulationResults.objects.create(
            run=run,
            metrics=metrics,
        )
        run.mark_completed()
        logger.info(f"Simulation id:{run.id} finished with Results id:{results.id}")

    except Exception as e:
        run.mark_failed(str(e))
        logger.exception(f"Simulation {run.id} failed. Error: {run.error_message}")
