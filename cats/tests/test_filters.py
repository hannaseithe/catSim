from datetime import datetime
from django.urls import reverse

from cats.api.serializers import SimulationStatusSerializer


def test_filter_by_status(auth_client_with_refresh, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh(user=user, password="test1password")
    url = reverse("simulation-list")
    response1 = auth_client.get(url, {"status": "pending"})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0] == SimulationStatusSerializer(sim_list[0]).data, "First Simulation of List response is different from first simulation of list in memory"

    response2 = auth_client.get(url, { "status": "finished"})
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data
    assert len(sims) == 0, "Length of response list is not 0"

def test_filter_by_created_before(auth_client_with_refresh, create_user, create_simulation_list):
    before_creation = datetime.now()
    before_creation_iso = before_creation.isoformat()

    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    after_creation = datetime.now()
    after_creation_iso = after_creation.isoformat()

    auth_client, _ = auth_client_with_refresh(user=user, password="test1password")

    url = reverse("simulation-list")
    response1 = auth_client.get(url, {"created_before": after_creation_iso})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0] == SimulationStatusSerializer(sim_list[0]).data, "First Simulation of List response is different from first simulation of list in memory"

    response2 = auth_client.get(url, {"created_before": before_creation_iso})
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data
    assert len(sims) == 0, "Length of response list is not 0"
