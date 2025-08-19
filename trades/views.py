"""
Views for the `trades` app.

This module defines function‑based views that handle listing trades,
creating new trades, updating sell information, and computing summary
statistics for the portfolio. The main page (`index`) brings together all
components into a single responsive layout.
"""
from __future__ import annotations
from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SellTradeForm, TradeForm, InvestmentForm
from .models import Trade, Investment

@login_required
def index(request: HttpRequest) -> HttpResponse:
    """Serve the single-page app: summary, add form, and portfolio table."""

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            add_form = TradeForm(request.POST)
            if add_form.is_valid():
                add_form.save(owner=request.user)
                return redirect("index")
        elif action == "sell":
            trade_id = request.POST.get("trade_id")
            trade = Trade.objects.get(pk=trade_id, owner=request.user)
            form = SellTradeForm(request.POST, instance=trade)
            if form.is_valid():
                form.save()
                return redirect("index")
        elif action == "edit":
            trade_id = request.POST.get("trade_id")
            trade = Trade.objects.get(pk=trade_id, owner=request.user)
            form = TradeForm(request.POST, instance=trade)
            if form.is_valid():
                form.save(owner=request.user)
                return redirect("index")
        elif action == "invest":
            investment_form = InvestmentForm(request.POST)
            if investment_form.is_valid():
                investment_form.save(owner=request.user)
                return redirect("index")

    # --- GET Request and Summary Calculations ---
    trades = Trade.objects.filter(owner=request.user).order_by("-date_of_purchase")
    investments = Investment.objects.filter(owner=request.user)
    today = timezone.localdate()

    open_qs = trades.filter(sell_price__isnull=True)
    closed_qs = trades.filter(sell_price__isnull=False)

    # 1. Custo (Cost Basis)
    cost_basis = trades.aggregate(total=Coalesce(Sum("buy_price"), Value(Decimal('0.0'))))['total']

    # 2. PnL Realizado (Realized PnL)
    realized_pnl_value = closed_qs.aggregate(
        pnl=Coalesce(Sum(F("sell_price") - F("buy_price")), Value(Decimal('0.0')))
    )['pnl']

    # 3. PnL Médio (para itens vendidos)
    closed_aggregates = closed_qs.aggregate(
        buy_sum=Coalesce(Sum("buy_price"), Value(Decimal('0.0'))),
        sell_sum=Coalesce(Sum("sell_price"), Value(Decimal('0.0')))
    )
    closed_buy_sum = closed_aggregates['buy_sum']
    closed_sell_sum = closed_aggregates['sell_sum']

    average_pnl_factor = (closed_sell_sum / closed_buy_sum) if closed_buy_sum > 0 else Decimal('1.0')
    average_pnl_percent = (average_pnl_factor - 1) * 100

    # 4. MTM (Mark to Market)
    mtm_value = Decimal('0.0')
    for trade in trades:
        if trade.sell_price is not None:
            mtm_value += trade.sell_price
        else:
            # Estima o valor do item aberto usando o PnL médio dos itens fechados
            mtm_value += trade.buy_price * (average_pnl_factor * Decimal(0.8))

    # Outras métricas
    total_investment = investments.aggregate(total=Coalesce(Sum("amount"), Value(Decimal('0.0'))))["total"]
    
    # PnL Total % (ROI sobre o investimento)
    roi_percent = (realized_pnl_value / total_investment * 100) if total_investment > 0 else Decimal('0.0')


    summary = {
        "cost_basis": float(cost_basis),
        "invested": float(total_investment),
        "realized_pnl_value": float(realized_pnl_value),
        "average_pnl_percent": float(average_pnl_percent),
        "mtm_value": float(mtm_value),
        "roi_percent": float(roi_percent)
    }

    # --- Chart Data ---
    daily_pnl = list(
        closed_qs
        .values(date=F('date_sold'))
        .annotate(daily_pnl=Sum(F('sell_price') - F('buy_price')))
        .order_by('date')
    )
    accumulated_pnl = 0.0
    pnl_data = []
    for pnl in daily_pnl:
        if pnl['date'] is None: continue
        pnl['daily_pnl'] = float(pnl['daily_pnl'])
        accumulated_pnl += pnl['daily_pnl']
        pnl_data.append({
            'date': pnl['date'].strftime("%Y-%m-%d"),
            'pnl': accumulated_pnl,
        })

    # --- Form preparation ---
    for t in trades:
        t.is_stale_purchase = bool(t.date_of_purchase and (today - t.date_of_purchase).days >= 7)
        t.days_until_stale = 7 - (today - t.date_of_purchase).days
        if t.sell_price is None:
            t.edit_form = SellTradeForm(instance=t)
        else:
            t.edit_form = TradeForm(instance=t)

    add_form = TradeForm()
    investment_form = InvestmentForm()

    context = {
        "trades": trades,
        "investments": investments,
        "add_form": add_form,
        "investment_form": investment_form,
        "summary": summary,
        "pnl_data": pnl_data,
    }
    return render(request, "trades/index.html", context)

def signup(request: HttpRequest) -> HttpResponse:
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