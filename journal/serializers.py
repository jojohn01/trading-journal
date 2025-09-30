from rest_framework import serializers
from .models import Trade

class TradeSerializer(serializers.ModelSerializer):
    """Serializer for the Trade model, including computed PnL and owner display."""
    owner = serializers.StringRelatedField(read_only=True)
    pnl = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = ['id', 'symbol', 'side', 'quantity', 'price', 'entry_time', "exit_price", "exit_time", "pnl", 'notes']
        read_only_fields = ['id', "pnl", 'created_at']

    def get_pnl(self, obj):
        """Return the computed profit and loss for the trade."""
        return obj.pnl
