from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"events/(?P<run_id>\d+)/$", consumers.SimulationConsumer.as_asgi()),
]