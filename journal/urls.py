from django.urls import path, include
from .views import TradeViewSet, healthz, home, trades_list, trades_create, trades_edit, dashboard, profile
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'trades', TradeViewSet, basename="trade")

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile, name="profile"),
    path("trades/", trades_list, name="trades_list"),
    path("trades/new/", trades_create, name="trades_create"),
    path("trades/<int:pk>/edit/", trades_edit, name="trades_edit"),
    path("healthz/", healthz),
    path("api/", include(router.urls)),
    path("trades/<int:pk>/delete/", trades_delete, name="trades_delete"),
]