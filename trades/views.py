"""
Views for the `trades` app.

This module defines function‑based views that handle listing trades,
creating new trades, updating sell information, and computing summary
statistics for the portfolio. The main page (`index`) brings together all
components into a single responsive layout.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Tuple

from django.db.models import Avg, Count, F, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SellTradeForm, TradeForm
from .models import Trade


def _compute_summary() -> Dict[str, object]:
    trades = Trade.objects.all()

    total_items = trades.count()
    open_positions = trades.filter(sell_price__isnull=True).count()
    closed_positions = trades.filter(sell_price__isnull=False).count()

    # Realized PnL = sum over sold trades of (sell_price - buy_price)
    realized_pnl = (
        trades.filter(sell_price__isnull=False)
        .annotate(pnl=F("sell_price") - F("buy_price"))
        .aggregate(total=Count("id"), sum=SumIfExists("pnl"))  # type: ignore
    )

    return {
        "total_items": total_items,
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "total_realized_pnl": float(realized_pnl.get("sum") or 0),
    }


# Helper for aggregation – Django doesn’t have SumIfExists, so we'll handle in
# a small wrapper below by doing a second aggregate when needed.
from django.db.models import Sum


def SumIfExists(field):  # noqa: N802 (Django-style helper name)
    return Sum(field)



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

    # Prepare the add form (blank)
    add_form = TradeForm()

    # Attach a SellTradeForm to each trade that is still open; the template can
    # access it as `trade.sell_form` (instead of indexing a dict), fixing the
    # previous TemplateSyntaxError.
    for t in trades:
        if t.sell_price is None:
            t.sell_form = SellTradeForm(instance=t)
        else:
            t.sell_form = None

    # Compute summary stats
    summary = {
        "total_items": trades.count(),
        "open_positions": trades.filter(sell_price__isnull=True).count(),
        "closed_positions": trades.filter(sell_price__isnull=False).count(),
        "total_realized_pnl": float(
            trades.filter(sell_price__isnull=False)
            .annotate(pnl=F("sell_price") - F("buy_price"))
            .aggregate(total_pnl=Sum("pnl"))["total_pnl"]
            or 0
        )
    }

    context = {
        "trades": trades,
        "add_form": add_form,
        "summary": summary,
    }
    return render(request, "trades/index.html", context)