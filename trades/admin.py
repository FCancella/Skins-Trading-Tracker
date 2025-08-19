"""
Admin configuration for the `trades` app.

This module registers the Trade model with the Django admin so that records
can be created, read, updated and deleted through the built‑in admin
interface. It uses a list display to show important fields in the model list
view.
"""
from __future__ import annotations

from django.contrib import admin

from .models import Trade, Investment


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    """Customization for how the Trade model appears in the admin."""

    list_display = (
        'item_name',
        'buy_price',
        'sell_price',
        'buy_source',
        'sell_source',
        'date_of_purchase',
        'date_sold',
        'pnl_value',
        'pnl_percent',
        'owner',
    )
    list_filter = ('buy_source', 'sell_source', 'date_of_purchase', 'date_sold')
    search_fields = ('item_name',)

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    """Admin view for Investments."""
    list_display = ('owner', 'amount', 'description', 'date')
    list_filter = ('owner', 'date')
    search_fields = ('description',)