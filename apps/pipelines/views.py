from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    DAGSerializer,
    PipelineSerializer,
    PipelineStageSerializer,
    PipelineWriteSerializer,
    StageUpdateSerializer,
    StageWriteSerializer,
)
from .services import (
    create_pipeline,
    create_stage,
    delete_pipeline,
    get_dag,
    get_pipeline_for_user,
    get_stage,
    list_pipelines,
    list_stages,
    update_pipeline,
    update_stage,
)


class PipelineViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        pipelines = list_pipelines(request.user)
        return Response(PipelineSerializer(pipelines, many=True).data)

    def create(self, request):
        serializer = PipelineWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pipeline = create_pipeline(user=request.user, **serializer.validated_data)
        return Response(PipelineSerializer(pipeline).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        pipeline = get_pipeline_for_user(pk, request.user)
        return Response(PipelineSerializer(pipeline).data)

    def update(self, request, pk=None):
        pipeline = get_pipeline_for_user(pk, request.user)
        serializer = PipelineWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pipeline = update_pipeline(pipeline, **serializer.validated_data)
        return Response(PipelineSerializer(pipeline).data)

    def partial_update(self, request, pk=None):
        pipeline = get_pipeline_for_user(pk, request.user)
        serializer = PipelineWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        pipeline = update_pipeline(pipeline, **serializer.validated_data)
        return Response(PipelineSerializer(pipeline).data)

    def destroy(self, request, pk=None):
        pipeline = get_pipeline_for_user(pk, request.user)
        delete_pipeline(pipeline)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PipelineStageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_pipeline(self, request, pipeline_pk):
        return get_pipeline_for_user(pipeline_pk, request.user)

    def list(self, request, pipeline_pk=None):
        pipeline = self._get_pipeline(request, pipeline_pk)
        return Response(PipelineStageSerializer(list_stages(pipeline), many=True).data)

    def create(self, request, pipeline_pk=None):
        pipeline = self._get_pipeline(request, pipeline_pk)
        serializer = StageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stage = create_stage(pipeline=pipeline, **serializer.validated_data)
        return Response(PipelineStageSerializer(stage).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, pipeline_pk=None):
        pipeline = self._get_pipeline(request, pipeline_pk)
        stage = get_stage(pk, pipeline)
        return Response(PipelineStageSerializer(stage).data)

    def partial_update(self, request, pk=None, pipeline_pk=None):
        pipeline = self._get_pipeline(request, pipeline_pk)
        stage = get_stage(pk, pipeline)
        serializer = StageUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        stage = update_stage(stage, **serializer.validated_data)
        return Response(PipelineStageSerializer(stage).data)

    def destroy(self, request, pk=None, pipeline_pk=None):
        pipeline = self._get_pipeline(request, pipeline_pk)
        stage = get_stage(pk, pipeline)
        stage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PipelineDAGView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pipeline_pk):
        pipeline = get_pipeline_for_user(pipeline_pk, request.user)
        dag = get_dag(pipeline)
        return Response(DAGSerializer(dag).data)
