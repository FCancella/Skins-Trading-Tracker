from django.contrib import admin
from .models import Store, StoreItem, StoreLog

class StoreItemInline(admin.TabularInline):
    model = StoreItem
    extra = 0

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'steam_id', 'items_count')
    inlines = [StoreItemInline]

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Itens'

@admin.register(StoreLog)
class StoreLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user_display', 'details_short')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'details', 'action')
    readonly_fields = ('timestamp', 'user', 'store', 'action', 'details')

    def user_display(self, obj):
        return obj.user.username if obj.user else "Visitante"
    user_display.short_description = 'Usuário'

    def details_short(self, obj):
        return (obj.details[:75] + '...') if obj.details and len(obj.details) > 75 else obj.details
    details_short.short_description = 'Detalhes'