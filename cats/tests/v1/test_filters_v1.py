from datetime import datetime, timedelta
from django.urls import reverse
from django.utils import timezone

from cats.api.v1.serializers import SimulationStatusSerializerV1


def test_filter_by_status(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"status": "pending"})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list[-1]).data.get("id"), "First returned Simulation is different from first created simulation"

    response2 = auth_client.get(url, { "status": "finished"})
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data.get("results")
    assert len(sims) == 0, "Length of response list is not 0"

def test_filter_by_created_at_max(auth_client_with_refresh_v1, create_user, create_simulation_list):
    before_creation = timezone.now()
    before_creation_iso = before_creation.isoformat()

    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    after_creation = timezone.now()
    after_creation_iso = after_creation.isoformat()

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"created_at_max": after_creation_iso})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list[-1]).data.get("id"), "First returned Simulation is different from first created simulation"

    response2 = auth_client.get(url, {"created_at_max": before_creation_iso})
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data.get("results")
    assert len(sims) == 0, "Length of response list is not 0"

def test_filter_by_created_at_with_date(auth_client_with_refresh_v1, create_user, create_simulation):

    user = create_user(email="test1@email.com",password="test1password")
    
    today = datetime.today()
    past_date = today + timedelta(days=-1)
    future_date = today + timedelta(days=1)
    sim1 = create_simulation(user = user, created_at=past_date)
    sim2 = create_simulation(user=user, created_at=today)
    sim3 =  create_simulation(user=user, created_at=future_date)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"created_at_min": today.isoformat()})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 1, "Length of response list is not 1"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim3).data.get("id"), "First returned Simulation is different from third created simulation"

    response2 = auth_client.get(url, {"created_at_max": today.isoformat()})
    
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data.get("results")
    assert len(sims) == 2, "Length of response list is not 2"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim2).data.get("id"), "First returned Simulation is different from second created simulation"
    assert sims[1].get("id") == SimulationStatusSerializerV1(sim1).data.get("id"), "Second returned Simulation is different from first created simulation"

def test_filter_by_created_at_min(auth_client_with_refresh_v1, create_user, create_simulation_list):
    before_creation = timezone.now()
    before_creation_iso = before_creation.isoformat()

    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    after_creation = timezone.now()
    after_creation_iso = after_creation.isoformat()

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")

    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"created_at_min": before_creation_iso})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list[-1]).data.get("id"), "First returned Simulation is different from first created simulation"

    response2 = auth_client.get(url, {"created_at_min": after_creation_iso})
    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data.get("results")
    assert len(sims) == 0, "Length of response list is not 0"

def test_filter_by_user(auth_client_with_refresh_v1, create_user, create_superuser, create_simulation_list):

    user1 = create_user(email="test1@email.com",password="test1password")
    user2 = create_user(email="test2@email.com",password="test2password")
    superuser = create_superuser()

    sim_list1 = create_simulation_list(user = user1)
    sim_list2 = create_simulation_list(user = user2)


    auth_client1, _ = auth_client_with_refresh_v1(user=user1, password="test1password")
    auth_client2, _ = auth_client_with_refresh_v1(user=superuser, password="supertestpassword")

    url = reverse("v1-simulation-list")
    response1 = auth_client1.get(url, {"user": user1.id})
    response2 = auth_client2.get(url, {"user": user1.id})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list1[-1]).data.get("id"), "First returned Simulation is different from first created simulation in first batch"

    assert response2.status_code == 200, "response status code not 200"
    sims = response2.data.get("results")
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list1[-1]).data.get("id"), "First returned Simulation is different from first created simulation in first batch"

    response3 = auth_client1.get(url, {"user": user2.id})
    response4 = auth_client2.get(url, {"user": user2.id})

    assert response3.status_code == 200, "response status code not 200"
    sims = response3.data.get("results")
    assert len(sims) == 0, "Length of response list is not 0"

    assert response4.status_code == 200, "response status code not 200"
    sims = response4.data.get("results")
    assert len(sims) == 5, "Length of response list is not 5"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list2[-1]).data.get("id"), "First returned Simulation is different from first created simulation in second batch"

def test_filter_by_iterations(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"iterations": 10})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 1, "Length of response list is not 1"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[0]).data.get("id"), "First returned Simulation is different from first created simulation"

def test_filter_by_iterations_max(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"iterations_max": 20})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 2, "Length of response list is not 2"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[0]).data.get("id"), "First returned Simulation is different from first created simulation"

def test_filter_by_iterations_min(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"iterations_min": 20})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 4, "Length of response list is not 4"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[1]).data.get("id"), "First returned Simulation is different from second created simulation"

def test_filter_by_cat_amounts(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"cat_amount": 6})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 1, "Length of response list is not 1"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[1]).data.get("id"), "First returned Simulation is different from second created simulation"

def test_filter_by_cat_amounts_max(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"cat_amount_max": 6})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 2, "Length of response list is not 2"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[0]).data.get("id"), "First returned Simulation is different from first created simulation"

def test_filter_by_cat_amounts_min(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"cat_amount_min": 6})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 4, "Length of response list is not 4"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[1]).data.get("id"), "First Simulation of List response is different from second simulation of list in memory"

def test_filter_by_node_amounts(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"node_amount": 10})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 1, "Length of response list is not 1"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[1]).data.get("id"), "First Simulation of List response is different from first simulation of list in memory"

def test_filter_by_node_amounts_max(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"node_amount_max": 10})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 2, "Length of response list is not 2"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[0]).data.get("id"), "First Simulation of List response is different from first simulation of list in memory"

def test_filter_by_node_amounts_min(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response1 = auth_client.get(url, {"node_amount_min": 10})
    
    assert response1.status_code == 200, "response status code not 200"
    sims = response1.data.get("results")
    assert len(sims) == 4, "Length of response list is not 4"
    assert sims[-1].get("id") == SimulationStatusSerializerV1(sim_list[1]).data.get("id"), "First Simulation of List response is different from first simulation of list in memory"

def test_ordering(auth_client_with_refresh_v1, create_user, create_simulation_list):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list1 = create_simulation_list(user = user)
    sim_list2 = create_simulation_list(user = user)

    auth_client, _ = auth_client_with_refresh_v1(user=user, password="test1password")
    url = reverse("v1-simulation-list")
    response = auth_client.get(url, {"ordering": "iterations"})
    sims = response.data.get("results")

    assert len(sims) == 10 , "The returned list is not 10 items long"
    assert sims[0].get("id") == SimulationStatusSerializerV1(sim_list1[0]).data.get("id"), "First returned Simulation does not equal first sim of first created batch"
    assert sims[1].get("id") == SimulationStatusSerializerV1(sim_list2[0]).data.get("id"), "Second returned Simulation does not equal first sim of second created batch"