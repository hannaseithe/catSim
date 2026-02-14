from django.urls import path
from .views import (
    SimulationDetailView,
    SimulationErrorView,
    SimulationListView,
    SimulationResultView,
    SimulationStartView,
)

urlpatterns = [
    path(
        "simulations/start/", SimulationStartView.as_view(), name="v1-simulation-start"
    ),
    path(
        "simulations/<int:id>/results/",
        SimulationResultView.as_view(),
        name="v1-simulation-get-results",
    ),
    path(
        "simulations/<int:id>/error/",
        SimulationErrorView.as_view(),
        name="v1-simulation-get-error",
    ),
    path(
        "simulations/<int:pk>/",
        SimulationDetailView.as_view(),
        name="v1-simulation-get-detail",
    ),
    path(
        "simulations/",
        SimulationListView.as_view(),
        name="v1-simulation-list",
    ),
]
