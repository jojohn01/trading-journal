from django import forms
from .models import Trade

class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = ["symbol", "side", "quantity", "price", "entry_time", "exit_price", "exit_time", "notes"]
        widgets = {
            # Nice browser picker; user enters local time
            "entry_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "exit_time":  forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }