from django.urls import reverse

from cats.api.serializers import SimulationStatusSerializer


def test_pagination(create_user, create_simulation_list, auth_client_with_refresh):
    user = create_user(email="test1@email.com",password="test1password")
    sim_list = create_simulation_list(user = user, number_of_sims=25)

    auth_client, _ = auth_client_with_refresh(user=user, password="test1password")
    url = reverse("simulation-list")
    response = auth_client.get(url, {"page_size": 10, "page": 2})

    sims = response.data.get("results")

    assert response.data.get("count") == 25, "Count field does not equal 25"
    assert response.data.get("next") is not None, "next field not there"
    assert response.data.get("previous") is not None, "previous field not there"
    assert len(sims) == 10, "Length of returned list is not 10"
    assert sims[0] == SimulationStatusSerializer(sim_list[10]).data, "First returned Sim does not equal the 11th created Sim"