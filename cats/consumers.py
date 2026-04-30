import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import CustomUser
from cats.models import SimulationRun


class SimulationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.run_id = self.scope["url_route"]["kwargs"]["run_id"]
        self.group_name = f"run_{self.run_id}"
        self.authenticated = False
        
        await self.channel_layer.group_add(
            self.group_name, self.channel_name
        )

    async def receive(self, text_data):
        if self.authenticated:
            return
        data = json.loads(text_data)
        token_string = data["access"]
        try: 
            token = AccessToken(token_string)
            user = await database_sync_to_async(CustomUser.objects.get)(id=token["user_id"])
            run = await database_sync_to_async(SimulationRun.objects.get)(id=self.run_id)
            if not (user.is_staff or run.user_id == user.id):
                await self.channel_layer.group_discard(
                    self.group_name, self.channel_name
                )
                await self.close()
            else:
                self.authenticated = True
            
        except (TokenError, CustomUser.DoesNotExist, SimulationRun.DoesNotExist):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )
            await self.close() 
        
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name, self.channel_name
        )

    async def simulation_event(self, event):
        if not self.authenticated:
            return
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))