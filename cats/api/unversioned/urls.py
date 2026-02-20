from django.urls import path
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    SimulationDetailView,
    SimulationErrorView,
    SimulationListView,
    SimulationResultView,
    SimulationStartView,
)

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path(
        "simulations/start/", SimulationStartView.as_view(), name="simulation-start"
    ),
    path(
        "simulations/<int:id>/results/",
        SimulationResultView.as_view(),
        name="simulation-get-results-id",
    ),
    path(
        "simulations/<int:id>/error/",
        SimulationErrorView.as_view(),
        name="simulation-get-error-id",
    ),
    path(
        "simulations/<int:id>/",
        SimulationDetailView.as_view(),
        name="simulation-get-detail-id",
    ),
    path(
        "simulations/",
        SimulationListView.as_view(),
        name="simulation-list",
    ),
]
