import logging
import secrets
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from cats.api.permissions import IsOwnerOrAdmin
from cats.api.serializers import (
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

        params = serializer.validated_data
        params["seed"] = secrets.randbits(32)

        run = SimulationRun.objects.create(params=params)
        run_simulation.delay(run.id)
        logger.info(
            f"Queued simulation {run.id} with seed {params['seed']} and parameters: {params}"
        )

        return Response(
            {"id": run.id, "status": run.status}, status=status.HTTP_201_CREATED
        )


class SimulationDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationStatusSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SimulationRun.objects.all()
        return SimulationRun.objects.filter(user=user)
    


class SimulationErrorView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id):
        run = get_object_or_404(SimulationRun, id=id)
        if run.status != SimulationRun.Status.FAILED:
            return Response(
                NOT_FAILED_RESPONSE,
                status=status.HTTP_409_CONFLICT,
            )
        serializer = SimulationErrorSerializer(run)
        return Response(serializer.data)


class SimulationResultView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id):
        run = get_object_or_404(SimulationRun, id=id)
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

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SimulationRun.objects.all()
        return SimulationRun.objects.filter(user=user)
