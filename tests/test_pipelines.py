import factory
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.pipelines.models import Pipeline, PipelineStage

User = get_user_model()


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'pipeline_user{n}@example.com')

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password('TestPass123!')
        self.save()


class PipelineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pipeline

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Pipeline {n}')
    description = 'A test pipeline'


class PipelineStageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PipelineStage

    pipeline = factory.SubFactory(PipelineFactory)
    name = factory.Sequence(lambda n: f'Stage {n}')
    depends_on = factory.LazyFunction(list)
    order = factory.Sequence(lambda n: n)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return c


@pytest.fixture
def pipeline(user):
    return PipelineFactory(user=user)


@pytest.fixture
def stage(pipeline):
    return PipelineStageFactory(pipeline=pipeline)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPipelineModel:
    def test_str(self):
        p = PipelineFactory(name='Training Pipeline')
        assert str(p) == 'Training Pipeline'

    def test_uuid_pk(self):
        p = PipelineFactory()
        assert len(str(p.pk)) == 36

    def test_timestamps(self):
        p = PipelineFactory()
        assert p.created_at is not None
        assert p.updated_at is not None


@pytest.mark.django_db
class TestPipelineStageModel:
    def test_str(self):
        p = PipelineFactory(name='MyPipeline')
        s = PipelineStageFactory(pipeline=p, name='preprocess')
        assert str(s) == 'MyPipeline / preprocess'

    def test_uuid_pk(self):
        s = PipelineStageFactory()
        assert len(str(s.pk)) == 36

    def test_default_status_pending(self):
        s = PipelineStageFactory()
        assert s.status == PipelineStage.Status.PENDING

    def test_default_depends_on_empty(self):
        s = PipelineStageFactory()
        assert s.depends_on == []

    def test_timestamps(self):
        s = PipelineStageFactory()
        assert s.created_at is not None
        assert s.updated_at is not None

    def test_unique_name_per_pipeline(self):
        p = PipelineFactory()
        PipelineStageFactory(pipeline=p, name='step-1')
        with pytest.raises(Exception):
            PipelineStageFactory(pipeline=p, name='step-1')


# ---------------------------------------------------------------------------
# Pipeline endpoints
# ---------------------------------------------------------------------------

PIPELINES_URL = '/api/pipelines/'


def pipeline_url(pk):
    return f'/api/pipelines/{pk}/'


@pytest.mark.django_db
class TestPipelineList:
    def test_list_authenticated(self, auth_client, pipeline):
        response = auth_client.get(PIPELINES_URL)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['name'] == pipeline.name

    def test_list_only_own_pipelines(self, auth_client, user, other_user):
        PipelineFactory(user=user)
        PipelineFactory(user=other_user)
        response = auth_client.get(PIPELINES_URL)
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_list_unauthenticated(self, client):
        response = client.get(PIPELINES_URL)
        assert response.status_code == 401


@pytest.mark.django_db
class TestPipelineCreate:
    def test_create_success(self, auth_client):
        payload = {'name': 'New Pipeline', 'description': 'desc'}
        response = auth_client.post(PIPELINES_URL, payload, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'New Pipeline'
        assert Pipeline.objects.filter(name='New Pipeline').exists()

    def test_create_missing_name(self, auth_client):
        response = auth_client.post(PIPELINES_URL, {'description': 'x'}, format='json')
        assert response.status_code == 400

    def test_create_unauthenticated(self, client):
        response = client.post(PIPELINES_URL, {'name': 'x'}, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestPipelineRetrieve:
    def test_retrieve_success(self, auth_client, pipeline):
        response = auth_client.get(pipeline_url(pipeline.pk))
        assert response.status_code == 200
        assert response.data['id'] == str(pipeline.pk)

    def test_retrieve_unauthenticated(self, client, pipeline):
        response = client.get(pipeline_url(pipeline.pk))
        assert response.status_code == 401

    def test_retrieve_other_users_pipeline_returns_404(self, auth_client, other_user):
        other = PipelineFactory(user=other_user)
        response = auth_client.get(pipeline_url(other.pk))
        assert response.status_code == 404


@pytest.mark.django_db
class TestPipelineUpdate:
    def test_full_update(self, auth_client, pipeline):
        payload = {'name': 'Updated', 'description': 'new'}
        response = auth_client.put(pipeline_url(pipeline.pk), payload, format='json')
        assert response.status_code == 200
        assert response.data['name'] == 'Updated'

    def test_partial_update(self, auth_client, pipeline):
        response = auth_client.patch(pipeline_url(pipeline.pk), {'name': 'Patched'}, format='json')
        assert response.status_code == 200
        assert response.data['name'] == 'Patched'

    def test_update_unauthenticated(self, client, pipeline):
        response = client.put(pipeline_url(pipeline.pk), {'name': 'x'}, format='json')
        assert response.status_code == 401

    def test_update_other_users_pipeline_returns_404(self, auth_client, other_user):
        other = PipelineFactory(user=other_user)
        response = auth_client.patch(pipeline_url(other.pk), {'name': 'x'}, format='json')
        assert response.status_code == 404


@pytest.mark.django_db
class TestPipelineDelete:
    def test_delete_success(self, auth_client, pipeline):
        response = auth_client.delete(pipeline_url(pipeline.pk))
        assert response.status_code == 204
        assert not Pipeline.objects.filter(pk=pipeline.pk).exists()

    def test_delete_unauthenticated(self, client, pipeline):
        response = client.delete(pipeline_url(pipeline.pk))
        assert response.status_code == 401

    def test_delete_other_users_pipeline_returns_404(self, auth_client, other_user):
        other = PipelineFactory(user=other_user)
        response = auth_client.delete(pipeline_url(other.pk))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Stage endpoints
# ---------------------------------------------------------------------------

def stages_url(pipeline_pk):
    return f'/api/pipelines/{pipeline_pk}/stages/'


def stage_url(pipeline_pk, stage_pk):
    return f'/api/pipelines/{pipeline_pk}/stages/{stage_pk}/'


@pytest.mark.django_db
class TestStageList:
    def test_list_success(self, auth_client, stage):
        response = auth_client.get(stages_url(stage.pipeline.pk))
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_list_unauthenticated(self, client, stage):
        response = client.get(stages_url(stage.pipeline.pk))
        assert response.status_code == 401

    def test_list_on_other_users_pipeline_returns_404(self, auth_client, other_user):
        other = PipelineFactory(user=other_user)
        PipelineStageFactory(pipeline=other)
        response = auth_client.get(stages_url(other.pk))
        assert response.status_code == 404


@pytest.mark.django_db
class TestStageCreate:
    def test_create_success(self, auth_client, pipeline):
        payload = {'name': 'preprocess', 'depends_on': [], 'order': 0}
        response = auth_client.post(stages_url(pipeline.pk), payload, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'preprocess'
        assert response.data['status'] == PipelineStage.Status.PENDING

    def test_create_with_dependencies(self, auth_client, pipeline):
        PipelineStageFactory(pipeline=pipeline, name='ingest')
        payload = {'name': 'transform', 'depends_on': ['ingest'], 'order': 1}
        response = auth_client.post(stages_url(pipeline.pk), payload, format='json')
        assert response.status_code == 201
        assert response.data['depends_on'] == ['ingest']

    def test_create_missing_name(self, auth_client, pipeline):
        response = auth_client.post(stages_url(pipeline.pk), {}, format='json')
        assert response.status_code == 400

    def test_create_unauthenticated(self, client, pipeline):
        response = client.post(stages_url(pipeline.pk), {'name': 'x'}, format='json')
        assert response.status_code == 401

    def test_create_on_other_users_pipeline_returns_404(self, auth_client, other_user):
        other = PipelineFactory(user=other_user)
        response = auth_client.post(stages_url(other.pk), {'name': 'x'}, format='json')
        assert response.status_code == 404


@pytest.mark.django_db
class TestStageRetrieve:
    def test_retrieve_success(self, auth_client, stage):
        response = auth_client.get(stage_url(stage.pipeline.pk, stage.pk))
        assert response.status_code == 200
        assert response.data['id'] == str(stage.pk)

    def test_retrieve_unauthenticated(self, client, stage):
        response = client.get(stage_url(stage.pipeline.pk, stage.pk))
        assert response.status_code == 401


@pytest.mark.django_db
class TestStageUpdate:
    def test_update_status(self, auth_client, stage):
        response = auth_client.patch(
            stage_url(stage.pipeline.pk, stage.pk),
            {'status': 'running'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['status'] == 'running'

    def test_update_invalid_status(self, auth_client, stage):
        response = auth_client.patch(
            stage_url(stage.pipeline.pk, stage.pk),
            {'status': 'not_valid'},
            format='json',
        )
        assert response.status_code == 400

    def test_update_unauthenticated(self, client, stage):
        response = client.patch(stage_url(stage.pipeline.pk, stage.pk), {}, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestStageDelete:
    def test_delete_success(self, auth_client, stage):
        response = auth_client.delete(stage_url(stage.pipeline.pk, stage.pk))
        assert response.status_code == 204
        assert not PipelineStage.objects.filter(pk=stage.pk).exists()

    def test_delete_unauthenticated(self, client, stage):
        response = client.delete(stage_url(stage.pipeline.pk, stage.pk))
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# DAG endpoint
# ---------------------------------------------------------------------------

def dag_url(pipeline_pk):
    return f'/api/pipelines/{pipeline_pk}/dag/'


@pytest.mark.django_db
class TestDAGView:
    def test_dag_returns_nodes_and_edges(self, auth_client, pipeline):
        PipelineStageFactory(pipeline=pipeline, name='ingest', depends_on=[], order=0)
        PipelineStageFactory(pipeline=pipeline, name='transform', depends_on=['ingest'], order=1)
        PipelineStageFactory(pipeline=pipeline, name='load', depends_on=['transform'], order=2)

        response = auth_client.get(dag_url(pipeline.pk))
        assert response.status_code == 200
        assert len(response.data['nodes']) == 3
        assert len(response.data['edges']) == 2

        node_names = {n['name'] for n in response.data['nodes']}
        assert node_names == {'ingest', 'transform', 'load'}

        edges = {(e['from'], e['to']) for e in response.data['edges']}
        assert ('ingest', 'transform') in edges
        assert ('transform', 'load') in edges

    def test_dag_empty_pipeline(self, auth_client, pipeline):
        response = auth_client.get(dag_url(pipeline.pk))
        assert response.status_code == 200
        assert response.data['nodes'] == []
        assert response.data['edges'] == []

    def test_dag_unauthenticated(self, client, pipeline):
        response = client.get(dag_url(pipeline.pk))
        assert response.status_code == 401

    def test_dag_other_users_pipeline_returns_404(self, auth_client, other_user):
        other = PipelineFactory(user=other_user)
        response = auth_client.get(dag_url(other.pk))
        assert response.status_code == 404
