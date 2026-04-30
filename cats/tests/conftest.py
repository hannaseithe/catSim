from datetime import datetime, date, time
from typing import Callable
import uuid as uuid_p
from django.utils import timezone
from django.urls import reverse
from django.utils.timezone import make_aware
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
def create_superuser(db):
    def _create_superuser(email="supertest@email.com", password="supertestpassword"):
        return CustomUser.objects.create_superuser(email=email,password=password)
    return _create_superuser 

@pytest.fixture
def create_simulation(db, create_user) -> Callable[[], SimulationRun]:
    def _create_simulation(created_at=None,user=None, params=None, uuid= None, status=None, checkpoint_state=None) -> SimulationRun:
        if not uuid:
            uuid=uuid_p.uuid4()
        if not created_at:
            created_at = timezone.now()
        elif isinstance(created_at,date):
            created_at = make_aware(datetime.combine(created_at, time.min))
        if not user:
            user = create_user()
        if params is None:
            params = {"iterations": 10}
        if status is None:
            status = SimulationRun.Status.PENDING
        return SimulationRun.objects.create(params = params, user=user, created_at=created_at, uuid=uuid, status=status, checkpoint_state=checkpoint_state)
    return _create_simulation

@pytest.fixture
def create_simulation_list(db,create_user, create_simulation):
    def _create_simulation_list(user=None, number_of_sims=5):
        if not user:
            user = create_user()
        return [create_simulation(user=user, params={"iterations":10*i, "cat_amount":3*i, "node_amount": 5*i}) for i in range(1,number_of_sims +1)]
    return _create_simulation_list

@pytest.fixture
def create_results(db, create_simulation, create_user):
    def _create_results(user=None, run=None, metrics=None):
        if metrics is None:
            metrics = DUMMY_METRICS
        if user is None:
            user = create_user()
        if run is None:
            run = create_simulation(user=user, uuid=uuid_p.uuid4())
        return SimulationResults.objects.create(run = run, metrics = metrics)
    return _create_results

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def auth_client_with_refresh_unversioned(db):
    def _login(user:CustomUser, password):
        api_client = APIClient()
        url = reverse('token-obtain-pair')
        response = api_client.post(url,{"email": user.email, "password":password}, format="json")
        access_token = response.data["access"]
        refresh_token = response.data["refresh"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return api_client,refresh_token
    return _login

@pytest.fixture
def auth_client_with_refresh_v1(db):
    def _login(user:CustomUser, password):
        api_client = APIClient()
        url = reverse('v1-token-obtain-pair')
        response = api_client.post(url,{"email": user.email, "password":password}, format="json")
        access_token = response.data["access"]
        refresh_token = response.data["refresh"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return api_client,refresh_token
    return _login

@pytest.fixture
def auth_client_with_access_v1(db):
    def _login(user:CustomUser, password):
        api_client = APIClient()
        url = reverse('v1-token-obtain-pair')
        response = api_client.post(url,{"email": user.email, "password":password}, format="json")
        access_token = response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return api_client,access_token
    return _login

@pytest.fixture
def valid_create_sim_args():
    return {
        "uuid": uuid_p.uuid4(),
        "params": {
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
    }

