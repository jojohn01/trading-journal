from django.db import models
from decimal import Decimal
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone



# Create your models here.
class Trade(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trades", null=True, blank=True)


    symbol = models.CharField(max_length=10)
    side = models.CharField(max_length=4, choices=[("BUY", "Buy"), ("SELL", "Sell")])
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    entry_time = models.DateTimeField(default=timezone.now)
    price = models.DecimalField(max_digits=10, decimal_places=4)
    exit_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.side} {self.quantity} {self.symbol} @ {self.price}"

    @property
    def pnl(self):
        if self.exit_price is None or self.exit_time is None:
            return None
        q = Decimal(self.quantity)
        entry = Decimal(self.price)
        exit = Decimal(self.exit_price)
        if self.side == "BUY":
            return (exit - entry) * q
        else:
            return (entry - exit) * q

    def clean(self):
        super().clean()
        if (self.exit_price is None) ^ (self.exit_time is None):
            raise ValidationError("Exit price and exit time must be set together (both or neither).")
        # If both set, exit_time cannot be before entry_time
        if self.exit_time and self.entry_time and self.exit_time < self.entry_time:
            raise ValidationError({"exit_time": "Exit time cannot be earlier than entry time."})
        # Quantity/price must be positive
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than 0."})
        if self.price is not None and self.price <= 0:
            raise ValidationError({"price": "Entry price must be greater than 0."})
        if self.exit_price is not None and self.exit_price <= 0:
            raise ValidationError({"exit_price": "Exit price must be greater than 0."})

    class Meta:
        ordering = ['-entry_time']
        constraints = [
        models.CheckConstraint(check=Q(quantity__gt=0), name="trade_quantity_gt_0"),
        models.CheckConstraint(check=Q(price__gt=0), name="trade_entry_price_gt_0"),
        models.CheckConstraint(
            check=(
                (Q(exit_price__isnull=True) & Q(exit_time__isnull=True)) |
                (Q(exit_price__isnull=False) & Q(exit_time__isnull=False))
            ),
            name="trade_exit_fields_both_or_neither",
        ),
    ]

    def save(self, *args, **kwargs):
        if self.symbol:
            self.symbol = self.symbol.upper().strip()
        super().save(*args, **kwargs)

class UserTradeSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trade_settings")

    # All optional — only applied if set
    default_symbol = models.CharField(max_length=32, blank=True)
    default_side = models.CharField(max_length=4, choices=[("BUY", "Buy"), ("SELL", "Sell")], blank=True)
    default_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    default_notes = models.TextField(blank=True)
    # add others as you like: default_symbol, default_price, etc.

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} settings"