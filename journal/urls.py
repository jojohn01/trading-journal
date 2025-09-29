from django.urls import path, include
from .views import TradeViewSet, healthz, home, trades_list, trades_create, trades_edit, trades_delete, trades_export_csv, dashboard, profile, trades_charts_page, api_daily_pnl, api_symbol_pnl, api_trade_pnl_series, trades_calendar_page, trades_import
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
    path("trades/export.csv", trades_export_csv, name="trades_export_csv"),
    path("trades/charts/", trades_charts_page, name="trades_charts"),
    path("api/stats/daily-pnl/", api_daily_pnl, name="api_daily_pnl"),
    path("api/stats/symbol-pnl/", api_symbol_pnl, name="api_symbol_pnl"),
    path("api/stats/trade-pnl/", api_trade_pnl_series, name="api_trade_pnl_series"),
    path("trades/calendar/", trades_calendar_page, name="trades_calendar"),
    path("trades/import/", trades_import, name="trades_import"),
]