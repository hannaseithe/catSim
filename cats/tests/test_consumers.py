from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
import pytest
from cats.routing import websocket_urlpatterns
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_consumer(create_user,auth_client_with_access_v1, create_simulation):
    user = await sync_to_async(create_user)(email="test1@email.com",password="test1password")
    run = await sync_to_async(create_simulation)(user=user)
    
    #Connect
    communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), f"events/{run.id}/")
    connected, subprotocol = await communicator.connect()
    assert connected

    # Authenticate
    _, access_token = await sync_to_async(auth_client_with_access_v1)(user=user, password="test1password")
    await communicator.send_json_to({"access": access_token})
    
    #Send event
    await channel_layer.group_send(
            f"run_{run.id}",
            {
                "type": "simulation_event",
                "message": {"event_type": "TEST_EVENT", "content": {"test": "some content"}},
            },
    )
    response = await communicator.receive_json_from()
    assert isinstance(response["message"], dict)
    assert response["message"]["event_type"] == "TEST_EVENT"

    await communicator.disconnect() 