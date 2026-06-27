from rest_framework.routers import DefaultRouter

from .views import AlertRuleViewSet

router = DefaultRouter()
router.register('', AlertRuleViewSet, basename='alert-rule')

urlpatterns = router.urls
