import pytest
import factory
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.experiments.models import Experiment, Metric, Run

User = get_user_model()


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'exp_user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted if extracted is not None else 'TestPass123!')
        self.save()


class ExperimentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Experiment

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Experiment {n}')
    description = 'A test experiment'
    tags = factory.LazyFunction(list)


class RunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Run

    experiment = factory.SubFactory(ExperimentFactory)
    name = factory.Sequence(lambda n: f'Run {n}')
    status = Run.Status.PENDING
    hyperparameters = factory.LazyFunction(dict)


class MetricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Metric

    run = factory.SubFactory(RunFactory)
    name = factory.Sequence(lambda n: f'metric_{n}')
    value = 0.95
    step = factory.Sequence(lambda n: n)


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
def experiment(user):
    return ExperimentFactory(user=user)


@pytest.fixture
def run(experiment):
    return RunFactory(experiment=experiment)


@pytest.fixture
def metric(run):
    return MetricFactory(run=run)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExperimentModel:
    def test_str(self):
        exp = ExperimentFactory(name='BERT fine-tune')
        assert str(exp) == 'BERT fine-tune'

    def test_uuid_pk(self):
        exp = ExperimentFactory()
        assert len(str(exp.pk)) == 36

    def test_timestamps(self):
        exp = ExperimentFactory()
        assert exp.created_at is not None
        assert exp.updated_at is not None

    def test_default_tags_is_list(self):
        exp = ExperimentFactory()
        assert isinstance(exp.tags, list)


@pytest.mark.django_db
class TestRunModel:
    def test_str_includes_experiment_name(self):
        run = RunFactory(experiment=ExperimentFactory(name='MyExp'), name='run-1')
        assert 'MyExp' in str(run)
        assert 'run-1' in str(run)

    def test_uuid_pk(self):
        run = RunFactory()
        assert len(str(run.pk)) == 36

    def test_default_status_is_pending(self):
        run = RunFactory()
        assert run.status == Run.Status.PENDING

    def test_timestamps(self):
        run = RunFactory()
        assert run.created_at is not None
        assert run.updated_at is not None


@pytest.mark.django_db
class TestMetricModel:
    def test_str(self):
        m = MetricFactory(name='loss', value=0.42, step=5)
        assert str(m) == 'loss=0.42 @ step 5'

    def test_uuid_pk(self):
        m = MetricFactory()
        assert len(str(m.pk)) == 36

    def test_timestamps(self):
        m = MetricFactory()
        assert m.created_at is not None
        assert m.updated_at is not None


# ---------------------------------------------------------------------------
# Experiment endpoints
# ---------------------------------------------------------------------------

EXPERIMENTS_URL = '/api/experiments/'


def experiment_url(pk):
    return f'/api/experiments/{pk}/'


@pytest.mark.django_db
class TestExperimentList:
    def test_list_authenticated(self, auth_client, experiment):
        response = auth_client.get(EXPERIMENTS_URL)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['name'] == experiment.name

    def test_list_only_own_experiments(self, auth_client, user, other_user):
        ExperimentFactory(user=user)
        ExperimentFactory(user=other_user)
        response = auth_client.get(EXPERIMENTS_URL)
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_list_unauthenticated(self, client):
        response = client.get(EXPERIMENTS_URL)
        assert response.status_code == 401


@pytest.mark.django_db
class TestExperimentCreate:
    def test_create_success(self, auth_client):
        payload = {'name': 'New Exp', 'description': 'desc', 'tags': ['nlp']}
        response = auth_client.post(EXPERIMENTS_URL, payload, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'New Exp'
        assert response.data['tags'] == ['nlp']
        assert Experiment.objects.filter(name='New Exp').exists()

    def test_create_missing_name(self, auth_client):
        response = auth_client.post(EXPERIMENTS_URL, {'description': 'x'}, format='json')
        assert response.status_code == 400

    def test_create_unauthenticated(self, client):
        response = client.post(EXPERIMENTS_URL, {'name': 'x'}, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestExperimentRetrieve:
    def test_retrieve_success(self, auth_client, experiment):
        response = auth_client.get(experiment_url(experiment.pk))
        assert response.status_code == 200
        assert response.data['id'] == str(experiment.pk)

    def test_retrieve_unauthenticated(self, client, experiment):
        response = client.get(experiment_url(experiment.pk))
        assert response.status_code == 401

    def test_retrieve_other_users_experiment_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        response = auth_client.get(experiment_url(other_exp.pk))
        assert response.status_code == 404


@pytest.mark.django_db
class TestExperimentUpdate:
    def test_full_update_success(self, auth_client, experiment):
        payload = {'name': 'Updated', 'description': 'new desc', 'tags': ['cv']}
        response = auth_client.put(experiment_url(experiment.pk), payload, format='json')
        assert response.status_code == 200
        assert response.data['name'] == 'Updated'

    def test_partial_update_success(self, auth_client, experiment):
        response = auth_client.patch(
            experiment_url(experiment.pk), {'name': 'Patched'}, format='json'
        )
        assert response.status_code == 200
        assert response.data['name'] == 'Patched'

    def test_update_unauthenticated(self, client, experiment):
        response = client.put(experiment_url(experiment.pk), {'name': 'x'}, format='json')
        assert response.status_code == 401

    def test_update_other_users_experiment_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        response = auth_client.patch(experiment_url(other_exp.pk), {'name': 'x'}, format='json')
        assert response.status_code == 404


@pytest.mark.django_db
class TestExperimentDelete:
    def test_delete_success(self, auth_client, experiment):
        response = auth_client.delete(experiment_url(experiment.pk))
        assert response.status_code == 204
        assert not Experiment.objects.filter(pk=experiment.pk).exists()

    def test_delete_unauthenticated(self, client, experiment):
        response = client.delete(experiment_url(experiment.pk))
        assert response.status_code == 401

    def test_delete_other_users_experiment_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        response = auth_client.delete(experiment_url(other_exp.pk))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Run endpoints
# ---------------------------------------------------------------------------

def runs_url(experiment_pk):
    return f'/api/experiments/{experiment_pk}/runs/'


def run_url(experiment_pk, run_pk):
    return f'/api/experiments/{experiment_pk}/runs/{run_pk}/'


@pytest.mark.django_db
class TestRunList:
    def test_list_success(self, auth_client, run):
        response = auth_client.get(runs_url(run.experiment.pk))
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_list_unauthenticated(self, client, run):
        response = client.get(runs_url(run.experiment.pk))
        assert response.status_code == 401


@pytest.mark.django_db
class TestRunCreate:
    def test_create_success(self, auth_client, experiment):
        payload = {'name': 'run-1', 'hyperparameters': {'lr': 0.001}}
        response = auth_client.post(runs_url(experiment.pk), payload, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'run-1'
        assert response.data['status'] == Run.Status.PENDING

    def test_create_defaults(self, auth_client, experiment):
        response = auth_client.post(runs_url(experiment.pk), {}, format='json')
        assert response.status_code == 201
        assert response.data['hyperparameters'] == {}

    def test_create_unauthenticated(self, client, experiment):
        response = client.post(runs_url(experiment.pk), {}, format='json')
        assert response.status_code == 401

    def test_create_on_other_users_experiment_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        response = auth_client.post(runs_url(other_exp.pk), {}, format='json')
        assert response.status_code == 404


@pytest.mark.django_db
class TestRunRetrieve:
    def test_retrieve_success(self, auth_client, run):
        response = auth_client.get(run_url(run.experiment.pk, run.pk))
        assert response.status_code == 200
        assert response.data['id'] == str(run.pk)

    def test_retrieve_unauthenticated(self, client, run):
        response = client.get(run_url(run.experiment.pk, run.pk))
        assert response.status_code == 401


@pytest.mark.django_db
class TestRunUpdate:
    def test_update_status(self, auth_client, run):
        response = auth_client.patch(
            run_url(run.experiment.pk, run.pk),
            {'status': 'running'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['status'] == 'running'

    def test_update_invalid_status(self, auth_client, run):
        response = auth_client.patch(
            run_url(run.experiment.pk, run.pk),
            {'status': 'invalid_status'},
            format='json',
        )
        assert response.status_code == 400

    def test_update_unauthenticated(self, client, run):
        response = client.patch(run_url(run.experiment.pk, run.pk), {}, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestRunDelete:
    def test_delete_success(self, auth_client, run):
        response = auth_client.delete(run_url(run.experiment.pk, run.pk))
        assert response.status_code == 204
        assert not Run.objects.filter(pk=run.pk).exists()

    def test_delete_unauthenticated(self, client, run):
        response = client.delete(run_url(run.experiment.pk, run.pk))
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Metric endpoints
# ---------------------------------------------------------------------------

def metrics_url(experiment_pk, run_pk):
    return f'/api/experiments/{experiment_pk}/runs/{run_pk}/metrics/'


@pytest.mark.django_db
class TestMetricView:
    def test_list_success(self, auth_client, metric):
        run = metric.run
        response = auth_client.get(metrics_url(run.experiment.pk, run.pk))
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['name'] == metric.name

    def test_list_filter_by_name(self, auth_client, run):
        MetricFactory(run=run, name='loss', step=0)
        MetricFactory(run=run, name='loss', step=1)
        MetricFactory(run=run, name='accuracy', step=0)
        response = auth_client.get(
            metrics_url(run.experiment.pk, run.pk) + '?name=loss'
        )
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_list_unauthenticated(self, client, run):
        response = client.get(metrics_url(run.experiment.pk, run.pk))
        assert response.status_code == 401

    def test_log_success(self, auth_client, run):
        payload = {'name': 'val_loss', 'value': 0.12, 'step': 3}
        response = auth_client.post(metrics_url(run.experiment.pk, run.pk), payload, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'val_loss'
        assert response.data['value'] == 0.12
        assert response.data['step'] == 3
        assert Metric.objects.filter(run=run, name='val_loss').exists()

    def test_log_missing_value(self, auth_client, run):
        response = auth_client.post(
            metrics_url(run.experiment.pk, run.pk), {'name': 'loss'}, format='json'
        )
        assert response.status_code == 400

    def test_log_missing_name(self, auth_client, run):
        response = auth_client.post(
            metrics_url(run.experiment.pk, run.pk), {'value': 0.5}, format='json'
        )
        assert response.status_code == 400

    def test_log_unauthenticated(self, client, run):
        response = client.post(
            metrics_url(run.experiment.pk, run.pk),
            {'name': 'loss', 'value': 0.5},
            format='json',
        )
        assert response.status_code == 401

    def test_log_on_other_users_run_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        other_run = RunFactory(experiment=other_exp)
        response = auth_client.post(
            metrics_url(other_exp.pk, other_run.pk),
            {'name': 'loss', 'value': 0.5},
            format='json',
        )
        assert response.status_code == 404
