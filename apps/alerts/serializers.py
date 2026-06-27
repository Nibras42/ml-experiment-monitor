from rest_framework import serializers

from .models import AlertRule


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = [
            'id', 'experiment', 'metric_name', 'condition',
            'threshold', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertRuleWriteSerializer(serializers.Serializer):
    experiment = serializers.UUIDField()
    metric_name = serializers.CharField(max_length=255)
    condition = serializers.ChoiceField(choices=AlertRule.Condition.choices)
    threshold = serializers.FloatField()
    is_active = serializers.BooleanField(required=False, default=True)


class AlertRuleUpdateSerializer(serializers.Serializer):
    metric_name = serializers.CharField(max_length=255, required=False)
    condition = serializers.ChoiceField(choices=AlertRule.Condition.choices, required=False)
    threshold = serializers.FloatField(required=False)
    is_active = serializers.BooleanField(required=False)
