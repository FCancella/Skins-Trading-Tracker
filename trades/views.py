"""
Views for the `trades` app.

This module defines function‑based views that handle listing trades,
creating new trades, updating sell information, and computing summary
statistics for the portfolio. The main page (`index`) brings together all
components into a single responsive layout.
"""
from __future__ import annotations
from decimal import Decimal
import os
import requests
import pandas as pd
from collections import defaultdict
from datetime import timedelta, datetime

from django.core.cache import cache
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from django.db.models import F, Sum, Value
from django.db.models import F, Sum, Value, Q
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SellTradeForm, TradeForm, InvestmentForm, CustomUserCreationForm, BulkTradeForm
from .models import Trade, Investment, SOURCE_CHOICES
from scanner.models import ScannedItem

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

def _calculate_portfolio_metrics(user: User, show_history: bool = False) -> dict:
    """
    Calcula as métricas de portfólio para um determinado usuário.

    Esta função centraliza a lógica de cálculo que é compartilhada
    entre as views `index` e `observer`.
    """
    trades = Trade.objects.filter(owner=user)
    investments = Investment.objects.filter(owner=user)

    open_qs = trades.filter(sell_price__isnull=True)
    
    closed_qs_all = trades.filter(sell_price__isnull=False)
    
    more_trades = False
    closed_qs_display = closed_qs_all
    if len(closed_qs_all) <= 15 or show_history:
        pass
    else:
        more_trades = True
        dates = trades.dates('sell_date', 'day').order_by('-sell_date')[:2]
        closed_qs_display = closed_qs_all.filter(
            Q(sell_date__gte=dates[1]) | Q(sell_date__isnull=True)
        )
    print(not show_history and more_trades)

    # 1. Custo (Cost Basis)
    cost_basis = open_qs.aggregate(total=Coalesce(Sum("buy_price"), Value(Decimal('0.0'))))['total']

    # 2. PnL Realizado (Realized PnL) - Use all closed trades for metrics
    realized_pnl_value = closed_qs_all.aggregate(
        pnl=Coalesce(Sum(F("sell_price") - F("buy_price")), Value(Decimal('0.0')))
    )['pnl']

    # 3. PnL Médio (para itens vendidos) - Use all closed trades for metrics
    closed_aggregates = closed_qs_all.aggregate(
        buy_sum=Coalesce(Sum("buy_price"), Value(Decimal('0.0'))),
        sell_sum=Coalesce(Sum("sell_price"), Value(Decimal('0.0')))
    )
    closed_buy_sum = closed_aggregates['buy_sum']
    closed_sell_sum = closed_aggregates['sell_sum']

    average_pnl_factor = (closed_sell_sum / closed_buy_sum) if closed_buy_sum > 0 else Decimal('1.0')
    average_pnl_percent = (average_pnl_factor - 1) * 100

    # 4. MTM (Mark to Market)
    mtm_value = cost_basis * (1 + (average_pnl_factor - 1) * Decimal('0.7')) if cost_basis > 0 else Decimal('0.0')

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
        closed_qs_all
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
    
    # Buscar preços de mercado atuais para itens em aberto
    open_item_names = open_qs.values_list('item_name', flat=True).distinct()
    
    buff_prices_qs = ScannedItem.objects.filter(
        name__in=open_item_names,
        source='buff'
    ).order_by('name', '-timestamp') # Ordena para que o mais recente venha primeiro para cada nome

    market_prices = {}
    # Itera sobre os resultados; como está ordenado, o primeiro que encontrarmos
    # para cada nome será o mais recente.
    for item in buff_prices_qs:
        if item.name not in market_prices:
            market_prices[item.name] = item.price
    
    # Group open trades
    grouped_open_trades_map = defaultdict(list)
    for trade in open_qs:
        key = (trade.item_name, trade.buy_price, trade.buy_source, trade.buy_date)
        grouped_open_trades_map[key].append(trade)

    grouped_open_trades = []
    for trades_in_group in grouped_open_trades_map.values():
        first_trade = trades_in_group[0]
        first_trade.edit_form = SellTradeForm(instance=first_trade)
        # Adicionar o preço de mercado ao objeto de trade para uso no template
        first_trade.market_price = market_prices.get(first_trade.item_name)
        
        grouped_open_trades.append({
            'trade': first_trade,
            'quantity': len(trades_in_group),
        })

    # Prepare forms for closed trades to be displayed
    closed_trades = list(closed_qs_display)
    for t in closed_trades:
        t.edit_form = TradeForm(instance=t)

    for i in investments:
        i.form = InvestmentForm(instance=i)

    trade_data = {
        'grouped_open_trades': grouped_open_trades,
        'closed_trades': closed_trades
    }
    
    # --- Cash per source calculation ---
    cash_per_source = defaultdict(Decimal)

    for investment in investments:
        cash_per_source[investment.get_source_display()] += investment.amount

    for trade in trades:
        cash_per_source[trade.get_buy_source_display()] -= trade.buy_price

    for trade in closed_qs_all:
        cash_per_source[trade.get_sell_source_display()] += trade.sell_price

    cash_per_source_data = {
        'labels': list(cash_per_source.keys()),
        'values': [float(v) for v in cash_per_source.values()],
    }

    # --- Inventory Cost per Source Calculation ---
    inventory_cost_by_source = open_qs.values('buy_source').annotate(
        total_cost=Sum('buy_price')
    ).order_by('-total_cost')

    source_display_map = dict(SOURCE_CHOICES)
    inventory_cost_data = {
        'labels': [source_display_map.get(item['buy_source'], item['buy_source']) for item in inventory_cost_by_source],
        'values': [float(item['total_cost']) for item in inventory_cost_by_source]
    }


    return {
        "trade_data": trade_data,
        "investments": investments,
        "summary": summary,
        "pnl_data": pnl_data,
        "cash_per_source_data": cash_per_source_data,
        "inventory_cost_data": inventory_cost_data,
        "show_history": show_history,
        "more_trades": more_trades
    }

def _calculate_update_notifications(user: User) -> dict:
    """
    Calcula as notificações de atualização de tradability e pagamento.
    """
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    # Trades que ficam "tradable" (buy_date + 7)
    tradable_today_count = Trade.objects.filter(
        owner=user, sell_date__isnull=True, buy_date=today - timedelta(days=7)
    ).count()
    tradable_tomorrow_count = Trade.objects.filter(
        owner=user, sell_date__isnull=True, buy_date=today - timedelta(days=6)
    ).count()

    # Trades cujo pagamento é liberado (sell_date + 8)
    payment_today_count = Trade.objects.filter(
        owner=user, sell_date=today - timedelta(days=8)
    ).count()
    payment_tomorrow_count = Trade.objects.filter(
        owner=user, sell_date=today - timedelta(days=7)
    ).count()

    updates_today = tradable_today_count + payment_today_count
    updates_tomorrow = tradable_tomorrow_count + payment_tomorrow_count

    next_update_date = None
    if updates_today == 0 and updates_tomorrow == 0:
        # Encontrar a próxima data de atualização
        next_tradable = Trade.objects.filter(
            owner=user, sell_date__isnull=True, buy_date__gt=today - timedelta(days=6)
        ).order_by('buy_date').first()

        next_payment = Trade.objects.filter(
            owner=user, sell_date__gt=today - timedelta(days=7)
        ).order_by('sell_date').first()

        next_tradable_date = (next_tradable.buy_date + timedelta(days=7)) if next_tradable else None
        next_payment_date = (next_payment.sell_date + timedelta(days=8)) if next_payment else None

        if next_tradable_date and next_payment_date:
            next_update_date = min(next_tradable_date, next_payment_date)
        else:
            next_update_date = next_tradable_date or next_payment_date

    return {
        "updates_today": updates_today,
        "updates_tomorrow": updates_tomorrow,
        "next_update_date": next_update_date,
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
    show_history = request.GET.get("history") == "true"
    context = {"public_users": public_users, "selected_user": None, "show_history": show_history}

    if selected_user_id:
        try:
            selected_user = User.objects.get(id=selected_user_id, profile__is_public=True)
            portfolio_data = _calculate_portfolio_metrics(selected_user, show_history)
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
    show_history = request.GET.get("history", "false") == "true"

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
    context = _calculate_portfolio_metrics(request.user, show_history)
    notification_context = _calculate_update_notifications(request.user)
    context.update(notification_context)
    
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

    source_mapping = dict(SOURCE_CHOICES)
    df['buy_source'] = df['buy_source'].map(source_mapping)
    df['sell_source'] = df['sell_source'].map(source_mapping)

    df.columns = [col.replace('_', ' ').title() for col in df.columns]

    df.to_csv(response, sep=';', index=False, date_format='%d-%m-%Y')

    return response

@login_required
def settings_view(request: HttpRequest) -> HttpResponse:
    """Exibe a página de configurações e os logs do scheduler."""
    log_file_path = '/app/logs/scheduler.log'
    log_content = "Arquivo de log não encontrado. O scheduler pode ainda não ter rodado."
    last_run_timestamp = None

    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            # Lê as últimas 100 linhas para não sobrecarregar a página
            lines = f.readlines()
            log_content = "".join(lines[-100:])

        # Pega a data da última modificação do arquivo
        last_modified_time = os.path.getmtime(log_file_path)
        last_run_timestamp = datetime.fromtimestamp(last_modified_time)

    context = {
        "log_content": log_content,
        "last_run": last_run_timestamp
    }
    return render(request, "trades/settings.html", context)
