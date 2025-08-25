from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import ScannedItem

@login_required
def scanner_view(request):
    """
    Busca, processa e agrupa os itens escaneados para exibição,
    além de calcular estatísticas do scanner.
    """
    # --- Lógica de processamento de itens ---
    dash_items = ScannedItem.objects.filter(
        source__in=['dash_bot', 'dash_p2p']
    ).exclude(diff__isnull=True).order_by('-diff')
    
    item_names = dash_items.values_list('name', flat=True)
    buff_prices_qs = ScannedItem.objects.filter(source='buff', name__in=item_names)
    buff_data_map = {
        item.name: {'price': item.price, 'offers': item.offers} 
        for item in buff_prices_qs
    }
    
    processed_items = []
    for item in dash_items:
        buff_data = buff_data_map.get(item.name, {}) # Pega o dict com preço e ofertas
        processed_items.append({
            'name': item.name,
            'buff_price': buff_data.get('price'),
            'buff_offers': buff_data.get('offers'), # Adiciona as ofertas
            'dash_price': item.price,
            'diff': item.diff,
            'source': item.source
        })

    # --- Lógica para os dados do painel de resumo ---
    last_check = ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p']).order_by('-timestamp').first()
    last_check_time = last_check.timestamp if last_check else None
    total_items = len(processed_items)
    next_run_in = None

    if last_check_time:
        next_run_time = last_check_time + timedelta(hours=1)
        time_difference = next_run_time - timezone.now()
        if time_difference.total_seconds() > 0:
            minutes, seconds = divmod(int(time_difference.total_seconds()), 60)
            next_run_in = f"{minutes}m {seconds}s"
        else:
            next_run_in = "Executando..."

    context = {
        'items': processed_items,
        'last_check_time': last_check_time,
        'total_items': total_items,
        'next_run_in': next_run_in,
    }
    return render(request, 'scanner/scanner_list.html', context)