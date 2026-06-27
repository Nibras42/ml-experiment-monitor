from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/experiments/', include('apps.experiments.urls')),
    path('api/alerts/', include('apps.alerts.urls')),
    path('api/pipelines/', include('apps.pipelines.urls')),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
]
