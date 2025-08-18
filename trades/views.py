"""
Views for the `trades` app.

This module defines function‑based views that handle listing trades,
creating new trades, updating sell information, and computing summary
statistics for the portfolio. The main page (`index`) brings together all
components into a single responsive layout.
"""
from __future__ import annotations

from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from django.db.models import F, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SellTradeForm, TradeForm
from .models import Trade

@login_required
def index(request: HttpRequest) -> HttpResponse:
    """Serve the single-page app: summary, add form, and portfolio table."""

    # Handle adding a new trade
    if request.method == "POST" and request.POST.get("action") == "add":
        add_form = TradeForm(request.POST)
        if add_form.is_valid():
            add_form.save(owner=request.user)
            return redirect("index")
        
    # Handle updating an existing trade's sell details
    elif request.method == "POST" and request.POST.get("action") == "sell":
        trade_id = request.POST.get("trade_id")
        trade = Trade.objects.get(pk=trade_id)
        form = SellTradeForm(request.POST, instance=trade)
        if form.is_valid():
            form.save()
            return redirect("index")

    # GET request – render the page
    trades = Trade.objects.filter(owner=request.user).order_by("-date_of_purchase")

    today = timezone.localdate()

    open_qs = trades.filter(sell_price__isnull=True)
    closed_qs = trades.filter(sell_price__isnull=False)

    # Cost basis (buy totals)
    agg_total = trades.aggregate(buy_sum=Sum("buy_price"))
    agg_open = open_qs.aggregate(buy_sum=Sum("buy_price"))
    agg_closed = closed_qs.aggregate(sell_sum=Sum("sell_price"))

    total_items_value = agg_total["buy_sum"] or 0.0
    open_positions_value = agg_open["buy_sum"] or 0.0
    closed_positions_value = agg_closed["sell_sum"] or 0.0

    # Realized PnL (R$)
    realized_pnl_value = closed_qs.aggregate(
        pnl_sum=Sum(F("sell_price") - F("buy_price"))
    )["pnl_sum"] or 0.0

    # Attach a SellTradeForm to each trade that is still open; the template can
    # access it as `trade.sell_form` (instead of indexing a dict), fixing the
    # previous TemplateSyntaxError.
    for t in trades:
        if t.sell_price is None:
            t.sell_form = SellTradeForm(instance=t)
            t.is_stale_purchase = bool(t.date_of_purchase and (today - t.date_of_purchase).days > 8)
        else:
            t.sell_form = None
            t.is_stale_purchase = False
    
    summary = {
        "total_items_amnt": trades.count(),
        "total_items_value": float(total_items_value),
        "open_positions_amnt": open_qs.count(),
        "open_positions_value": float(open_positions_value),
        "closed_positions_amnt": closed_qs.count(),
        "closed_positions_value": float(closed_positions_value),
        "total_realized_pnl": float(realized_pnl_value),
        "total_realized_pnl_pct": float(realized_pnl_value) / float(total_items_value) * 100 if total_items_value else 0,
}

    # Prepare the add form (blank)
    add_form = TradeForm()

    context = {
        "trades": trades,
        "add_form": add_form,
        "summary": summary,
    }
    return render(request, "trades/index.html", context)

def signup(request: HttpRequest) -> HttpResponse:
    """Minimal signup: creates a user and logs them in, then redirects to index."""
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("index")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})
