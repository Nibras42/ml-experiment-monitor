from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PipelineDAGView, PipelineStageViewSet, PipelineViewSet

router = DefaultRouter()
router.register('', PipelineViewSet, basename='pipeline')

stage_list = PipelineStageViewSet.as_view({'get': 'list', 'post': 'create'})
stage_detail = PipelineStageViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})

urlpatterns = [
    *router.urls,
    path('<uuid:pipeline_pk>/stages/', stage_list, name='stage-list'),
    path('<uuid:pipeline_pk>/stages/<uuid:pk>/', stage_detail, name='stage-detail'),
    path('<uuid:pipeline_pk>/dag/', PipelineDAGView.as_view(), name='pipeline-dag'),
]
