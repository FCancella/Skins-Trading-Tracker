"""
Views for the `trades` app.

This module defines function‑based views that handle listing trades,
creating new trades, updating sell information, and computing summary
statistics for the portfolio. The main page (`index`) brings together all
components into a single responsive layout.
"""
from __future__ import annotations
from decimal import Decimal
import requests
import pandas as pd
from collections import defaultdict

from django.core.cache import cache
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SellTradeForm, TradeForm, InvestmentForm, CustomUserCreationForm, BulkTradeForm
from .models import Trade, Investment

def _get_exchange_rate(currency: str) -> Decimal | None:
    rate = cache.get(currency)
    if rate:
        return rate
    try:
        response = requests.get(f"https://open.er-api.com/v6/latest/{currency}")
        response.raise_for_status()
        data = response.json()
        rate = Decimal(data["rates"]["BRL"]).quantize(Decimal("0.0001"))
        cache.set(currency, rate)
        return rate
    except (requests.RequestException, KeyError, TypeError):
        return None

def _convert_currency_to_brl(amount_str: str, currency: str) -> Decimal | None:
    """Converte um valor de uma moeda estrangeira para BRL."""
    if currency not in ["CNY", "USD"]:
        return Decimal(amount_str)
    
    rate = _get_exchange_rate(currency)
    if rate is None:
        return None
        
    try:
        amount = Decimal(amount_str)
        return round(amount * rate, 2)
    except Exception:
        return None

def _calculate_portfolio_metrics(user: User) -> dict:
    """
    Calcula as métricas de portfólio para um determinado usuário.

    Esta função centraliza a lógica de cálculo que é compartilhada
    entre as views `index` e `observer`.
    """
    trades = Trade.objects.filter(owner=user)
    investments = Investment.objects.filter(owner=user)

    open_qs = trades.filter(sell_price__isnull=True)
    closed_qs = trades.filter(sell_price__isnull=False)

    # 1. Custo (Cost Basis)
    cost_basis = open_qs.aggregate(total=Coalesce(Sum("buy_price"), Value(Decimal('0.0'))))['total']

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
    mtm_value = sum(
        (t.buy_price * ((average_pnl_factor - 1) * Decimal('0.7') + 1))
        for t in trades if t.sell_price is None
    )

    # 5. Total Investment
    total_investment = investments.aggregate(total=Coalesce(Sum("amount"), Value(Decimal('0.0'))))["total"]
    
    # 6. Cash
    cash = total_investment + realized_pnl_value - cost_basis

    # 7. NAV (Net Asset Value)
    nav = cash + mtm_value
    
    # PnL Total % (ROI sobre o investimento)
    roi_percent = (realized_pnl_value / total_investment * 100) if total_investment > 0 else Decimal('0.0')

    summary = {
        "cost_basis": float(cost_basis),
        "invested": float(total_investment),
        "realized_pnl_value": float(realized_pnl_value),
        "average_pnl_percent": float(average_pnl_percent),
        "mtm_value": float(mtm_value),
        "roi_percent": float(roi_percent),
        "cash": float(cash),
        "nav": float(nav),
    }

    # --- Chart Data ---
    daily_pnl = list(
        closed_qs
        .values(date=F('sell_date'))
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

    # --- Grouping and Form Preparation ---
    # Group open trades
    grouped_open_trades_map = defaultdict(list)
    for trade in open_qs:
        key = (trade.item_name, trade.buy_price, trade.buy_source, trade.buy_date)
        grouped_open_trades_map[key].append(trade)

    grouped_open_trades = []
    for trades_in_group in grouped_open_trades_map.values():
        first_trade = trades_in_group[0]
        first_trade.edit_form = SellTradeForm(instance=first_trade)
        grouped_open_trades.append({
            'trade': first_trade,
            'quantity': len(trades_in_group),
        })

    # Prepare forms for closed trades
    closed_trades = list(closed_qs)
    for t in closed_trades:
        t.edit_form = TradeForm(instance=t)

    for i in investments:
        i.form = InvestmentForm(instance=i)

    trade_data = {
        'grouped_open_trades': grouped_open_trades,
        'closed_trades': closed_trades
    }

    return {
        "trade_data": trade_data,
        "investments": investments,
        "summary": summary,
        "pnl_data": pnl_data,
    }

def home(request: HttpRequest) -> HttpResponse:
    """Displays the homepage with options to login or spectate."""
    if request.user.is_authenticated:
        return redirect("index")
    return render(request, "trades/home.html")

def observer(request: HttpRequest) -> HttpResponse:
    """Displays a list of public users and their portfolios."""
    public_users = User.objects.filter(profile__is_public=True)
    if request.user.is_authenticated:
        public_users = public_users.exclude(id=request.user.id)
    selected_user_id = request.GET.get("user_id")
    context = {"public_users": public_users, "selected_user": None}

    if selected_user_id:
        try:
            selected_user = User.objects.get(id=selected_user_id, profile__is_public=True)
            portfolio_data = _calculate_portfolio_metrics(selected_user)
            context.update(portfolio_data)
            context["selected_user"] = selected_user
        except User.DoesNotExist:
            # O template já lida com o caso de usuário não encontrado
            pass

    return render(request, "trades/observer.html", context)

@login_required
def index(request: HttpRequest) -> HttpResponse:
    add_form = TradeForm()
    bulk_add_form = BulkTradeForm()
    investment_form = InvestmentForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            add_form = TradeForm(request.POST) # Re-populate form on error
            price = request.POST.get("buy_price")
            currency = request.POST.get("buy_price_currency")
            
            converted_price = _convert_currency_to_brl(price, currency)
            if converted_price is None:
                add_form.add_error(None, f"Não foi possível converter a taxa de {currency} para BRL.")
            else:
                post_data = request.POST.copy()
                post_data['buy_price'] = converted_price
                add_form = TradeForm(post_data)

            if add_form.is_valid():
                add_form.save(owner=request.user)
                return redirect("index")
        elif action == "bulk_add":
            bulk_add_form = BulkTradeForm(request.POST) # Re-populate
            if bulk_add_form.is_valid():
                data = bulk_add_form.cleaned_data
                quantity = data.pop('quantity')
                currency = data.pop('buy_price_currency')
                
                converted_price = _convert_currency_to_brl(data['buy_price'], currency)
                if converted_price is None:
                    bulk_add_form.add_error(None, f"Não foi possível converter a taxa de {currency} para BRL.")
                else:
                    data['buy_price'] = converted_price
                    trades_to_create = [Trade(owner=request.user, **data) for _ in range(quantity)]
                    Trade.objects.bulk_create(trades_to_create)
                    return redirect("index")
        elif action == "sell":
            trade_id = request.POST.get("trade_id")
            trade = Trade.objects.get(pk=trade_id, owner=request.user)
            form = SellTradeForm(request.POST, instance=trade)
            
            price = request.POST.get("sell_price")
            currency = request.POST.get("sell_price_currency")

            converted_price = _convert_currency_to_brl(price, currency)
            if converted_price is None:
                form.add_error(None, f"Não foi possível converter a taxa de {currency} para BRL.")
            else:
                post_data = request.POST.copy()
                post_data['sell_price'] = converted_price
                form = SellTradeForm(post_data, instance=trade)

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
        elif action == "edit_investment":
            investment_id = request.POST.get("investment_id")
            investment = Investment.objects.get(pk=investment_id, owner=request.user)
            form = InvestmentForm(request.POST, instance=investment)
            if form.is_valid():
                form.save(owner=request.user)
                return redirect("index")
        elif action == "delete_investment":
            investment_id = request.POST.get("investment_id")
            investment = Investment.objects.get(pk=investment_id, owner=request.user)
            investment.delete()
            return redirect("index")
        elif action == "delete":
            trade_id = request.POST.get("trade_id")
            trade = Trade.objects.get(pk=trade_id, owner=request.user)
            trade.delete()
            return redirect("index")
        elif action == "unsell":
            trade_id = request.POST.get("trade_id")
            trade = Trade.objects.get(pk=trade_id, owner=request.user)
            trade.sell_price = None
            trade.sell_date = None
            trade.sell_source = None
            trade.save()
            return redirect("index")

    # --- GET Request or failed POST ---
    context = _calculate_portfolio_metrics(request.user)
    context["add_form"] = add_form
    context["bulk_add_form"] = bulk_add_form
    context["investment_form"] = investment_form
    
    return render(request, "trades/index.html", context)

@login_required
def toggle_profile_public(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        profile = request.user.profile
        profile.is_public = request.POST.get('is_public') == 'on'
        profile.save()
    return redirect(request.META.get('HTTP_REFERER', 'index'))

def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("index")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("index")
    else:
        # E aqui também
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})

@login_required
def export_portfolio(request: HttpRequest) -> HttpResponse:
    """Gera e retorna um arquivo CSV com todos os trades do usuário usando pandas."""
    response = HttpResponse(content_type='text/csv')
    today = timezone.now().strftime('%Y-%m-%d')
    response['Content-Disposition'] = f'attachment; filename="portfolio-{request.user.username}-{today}.csv"'

    trades = Trade.objects.filter(owner=request.user)
    df = pd.DataFrame(list(trades.values()))
    df.drop(columns=['id', 'owner_id'], inplace=True)

    source_mapping = dict(Trade.SOURCE_CHOICES)
    df['buy_source'] = df['buy_source'].map(source_mapping)
    df['sell_source'] = df['sell_source'].map(source_mapping)

    df.columns = [col.replace('_', ' ').title() for col in df.columns]

    df.to_csv(response, sep=';', index=False, date_format='%d-%m-%Y')

    return response