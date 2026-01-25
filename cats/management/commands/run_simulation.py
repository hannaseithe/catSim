from django.core.management.base import BaseCommand
import secrets

from accounts.models import CustomUser
from cats.models import SimulationRun

import logging

from cats.tasks import run_simulation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Queue a simulation run"

    def add_arguments(self, parser):
        parser.add_argument("-u", "--user_id", type=int, required=True, help="Id of user the Simulation should be attached to")
        parser.add_argument(
            "-i", "--iterations", type=int, default=1000, help="Number of iterations"
        )
        parser.add_argument(
            "-ca", "--cat_amount", type=int, default=10, help="Amount of cats"
        )
        parser.add_argument(
            "-na", "--node_amount", type=int, default=60, help="Amount of loations"
        )
        parser.add_argument(
            "-me",
            "--mean_edges",
            type=int,
            default=4,
            help="The average amount of connections between nodes",
        )
        parser.add_argument(
            "-ve",
            "--var_edges",
            type=int,
            default=1.0,
            help="The variance of connections between nodes",
        )
        parser.add_argument(
            "-ma",
            "--mean_aggressive",
            type=float,
            default=0.0,
            help="The average value of aggressiveness. Must be between -1.0 and 1.0. -1.0 is very friendly",
        )
        parser.add_argument(
            "-va",
            "--var_aggressive",
            type=float,
            default=0.1,
            help="The variance of aggressiveness",
        )
        parser.add_argument(
            "-ml",
            "--mean_laziness",
            type=float,
            default=0.5,
            help="The average value of laziness. Must be between 0.0 and 1.0",
        )
        parser.add_argument(
            "-vl",
            "--var_laziness",
            type=float,
            default=0.05,
            help="The variance of laziness",
        )

    def handle(self, *args, **options):
        seed = secrets.randbits(32)

        param_keys = [
            "iterations",
            "cat_amount",
            "node_amount",
            "mean_edges",
            "var_edges",
            "mean_aggressive",
            "var_aggressive",
            "mean_laziness",
            "var_laziness",
        ]
        params = {key: options[key] for key in param_keys}
        params["seed"] = seed

        user = CustomUser.objects.get(id=options["user_id"])
        run = SimulationRun.objects.create(params=params, user=user)
        run_simulation.delay(run.id)
        logger.info(
            f"Queued simulation {run.id} with seed {seed} and parameters: {params}"
        )
