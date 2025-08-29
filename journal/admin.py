from django.contrib import admin
from .models import Trade

# Register your models here.
@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'symbol', 'side', 'quantity', 'price']
    search_fields = ['symbol', 'side']
    list_filter = ['side', 'timestamp']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    fieldsets = (
        (None, {"fields": ("symbol", "side", "quantity", "price")}),
        ("Meta", {"fields": ("timestamp", "notes")}),
    )
    def short_notes(self, obj):
        if obj.notes and len(obj.notes) > 30:
            return obj.notes[:30] + "…"
        return obj.notes
    short_notes.short_description = "Notes"
