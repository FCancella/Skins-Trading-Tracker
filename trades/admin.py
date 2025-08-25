"""
Admin configuration for the `trades` app.

This module registers the Trade model with the Django admin so that records
can be created, read, updated and deleted through the built‑in admin
interface. It uses a list display to show important fields in the model list
view.
"""
from __future__ import annotations

from django.contrib import admin

from .models import Trade, Investment, Profile


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    """Customization for how the Trade model appears in the admin."""

    list_display = (
        'item_name',
        'buy_price',
        'sell_price',
        'buy_source',
        'sell_source',
        'buy_date',
        'sell_date',
        'pnl_value',
        'pnl_percent',
        'owner',
    )
    list_filter = ('buy_source', 'sell_source', 'buy_date', 'sell_date')
    search_fields = ('item_name',)

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    """Admin view for Investments."""
    list_display = ('owner', 'amount', 'description', 'date')
    list_filter = ('owner', 'date')
    search_fields = ('description',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin view for Profiles."""
    list_display = ('user', 'is_public')
    list_filter = ('is_public',)
    search_fields = ('user__username',)