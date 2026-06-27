import logging

from django.shortcuts import get_object_or_404

from .models import Pipeline, PipelineStage

logger = logging.getLogger(__name__)


def create_pipeline(user, name, description=''):
    pipeline = Pipeline.objects.create(user=user, name=name, description=description)
    logger.info('Pipeline created: %s by %s', pipeline.id, user.email)
    return pipeline


def get_pipeline_for_user(pipeline_id, user):
    return get_object_or_404(Pipeline, id=pipeline_id, user=user)


def update_pipeline(pipeline, name=None, description=None):
    if name is not None:
        pipeline.name = name
    if description is not None:
        pipeline.description = description
    pipeline.save()
    return pipeline


def delete_pipeline(pipeline):
    pipeline.delete()


def list_pipelines(user):
    return Pipeline.objects.filter(user=user)


def create_stage(pipeline, name, depends_on=None, order=0):
    stage = PipelineStage.objects.create(
        pipeline=pipeline,
        name=name,
        depends_on=depends_on if depends_on is not None else [],
        order=order,
    )
    logger.info('Stage created: %s for pipeline %s', stage.id, pipeline.id)
    return stage


def get_stage(stage_id, pipeline):
    return get_object_or_404(PipelineStage, id=stage_id, pipeline=pipeline)


def update_stage(stage, name=None, status=None, depends_on=None, order=None, started_at=None, ended_at=None):
    if name is not None:
        stage.name = name
    if status is not None:
        stage.status = status
    if depends_on is not None:
        stage.depends_on = depends_on
    if order is not None:
        stage.order = order
    if started_at is not None:
        stage.started_at = started_at
    if ended_at is not None:
        stage.ended_at = ended_at
    stage.save()
    return stage


def list_stages(pipeline):
    return PipelineStage.objects.filter(pipeline=pipeline)


def get_dag(pipeline):
    stages = list_stages(pipeline)
    nodes = [
        {
            'id': str(s.id),
            'name': s.name,
            'status': s.status,
            'order': s.order,
        }
        for s in stages
    ]
    edges = [
        {'from': dep, 'to': s.name}
        for s in stages
        for dep in s.depends_on
    ]
    return {'nodes': nodes, 'edges': edges}
