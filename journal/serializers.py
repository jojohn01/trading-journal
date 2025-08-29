from rest_framework import serializers
from .models import Trade

class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ['id', 'symbol', 'side', 'quantity', 'price', 'timestamp', 'notes']
        read_only_fields = ['id', 'timestamp']