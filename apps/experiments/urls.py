from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ExperimentViewSet, MetricView, RunViewSet

router = DefaultRouter()
router.register('', ExperimentViewSet, basename='experiment')

run_list = RunViewSet.as_view({'get': 'list', 'post': 'create'})
run_detail = RunViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})

urlpatterns = [
    *router.urls,
    path('<uuid:experiment_pk>/runs/', run_list, name='run-list'),
    path('<uuid:experiment_pk>/runs/<uuid:pk>/', run_detail, name='run-detail'),
    path('<uuid:experiment_pk>/runs/<uuid:run_pk>/metrics/', MetricView.as_view(), name='metric-list'),
]
