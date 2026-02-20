import logging
import secrets
from django.db import transaction
from django.db.models import F, IntegerField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from cats.api.v1.filters import SimulationFilter
from cats.api.paginations import SimulationPagination
from cats.api.permissions import IsOwnerOrAdmin
from cats.api.v1.serializers import (
    SimulationCreateSerializerV1,
    SimulationErrorSerializerV1,
    SimulationResultSerializerV1,
    SimulationStatusSerializerV1,
)
from cats.models import SimulationResults, SimulationRun
from cats.tasks import run_simulation

logger = logging.getLogger(__name__)

NOT_FAILED_RESPONSE = {"detail": "Simulation has not failed"}
NOT_COMPLETED_RESPONSE = {"detail": "Simulation has not completed"}

class TokenRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

class TokenRefreshRequestSerializer(serializers.Serializer):
    access = serializers.CharField()

class TokenRefreshResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()

@extend_schema(
    request=TokenRequestSerializer,
    responses=TokenResponseSerializer,
)
class CustomTokenObtainPairViewV1(TokenObtainPairView):
    pass

@extend_schema(
    request=TokenRefreshRequestSerializer,
    responses=TokenRefreshResponseSerializer,
)
class CustomTokenRefreshViewV1(TokenRefreshView):
    pass


class SimulationStartView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationCreateSerializerV1

    def post(self, request):
        serializer = SimulationCreateSerializerV1(data=request.data)
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

@extend_schema(
    request=None,
    responses={
        200: {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "uuid": {"type": "string"},
                "detail": {"type": "string", "example": "The SimulationRun has been canceled."},
            },
        },
        409: {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "uuid": {"type": "string"},
                "detail": {
                    "type": "string",
                    "example": "The SimulationRun is not pending nor running, and can therefore not be canceled.",
                },
            },
        },
        400: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "No identifier provided."},
            },
        },
        404: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"},
            },
        },
    },
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
    
@extend_schema(
    request=None,
    responses={
        200: {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "uuid": {"type": "string"},
                "detail": {"type": "string", "example": "The SimulationRun has been deleted."},
            },
        },
        409: {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "uuid": {"type": "string"},
                "detail": {
                    "type": "string",
                    "example": "The SimulationRun has not finished, and can therefore not be deleted. Cancel the simulation first.",
                },
            },
        },
        400: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "No identifier provided."},
            },
        },
        404: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"},
            },
        },
    },
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
                    "detail": "The SimulationRun has not finished, and can therefore not be deleted. Cancel the simulation first.",
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
    serializer_class = SimulationStatusSerializerV1

    def get(self, request, id=None, simulation_uuid=None):
        if id:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        self.check_object_permissions(request, run)
        serializer = SimulationStatusSerializerV1(run)
        return Response(serializer.data)


class SimulationErrorView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationErrorSerializerV1

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
        serializer = SimulationErrorSerializerV1(run)
        return Response(serializer.data)


class SimulationResultView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationResultSerializerV1

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
        serializer = SimulationResultSerializerV1(result)
        return Response(serializer.data)

@extend_schema(
    parameters=[
        OpenApiParameter(
            name='ordering',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Field to order by. Prefix with "-" for descending.',
            enum=['created_at', '-created_at', 'iterations', '-iterations', 'cat_amount', '-cat_amount', 'node_amount', '-node_amount'],
            required=False
        ),
        OpenApiParameter(
            name='page',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Page number within the paginated result set.',
            required=False,
            default=1
        ),
        OpenApiParameter(
            name='page_size',
            type= {"type": "integer", "maximum": 100},
            location=OpenApiParameter.QUERY,
            description='Number of results per page (max 100)',
            required=False,
            default=10,
        )
    ]
)
class SimulationListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationStatusSerializerV1

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SimulationFilter
    ordering_fields = ["created_at", "iterations", "cat_amount", "node_amount"]
    ordering = ["-created_at"]

    pagination_class = SimulationPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SimulationRun.objects.none()

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
