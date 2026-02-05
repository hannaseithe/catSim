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

def test_filter_by_created_after(auth_client_with_refresh, create_user, create_simulation_list):
    before_creation = datetime.now()
    before_creation_iso = before_creation.isoformat()

    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    after_creation = datetime.now()
    after_creation_iso = after_creation.isoformat()

    auth_client, _ = auth_client_with_refresh(user=user, password="test1password")

    url = reverse("simulation-list")
    response1 = auth_client.get(url, {"created_after": before_creation_iso})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0] == SimulationStatusSerializer(sim_list[0]).data, "First Simulation of List response is different from first simulation of list in memory"

    response2 = auth_client.get(url, {"created_after": after_creation_iso})
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data
    assert len(sims) == 0, "Length of response list is not 0"

def test_filter_by_user(auth_client_with_refresh, create_user, create_superuser, create_simulation_list):

    user1 = create_user(email="test1@email.com",password="test1password")
    user2 = create_user(email="test2@email.com",password="test2password")
    superuser = create_superuser()

    sim_list1 = create_simulation_list(user = user1)
    sim_list2 = create_simulation_list(user = user2)


    auth_client1, _ = auth_client_with_refresh(user=user1, password="test1password")
    auth_client2, _ = auth_client_with_refresh(user=superuser, password="supertestpassword")

    url = reverse("simulation-list")
    response1 = auth_client1.get(url, {"user": user1.id})
    response2 = auth_client2.get(url, {"user": user1.id})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0] == SimulationStatusSerializer(sim_list1[0]).data, "First Simulation of List response is different from first simulation of list in memory"

    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0] == SimulationStatusSerializer(sim_list1[0]).data, "First Simulation of List response is different from first simulation of list in memory"

    print(user2.id)
    print(superuser.id)
    response3 = auth_client1.get(url, {"user": user2.id})
    response4 = auth_client2.get(url, {"user": user2.id})

    assert response3.status_code == 200, "response status code not 200"
    sims = response3.data
    assert len(sims) == 0, "Length of response list is not 0"

    assert response4.status_code == 200, "response status code not 200"
    sims = response4.data
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0] == SimulationStatusSerializer(sim_list2[0]).data, "First Simulation of List response is different from first simulation of list in memory"
