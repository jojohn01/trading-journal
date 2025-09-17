from django import forms
from .models import Trade

class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = ["symbol", "side", "quantity", "price", "entry_time", "exit_price", "exit_time", "notes"]
        widgets = {
            # Nice browser picker; user enters local time
            "entry_time": forms.DateTimeInput(attrs={"type": "datetime-local", "step": 1}),
            "exit_time":  forms.DateTimeInput(attrs={"type": "datetime-local", "step": 1}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # pass request.user from the view
        super().__init__(*args, **kwargs)
        if user and not self.instance.pk:
            s = getattr(user, "trade_settings", None)
            if s:
                if s.default_side:
                    self.fields["side"].initial = s.default_side
                if s.default_quantity is not None:
                    self.fields["quantity"].initial = s.default_quantity
                if s.default_notes:
                    self.fields["notes"].initial = s.default_notes


class UserTradeSettingsForm(forms.ModelForm):
    class Meta:
        model = UserTradeSettings
        fields = ["default_side", "default_quantity", "default_notes"]