"""
Data models for the `trades` app.

The primary model defined here is ``Trade``, representing a single
Counter‑Strike skin trade. Each trade captures details about the item,
pricing and source information for both purchase and sale, as well as
timestamp fields to record when the trade was entered and when it was
completed. Convenience properties are provided to calculate the profit
or loss and holding duration.
"""

from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    """Represents user profile settings."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False, verbose_name="Perfil Público")

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Trade(models.Model):
    """Model representing a Counter‑Strike skin trade item."""

    SOURCE_CHOICES: list[tuple[str, str]] = [
        ('youpin', 'Youpin'),
        ('skinport', 'Skinport'),
        ('floatdb', 'Floatdb'),
        ('dash_bot', 'Dash BOT'),
        ('dash_p2p', 'Dash P2P'),
        ('buff', 'BUFF'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trades",
        db_index=True,
    )
    item_name = models.CharField(max_length=100)
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    buy_source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    sell_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, null=True, blank=True)
    buy_date = models.DateField(default=timezone.now)
    sell_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["owner"])]
        ordering = [F('sell_date').desc(nulls_first=True),
                    '-buy_date',
                    'item_name']

    def __str__(self) -> str:
        return f"{self.item_name} ({self.buy_price})"

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

class Investment(models.Model):
    """Represents a single investment/contribution made by a user."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.amount} on {self.date}"