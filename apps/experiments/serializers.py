from rest_framework import serializers

from .models import Experiment, Metric, Run


class ExperimentSerializer(serializers.ModelSerializer):
    run_count = serializers.IntegerField(source='runs.count', read_only=True)

    class Meta:
        model = Experiment
        fields = ['id', 'name', 'description', 'tags', 'run_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'run_count', 'created_at', 'updated_at']


class ExperimentWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='', allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )


class RunSerializer(serializers.ModelSerializer):
    metric_count = serializers.IntegerField(source='metrics.count', read_only=True)

    class Meta:
        model = Run
        fields = [
            'id', 'name', 'status', 'hyperparameters',
            'started_at', 'ended_at', 'metric_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'metric_count', 'created_at', 'updated_at']


class RunWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, default='', allow_blank=True)
    hyperparameters = serializers.DictField(required=False, default=dict)


class RunUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Run.Status.choices, required=False)
    hyperparameters = serializers.DictField(required=False)
    started_at = serializers.DateTimeField(required=False)
    ended_at = serializers.DateTimeField(required=False)


class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = ['id', 'name', 'value', 'step', 'created_at']
        read_only_fields = ['id', 'created_at']


class LogMetricSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    value = serializers.FloatField()
    step = serializers.IntegerField(min_value=0, required=False, default=0)
