from dataclasses import asdict
import uuid as uuid_p
from asgiref.sync import async_to_sync
from celery.result import AsyncResult
from channels.layers import get_channel_layer
from django.db import models
from django.utils import timezone

from cats.events import Action, QueueEvent, Source, StateTransitionEvent
from django_project import settings

channel_layer = get_channel_layer()


class InvalidSimulationState(Exception):
    """Raised when a simulation run is transitioned into an invalid state."""


class SimulationRun(models.Model):
    uuid = models.UUIDField(unique=True, editable=False, default=uuid_p.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="simulations",
    )
    params = models.JSONField()

    checkpoint_tick = models.IntegerField(null=True)
    checkpoint_state = models.JSONField(null=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    stopped_at = models.DateTimeField(null=True)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"
        PAUSED = "paused", "Paused"

    class Queued(models.TextChoices):
        RUN = "run", "Run"
        RESUME = "resume", "Resume"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    queued_for = models.CharField(
        max_length=20, choices=Queued.choices, null=True, db_index=True
    )

    error_message = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=50, blank=True, null=True)

    pause_requested = models.BooleanField(default=False)

    def mark_running(self, source: Source, tick: int):
        if self.queued_for not in (
            self.Queued.RUN,
            self.Queued.RESUME,
        ):
            raise InvalidSimulationState(
                "Cannot start simulation if not queued for start or resume"
            )
        old_status = self.status
        self.status = self.Status.RUNNING
        self.queued_for = None
        self.started_at = timezone.now()
        self.save(update_fields=["status", "queued_for", "started_at"])

        event = StateTransitionEvent(
            old_status=old_status, new_status=self.status, source=source, tick=tick
        )
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.STATE_TRANSITION, content=event
        )

    def mark_completed(self, source: Source, tick: int):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot complete simulation in state '{self.status}'"
            )
        old_status = self.status
        self.status = self.Status.FINISHED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

        event = StateTransitionEvent(
            old_status=old_status, new_status=self.status, source=source, tick=tick
        )
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.STATE_TRANSITION, content=event
        )

    # TODO(API v2): replace finished_at with stopped_at for FAILED state - breaking change
    def mark_failed(self, error_message, source: Source, tick: int):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot fail simulation in state '{self.status}'"
            )
        old_status = self.status
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=["status", "finished_at", "error_message"])

        event = StateTransitionEvent(
            old_status=old_status,
            new_status=self.status,
            source=source,
            tick=tick,
            message=error_message,
        )
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.STATE_TRANSITION, content=event
        )

    def mark_cancelled(self, source: Source):
        if self.status not in (self.Status.RUNNING, self.Status.PENDING):
            raise InvalidSimulationState(
                f"Cannot cancel simulation in state '{self.status}'"
            )
        old_status = self.status
        self.status = self.Status.CANCELED
        self.stopped_at = timezone.now()
        self.save(update_fields=["status", "stopped_at"])

        event = StateTransitionEvent(
            old_status=old_status, new_status=self.status, source=source, tick=None
        )
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.STATE_TRANSITION, content=event
        )

    def cancel(self, source: Source):
        if self.status not in (self.Status.RUNNING, self.Status.PENDING):
            raise InvalidSimulationState(
                f"Cannot cancel simulation in state '{self.status}'"
            )
        task = AsyncResult(self.celery_task_id)
        task.revoke(terminate=True)
        self.mark_cancelled(source=source)

    def mark_paused(self, source: Source, tick: int):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot pause simulation in state '{self.status}'"
            )
        old_status = self.status
        self.status = self.Status.PAUSED
        self.pause_requested = False
        self.stopped_at = timezone.now()
        self.save(update_fields=["status", "pause_requested", "stopped_at"])

        event = StateTransitionEvent(
            old_status=old_status, new_status=self.status, source=source, tick=tick
        )
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.STATE_TRANSITION, content=event
        )

    def mark_run_queued(self, source: Source):
        if self.status not in (self.Status.PENDING, ""):
            raise InvalidSimulationState(
                f"Cannot queue simulation for run in state '{self.status}'"
            )
        self.queued_for = self.Queued.RUN
        self.save(update_fields=["queued_for"])

        event = QueueEvent(source=source, action=Action.RUN)
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.QUEUE, content=event
        )

    def mark_resume_queued(self, source: Source):
        if self.status not in (
            self.Status.CANCELED,
            self.Status.PAUSED,
            self.Status.FAILED,
        ):
            raise InvalidSimulationState(
                f"Cannot queue simulation for resume in state '{self.status}'"
            )
        self.queued_for = self.Queued.RESUME
        self.save(update_fields=["queued_for"])

        event = QueueEvent(source=source, action=Action.RESUME)
        SimulationEvent.emit_event(
            run=self, event_type=SimulationEvent.Type.QUEUE, content=event
        )


class SimulationResults(models.Model):
    run = models.OneToOneField(
        SimulationRun, on_delete=models.CASCADE, related_name="result"
    )
    metrics = models.JSONField()


class SimulationEvent(models.Model):
    run = models.ForeignKey(
        SimulationRun, on_delete=models.CASCADE, related_name="events"
    )

    class Type(models.TextChoices):
        PROGRESS = "progress", "Progress"
        STATE_TRANSITION = "state_transition", "State_Transition"
        QUEUE = "queue", "Queue"

    event_type = models.CharField(max_length=20, choices=Type.choices)
    logged_at = models.DateTimeField(default=timezone.now)
    content = models.JSONField()

    @staticmethod
    def emit_event(run, event_type, content):
        SimulationEvent.objects.create(
            run=run, event_type=event_type, content=asdict(content)
        )
        async_to_sync(channel_layer.group_send)(
            f"run_{run.id}",
            {
                "type": "simulation_event",
                "message": {"event_type": event_type, "content": asdict(content)},
            },
        )

    class Meta:
        indexes = [models.Index(fields=["run", "event_type", "logged_at"])]
