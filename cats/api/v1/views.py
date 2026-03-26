import logging
import secrets
from django.db import transaction
from django.db.models import F, IntegerField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    OpenApiParameter,
    OpenApiRequest,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


from cats.api.serializers import DetailSerializer
from cats.api.v1.filters import SimulationFilter
from cats.api.paginations import SimulationPagination
from cats.api.permissions import IsOwnerOrAdmin
from cats.api.v1.serializers import (
    LoginErrorSerializerV1,
    SimulationActionResponseSerializerV1,
    SimulationCreateResponseSerializerV1,
    SimulationCreateSerializerV1,
    SimulationErrorSerializerV1,
    SimulationExistsResponseSerializerV1,
    SimulationResultSerializerV1,
    SimulationStatusSerializerV1,
    TokenRefreshRequestSerializerV1,
    TokenRefreshResponseSerializerV1,
    TokenRequestSerializerV1,
    TokenResponseSerializerV1,
)
from cats.models import SimulationResults, SimulationRun
from cats.tasks import run_simulation

logger = logging.getLogger(__name__)

NOT_FAILED_RESPONSE = {"detail": "Simulation has not failed"}
NOT_COMPLETED_RESPONSE = {"detail": "Simulation has not completed"}


@extend_schema(
    request=TokenRequestSerializerV1,
    responses={
        200: OpenApiResponse(
            response=TokenResponseSerializerV1,
            description="Access and Refresh Token for authorization",
        ),
        400: OpenApiResponse(
            response=LoginErrorSerializerV1,
            description="Validation error or invalid credentials",
        ),
    },
)
class CustomTokenObtainPairViewV1(TokenObtainPairView):
    pass


@extend_schema(
    description="This request allows a user to obtain a new acces token by passing in their refresh token",
    request=OpenApiRequest(
        examples=[
            OpenApiExample(
                name="Valid Refresh Request",
                value={"refresh": "refresh_token"},
                description="Accepts an refresh token that had been provided before through successful login",
            )
        ],
        request=TokenRefreshRequestSerializerV1,
    ),
    responses={
        200: OpenApiResponse(
            response=TokenRefreshResponseSerializerV1,
            description="New access token for Refreshed Session",
        ),
        400: OpenApiResponse(
            response=LoginErrorSerializerV1,
            description="Request is malformed or invalid",
        ),
        401: OpenApiResponse(
            response=LoginErrorSerializerV1,
            description="Refresh token is invalid",
        ),
    },
)
class CustomTokenRefreshViewV1(TokenRefreshView):
    pass


@extend_schema(
    responses={
        200: OpenApiResponse(response=SimulationExistsResponseSerializerV1, description="Simulation already exists"),
        201: OpenApiResponse(response=SimulationCreateResponseSerializerV1, description="Simulation created and queued for run"),
    }
)
class SimulationStartView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationCreateSerializerV1

    def post(self, request):
        serializer = SimulationCreateSerializerV1(data=request.data)
        serializer.is_valid(raise_exception=True)

        uuid = serializer.validated_data["uuid"]

        params = serializer.validated_data["params"]
        params["seed"] = secrets.randbits(32)

        with transaction.atomic():
            run, created = SimulationRun.objects.get_or_create(
                uuid=uuid, defaults={"user": request.user, "params": params}
            )
            if created:
                run.mark_run_queued()
                def start_worker(run=run):
                    task_result = run_simulation.delay(run.id)
                    run.celery_task_id = task_result.id
                    run.save(update_fields=["celery_task_id"])
                transaction.on_commit(start_worker)
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
        200: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun has been canceled."),
        409: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun is not pending nor running, and can therefore not be canceled."),
    },
)
class SimulationCancelView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, simulation_id=None, simulation_uuid=None):
        if simulation_id is not None:
            run = get_object_or_404(SimulationRun, id=simulation_id)
        elif simulation_uuid is not None:
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
        200: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun has been queued to be paused."),
        409: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun is not running, and can therefore not be paused."),
    },
)
class SimulationPauseView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, simulation_id=None, simulation_uuid=None):
        if simulation_id is not None:
            run = get_object_or_404(SimulationRun, id=simulation_id)
        elif simulation_uuid is not None:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        self.check_object_permissions(request, run)

        identifiers = {"id": run.id, "uuid": run.uuid}
        if run.status not in (
            SimulationRun.Status.RUNNING,
        ):
            return Response(
                {
                    **identifiers,
                    "detail": "The SimulationRun is not running, and can therefore not be paused.",
                },
                status=409,
            )
        run.pause_requested = True
        run.save(update_fields=['pause_requested'])
        return Response(
            {**identifiers, "detail": "The SimulationRun has been queued to be paused."},
            status=200,
        )
    
@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun has been queued to be resumed."),
        409: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun is not paused/canceled/failed OR a resume has already been queued OR no checkpoint state was saved from where it can be resumed"),
    },
)
class SimulationResumeView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, simulation_id=None, simulation_uuid=None):
        with transaction.atomic():
            if simulation_id is not None:
                run = get_object_or_404(SimulationRun.objects.select_for_update(), id=simulation_id)
            elif simulation_uuid is not None:
                run = get_object_or_404(SimulationRun.objects.select_for_update(), uuid=simulation_uuid)
            else:
                return Response({"detail": "No identifier provided."}, status=400)

            self.check_object_permissions(request, run)

            identifiers = {"id": run.id, "uuid": run.uuid}
            if run.queued_for in (SimulationRun.Queued.RESUME,):
                return Response(
                    {
                        **identifiers,
                        "detail": "The resume of the SimulationRun has already been queued.",
                    },
                    status=409,
                )

            if run.status not in (
                SimulationRun.Status.PAUSED,
                SimulationRun.Status.CANCELED,
                SimulationRun.Status.FAILED
            ):
                return Response(
                    {
                        **identifiers,
                        "detail": "The SimulationRun has not been paused, cancelled or failed, and can therefore not be resumed.",
                    },
                    status=409,
                )
            
            if run.checkpoint_state is None:
                return Response(
                    {
                        **identifiers,
                        "detail": "The SimulationRun has not been saved on a checkpoint state, and can therefore not be resumed.",
                    },
                    status=409,
                )
            
            run.mark_resume_queued()
            def start_worker(run = run):
                task_result = run_simulation.delay(run.id)
                run.celery_task_id = task_result.id
                run.save(update_fields=["celery_task_id"])
            transaction.on_commit(start_worker)
        return Response(
            {**identifiers, "detail": "The SimulationRun has been queued to be resumed."},
            status=200,
        )

@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun has been deleted."),
        409: OpenApiResponse(response=SimulationActionResponseSerializerV1, description="The SimulationRun has not finished, and can therefore not be deleted. Cancel the simulation first."),
    },
)
class SimulationDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def delete(self, request, simulation_id=None, simulation_uuid=None):
        if simulation_id is not None:
            run = get_object_or_404(SimulationRun, id=simulation_id)
        elif simulation_uuid is not None:
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


@extend_schema(
    responses={
        200: OpenApiResponse(response=SimulationStatusSerializerV1, description="Detailed Information on a simulation run"),
    }
)
class SimulationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationStatusSerializerV1

    def get(self, request, id=None, simulation_uuid=None):
        if id is not None:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid is not None:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        self.check_object_permissions(request, run)
        serializer = SimulationStatusSerializerV1(run)
        return Response(serializer.data)


@extend_schema(
    responses={
        200: OpenApiResponse(response=SimulationErrorSerializerV1, description="Error information if the simulation run has failed"),
        409: OpenApiResponse(response=DetailSerializer, description="Simulation has not failed."),
    }
)
class SimulationErrorView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationErrorSerializerV1

    def get(self, request, id=None, simulation_uuid=None):
        if id is not None:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid is not None:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        if run.status != SimulationRun.Status.FAILED:
            return Response(
                NOT_FAILED_RESPONSE,
                status=status.HTTP_409_CONFLICT,
            )
        serializer = SimulationErrorSerializerV1(run)
        return Response(serializer.data, status=200)


@extend_schema(
    responses={
        200: OpenApiResponse(response=SimulationResultSerializerV1, description="The results of a completed simulation run"),
        409: OpenApiResponse(response=DetailSerializer, description="Simulation has not completed."),
    }
)
class SimulationResultView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationResultSerializerV1

    def get(self, request, id=None, simulation_uuid=None):
        if id is not None:
            run = get_object_or_404(SimulationRun, id=id)
        elif simulation_uuid is not None:
            run = get_object_or_404(SimulationRun, uuid=simulation_uuid)
        else:
            return Response({"detail": "No identifier provided."}, status=400)

        if run.status != SimulationRun.Status.FINISHED:
            return Response(
                NOT_COMPLETED_RESPONSE,
                status=status.HTTP_409_CONFLICT,
            )
        result = get_object_or_404(SimulationResults, run__id=run.id)
        serializer = SimulationResultSerializerV1(result)
        return Response(serializer.data, status=200)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="iterations", type={"type": "number", "maximum": 1e50, "minimum": 1}
        ),
        OpenApiParameter(
            name="iterations_min",
            type={"type": "number", "maximum": 1e50, "minimum": 1},
        ),
        OpenApiParameter(
            name="iterations_max",
            type={"type": "number", "maximum": 1e50, "minimum": 1},
        ),
        OpenApiParameter(
            name="cat_amount", type={"type": "number", "maximum": 1e50, "minimum": 1}
        ),
        OpenApiParameter(
            name="cat_amount_min",
            type={"type": "number", "maximum": 1e50, "minimum": 1},
        ),
        OpenApiParameter(
            name="cat_amount_max",
            type={"type": "number", "maximum": 1e50, "minimum": 1},
        ),
        OpenApiParameter(
            name="node_amount", type={"type": "number", "maximum": 1e50, "minimum": 1}
        ),
        OpenApiParameter(
            name="node_amount_min",
            type={"type": "number", "maximum": 1e50, "minimum": 1},
        ),
        OpenApiParameter(
            name="node_amount_max",
            type={"type": "number", "maximum": 1e50, "minimum": 1},
        ),
        OpenApiParameter(
            name="user", type={"type": "number", "maximum": 1e18, "minimum": 1}
        ),
        OpenApiParameter(
            name="ordering",
            type=str,
            location=OpenApiParameter.QUERY,
            description='Field to order by. Prefix with "-" for descending.',
            enum=[
                "created_at",
                "-created_at",
                "iterations",
                "-iterations",
                "cat_amount",
                "-cat_amount",
                "node_amount",
                "-node_amount",
            ],
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Page number within the paginated result set.",
            required=False,
            default=1,
        ),
        OpenApiParameter(
            name="page_size",
            type={"type": "integer", "maximum": 100},
            location=OpenApiParameter.QUERY,
            description="Number of results per page (max 100)",
            required=False,
            default=10,
        ),
    ],
    responses={
        200: OpenApiResponse(response=SimulationStatusSerializerV1,description= "Returns a list of simulations"),
    },
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
