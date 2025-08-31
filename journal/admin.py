from django.contrib import admin
from .models import Trade

# Register your models here.
@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    # Table columns
    list_display = ['timestamp', 'symbol', 'side', 'quantity', 'price']
    autocomplete_fields = ("owner",)
    readonly_fields = ("owner", "timestamp")
    search_fields = ['symbol', 'side']
    list_filter = ['side', 'timestamp']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    fieldsets = (
        (None, {"fields": ("symbol", "side", "quantity", "price")}),
        ("Meta", {"fields": ("timestamp", "notes")}),
    )

    def pnl(self, obj):
        """
        Read-only computed PnL:
        - BUY: (exit - entry) * qty
        - SELL: (entry - exit) * qty
        - None if trade is still open (no exit fields)
        """
        return obj.pnl

    pnl.short_description = "PnL"

    def status(self, obj):
        """Show Open/Closed based on exit fields."""
        return "Closed" if obj.exit_price is not None else "Open"

    def short_notes(self, obj):
        if obj.notes and len(obj.notes) > 30:
            return obj.notes[:30] + "…"
        return obj.notes
    short_notes.short_description = "Notes"
