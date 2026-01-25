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
def login(db):
    def _login(api_client:APIClient, user:CustomUser, password):
        url = reverse('token_obtain_pair')
        response = api_client.post(url,{"email": user.email, "password":password}, format="json")
        access_token = response.data["access"]
        refresh_token = response.data["refresh"]
        return (access_token,refresh_token)
    return _login

