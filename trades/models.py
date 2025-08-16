"""
Data models for the `trades` app.

The primary model defined here is ``Trade``, representing a single
Counter‑Strike skin trade. Each trade captures details about the item,
pricing and source information for both purchase and sale, as well as
timestamp fields to record when the trade was entered and when it was
completed. Convenience properties are provided to calculate the profit
or loss and holding duration.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from django.db import models
from django.utils import timezone


class Trade(models.Model):
    """Model representing a Counter‑Strike skin trade item."""

    SOURCE_CHOICES: list[tuple[str, str]] = [
        ('youpin', 'Youpin'),
        ('skinport', 'Skinport'),
        ('floatdb', 'Floatdb'),
        ('dash_bot', 'Dash BOT'),
        ('dash_p2p', 'Dash P2P'),
    ]

    item_name = models.CharField(max_length=100)
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    buy_source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    sell_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, null=True, blank=True)
    date_of_purchase = models.DateField(default=timezone.now)
    date_sold = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-date_of_purchase', 'item_name']

    def __str__(self) -> str:
        return f"{self.item_name} ({self.buy_price})"

    @property
    def pnl(self) -> Optional[Decimal]:
        """Return the profit or loss for this trade if it is sold.

        If the trade has not been sold yet (sell_price is None), return None.
        PnL is calculated as sell_price minus buy_price.
        """
        if self.sell_price is None:
            return None
        return self.sell_price - self.buy_price

    @property
    def pnl_value(self):
        if self.sell_price is None:
            return None
        return (self.sell_price or Decimal("0")) - (self.buy_price or Decimal("0"))

    @property
    def pnl_percent(self):
        if self.sell_price is None or not self.buy_price:
            return None
        return (self.pnl_value / self.buy_price) * Decimal("100")
