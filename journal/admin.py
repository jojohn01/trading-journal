from django.contrib import admin
from .models import Trade, UserTradeSettings
from django.db.models import (
    F, Q, Value, Case, When, DecimalField, ExpressionWrapper
)
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.account.admin import EmailAddressAdmin, EmailConfirmationAdmin
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.admin import SocialAppAdmin, SocialAccountAdmin, SocialTokenAdmin
from django.contrib.auth import get_user_model

class StatusFilter(admin.SimpleListFilter):
    """Admin filter for trade status (open/closed)."""
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        """Return filter options for status."""
        return (("open", "Open"), ("closed", "Closed"))

    def queryset(self, request, queryset):
        """Filter queryset by open or closed status."""
        if self.value() == "open":
            return queryset.filter(exit_price__isnull=True, exit_time__isnull=True)
        if self.value() == "closed":
            return queryset.filter(Q(exit_price__isnull=False) | Q(exit_time__isnull=False))
        return queryset

class PnLFilter(admin.SimpleListFilter):
    """Admin filter for profit and loss (PnL)."""
    title = "PnL"
    parameter_name = "pnl"

    def lookups(self, request, model_admin):
        """Return filter options for PnL."""
        return (("g", "Gain (≥ 0)"), ("l", "Loss (< 0)"))

    def queryset(self, request, queryset):
        """Filter queryset by PnL value."""
        if self.value() == "g":
            return queryset.filter(pnl_value__gte=0)
        if self.value() == "l":
            return queryset.filter(pnl_value__lt=0)
        return queryset


@admin.register(UserTradeSettings)
class UserTradeSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for UserTradeSettings model."""
    list_display = ("user", "default_symbol", "default_side", "default_quantity", "updated_at")
    search_fields = ("user__username", "user__email")


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    """Admin configuration for the Trade model."""
    list_display = (
        "entry_time", "owner", "symbol", "side",
        "quantity", "price", "exit_price", "pnl", "status", "short_notes",
        "created_at",
    )
    list_display_links = ("entry_time", "symbol")
    search_fields = ("symbol", "notes")
    list_filter = ("side", "entry_time", StatusFilter, PnLFilter)
    date_hierarchy = "entry_time"
    ordering = ("-entry_time",)
    list_per_page = 25
    autocomplete_fields = ("owner",)
    readonly_fields = ("owner", "created_at",)
    fieldsets = (
        (None, {
            "fields": ("symbol", "side", "quantity", "price", "notes")
        }),
        ("Timing", {
            "fields": ("entry_time", "exit_price", "exit_time")
        }),
        ("System", {
            "fields": ("owner", "created_at"),
        }),
    )

    def get_queryset(self, request):
        """
        Annotate queryset with PnL value for admin display and filtering.
        BUY:  (exit - entry) * qty
        SELL: (entry - exit) * qty
        If exit_price is NULL (open trade), PnL is NULL.
        """
        qs = super().get_queryset(request)
        buy_expr  = (F("exit_price") - F("price")) * F("quantity")
        sell_expr = (F("price") - F("exit_price")) * F("quantity")

        pnl_case = Case(
            When(exit_price__isnull=True, then=Value(None)),
            When(side="BUY",  then=ExpressionWrapper(buy_expr,  output_field=DecimalField(max_digits=12, decimal_places=2))),
            When(side="SELL", then=ExpressionWrapper(sell_expr, output_field=DecimalField(max_digits=12, decimal_places=2))),
            default=Value(None),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        return qs.annotate(pnl_value=pnl_case)

    def pnl(self, obj):
        """Return annotated PnL value for display."""
        return getattr(obj, "pnl_value", None)
    pnl.short_description = "PnL"
    pnl.admin_order_field = "pnl_value"

    def status(self, obj):
        """Return 'Closed' if exit recorded, else 'Open'."""
        return "Closed" if (obj.exit_price is not None or obj.exit_time is not None) else "Open"

    def short_notes(self, obj):
        """Return truncated notes for table display."""
        if obj.notes and len(obj.notes) > 30:
            return obj.notes[:30] + "…"
        return obj.notes
    short_notes.short_description = "Notes"

    def save_model(self, request, obj, form, change):
        """Auto-assign owner on create."""
        if not change and not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)



if not admin.site.is_registered(EmailAddress):
    admin.site.register(EmailAddress, EmailAddressAdmin)
if not admin.site.is_registered(EmailConfirmation):
    admin.site.register(EmailConfirmation, EmailConfirmationAdmin)
if not admin.site.is_registered(SocialApp):
    admin.site.register(SocialApp, SocialAppAdmin)
if not admin.site.is_registered(SocialAccount):
    admin.site.register(SocialAccount, SocialAccountAdmin)
if not admin.site.is_registered(SocialToken):
    admin.site.register(SocialToken, SocialTokenAdmin)


class EmailAddressInline(admin.TabularInline):
    """Inline admin for user email addresses."""
    model = EmailAddress
    extra = 0
    fields = ("email", "primary", "verified")
    readonly_fields = ()

User = get_user_model()

try:
    # If someone already registered a custom UserAdmin, extend it; otherwise register fresh
    from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
    class UserAdmin(DjangoUserAdmin):
        """Custom UserAdmin with email address inline."""
        inlines = list(getattr(DjangoUserAdmin, "inlines", [])) + [EmailAddressInline]
    admin.site.unregister(User)
    admin.site.register(User, UserAdmin)
except admin.sites.NotRegistered:
    class UserAdmin(admin.ModelAdmin):
        """Fallback UserAdmin with email address inline."""
        inlines = [EmailAddressInline]
    admin.site.register(User, UserAdmin)