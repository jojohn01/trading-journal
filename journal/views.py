from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets, permissions
from .models import Trade
from .serializers import TradeSerializer
from .forms import TradeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


# Create your views here.

def healthz(_request):
    return JsonResponse({"status": "ok"})

def home(request):
    return render(request, "home.html")



@login_required
def trades_list(request):
    trades = Trade.objects.filter(owner=request.user).order_by("-entry_time")
    return render(request, "trades/list.html", {"trades": trades})

@login_required
def trades_create(request):
    if request.method == "POST":
        form = TradeForm(request.POST)
        if form.is_valid():
            trade = form.save(commit=False)
            trade.owner = request.user
            trade.save()
            messages.success(request, "Trade created successfully.")
            return redirect("trades_list")
    else:
        form = TradeForm()
    return render(request, "trades/create.html", {"form": form})


@login_required
def trades_edit(request, pk):
    trade = get_object_or_404(Trade, pk=pk, owner=request.user)
    if request.method == "POST":
        form = TradeForm(request.POST, instance=trade)
        if form.is_valid():
            form.save()
            messages.success(request, "Trade updated successfully.")
            return redirect("trades_list")
    else:
        form = TradeForm(instance=trade)
    return render(request, "trades/edit.html", {"form": form, "trade": trade})


@login_required
def dashboard(request):
    # Minimal skeleton: a couple of counts for now
    trades = Trade.objects.filter(owner=request.user)
    context = {
        "trade_count": trades.count(),
        "open_count": trades.filter(exit_time__isnull=True).count(),
        "closed_count": trades.filter(exit_time__isnull=False).count(),
        # later: totals, PnL chart data, recent trades, etc.
    }
    return render(request, "dashboard.html", context)

@login_required
def profile(request):
    # Skeleton profile page — later we can add edit form / avatar / token, etc.
    return render(request, "profile.html", {"user_obj": request.user})


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner == request.user


class TradeViewSet(viewsets.ModelViewSet):
    serializer_class = TradeSerializer
    ordering_fields = ["entry_time", "price", "quantity"]
    search_fields = ["symbol", "notes"]
    filterset_fields = ["side", "entry_time"]
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    
    def get_queryset(self):
        # Each user only sees their own trades
        return Trade.objects.filter(owner=self.request.user).order_by("-entry_time")

    def perform_create(self, serializer):
        # Auto-set the owner on create
        serializer.save(owner=self.request.user)