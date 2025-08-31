from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets, permissions
from .models import Trade
from .serializers import TradeSerializer

# Create your views here.

def healthz(_request):
    return JsonResponse({"status": "ok"})

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner == request.user


class TradeViewSet(viewsets.ModelViewSet):
    serializer_class = TradeSerializer
    ordering_fields = ["timestamp", "price", "quantity"]
    search_fields = ["symbol", "notes"]
    filterset_fields = ["side", "timestamp"]
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    
    def get_queryset(self):
        # Each user only sees their own trades
        return Trade.objects.filter(owner=self.request.user).order_by("-timestamp")

    def perform_create(self, serializer):
        # Auto-set the owner on create
        serializer.save(owner=self.request.user)