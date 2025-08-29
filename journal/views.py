from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets
from .models import Trade
from .serializers import TradeSerializer

# Create your views here.

def healthz(_request):
    return JsonResponse({"status": "ok"})

class TradeViewSet(viewsets.ModelViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    ordering_fields = ["timestamp", "price", "quantity"]
    search_fields = ["symbol", "notes"]