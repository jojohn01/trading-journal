from rest_framework import serializers
from .models import Trade

class TradeSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    pnl = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = ['id', 'symbol', 'side', 'quantity', 'price', 'entry_time', "exit_price", "exit_time", "pnl", 'notes']
        read_only_fields = ['id', "pnl", 'created_at']

    def get_pnl(self, obj):
        """Expose the Trade model’s computed PnL property."""
        return obj.pnl
