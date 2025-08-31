from rest_framework import serializers
from .models import Trade

class TradeSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    pnl = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = ['id', 'owner', 'symbol', 'side', 'quantity', 'price', 'timestamp', 'notes', "exit_price", "exit_timestamp", "pnl"]
        read_only_fields = ['id', 'timestamp', "pnl", 'owner']

    def get_pnl(self, obj):
        """Expose the Trade model’s computed PnL property."""
        return obj.pnl
