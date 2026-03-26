import json

from celery import shared_task, states
from celery.result import AsyncResult
from celery.signals import worker_ready

from cats.models import SimulationResults, SimulationRun
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from simulation.metrics import extract_metrics
from simulation.simulation import Simulation, SimulationParameters, SimulationState

import logging

logger = logging.getLogger(__name__)



@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    with transaction.atomic():
        qs = SimulationRun.objects.select_for_update().filter(Q(status=SimulationRun.Status.RUNNING) | Q(queued_for=SimulationRun.Queued.RUN) | Q(queued_for=SimulationRun.Queued.RESUME))
        for run in qs:
            if AsyncResult(run.celery_task_id).state not in (states.STARTED, states.PENDING):
                if run.queued_for is None:
                    if run.checkpoint_state is not None:
                        run.mark_failed("Simulation crashed")
                        run.mark_resume_queued()
                    else: 
                        run.status = ""
                        run.save(update_fields=["status"])
                        run.mark_run_queued()
                def start_worker(run = run):
                    task_result = run_simulation.delay(run.id)
                    run.celery_task_id = task_result.id
                    run.save(update_fields=['celery_task_id'])
                transaction.on_commit(start_worker)

@shared_task(bind=True)
def run_simulation(self, run_id):
    return run_simulation_logic(run_id)


def run_simulation_logic(run_id):
    run = SimulationRun.objects.get(id=run_id)
    resume = run.queued_for == SimulationRun.Queued.RESUME
    run.mark_running()
    sim = None
    last_good_sim = None
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
            last_good_sim = sim
            run.refresh_from_db(fields=['pause_requested'])
            if run.pause_requested:
                save_checkpoint(run, sim)
                run.mark_paused()
                logger.info(f"Simulation id:{run.id} has been paused on tick: {run.checkpoint_tick}")
                return
            if sim.state.run.tick % settings.SIMULATION_CHECKPOINT_INTERVAL == 0:
                save_checkpoint(run, sim)

        metrics = extract_metrics(sim)

        results = SimulationResults.objects.create(
            run=run,
            metrics=metrics,
        )
        run.mark_completed()
        logger.info(f"Simulation id:{run.id} finished with Results id:{results.id}")

    except Exception as e:
        try:
            if last_good_sim is not None:
                save_checkpoint(run, last_good_sim)
        except Exception as inner_e:
            logger.exception(f"Checkpoint save failed for failed simulation {run.id}. Error: {inner_e}")
        run.mark_failed(str(e))
        logger.exception(f"Simulation {run.id} failed. Error: {run.error_message}")

def save_checkpoint(run: SimulationRun, sim: Simulation):
    run.checkpoint_tick = sim.state.run.tick
    run.checkpoint_state = sim.serialize_state()
    run.save(update_fields=["checkpoint_tick", "checkpoint_state"])
