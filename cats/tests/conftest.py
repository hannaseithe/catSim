from django.urls import reverse
import pytest
from accounts.models import CustomUser
from cats.models import SimulationResults, SimulationRun
from rest_framework.test import APIClient

DUMMY_METRICS = {"foo": "bar"}

@pytest.fixture
def create_user(db):
    def _create_user(email="test@email.com", password="testpassword"):
        return CustomUser.objects.create_user(email=email,password=password)
    return _create_user

@pytest.fixture
def create_simulation(db, create_user):
    def _create_simulation(user=None, params=None):
        if not user:
            user = create_user()
        if params is None:
            params = {"iterations": 10}
        return SimulationRun.objects.create(params = params, user=user)
    return _create_simulation

@pytest.fixture
def create_simulation_list(db,create_user, create_simulation):
    def _create_simulation_list(user=None, number_of_lists=5):
        if not user:
            user = create_user()
        return [create_simulation(user=user, params={"iterations":10*i}) for i in range(1,number_of_lists +1)]
    return _create_simulation_list

@pytest.fixture
def create_results(db, create_simulation, create_user):
    def _create_results(user=None, run=None, metrics=None):
        if metrics is None:
            metrics = DUMMY_METRICS
        if user is None:
            user = create_user()
        if run is None:
            run = create_simulation(user=user)
        return SimulationResults.objects.create(run = run, metrics = metrics)
    return _create_results

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def auth_client_with_refresh(db, api_client):
    def _login(user:CustomUser, password):
        url = reverse('token_obtain_pair')
        response = api_client.post(url,{"email": user.email, "password":password}, format="json")
        access_token = response.data["access"]
        refresh_token = response.data["refresh"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return api_client,refresh_token
    return _login

@pytest.fixture
def valid_create_sim_args():
    return {
        "iterations": 100,
        "cat_amount": 10,
        "node_amount": 60,
        "mean_edges": 4,
        "var_edges": 1.0,
        "mean_aggressive": 0.0,
        "var_aggressive": 0.1,
        "mean_laziness": 0.5,
        "var_laziness": 0.05,
    }

