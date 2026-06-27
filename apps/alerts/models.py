import uuid

from django.conf import settings
from django.db import models


class AlertRule(models.Model):
    class Condition(models.TextChoices):
        GREATER_THAN = 'gt', 'Greater than'
        LESS_THAN = 'lt', 'Less than'
        EQUAL = 'eq', 'Equal to'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alert_rules',
    )
    experiment = models.ForeignKey(
        'experiments.Experiment',
        on_delete=models.CASCADE,
        related_name='alert_rules',
    )
    metric_name = models.CharField(max_length=255)
    condition = models.CharField(max_length=10, choices=Condition.choices)
    threshold = models.FloatField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.metric_name} {self.condition} {self.threshold}'


class AlertEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='events')
    metric = models.ForeignKey(
        'experiments.Metric',
        on_delete=models.CASCADE,
        related_name='alert_events',
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('rule', 'metric')
        ordering = ['-triggered_at']

    def __str__(self):
        return f'{self.rule} triggered by metric {self.metric_id}'
