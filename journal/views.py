from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets, permissions
from .models import Trade, UserTradeSettings
from .serializers import TradeSerializer
from .forms import TradeForm, UserTradeSettingsForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import F, Case, When, Value, DecimalField, ExpressionWrapper, Q, Sum, Count, IntegerField
import csv
from django.db.models.functions import TruncDate
import calendar as _cal
from datetime import date, datetime, timedelta

PNL_EXPR = Case(
    When(side="BUY",  then=(F("exit_price") - F("price")) * F("quantity")),
    When(side="SELL", then=(F("price") - F("exit_price")) * F("quantity")),
    default=None,
    output_field=DecimalField(max_digits=16, decimal_places=2),
)

def healthz(_request):
    return JsonResponse({"status": "ok"})

def home(request):
    return render(request, "home.html")

def _annotate_pnl(qs):
    buy_expr  = (F("exit_price") - F("price")) * F("quantity")
    sell_expr = (F("price") - F("exit_price")) * F("quantity")
    return qs.annotate(
        pnl_value=Case(
            When(exit_price__isnull=True, then=Value(None)),
            When(side="BUY",  then=ExpressionWrapper(buy_expr,  output_field=DecimalField(max_digits=12, decimal_places=2))),
            When(side="SELL", then=ExpressionWrapper(sell_expr, output_field=DecimalField(max_digits=12, decimal_places=2))),
            default=Value(None),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

# --- helper: parse datetime from query params (accepts date or datetime-local) ---
def _parse_dt(s: str | None):
    if not s:
        return None
    fmts = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
    for fmt in fmts:
        try:
            dt = timezone.datetime.strptime(s, fmt)
            return timezone.make_aware(dt)
        except ValueError:
            continue
    return None


def _month_bounds(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return start, next_month  # [start, next_month)

def _color_for_pnl(pnl: float | None, max_abs: float) -> str:
    """
    Return a hex color for the cell background.
    - Positive => green scale
    - Negative => red scale
    - None/0 => neutral light gray
    Intensity ∝ |pnl| / max_abs with a floor for visibility.
    """
    if not pnl or max_abs <= 0:
        return "#f2f2f2"  # neutral
    ratio = min(abs(pnl) / max_abs, 1.0)
    ratio = max(ratio, 0.15)  # minimum visible tint
    # Simple lerp between light and stronger tone
    if pnl > 0:
        # green-ish
        r, g, b = (220 - int(120 * ratio), 255 - int(60 * ratio), 220 - int(120 * ratio))
    else:
        # red-ish
        r, g, b = (255 - int(60 * ratio), 220 - int(120 * ratio), 220 - int(120 * ratio))
    return f"#{r:02x}{g:02x}{b:02x}"

@login_required
def trades_calendar_page(request):
    """
    Monthly calendar colored by realized PnL.
    Hover shows PnL, #trades, wins, win rate. Click a day to jump to filtered list.
    """
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    start, next_month = _month_bounds(year, month)

    # Week layout & headers (0=Mon, 6=Sun)
    first_weekday = 0
    cal = _cal.Calendar(firstweekday=first_weekday)
    weekdays = [_cal.day_abbr[(first_weekday + i) % 7] for i in range(7)]
    weeks = cal.monthdatescalendar(year, month)

    # ----- FIXED: define once, then reuse consistently -----
    pnl_value_expr = ExpressionWrapper(
        PNL_EXPR, output_field=DecimalField(max_digits=16, decimal_places=2)
    )

    # Closed trades in the month (by exit_time) → per-day stats
    qs = (
        Trade.objects
        .filter(
            owner=request.user,
            exit_price__isnull=False,
            exit_time__gte=start,
            exit_time__lt=next_month,
        )
        # Step A: add day + pnl_value
        .annotate(
            day=TruncDate("exit_time"),
            pnl_value=pnl_value_expr,
        )
        # Step B: now we can reference the annotation name 'pnl_value'
        .annotate(
            is_win=Case(
                When(pnl_value__gt=0, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        # Step C: group & aggregate
        .values("day")
        .annotate(
            pnl=Sum("pnl_value"),
            trades=Count("id"),
            wins=Sum("is_win"),
        )
        .order_by("day")
    )


    # Build map of day → stats
    day_stats = {}
    for row in qs:
        d = row["day"]
        pnl = float(row["pnl"] or 0)
        trades = int(row["trades"] or 0)
        wins = int(row["wins"] or 0)
        win_rate = (wins / trades * 100.0) if trades else 0.0
        day_stats[d] = {"pnl": pnl, "trades": trades, "wins": wins, "win_rate": win_rate}

    max_abs = max((abs(v["pnl"]) for v in day_stats.values()), default=0.0)

    # Build cells
    grid = []
    for week in weeks:
        row = []
        for d in week:
            in_month = (d.month == month)
            stats = day_stats.get(d) if in_month else None
            pnl = stats["pnl"] if stats else None
            color = _color_for_pnl(pnl, max_abs) if in_month else "#ffffff"
            link = f"/trades/?start={d.isoformat()}&end={d.isoformat()}" if in_month else None

            if stats:
                tooltip = (
                    f"{d.isoformat()}\n"
                    f"PnL: {stats['pnl']:.2f}\n"
                    f"Trades: {stats['trades']}  "
                    f"Wins: {stats['wins']}  "
                    f"Win rate: {stats['win_rate']:.0f}%"
                )
            elif in_month:
                tooltip = f"{d.isoformat()}\nNo closed trades"
            else:
                tooltip = ""

            row.append({
                "date": d,
                "in_month": in_month,
                "pnl": pnl,
                "color": color,
                "link": link,
                "tooltip": tooltip,
            })
        grid.append(row)

    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)

    context = {
        "year": year,
        "month": month,
        "month_name": _cal.month_name[month],
        "weekdays": weekdays,
        "grid": grid,
        "has_data": max_abs > 0,
        "legend_max": f"{max_abs:.2f}",
        "prev_link": f"?year={prev_y}&month={prev_m}",
        "next_link": f"?year={next_y}&month={next_m}",
    }
    return render(request, "trades/calendar.html", context)
# Create your views here.

@login_required
def api_trade_pnl_series(request):
    """
    Returns each CLOSED trade's realized PnL in chronological order (by exit_time).
    Filterable via ?symbol=&side=&start=&end= (same semantics as your other chart APIs).
    """
    qs = Trade.objects.filter(owner=request.user, exit_price__isnull=False)

    # filters
    symbol = (request.GET.get("symbol") or "").strip()
    side   = (request.GET.get("side") or "").strip().upper()
    start  = (request.GET.get("start") or "").strip()
    end    = (request.GET.get("end") or "").strip()

    if symbol:
        qs = qs.filter(symbol__icontains=symbol)
    if side in {"BUY", "SELL"}:
        qs = qs.filter(side=side)

    start_dt = _parse_dt(start)
    end_dt   = _parse_dt(end)
    if start_dt:
        qs = qs.filter(exit_time__gte=start_dt)
    if end_dt:
        if len(end) == 10:
            qs = qs.filter(exit_time__lt=_parse_dt(end) + timezone.timedelta(days=1))
        else:
            qs = qs.filter(exit_time__lte=end_dt)

    # compute per-trade realized PnL (adjust to subtract fees if you track them)
    pnl_expr = ExpressionWrapper(PNL_EXPR, output_field=DecimalField(max_digits=16, decimal_places=2))
    qs = qs.order_by("exit_time").values("id", "exit_time", "symbol").annotate(pnl=pnl_expr)

    labels = [row["exit_time"].isoformat(timespec="seconds") for row in qs]  # x-axis labels
    values = [float(row["pnl"] or 0) for row in qs]

    return JsonResponse({"labels": labels, "values": values})



@login_required
def trades_charts_page(request):
    return render(request, "trades/charts.html")

@login_required
def api_daily_pnl(request):
    qs = Trade.objects.filter(owner=request.user, exit_price__isnull=False)

    # filters: symbol/side/date range (by exit_time)
    symbol = (request.GET.get("symbol") or "").strip()
    side   = (request.GET.get("side") or "").strip().upper()
    start  = (request.GET.get("start") or "").strip()
    end    = (request.GET.get("end") or "").strip()

    if symbol:
        qs = qs.filter(symbol__icontains=symbol)
    if side in {"BUY", "SELL"}:
        qs = qs.filter(side=side)

    start_dt = _parse_dt(start)
    end_dt   = _parse_dt(end)
    if start_dt:
        qs = qs.filter(exit_time__gte=start_dt)
    if end_dt:
        if len(end) == 10:
            qs = qs.filter(exit_time__lt=_parse_dt(end) + timezone.timedelta(days=1))
        else:
            qs = qs.filter(exit_time__lte=end_dt)

    qs = qs.annotate(day=TruncDate("exit_time")).values("day") \
           .annotate(pnl=Sum(ExpressionWrapper(PNL_EXPR, output_field=DecimalField(max_digits=16, decimal_places=2)))) \
           .order_by("day")

    # return both labels and values, and also the signed values for shadow coloring
    labels = [row["day"].isoformat() for row in qs]
    values = [float(row["pnl"] or 0) for row in qs]
    return JsonResponse({"labels": labels, "values": values})


@login_required
def api_symbol_pnl(request):
    qs = Trade.objects.filter(owner=request.user, exit_price__isnull=False)

    # same filters; aggregating by symbol after filters
    symbol = (request.GET.get("symbol") or "").strip()
    side   = (request.GET.get("side") or "").strip().upper()
    start  = (request.GET.get("start") or "").strip()
    end    = (request.GET.get("end") or "").strip()

    if symbol:
        qs = qs.filter(symbol__icontains=symbol)
    if side in {"BUY", "SELL"}:
        qs = qs.filter(side=side)

    start_dt = _parse_dt(start)
    end_dt   = _parse_dt(end)
    if start_dt:
        qs = qs.filter(exit_time__gte=start_dt)
    if end_dt:
        if len(end) == 10:
            qs = qs.filter(exit_time__lt=_parse_dt(end) + timezone.timedelta(days=1))
        else:
            qs = qs.filter(exit_time__lte=end_dt)

    qs = qs.values("symbol").annotate(
        pnl=Sum(ExpressionWrapper(PNL_EXPR, output_field=DecimalField(max_digits=16, decimal_places=2)))
    ).order_by("symbol")

    return JsonResponse({
        "labels": [row["symbol"] for row in qs],
        "values": [float(row["pnl"] or 0) for row in qs],
    })



@login_required
def trades_list(request):
    trades = Trade.objects.filter(owner=request.user).order_by("-entry_time")
    return render(request, "trades/list.html", {"trades": trades})

@login_required
def trades_create(request):
    if request.method == "POST":
        form = TradeForm(request.POST, user=request.user)
        if form.is_valid():
            trade = form.save(commit=False)
            trade.owner = request.user
            trade.save()
            messages.success(request, "Trade created successfully.")
            return redirect("trades_list")
    else:
        form = TradeForm(user=request.user)
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
def trades_delete(request, pk):
    trade = get_object_or_404(Trade, pk=pk, owner=request.user)
    if request.method == "POST":
        trade.delete()
        from django.contrib import messages
        messages.warning(request, "Trade deleted.")
        return redirect("trades_list")
    return render(request, "trades/delete_confirm.html", {"trade": trade})


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
    settings_obj, _ = UserTradeSettings.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserTradeSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile defaults saved.")
            return redirect("profile")
    else:
        form = UserTradeSettingsForm(instance=settings_obj)
    return render(request, "profile.html", {"user_obj": request.user, "settings_form": form})

@login_required
def trades_list(request):
    qs = Trade.objects.filter(owner=request.user)

    # filters from querystring
    symbol = (request.GET.get("symbol") or "").strip()
    side   = (request.GET.get("side") or "").strip().upper()
    start  = (request.GET.get("start") or "").strip()  # YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS]
    end    = (request.GET.get("end") or "").strip()

    if symbol:
        qs = qs.filter(symbol__icontains=symbol)
    if side in {"BUY", "SELL"}:
        qs = qs.filter(side=side)

    start_dt = _parse_dt(start)
    end_dt   = _parse_dt(end)

    if start_dt:
        qs = qs.filter(entry_time__gte=start_dt)
    if end_dt:
        # if end is just a date (length 10), treat as inclusive end-of-day
        if len(end) == 10:
            qs = qs.filter(entry_time__lt=end_dt + timezone.timedelta(days=1))
        else:
            qs = qs.filter(entry_time__lte=end_dt)

    qs = _annotate_pnl(qs).order_by("-entry_time")

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    context = {
        "trades": page_obj,
        "page_obj": page_obj,
        "filters": {"symbol": symbol, "side": side, "start": start, "end": end},
    }
    return render(request, "trades/list.html", context)

@login_required
def trades_export_csv(request):
    qs = Trade.objects.filter(owner=request.user)

    # same filters as trades_list
    symbol = (request.GET.get("symbol") or "").strip()
    side   = (request.GET.get("side") or "").strip().upper()
    start  = (request.GET.get("start") or "").strip()
    end    = (request.GET.get("end") or "").strip()

    if symbol:
        qs = qs.filter(symbol__icontains=symbol)
    if side in {"BUY", "SELL"}:
        qs = qs.filter(side=side)

    start_dt = _parse_dt(start)
    end_dt   = _parse_dt(end)
    if start_dt:
        qs = qs.filter(entry_time__gte=start_dt)
    if end_dt:
        if len(end) == 10:
            qs = qs.filter(entry_time__lt=end_dt + timezone.timedelta(days=1))
        else:
            qs = qs.filter(entry_time__lte=end_dt)

    qs = _annotate_pnl(qs).order_by("-entry_time")

    # stream CSV
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="trades_export.csv"'
    w = csv.writer(resp)
    w.writerow(["id","entry_time","symbol","side","quantity","price","exit_price","exit_time","pnl","notes"])
    for t in qs:
        w.writerow([
            t.id,
            t.entry_time.isoformat(timespec="seconds"),
            t.symbol,
            t.side,
            t.quantity,
            t.price,
            "" if t.exit_price is None else t.exit_price,
            "" if not t.exit_time else t.exit_time.isoformat(timespec="seconds"),
            "" if t.pnl_value is None else f"{t.pnl_value:.2f}",
            (t.notes or "").replace("\r", " ").replace("\n", " "),
        ])
    return resp


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