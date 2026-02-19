import logging
import secrets
from django.db import transaction
from django.db.models import F, IntegerField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from cats.api.v1.filters import SimulationFilter
from cats.api.paginations import SimulationPagination
from cats.api.permissions import IsOwnerOrAdmin
from cats.api.v1.serializers import (
    SimulationCreateSerializer,
    SimulationErrorSerializer,
    SimulationResultSerializer,
    SimulationStatusSerializer,
)
from cats.models import SimulationResults, SimulationRun
from cats.tasks import run_simulation

logger = logging.getLogger(__name__)

NOT_FAILED_RESPONSE = {"detail": "Simulation has not failed"}
NOT_COMPLETED_RESPONSE = {"detail": "Simulation has not completed"}


class SimulationStartView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request):
        serializer = SimulationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        print(serializer.validated_data)

        uuid = serializer.validated_data["uuid"]

        params = serializer.validated_data["params"]
        params["seed"] = secrets.randbits(32)

        with transaction.atomic():
            run, created = SimulationRun.objects.get_or_create(
                uuid=uuid, defaults={"user": request.user, "params": params}
            )
            if created:
                task_result = run_simulation.delay(run.id)
                run.celery_task_id = task_result.id
                run.save()
                logger.info(
                    f"Queued simulation {run.id} with seed {params['seed']} and parameters: {params}"
                )
                return Response(
                    {"id": run.id, "uuid": run.uuid, "status": run.status},
                    status=status.HTTP_201_CREATED,
                )
        return Response(
            {
                "id": run.id,
                "uuid": uuid,
                "status": run.status,
                "message": "Simulation already exists",
            },
            status=status.HTTP_200_OK,
        )


class SimulationCancelView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, simulation_id=None, simulation_uuid=None):
        if simulation_id:
            run = get_object_or_404(SimulationRun, id=simulation_id)
        elif simulation_uuid:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)
        
        self.check_object_permissions(request, run)

        identifiers = {"id": run.id, "uuid": run.uuid}
        if run.status not in (
            SimulationRun.Status.RUNNING,
            SimulationRun.Status.PENDING,
        ):
            print(f"The status of the simulation: {run.status}")
            return Response(
                {
                    **identifiers,
                    "detail": "The SimulationRun is not pending nor running, and can therefore not be canceled.",
                },
                status=409,
            )
        run.cancel()
        return Response(
            {**identifiers, "detail": "The SimulationRun has been canceled."},
            status=200,
        )
    
class SimulationDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def delete(self, request, simulation_id=None, simulation_uuid=None):
        if simulation_id:
            run = get_object_or_404(SimulationRun, id=simulation_id)
        elif simulation_uuid:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        
        self.check_object_permissions(request, run)

        identifiers = {"id": run.id, "uuid": run.uuid}
        if run.status not in (
            SimulationRun.Status.CANCELED,
            SimulationRun.Status.FINISHED,
            SimulationRun.Status.FAILED,
        ):
            print(f"The status of the simulation: {run.status}")
            return Response(
                {
                    **identifiers,
                    "detail": "The SimulationRun has not finished, and can therefore not be deleted. Cancel the simulation first",
                },
                status=409,
            )
        run.delete()
        return Response(
            {**identifiers, "detail": "The SimulationRun has been deleted."},
            status=200,
        )


class SimulationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id=None, simulation_uuid=None):
        if id:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        self.check_object_permissions(request, run)
        serializer = SimulationStatusSerializer(run)
        return Response(serializer.data)


class SimulationErrorView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id=None, simulation_uuid=None):
        if id:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        if run.status != SimulationRun.Status.FAILED:
            return Response(
                NOT_FAILED_RESPONSE,
                status=status.HTTP_409_CONFLICT,
            )
        serializer = SimulationErrorSerializer(run)
        return Response(serializer.data)


class SimulationResultView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id=None, simulation_uuid=None):
        if id:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        if run.status != SimulationRun.Status.FINISHED:
            return Response(
                NOT_COMPLETED_RESPONSE,
                status=status.HTTP_409_CONFLICT,
            )
        result = get_object_or_404(SimulationResults, run__id=id)
        serializer = SimulationResultSerializer(result)
        return Response(serializer.data)


class SimulationListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationStatusSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SimulationFilter
    ordering_fields = ["created_at", "iterations", "cat_amount", "node_amount"]
    ordering = ["-created_at"]

    pagination_class = SimulationPagination

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            qs = SimulationRun.objects.all()
        else:
            qs = SimulationRun.objects.filter(user=user)

        qs = qs.annotate(
            iterations=Cast(F("params__iterations"), IntegerField()),
            cat_amount=Cast(F("params__cat_amount"), IntegerField()),
            node_amount=Cast(F("params__node_amount"), IntegerField()),
        )
        return qs
