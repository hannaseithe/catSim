from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import (
    CustomTokenObtainPairViewV1,
    CustomTokenRefreshViewV1,
    SimulationCancelView,
    SimulationDeleteView,
    SimulationDetailView,
    SimulationErrorView,
    SimulationListView,
    SimulationPauseView,
    SimulationResultView,
    SimulationResumeView,
    SimulationStartView,
)


urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('token/', CustomTokenObtainPairViewV1.as_view(), name='v1-token-obtain-pair'),
    path('token/refresh/', CustomTokenRefreshViewV1.as_view(), name='v1-token-refresh'),
    path(
        "simulations/start/", SimulationStartView.as_view(), name="v1-simulation-start"
    ),
    path(
        "simulations/<int:simulation_id>/cancel/",
        SimulationCancelView.as_view(),
        name="v1-simulation-cancel-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/cancel/",
        SimulationCancelView.as_view(),
        name="v1-simulation-cancel-uuid",
    ),
    path(
        "simulations/<int:simulation_id>/pause/",
        SimulationPauseView.as_view(),
        name="v1-simulation-pause-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/pause/",
        SimulationPauseView.as_view(),
        name="v1-simulation-pause-uuid",
    ),
      path(
        "simulations/<int:simulation_id>/resume/",
        SimulationResumeView.as_view(),
        name="v1-simulation-resume-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/resume/",
        SimulationResumeView.as_view(),
        name="v1-simulation-resume-uuid",
    ),
    path(
        "simulations/<int:simulation_id>/delete/",
        SimulationDeleteView.as_view(),
        name="v1-simulation-delete-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/delete/",
        SimulationDeleteView.as_view(),
        name="v1-simulation-delete-uuid",
    ),
    path(
        "simulations/<int:id>/results/",
        SimulationResultView.as_view(),
        name="v1-simulation-get-results-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/results/",
        SimulationResultView.as_view(),
        name="v1-simulation-get-results-uuid",
    ),
    path(
        "simulations/<int:id>/error/",
        SimulationErrorView.as_view(),
        name="v1-simulation-get-error-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/error/",
        SimulationErrorView.as_view(),
        name="v1-simulation-get-error-uuid",
    ),
    path(
        "simulations/<int:id>/",
        SimulationDetailView.as_view(),
        name="v1-simulation-get-detail-id",
    ),
    path(
        "simulations/<uuid:simulation_uuid>/",
        SimulationDetailView.as_view(),
        name="v1-simulation-get-detail-uuid",
    ),
    path(
        "simulations/",
        SimulationListView.as_view(),
        name="v1-simulation-list",
    ),
]
