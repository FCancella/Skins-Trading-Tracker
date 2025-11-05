from django.contrib import admin
from .models import ScannedItem, BlackList, SchedulerLogs, Item, Collection, Crate

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

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin view for Items."""
    list_display = ('name', 'price', 'offers', 'price_time', 'rarity', 'category', 'special')
    search_fields = ('name', 'market_hash_name')
    list_filter = ('category', 'rarity', 'special', 'price_time')
    # Deixa os campos M2M como apenas leitura no admin para evitar erros
    readonly_fields = ('collections', 'crates') 

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """Admin view for Collections."""
    list_display = ('name', 'id')
    search_fields = ('name', 'id')

@admin.register(Crate)
class CrateAdmin(admin.ModelAdmin):
    """Admin view for Crates."""
    list_display = ('name', 'id')
    search_fields = ('name', 'id')