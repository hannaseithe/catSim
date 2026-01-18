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
        "api/simulations/start/", SimulationStartView.as_view(), name="simulation-start"
    ),
    path(
        "api/simulations/<int:id>/results/",
        SimulationResultView.as_view(),
        name="simulation-get-results",
    ),
    path(
        "api/simulations/<int:id>/error/",
        SimulationErrorView.as_view(),
        name="simulation-get-error",
    ),
    path(
        "api/simulations/<int:id>",
        SimulationDetailView.as_view(),
        name="simulation-get-detail",
    ),
    path(
        "api/simulations/",
        SimulationListView.as_view(),
        name="simulation-list",
    ),
]
