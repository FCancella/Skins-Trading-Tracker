"""
Views for the `trades` app.

This module defines function‑based views that handle listing trades,
creating new trades, updating sell information, and computing summary
statistics for the portfolio. The main page (`index`) brings together all
components into a single responsive layout.
"""
from __future__ import annotations

from django.db.models import Avg, Count, F, Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SellTradeForm, TradeForm
from .models import Trade


def index(request: HttpRequest) -> HttpResponse:
    """Serve the single-page app: summary, add form, and portfolio table."""

    # Handle adding a new trade
    if request.method == "POST" and request.POST.get("action") == "add":
        add_form = TradeForm(request.POST)
        if add_form.is_valid():
            add_form.save()
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
    trades = Trade.objects.all().order_by("-date_of_purchase")

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
        else:
            t.sell_form = None
    
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