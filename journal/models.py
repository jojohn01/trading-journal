from django.db import models
from decimal import Decimal
from django.db.models import Q
from django.core.exceptions import ValidationError

# Create your models here.
class Trade(models.Model):
    symbol = models.CharField(max_length=10)
    side = models.CharField(max_length=4, choices=[("BUY", "Buy"), ("SELL", "Sell")])
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    exit_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    exit_timestamp = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.side} {self.quantity} {self.symbol} @ {self.price}"

    @property
    def pnl(self):
        if self.exit_price is None or self.exit_timestamp is None:
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
        # If both set, exit_time cannot be before entry timestamp
        if self.exit_time and self.timestamp and self.exit_time < self.timestamp:
            raise ValidationError({"exit_time": "Exit time cannot be earlier than entry time."})
        # Quantity/price must be positive
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than 0."})
        if self.price is not None and self.price <= 0:
            raise ValidationError({"price": "Entry price must be greater than 0."})
        if self.exit_price is not None and self.exit_price <= 0:
            raise ValidationError({"exit_price": "Exit price must be greater than 0."})

    class Meta:
        ordering = ['-timestamp']