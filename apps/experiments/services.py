import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404

from .models import Experiment, Metric, Run

logger = logging.getLogger(__name__)


def create_experiment(user, name, description='', tags=None):
    experiment = Experiment.objects.create(
        user=user,
        name=name,
        description=description,
        tags=tags if tags is not None else [],
    )
    logger.info('Experiment created: %s by %s', experiment.id, user.email)
    return experiment


def get_experiment_for_user(experiment_id, user):
    return get_object_or_404(Experiment, id=experiment_id, user=user)


def update_experiment(experiment, name=None, description=None, tags=None):
    if name is not None:
        experiment.name = name
    if description is not None:
        experiment.description = description
    if tags is not None:
        experiment.tags = tags
    experiment.save()
    return experiment


def delete_experiment(experiment):
    experiment.delete()


def list_experiments(user):
    return Experiment.objects.filter(user=user)


def create_run(experiment, name='', hyperparameters=None):
    run = Run.objects.create(
        experiment=experiment,
        name=name,
        hyperparameters=hyperparameters if hyperparameters is not None else {},
    )
    logger.info('Run created: %s for experiment %s', run.id, experiment.id)
    return run


def get_run_for_experiment(run_id, experiment):
    return get_object_or_404(Run, id=run_id, experiment=experiment)


def update_run(run, name=None, status=None, hyperparameters=None, started_at=None, ended_at=None):
    if name is not None:
        run.name = name
    if status is not None:
        run.status = status
    if hyperparameters is not None:
        run.hyperparameters = hyperparameters
    if started_at is not None:
        run.started_at = started_at
    if ended_at is not None:
        run.ended_at = ended_at
    run.save()
    return run


def list_runs(experiment):
    return Run.objects.filter(experiment=experiment)


def log_metric(run, name, value, step=0):
    metric = Metric.objects.create(run=run, name=name, value=value, step=step)
    broadcast_metric(metric)
    return metric


def broadcast_metric(metric):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f'run_{metric.run_id}',
        {
            'type': 'metric_logged',
            'metric': {
                'id': str(metric.id),
                'name': metric.name,
                'value': metric.value,
                'step': metric.step,
                'created_at': metric.created_at.isoformat(),
            },
        },
    )


def list_metrics(run, name=None):
    qs = Metric.objects.filter(run=run)
    if name:
        qs = qs.filter(name=name)
    return qs


def get_latest_metric_for_experiment(experiment, metric_name):
    return (
        Metric.objects.filter(run__experiment=experiment, name=metric_name)
        .order_by('-created_at')
        .first()
    )
