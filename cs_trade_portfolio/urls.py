"""
URL configuration for the Counter‑Strike skin trade management project.
"""
from __future__ import annotations

from trades import views as trade_views
from scanner import views as scanner_views
from django.urls import include, path
from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),

    path("", trade_views.home, name="home"),
    path("portfolio/", trade_views.index, name="index"),
    path("observer/", trade_views.observer, name="observer"),
    path("signup/", trade_views.signup, name="signup"),
    path("profile/toggle/", trade_views.toggle_profile_public, name="toggle_profile_public"),
    path("export/", trade_views.export_portfolio, name="export_portfolio"),

    path("scanner/", scanner_views.scanner_view, name="scanner_list"),
    path("scanner/logs/", scanner_views.scheduler_logs_view, name="scheduler_logs"),
    path("scanner/api/logs/", scanner_views.log_scheduler_event, name="scanner_api_logs"),
    
    # Endpoints da API do Scanner
    path("scanner/api/add-items/", scanner_views.scanner_api_add_items, name="scanner_api_add_items"),
    path("scanner/api/items-to-update/", scanner_views.get_items_to_update, name="scanner_api_get_items_to_update"),
    path("scanner/api/update-buff-prices/", scanner_views.update_buff_prices, name="scanner_api_update_buff_prices"),
    path("scanner/api/calculate-differences/", scanner_views.calculate_differences, name="scanner_api_calculate_differences"),
    path("scanner/api/items-to-price/", scanner_views.get_items_to_price, name="scanner_api_get_items_to_price"),
]