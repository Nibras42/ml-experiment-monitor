import asyncio

import factory
import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.experiments.models import Experiment, Run
from apps.experiments.routing import websocket_urlpatterns
from apps.experiments.services import log_metric
from apps.users.middleware import JWTAuthMiddleware

User = get_user_model()

application = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'ws_user{n}@example.com')

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password('TestPass123!')
        self.save()


class ExperimentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Experiment

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'WS Experiment {n}')


class RunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Run

    experiment = factory.SubFactory(ExperimentFactory)
    name = factory.Sequence(lambda n: f'WS Run {n}')


def run_async(coro):
    return asyncio.run(coro)


@pytest.mark.django_db(transaction=True)
class TestRunMetricsConsumer:
    def test_connect_with_valid_token_succeeds(self):
        user = UserFactory()
        run = RunFactory(experiment=ExperimentFactory(user=user))
        token = str(AccessToken.for_user(user))

        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/runs/{run.id}/?token={token}')
            connected, _ = await communicator.connect()
            assert connected
            await communicator.disconnect()

        run_async(scenario())

    def test_connect_without_token_rejected(self):
        run = RunFactory()

        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/runs/{run.id}/')
            connected, _ = await communicator.connect()
            assert not connected

        run_async(scenario())

    def test_connect_with_invalid_token_rejected(self):
        run = RunFactory()

        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/runs/{run.id}/?token=garbage')
            connected, _ = await communicator.connect()
            assert not connected

        run_async(scenario())

    def test_connect_to_other_users_run_rejected(self):
        owner = UserFactory()
        intruder = UserFactory()
        run = RunFactory(experiment=ExperimentFactory(user=owner))
        token = str(AccessToken.for_user(intruder))

        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/runs/{run.id}/?token={token}')
            connected, _ = await communicator.connect()
            assert not connected

        run_async(scenario())

    def test_receives_broadcast_when_metric_logged(self):
        user = UserFactory()
        run = RunFactory(experiment=ExperimentFactory(user=user))
        token = str(AccessToken.for_user(user))

        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/runs/{run.id}/?token={token}')
            connected, _ = await communicator.connect()
            assert connected

            await database_sync_to_async(log_metric)(run=run, name='loss', value=0.5, step=1)

            response = await communicator.receive_json_from()
            assert response['name'] == 'loss'
            assert response['value'] == 0.5
            assert response['step'] == 1

            await communicator.disconnect()

        run_async(scenario())
