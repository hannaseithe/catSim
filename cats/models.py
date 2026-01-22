from django.db import models
from django.utils import timezone

from django_project import settings


class InvalidSimulationState(Exception):
    """Raised when a simulation run is transitioned into an invalid state."""


class SimulationRun(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="simulations",
    )
    params = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    class Status(models.TextChoices):
        PENDING = "pending", "PENDING"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    error_message = models.TextField(null=True, blank=True)

    def mark_running(self):
        if self.status != self.Status.PENDING:
            raise InvalidSimulationState(
                f"Cannot start simulation in state '{self.status}'"
            )
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_completed(self):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot complete simulation in state '{self.status}'"
            )
        self.status = self.Status.FINISHED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_failed(self, error_message):
        if self.status != self.Status.RUNNING:
            raise InvalidSimulationState(
                f"Cannot fail simulation in state '{self.status}'"
            )
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=["status", "finished_at", "error_message"])


class SimulationResults(models.Model):
    run = models.OneToOneField(
        SimulationRun, on_delete=models.CASCADE, related_name="result"
    )
    metrics = models.JSONField()
