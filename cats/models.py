from django.db import models



class SimulationRun(models.Model):

    params = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at =models.DateTimeField(null=True)

    class Status(models.TextChoices):
        PENDING = "pending", "PENDING"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"

    status= models.CharField(
        max_length=20,
        choices= Status.choices,
        default=Status.PENDING
    )

    error_messages = models.TextField(null=True,blank=True)

class SimulationResults(models.Model):
    run = models.OneToOneField(
        SimulationRun,
        on_delete=models.CASCADE,
        related_name='result'
        )
    metrics= models.JSONField()