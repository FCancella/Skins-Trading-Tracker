from django.contrib import admin
from .models import ScannedItem, BlackList, SchedulerLogs

@admin.register(ScannedItem)
class ScannedItemAdmin(admin.ModelAdmin):
    """Admin view for Scanned Items."""
    list_display = ('name', 'price', 'source', 'diff', 'timestamp')
    list_filter = ('source', 'timestamp')
    search_fields = ('name',)

@admin.register(BlackList)
class BlackListAdmin(admin.ModelAdmin):
    """Admin view for Blacklisted Items."""
    list_display = ('name', 'offers', 'timestamp')
    search_fields = ('name',)

@admin.register(SchedulerLogs)
class SchedulerLogsAdmin(admin.ModelAdmin):
    """Admin view for Scheduler Logs."""
    list_display = ('timestamp', 'message')
    list_filter = ('timestamp',)
    search_fields = ('message',)