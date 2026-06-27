import logging

from django.shortcuts import get_object_or_404

from .models import AlertEvent, AlertRule
from .signals import alert_triggered

logger = logging.getLogger(__name__)

CONDITION_CHECKS = {
    AlertRule.Condition.GREATER_THAN: lambda value, threshold: value > threshold,
    AlertRule.Condition.LESS_THAN: lambda value, threshold: value < threshold,
    AlertRule.Condition.EQUAL: lambda value, threshold: value == threshold,
}


def is_breached(rule, value):
    return CONDITION_CHECKS[rule.condition](value, rule.threshold)


def create_alert_rule(user, experiment, metric_name, condition, threshold, is_active=True):
    rule = AlertRule.objects.create(
        user=user,
        experiment=experiment,
        metric_name=metric_name,
        condition=condition,
        threshold=threshold,
        is_active=is_active,
    )
    logger.info('Alert rule created: %s', rule.id)
    return rule


def list_alert_rules(user):
    return AlertRule.objects.filter(user=user)


def get_alert_rule_for_user(rule_id, user):
    return get_object_or_404(AlertRule, id=rule_id, user=user)


def update_alert_rule(rule, metric_name=None, condition=None, threshold=None, is_active=None):
    if metric_name is not None:
        rule.metric_name = metric_name
    if condition is not None:
        rule.condition = condition
    if threshold is not None:
        rule.threshold = threshold
    if is_active is not None:
        rule.is_active = is_active
    rule.save()
    return rule


def delete_alert_rule(rule):
    rule.delete()


def evaluate_rule(rule):
    from apps.experiments.services import get_latest_metric_for_experiment

    metric = get_latest_metric_for_experiment(rule.experiment, rule.metric_name)
    if metric is None or not is_breached(rule, metric.value):
        return None

    event, created = AlertEvent.objects.get_or_create(rule=rule, metric=metric)
    if created:
        alert_triggered.send(sender=AlertRule, event=event)
        logger.info('Alert triggered: rule=%s metric=%s', rule.id, metric.id)
    return event if created else None


def get_alert_event_context(event_id):
    event = AlertEvent.objects.select_related(
        'rule__user', 'rule__experiment', 'metric__run',
    ).get(id=event_id)
    rule = event.rule
    metric = event.metric
    return {
        'to_email': rule.user.email,
        'experiment_name': rule.experiment.name,
        'metric_name': rule.metric_name,
        'condition': rule.get_condition_display(),
        'threshold': rule.threshold,
        'value': metric.value,
        'run_id': str(metric.run_id),
        'triggered_at': event.triggered_at.isoformat(),
    }
