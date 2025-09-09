from django.contrib import admin
from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin view for Subscriptions."""
    list_display = ('user', 'status', 'end_date', 'mp_payment_id', 'updated_at')
    list_filter = ('status', 'end_date')
    search_fields = ('user__username', 'mp_payment_id')
    readonly_fields = ('user', 'created_at', 'updated_at')