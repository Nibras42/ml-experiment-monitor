from rest_framework import serializers

from .models import Pipeline, PipelineStage


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = [
            'id', 'name', 'depends_on', 'status', 'order',
            'started_at', 'ended_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PipelineSerializer(serializers.ModelSerializer):
    stage_count = serializers.IntegerField(source='stages.count', read_only=True)

    class Meta:
        model = Pipeline
        fields = ['id', 'name', 'description', 'stage_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'stage_count', 'created_at', 'updated_at']


class PipelineWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='', allow_blank=True)


class StageWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    depends_on = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list,
    )
    order = serializers.IntegerField(min_value=0, required=False, default=0)


class StageUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    status = serializers.ChoiceField(choices=PipelineStage.Status.choices, required=False)
    depends_on = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
    )
    order = serializers.IntegerField(min_value=0, required=False)
    started_at = serializers.DateTimeField(required=False)
    ended_at = serializers.DateTimeField(required=False)


class DAGSerializer(serializers.Serializer):
    nodes = serializers.ListField(child=serializers.DictField())
    edges = serializers.ListField(child=serializers.DictField())
