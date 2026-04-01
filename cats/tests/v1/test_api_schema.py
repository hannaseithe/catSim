from django.urls import reverse
from django.contrib.auth import get_user_model
import pytest
from rest_framework_simplejwt.tokens import RefreshToken
import schemathesis
from schemathesis.specs.openapi.checks import ignored_auth
from cats.api.v1.serializers import SimulationParamsSerializerV1
from django_project.wsgi import application
from hypothesis import settings, HealthCheck


url = reverse('schema')
schema = (
    schemathesis.openapi.from_wsgi(url, app=application)    
    .exclude(path_regex=r"/api/v1/token/.*")
    .exclude(path_regex=r"/api/token/.*")
    .exclude(path_regex=r"^/api/(?!v1/)")
    .exclude(path_regex=r"/schema/")
)

User = get_user_model()

@pytest.fixture
def auth_headers(db):
    user = User.objects.create_user(
        email="schematestuser@email.com",
        password="password123"
    )
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    return {"Authorization": f"Bearer {access_token}"}


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@schema.parametrize()
def test_api(case, auth_headers, db):
    #we have to monkey_patch the authorization header
    case.headers = {**case.headers, **auth_headers}
    response = case.call(app=application)

    #exclude not specified parameters for list view
    url_list = reverse("v1-simulation-list")
    if response.status_code==200 and case.path == url_list:
        parameters = list(case.operation.iter_parameters())
        if any(key not in parameters for key in case.query.keys()):
            return

    #exclude non_field_errors for start endpoint, which cant be covered through the definition
    url_start = reverse("v1-simulation-start")
    if response.status_code==400 and case.path == url_start:
        if isinstance(case.body, dict) and case.body.get("params") and isinstance(case.body["params"],dict):
            data = case.body["params"]
            serializer = SimulationParamsSerializerV1()
            cat_amount = data.get("cat_amount",serializer.fields["cat_amount"].get_default())
            node_amount = data.get("node_amount",serializer.fields["node_amount"].get_default())
            mean_edges = data.get("mean_edges",serializer.fields["mean_edges"].get_default())
            var_edges = data.get("var_edges", serializer.fields["var_edges"].get_default())


            if isinstance(cat_amount,int) and isinstance(node_amount,int):
                if cat_amount * 3 >= node_amount:
                    return
            if isinstance(mean_edges,(int,float)) and isinstance(node_amount,int):
                if mean_edges * 2 >= node_amount:
                    return
            if isinstance(mean_edges,(int,float)) and isinstance(var_edges,(int,float)):
                if var_edges * 3 >= mean_edges:
                    return
    
    case.validate_response(response, excluded_checks=[ignored_auth])