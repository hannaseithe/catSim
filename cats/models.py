import uuid as uuid_p
from celery.result import AsyncResult
from django.db import models
from django.utils import timezone

from django_project import settings


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

    created_at = models.DateTimeField(default=timezone.now)
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
        max_length=20, choices=Queued.choices, null=True
    )

    error_message = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=50, blank=True, null=True)

    pause_requested = models.BooleanField(default=False)

    def mark_running(self):
        if self.queued_for not in (
            self.Queued.RUN,
            self.Queued.RESUME,
        ):
            raise InvalidSimulationState(
                "Cannot start simulation if not queued for start or resume"
            )
        self.status = self.Status.RUNNING
        self.queued_for = None
        self.started_at = timezone.now()
        self.save(update_fields=["status", "queued_for", "started_at"])

    def mark_completed(self):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot complete simulation in state '{self.status}'"
            )
        self.status = self.Status.FINISHED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    # TODO(API v2): replace finished_at with stopped_at for FAILED state - breaking change 
    def mark_failed(self, error_message):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot fail simulation in state '{self.status}'"
            )
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=["status", "finished_at", "error_message"])

    def mark_cancelled(self):
        if self.status not in (self.Status.RUNNING, self.Status.PENDING):
            raise InvalidSimulationState(
                f"Cannot cancel simulation in state '{self.status}'"
            )
        self.status = self.Status.CANCELED
        self.stopped_at = timezone.now()
        self.save(update_fields=["status", "stopped_at"])

    def cancel(self):
        if self.status not in (self.Status.RUNNING, self.Status.PENDING):
            raise InvalidSimulationState(
                f"Cannot cancel simulation in state '{self.status}'"
            )
        task = AsyncResult(self.celery_task_id)
        task.revoke(terminate=True)
        self.mark_cancelled()

    def mark_paused(self):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot pause simulation in state '{self.status}'"
            )
        self.status = self.Status.PAUSED
        self.pause_requested = False
        self.stopped_at = timezone.now()
        self.save(update_fields=['status','pause_requested','stopped_at'])

    def mark_run_queued(self):
        if self.status not in (self.Status.PENDING, ):
            raise InvalidSimulationState(
                f"Cannot queue simulation for run in state '{self.status}'"
            )
        self.queued_for = self.Queued.RUN
        self.save(update_fields=['queued_for'])

    def mark_resume_queued(self):
        if self.status not in (self.Status.CANCELED, self.Status.PAUSED):
            raise InvalidSimulationState(
                f"Cannot queue simulation for resume in state '{self.status}'"
            )
        self.queued_for = self.Queued.RESUME
        self.save(update_fields=['queued_for'])



class SimulationResults(models.Model):
    run = models.OneToOneField(
        SimulationRun, on_delete=models.CASCADE, related_name="result"
    )
    metrics = models.JSONField()
