import factory
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.alerts.models import AlertEvent, AlertRule
from apps.alerts.services import evaluate_rule, is_breached
from apps.alerts.tasks import check_alert_thresholds
from apps.experiments.models import Experiment, Run
from apps.experiments.services import log_metric

User = get_user_model()


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'alert_user{n}@example.com')

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
    name = factory.Sequence(lambda n: f'Alert Experiment {n}')


class RunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Run

    experiment = factory.SubFactory(ExperimentFactory)
    name = factory.Sequence(lambda n: f'Alert Run {n}')


class AlertRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlertRule

    user = factory.SelfAttribute('experiment.user')
    experiment = factory.SubFactory(ExperimentFactory)
    metric_name = 'loss'
    condition = AlertRule.Condition.GREATER_THAN
    threshold = 0.5
    is_active = True


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


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAlertRuleModel:
    def test_str(self):
        rule = AlertRuleFactory(metric_name='loss', condition='gt', threshold=0.5)
        assert str(rule) == 'loss gt 0.5'

    def test_uuid_pk(self):
        rule = AlertRuleFactory()
        assert len(str(rule.pk)) == 36

    def test_timestamps(self):
        rule = AlertRuleFactory()
        assert rule.created_at is not None
        assert rule.updated_at is not None

    def test_default_is_active_true(self):
        rule = AlertRuleFactory()
        assert rule.is_active is True


@pytest.mark.django_db
class TestAlertEventModel:
    def test_str_and_uuid_pk(self, run):
        rule = AlertRuleFactory(experiment=run.experiment)
        metric = log_metric(run=run, name='loss', value=0.9, step=0)
        event = AlertEvent.objects.create(rule=rule, metric=metric)
        assert str(rule) in str(event)
        assert len(str(event.pk)) == 36

    def test_unique_together_prevents_duplicate_event(self, run):
        rule = AlertRuleFactory(experiment=run.experiment)
        metric = log_metric(run=run, name='loss', value=0.9, step=0)
        AlertEvent.objects.create(rule=rule, metric=metric)
        with pytest.raises(Exception):
            AlertEvent.objects.create(rule=rule, metric=metric)


# ---------------------------------------------------------------------------
# Service logic tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIsBreached:
    def test_greater_than(self):
        rule = AlertRuleFactory(condition=AlertRule.Condition.GREATER_THAN, threshold=0.5)
        assert is_breached(rule, 0.9) is True
        assert is_breached(rule, 0.1) is False

    def test_less_than(self):
        rule = AlertRuleFactory(condition=AlertRule.Condition.LESS_THAN, threshold=0.5)
        assert is_breached(rule, 0.1) is True
        assert is_breached(rule, 0.9) is False

    def test_equal(self):
        rule = AlertRuleFactory(condition=AlertRule.Condition.EQUAL, threshold=0.5)
        assert is_breached(rule, 0.5) is True
        assert is_breached(rule, 0.6) is False


@pytest.mark.django_db
class TestEvaluateRule:
    def test_creates_event_when_breached(self, run):
        rule = AlertRuleFactory(
            experiment=run.experiment, metric_name='loss',
            condition=AlertRule.Condition.GREATER_THAN, threshold=0.5,
        )
        log_metric(run=run, name='loss', value=0.9, step=0)

        event = evaluate_rule(rule)
        assert event is not None
        assert AlertEvent.objects.filter(rule=rule).count() == 1

    def test_returns_none_when_not_breached(self, run):
        rule = AlertRuleFactory(
            experiment=run.experiment, metric_name='loss',
            condition=AlertRule.Condition.GREATER_THAN, threshold=0.5,
        )
        log_metric(run=run, name='loss', value=0.1, step=0)

        event = evaluate_rule(rule)
        assert event is None
        assert AlertEvent.objects.filter(rule=rule).count() == 0

    def test_returns_none_when_no_metric_logged(self, run):
        rule = AlertRuleFactory(experiment=run.experiment, metric_name='nonexistent')
        assert evaluate_rule(rule) is None

    def test_does_not_duplicate_event_for_same_metric(self, run):
        rule = AlertRuleFactory(
            experiment=run.experiment, metric_name='loss',
            condition=AlertRule.Condition.GREATER_THAN, threshold=0.5,
        )
        log_metric(run=run, name='loss', value=0.9, step=0)

        evaluate_rule(rule)
        evaluate_rule(rule)

        assert AlertEvent.objects.filter(rule=rule).count() == 1

    def test_sends_alert_email_on_trigger(self, run, mailoutbox):
        rule = AlertRuleFactory(
            experiment=run.experiment, metric_name='loss',
            condition=AlertRule.Condition.GREATER_THAN, threshold=0.5,
        )
        log_metric(run=run, name='loss', value=0.9, step=0)

        evaluate_rule(rule)

        assert len(mailoutbox) == 1
        assert rule.user.email in mailoutbox[0].to
        assert 'loss' in mailoutbox[0].subject


# ---------------------------------------------------------------------------
# Celery task tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCheckAlertThresholdsTask:
    def test_only_evaluates_active_rules(self, run):
        active_rule = AlertRuleFactory(
            experiment=run.experiment, metric_name='loss',
            condition=AlertRule.Condition.GREATER_THAN, threshold=0.5, is_active=True,
        )
        AlertRuleFactory(
            experiment=run.experiment, metric_name='loss',
            condition=AlertRule.Condition.GREATER_THAN, threshold=0.5, is_active=False,
        )
        log_metric(run=run, name='loss', value=0.9, step=0)

        triggered = check_alert_thresholds.delay().get()

        assert triggered == 1
        assert AlertEvent.objects.filter(rule=active_rule).exists()


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

ALERTS_URL = '/api/alerts/'


def alert_url(pk):
    return f'/api/alerts/{pk}/'


@pytest.mark.django_db
class TestAlertRuleList:
    def test_list_authenticated(self, auth_client, user):
        AlertRuleFactory(experiment=ExperimentFactory(user=user))
        response = auth_client.get(ALERTS_URL)
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_list_unauthenticated(self, client):
        response = client.get(ALERTS_URL)
        assert response.status_code == 401


@pytest.mark.django_db
class TestAlertRuleCreate:
    def test_create_success(self, auth_client, experiment):
        payload = {
            'experiment': str(experiment.pk),
            'metric_name': 'accuracy',
            'condition': 'lt',
            'threshold': 0.8,
        }
        response = auth_client.post(ALERTS_URL, payload, format='json')
        assert response.status_code == 201
        assert response.data['metric_name'] == 'accuracy'

    def test_create_missing_threshold(self, auth_client, experiment):
        payload = {'experiment': str(experiment.pk), 'metric_name': 'loss', 'condition': 'gt'}
        response = auth_client.post(ALERTS_URL, payload, format='json')
        assert response.status_code == 400

    def test_create_invalid_condition(self, auth_client, experiment):
        payload = {
            'experiment': str(experiment.pk), 'metric_name': 'loss',
            'condition': 'not_a_condition', 'threshold': 0.5,
        }
        response = auth_client.post(ALERTS_URL, payload, format='json')
        assert response.status_code == 400

    def test_create_unauthenticated(self, client, experiment):
        payload = {'experiment': str(experiment.pk), 'metric_name': 'loss', 'condition': 'gt', 'threshold': 0.5}
        response = client.post(ALERTS_URL, payload, format='json')
        assert response.status_code == 401

    def test_create_on_other_users_experiment_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        payload = {'experiment': str(other_exp.pk), 'metric_name': 'loss', 'condition': 'gt', 'threshold': 0.5}
        response = auth_client.post(ALERTS_URL, payload, format='json')
        assert response.status_code == 404


@pytest.mark.django_db
class TestAlertRuleRetrieve:
    def test_retrieve_success(self, auth_client, experiment):
        rule = AlertRuleFactory(experiment=experiment)
        response = auth_client.get(alert_url(rule.pk))
        assert response.status_code == 200
        assert response.data['id'] == str(rule.pk)

    def test_retrieve_unauthenticated(self, client, experiment):
        rule = AlertRuleFactory(experiment=experiment)
        response = client.get(alert_url(rule.pk))
        assert response.status_code == 401

    def test_retrieve_other_users_rule_returns_404(self, auth_client, other_user):
        other_exp = ExperimentFactory(user=other_user)
        rule = AlertRuleFactory(experiment=other_exp)
        response = auth_client.get(alert_url(rule.pk))
        assert response.status_code == 404


@pytest.mark.django_db
class TestAlertRuleUpdate:
    def test_partial_update_success(self, auth_client, experiment):
        rule = AlertRuleFactory(experiment=experiment)
        response = auth_client.patch(alert_url(rule.pk), {'threshold': 0.99}, format='json')
        assert response.status_code == 200
        assert response.data['threshold'] == 0.99

    def test_update_unauthenticated(self, client, experiment):
        rule = AlertRuleFactory(experiment=experiment)
        response = client.patch(alert_url(rule.pk), {'threshold': 0.1}, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestAlertRuleDelete:
    def test_delete_success(self, auth_client, experiment):
        rule = AlertRuleFactory(experiment=experiment)
        response = auth_client.delete(alert_url(rule.pk))
        assert response.status_code == 204
        assert not AlertRule.objects.filter(pk=rule.pk).exists()

    def test_delete_unauthenticated(self, client, experiment):
        rule = AlertRuleFactory(experiment=experiment)
        response = client.delete(alert_url(rule.pk))
        assert response.status_code == 401
