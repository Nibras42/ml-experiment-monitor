from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ExperimentSerializer,
    ExperimentWriteSerializer,
    LogMetricSerializer,
    MetricSerializer,
    RunSerializer,
    RunUpdateSerializer,
    RunWriteSerializer,
)
from .services import (
    create_experiment,
    create_run,
    delete_experiment,
    get_experiment_for_user,
    get_run_for_experiment,
    list_experiments,
    list_metrics,
    list_runs,
    log_metric,
    update_experiment,
    update_run,
)


class ExperimentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        experiments = list_experiments(request.user)
        return Response(ExperimentSerializer(experiments, many=True).data)

    def create(self, request):
        serializer = ExperimentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        experiment = create_experiment(user=request.user, **serializer.validated_data)
        return Response(ExperimentSerializer(experiment).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        experiment = get_experiment_for_user(pk, request.user)
        return Response(ExperimentSerializer(experiment).data)

    def update(self, request, pk=None):
        experiment = get_experiment_for_user(pk, request.user)
        serializer = ExperimentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        experiment = update_experiment(experiment, **serializer.validated_data)
        return Response(ExperimentSerializer(experiment).data)

    def partial_update(self, request, pk=None):
        experiment = get_experiment_for_user(pk, request.user)
        serializer = ExperimentWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        experiment = update_experiment(experiment, **serializer.validated_data)
        return Response(ExperimentSerializer(experiment).data)

    def destroy(self, request, pk=None):
        experiment = get_experiment_for_user(pk, request.user)
        delete_experiment(experiment)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RunViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_experiment(self, request, experiment_pk):
        return get_experiment_for_user(experiment_pk, request.user)

    def list(self, request, experiment_pk=None):
        experiment = self._get_experiment(request, experiment_pk)
        return Response(RunSerializer(list_runs(experiment), many=True).data)

    def create(self, request, experiment_pk=None):
        experiment = self._get_experiment(request, experiment_pk)
        serializer = RunWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = create_run(experiment=experiment, **serializer.validated_data)
        return Response(RunSerializer(run).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, experiment_pk=None):
        experiment = self._get_experiment(request, experiment_pk)
        run = get_run_for_experiment(pk, experiment)
        return Response(RunSerializer(run).data)

    def partial_update(self, request, pk=None, experiment_pk=None):
        experiment = self._get_experiment(request, experiment_pk)
        run = get_run_for_experiment(pk, experiment)
        serializer = RunUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        run = update_run(run, **serializer.validated_data)
        return Response(RunSerializer(run).data)

    def destroy(self, request, pk=None, experiment_pk=None):
        experiment = self._get_experiment(request, experiment_pk)
        run = get_run_for_experiment(pk, experiment)
        run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MetricView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_run(self, request, experiment_pk, run_pk):
        experiment = get_experiment_for_user(experiment_pk, request.user)
        return get_run_for_experiment(run_pk, experiment)

    def get(self, request, experiment_pk, run_pk):
        run = self._get_run(request, experiment_pk, run_pk)
        name_filter = request.query_params.get('name')
        metrics = list_metrics(run, name=name_filter)
        return Response(MetricSerializer(metrics, many=True).data)

    def post(self, request, experiment_pk, run_pk):
        run = self._get_run(request, experiment_pk, run_pk)
        serializer = LogMetricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        metric = log_metric(run=run, **serializer.validated_data)
        return Response(MetricSerializer(metric).data, status=status.HTTP_201_CREATED)
