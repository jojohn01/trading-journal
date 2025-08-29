from django.urls import path, include
from .views import healthz, TradeViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'trades', TradeViewSet)

urlpatterns = [path("healthz/", healthz), path("api/", include(router.urls))]