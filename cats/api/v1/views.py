from datetime import timedelta
import logging
import secrets
from django.core.cache import cache
from django.db import transaction
from django.db.models import (
    F,
    Q,
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    IntegerField,
    OuterRef,
    Subquery,
)
from django.db.models.functions import Cast, Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_project.celery import app
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    OpenApiParameter,
    OpenApiRequest,
    inline_serializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
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
from cats.events import Action, QueueEvent, Source
from cats.models import SimulationEvent, SimulationResults, SimulationRun
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
        200: OpenApiResponse(
            response=SimulationExistsResponseSerializerV1,
            description="Simulation already exists",
        ),
        201: OpenApiResponse(
            response=SimulationCreateResponseSerializerV1,
            description="Simulation created and queued for run",
        ),
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
                run.mark_run_queued(source=Source.API)

                def start_worker(run=run):
                    task_result = run_simulation.delay(run.id)
                    run.celery_task_id = task_result.id
                    run.save(update_fields=["celery_task_id"])

                    logger.info(
                        f"Queued simulation {run.id} for RUN with seed {run.params['seed']} and parameters: {run.params}"
                    )

                transaction.on_commit(start_worker)

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
        200: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun has been canceled.",
        ),
        409: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun is not pending nor running, and can therefore not be canceled.",
        ),
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
        run.cancel(source=Source.API)
        return Response(
            {**identifiers, "detail": "The SimulationRun has been canceled."},
            status=200,
        )


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun has been queued to be paused.",
        ),
        409: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun is not running, and can therefore not be paused.",
        ),
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
        if run.status not in (SimulationRun.Status.RUNNING,):
            return Response(
                {
                    **identifiers,
                    "detail": "The SimulationRun is not running, and can therefore not be paused.",
                },
                status=409,
            )
        run.pause_requested = True
        run.save(update_fields=["pause_requested"])

        logger.info(f"Queued simulation {run.id} for PAUSE")
        event = QueueEvent(source=Source.API, action=Action.PAUSE)
        SimulationEvent.emit_event(
            run=run, event_type=SimulationEvent.Type.QUEUE, content=event
        )
        return Response(
            {
                **identifiers,
                "detail": "The SimulationRun has been queued to be paused.",
            },
            status=200,
        )


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun has been queued to be resumed.",
        ),
        409: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun is not paused/canceled/failed OR a resume has already been queued OR no checkpoint state was saved from where it can be resumed",
        ),
    },
)
class SimulationResumeView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, simulation_id=None, simulation_uuid=None):
        with transaction.atomic():
            if simulation_id is not None:
                run = get_object_or_404(
                    SimulationRun.objects.select_for_update(), id=simulation_id
                )
            elif simulation_uuid is not None:
                run = get_object_or_404(
                    SimulationRun.objects.select_for_update(), uuid=simulation_uuid
                )
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
                SimulationRun.Status.FAILED,
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

            run.mark_resume_queued(source=Source.API)

            def start_worker(run=run):
                task_result = run_simulation.delay(run.id)
                run.celery_task_id = task_result.id
                run.save(update_fields=["celery_task_id"])

                logger.info(f"Queued simulation {run.id} for RESUME")

            transaction.on_commit(start_worker)
        return Response(
            {
                **identifiers,
                "detail": "The SimulationRun has been queued to be resumed.",
            },
            status=200,
        )


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun has been deleted.",
        ),
        409: OpenApiResponse(
            response=SimulationActionResponseSerializerV1,
            description="The SimulationRun has not finished, and can therefore not be deleted. Cancel the simulation first.",
        ),
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
        200: OpenApiResponse(
            response=SimulationStatusSerializerV1,
            description="Detailed Information on a simulation run",
        ),
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
        200: OpenApiResponse(
            response=SimulationErrorSerializerV1,
            description="Error information if the simulation run has failed",
        ),
        409: OpenApiResponse(
            response=DetailSerializer, description="Simulation has not failed."
        ),
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
        200: OpenApiResponse(
            response=SimulationResultSerializerV1,
            description="The results of a completed simulation run",
        ),
        409: OpenApiResponse(
            response=DetailSerializer, description="Simulation has not completed."
        ),
    }
)
class SimulationResultView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = SimulationResultSerializerV1

    def get(self, request, id=None, simulation_uuid=None):
        def query_result(id):

            result = get_object_or_404(SimulationResults, run__id=run.id)
            serializer = SimulationResultSerializerV1(result)
            return serializer.data


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

        data = cache.get_or_set(f"result:{run.id}", lambda: query_result(run), timeout=None)
        return Response(data, status=200)


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
        200: OpenApiResponse(
            response=SimulationStatusSerializerV1,
            description="Returns a list of simulations",
        ),
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


@extend_schema(
    responses={
        200: inline_serializer(
            name="QueueStatusResponse",
            fields={
                "queue_depth": serializers.IntegerField(),
                "avg_waiting_time": serializers.FloatField(allow_null=True),
            }
        )
    }
)
class SimulationQueueStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queue_depth = SimulationRun.objects.filter(queued_for__isnull=False).count()

        def query_avg_waiting_time():
            latest_queue_events = (
                SimulationEvent.objects.filter(
                    run=OuterRef("id"), event_type=SimulationEvent.Type.QUEUE
                )
                .order_by("-logged_at")
                .values("logged_at")[:1]
            )
            result =  (
                SimulationRun.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=1)
                )
                .annotate(latest_queued_at=Subquery(latest_queue_events))
                .annotate(
                    waiting_time=ExpressionWrapper(
                        F("started_at") - F("latest_queued_at"),
                        output_field=DurationField(),
                    )
                )
                .aggregate(avg_waiting_time=Avg("waiting_time"))["avg_waiting_time"]
            )
            return result.total_seconds() if result else None

        avg_waiting_time = cache.get_or_set("queue_status:avg_waiting_time", lambda: query_avg_waiting_time(), timeout=60)


        return Response(
            {
                "queue_depth": queue_depth,
                "avg_waiting_time": avg_waiting_time,
            },
            status=200,
        )


@extend_schema(
    responses={
        200: inline_serializer(
            name="HealthResponse",
            fields={
                "success_rate": serializers.FloatField(allow_null=True),
                "failure_per_run": serializers.FloatField(allow_null=True),
                "resume_per_run": serializers.FloatField(allow_null=True),
                "worker_ok": serializers.BooleanField(),
            }
        )
    }
)
class SimulationHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        def query_success_rate():
            result = SimulationRun.objects.filter(
                Q(created_at__gte=timezone.now() - timedelta(days=1))
            ).aggregate(
                finished=Count("id", filter=Q(status=SimulationRun.Status.FINISHED)),
                failed=Count("id", filter=Q(status=SimulationRun.Status.FAILED)),
            )
            return (
                0
                if result["failed"] == 0 and result["finished"] == 0
                else result["finished"] / (result["finished"] + result["failed"])
            )
        success_rate = cache.get_or_set("health:success_rate", lambda: query_success_rate(), timeout=300)

        def query_failure_per_run():
            failed_amount = (
                SimulationEvent.objects.filter(run=OuterRef("id"), event_type=SimulationEvent.Type.STATE_TRANSITION, content__new_status=SimulationRun.Status.FAILED)
                .values('run').annotate(c=Count('id')).values('c')[:1] 
            )
            result = (
                SimulationRun.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=1)
                )
                .annotate(failed_amount=Coalesce(Subquery(failed_amount), 0))
                .aggregate(avg_failed=Avg("failed_amount"))["avg_failed"]
            ) 
            return result if result else 0

        failure_per_run = cache.get_or_set("health:failure_per_run", lambda: query_failure_per_run(), timeout=300)

        def query_resume_per_run():
            resume_amount = (
                SimulationEvent.objects.filter(run=OuterRef("id"), event_type=SimulationEvent.Type.QUEUE, content__action=Action.RESUME)
                .values('run').annotate(c=Count('id')).values('c')[:1] 
            )
            result =  (
                SimulationRun.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=1)
                )
                .annotate(resumed_amount=Coalesce(Subquery(resume_amount),0))
                .aggregate(avg_resumed=Avg("resumed_amount"))["avg_resumed"]
            )
            return result if result else 0
        
        resume_per_run = cache.get_or_set("health:resume_per_run", lambda: query_resume_per_run(), timeout=300)

        worker_ok = bool(app.control.inspect(timeout=0.1).ping())

        return Response({
            "success_rate": success_rate,
            "failure_per_run": failure_per_run,
            "resume_per_run": resume_per_run,
            "worker_ok": worker_ok
        }, status=200)


