"""
URL configuration for the Counter‑Strike skin trade management project.
"""
from __future__ import annotations

from trades import views as trade_views
from scanner import views as scanner_views
from subscriptions import views as subscription_views
from django.urls import include, path
from django.contrib import admin
from django.conf import settings

def global_settings_context(request):
    """Expõe a configuração PAYMENT para todos os templates."""
    return {'PAYMENT_ENABLED': settings.PAYMENT}

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("accounts/", include("django.contrib.auth.urls")),
    path('accounts/', include('allauth.urls')),
    # Já está incluido em "django.contrib.auth.urls"
    # path("accounts/password_change/", PasswordChangeView.as_view(template_name='registration/passwordChangeForm.html),

    path('i18n/', include('django.conf.urls.i18n')),

    path("", trade_views.home, name="home"),
    path("portfolio/", trade_views.index, name="index"),
    path("observer/", trade_views.observer, name="observer"),
    path("profile/toggle/", trade_views.toggle_profile_public, name="toggle_profile_public"),
    path("profile/change-username/", trade_views.change_username, name="change_username"), # <-- ADICIONE ESTA LINHA
    path("export/", trade_views.export_portfolio, name="export_portfolio"),
    path("price-history/<int:trade_id>/", trade_views.price_history, name="price_history"),
    path("get-trade-form/<int:trade_id>/", trade_views.get_trade_form, name="get_trade_form"),

    path("scanner/", scanner_views.scanner_view, name="scanner_list"),
    path("scanner/logs/", scanner_views.scheduler_logs_view, name="scheduler_logs"),
    path("scanner/api/logs/", scanner_views.log_scheduler_event, name="scanner_api_logs"),
    
    # Endpoints da API do Scanner
    path("scanner/api/add-items/", scanner_views.scanner_api_add_items, name="scanner_api_add_items"),
    path("scanner/api/items-to-update/", scanner_views.get_items_to_update, name="scanner_api_get_items_to_update"),
    path("scanner/api/update-buff-prices/", scanner_views.update_buff_prices, name="scanner_api_update_buff_prices"),
    path("scanner/api/calculate-differences/", scanner_views.calculate_differences, name="scanner_api_calculate_differences"),
    path("scanner/api/items-to-price/", scanner_views.get_items_to_price, name="scanner_api_get_items_to_price"),
    path("scanner/api/get-item-batch/", scanner_views.get_items_for_pricing, name="scanner_api_get_item_batch"),
    path("scanner/api/submit-item-batch/", scanner_views.submit_item_prices, name="scanner_api_submit_item_batch"),

    # Payment URLs
    path("subscription/", subscription_views.subscription_details, name="subscription_details"),
    path("plans/", subscription_views.plans, name="plans"),
    path("activate-trial/", subscription_views.activate_trial, name="activate_trial"),
    path("create-payment/", subscription_views.create_payment, name="create_payment"),
    path("retry-payment/", subscription_views.retry_payment, name="retry_payment"),
    path("payment-success/", subscription_views.payment_success, name="payment_success"),
    path("payment-failure/", subscription_views.payment_failure, name="payment_failure"),
    path("payment-pending/", subscription_views.payment_pending, name="payment_pending"),
    path("mp-webhook/", subscription_views.mp_webhook, name="mp_webhook"),
]