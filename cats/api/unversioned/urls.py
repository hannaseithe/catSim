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
        "simulations/start/", SimulationStartView.as_view(), name="simulation-start"
    ),
    path(
        "simulations/<int:id>/results/",
        SimulationResultView.as_view(),
        name="simulation-get-results",
    ),
    path(
        "simulations/<int:id>/error/",
        SimulationErrorView.as_view(),
        name="simulation-get-error",
    ),
    path(
        "simulations/<int:pk>/",
        SimulationDetailView.as_view(),
        name="simulation-get-detail",
    ),
    path(
        "simulations/",
        SimulationListView.as_view(),
        name="simulation-list",
    ),
]
