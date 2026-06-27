from django.urls import path

from .views import (
    DashboardHomeView,
    ExperimentDetailView,
    ExperimentListView,
    PipelineDetailView,
    PipelineListView,
    RunCompareView,
    RunDetailView,
    WebLoginView,
    WebLogoutView,
)

app_name = 'dashboard'

urlpatterns = [
    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    path('', DashboardHomeView.as_view(), name='home'),
    path('experiments/', ExperimentListView.as_view(), name='experiment-list'),
    path('experiments/<uuid:pk>/', ExperimentDetailView.as_view(), name='experiment-detail'),
    path('experiments/<uuid:experiment_pk>/runs/<uuid:run_pk>/', RunDetailView.as_view(), name='run-detail'),
    path('experiments/<uuid:experiment_pk>/compare/', RunCompareView.as_view(), name='run-compare'),
    path('pipelines/', PipelineListView.as_view(), name='pipeline-list'),
    path('pipelines/<uuid:pk>/', PipelineDetailView.as_view(), name='pipeline-detail'),
]
