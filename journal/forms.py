from django import forms
from .models import Trade, UserTradeSettings
from django.contrib.auth import get_user_model

User = get_user_model()

class TradeForm(forms.ModelForm):
    """Form for creating and editing Trade instances."""
    class Meta:
        model = Trade
        fields = ["symbol", "side", "quantity", "price", "entry_time", "exit_price", "exit_time", "notes"]
        widgets = {
            # Nice browser picker; user enters local time
            "entry_time": forms.DateTimeInput(attrs={"type": "datetime-local", "step": 1}),
            "exit_time":  forms.DateTimeInput(attrs={"type": "datetime-local", "step": 1}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form, optionally setting defaults from user trade settings."""
        user = kwargs.pop("user", None)  # pass request.user from the view
        super().__init__(*args, **kwargs)
        if user and not self.instance.pk:
            s = getattr(user, "trade_settings", None)
            if s:
                if s.default_symbol:
                    self.fields["symbol"].initial = s.default_symbol
                if s.default_side:
                    self.fields["side"].initial = s.default_side
                if s.default_quantity is not None:
                    self.fields["quantity"].initial = s.default_quantity
                if s.default_notes:
                    self.fields["notes"].initial = s.default_notes


class UserTradeSettingsForm(forms.ModelForm):
    """Form for editing user trade default settings."""
    class Meta:
        model = UserTradeSettings
        fields = ["default_symbol", "default_side", "default_quantity", "default_notes"]


class TradesImportForm(forms.Form):
    """Form for importing trades from a file (CSV/XLSX)."""
    file = forms.FileField(help_text="Upload a CSV or XLSX exported from this app.")
    dry_run = forms.BooleanField(required=False, initial=True, help_text="Preview without saving")
    skip_existing = forms.BooleanField(required=False, initial=True, help_text="Skip trades that already exist (by entry time and symbol).")


class ProfileForm(forms.ModelForm):
    """Form for editing user profile information."""
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_username(self):
        """Ensure username is unique (case-insensitive)."""
        uname = self.cleaned_data["username"]
        qs = User.objects.filter(username__iexact=uname).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("That username is taken.")
        return uname