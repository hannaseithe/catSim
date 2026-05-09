import json
import time

from celery import shared_task, states
from celery.result import AsyncResult
from celery.signals import worker_ready

from cats.events import ProgressEvent, Source
from cats.models import SimulationEvent, SimulationResults, SimulationRun
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from simulations.cat_sim_1.metrics import extract_metrics
from simulations.cat_sim_1.simulation import Simulation, SimulationParameters, SimulationState

import logging

logger = logging.getLogger(__name__)



@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    logger.info("on worker_ready started")
    with transaction.atomic():
        qs = SimulationRun.objects.select_for_update().filter(Q(status=SimulationRun.Status.RUNNING) | Q(queued_for=SimulationRun.Queued.RUN) | Q(queued_for=SimulationRun.Queued.RESUME))
        for run in qs:
            if AsyncResult(run.celery_task_id).state in (states.STARTED, states.FAILURE):
                if run.queued_for is None:
                    if run.checkpoint_state is not None:
                        run.mark_failed(error_message="Simulation crashed", source= Source.RECOVERY, tick=run.checkpoint_tick)
                        run.mark_resume_queued(source=Source.RECOVERY)
                    else: 
                        run.status = ""
                        run.save(update_fields=["status"])
                        run.mark_run_queued(source=Source.RECOVERY)
                def start_worker(run = run):
                    task_result = run_simulation.delay(run.id)
                    logger.info(f"Simulation with id: {run.id} resumed after celery restart")
                    run.celery_task_id = task_result.id
                    run.save(update_fields=['celery_task_id'])
                transaction.on_commit(start_worker)

@shared_task(bind=True)
def run_simulation(self, run_id):
    return run_simulation_logic(run_id)


def run_simulation_logic(run_id):
    run = SimulationRun.objects.get(id=run_id)

    resume = run.queued_for == SimulationRun.Queued.RESUME
    source = Source.WORKER if not resume else Source.RECOVERY
    tick = run.checkpoint_tick if run.checkpoint_tick  else 0
    run.mark_running(source=source,tick=tick)


    sim = None
    last_good_sim = None
    try:
        params = SimulationParameters(**run.params)
        sim = Simulation(params=params)
        now = time.time()
        start = now
        if resume:
            logger.info(f"Simulation {run.id} resumed")
            sim.state = SimulationState.from_dict(json.loads(run.checkpoint_state))
        else:
            logger.info(f"Simulation {run.id} started")
            sim.generate_initial_state()
        for sim in sim.run():
            last_good_sim = sim

            # emit ProgressEvent
            if (new_now := time.time()) - now > settings.SIMULATION_PROGRESS_INTERVAL_DURATION and sim.state.run.tick > 0:
                progress = sim.state.run.tick / sim.params.iterations *100
                elapsed_time = (new_now-start)
                remaining_time = (sim.params.iterations - sim.state.run.tick) * (elapsed_time/sim.state.run.tick)
                event = ProgressEvent(tick=sim.state.run.tick, progress=progress, elapsed_time=elapsed_time, remaining_time=remaining_time)
                SimulationEvent.emit_event(run=run, event_type=SimulationEvent.Type.PROGRESS, content=event)
                now = new_now

            # pause if requested
            run.refresh_from_db(fields=['pause_requested'])
            if run.pause_requested:
                save_checkpoint(run, sim)
                run.mark_paused(source=Source.WORKER, tick=run.checkpoint_tick)
                logger.info(f"Simulation id:{run.id} has been paused on tick: {run.checkpoint_tick}")
                return
            
            # save checkpoint
            if sim.state.run.tick % settings.SIMULATION_CHECKPOINT_INTERVAL == 0:
                save_checkpoint(run, sim)

        metrics = extract_metrics(sim)

        results = SimulationResults.objects.create(
            run=run,
            metrics=metrics,
        )
        run.mark_completed(source= Source.WORKER, tick=sim.state.run.tick)
        logger.info(f"Simulation id:{run.id} finished with Results id:{results.id}")

    except Exception as e:
        try:
            if last_good_sim is not None:
                save_checkpoint(run, last_good_sim)
        except Exception as inner_e:
            logger.exception(f"Checkpoint save failed for failed simulation {run.id}. Error: {inner_e}")
        run.mark_failed(error_message=str(e), source=Source.WORKER, tick=run.checkpoint_tick if last_good_sim else None)
        logger.exception(f"Simulation {run.id} failed. Error: {run.error_message}")

def save_checkpoint(run: SimulationRun, sim: Simulation):
    run.checkpoint_tick = sim.state.run.tick
    run.checkpoint_state = sim.serialize_state()
    run.save(update_fields=["checkpoint_tick", "checkpoint_state"])
