import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Run


class RunMetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.run_id = self.scope['url_route']['kwargs']['run_id']
        user = self.scope['user']

        if not user or not user.is_authenticated:
            await self.close()
            return

        if not await self._user_owns_run(user, self.run_id):
            await self.close()
            return

        self.group_name = f'run_{self.run_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def metric_logged(self, event):
        await self.send(text_data=json.dumps(event['metric']))

    @database_sync_to_async
    def _user_owns_run(self, user, run_id):
        return Run.objects.filter(id=run_id, experiment__user=user).exists()
