import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from .models import ScannedItem, BlackList, SchedulerLogs, Item
from trades.utils import _get_exchange_rate
from scanner.services.utils import load_id_dict, clear_item_name
from django.core.paginator import Paginator
from trades.models import Trade

# Decorator para autenticação da API
def api_key_required(view_func):
    @csrf_exempt
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if not api_key or api_key != settings.SCANNER_API_KEY:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@api_key_required
def get_all_items(request):
    """
    API endpoint to fetch all items data for genetic algorithm.
    Returns optimized data structure with all necessary fields.
    Supports merge_duplicates parameter to combine items with identical names.
    """
    try:
        # Check if merge_duplicates parameter is set
        merge_duplicates = request.GET.get('merge_duplicates', '').lower() == 'true'
        
        # Fetch all items excluding souvenirs with prefetch
        if merge_duplicates:
            # Use distinct to get only one item per name (keeps first occurrence)
            items = Item.objects.filter(souvenir=False).order_by('name', '-offers').distinct('name').prefetch_related('crates', 'collections')
        else:
            items = Item.objects.filter(souvenir=False).prefetch_related('crates', 'collections')
        
        # Build items list
        items_list = []
        for item in items:
            # Get sources (crates/collections)
            crates = [f"crate_{c.id}" for c in item.crates.all() if 'Souvenir' not in c.name]
            collections = [f"collection_{c.id}" for c in item.collections.all()]
            sources = crates if crates else collections
            
            items_list.append({
                'id': item.id,
                'name': item.name,
                'min_float': item.min_float or 0.0,
                'max_float': item.max_float or 1.0,
                'real_min_float': item.real_min_float,
                'real_max_float': item.real_max_float,
                'price': float(item.price) if item.price else 0.0,
                'offers': item.offers or 0,
                'real_rarity': item.real_rarity,
                'stattrak': item.stattrak,
                'sources': sources
            })
        
        return JsonResponse({
            'count': len(items_list),
            'items': items_list
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_key_required
def get_sources_relations(request):
    """
    API endpoint to fetch crates/collections and their related items.
    Returns mapping of sources to item IDs for genetic algorithm.
    Supports merge_duplicates parameter to only include one item per name.
    """
    try:
        from .models import Crate, Collection
        
        # Check if merge_duplicates parameter is set
        merge_duplicates = request.GET.get('merge_duplicates', '').lower() == 'true'
        
        sources = {}
        
        # Get all crates with their items
        crates = Crate.objects.prefetch_related('items').all()
        for crate in crates:
            if 'Souvenir' not in crate.name:
                items_query = crate.items.filter(souvenir=False)
                if merge_duplicates:
                    items_query = items_query.order_by('name', '-offers').distinct('name')
                item_ids = list(items_query.values_list('id', flat=True))
                if item_ids:
                    sources[f"crate_{crate.id}"] = {
                        'type': 'crate',
                        'name': crate.name,
                        'items': item_ids
                    }
        
        # Get all collections with their items
        collections = Collection.objects.prefetch_related('items').all()
        for collection in collections:
            items_query = collection.items.filter(souvenir=False)
            if merge_duplicates:
                items_query = items_query.order_by('name', '-offers').distinct('name')
            item_ids = list(items_query.values_list('id', flat=True))
            if item_ids:
                sources[f"collection_{collection.id}"] = {
                    'type': 'collection',
                    'name': collection.name,
                    'items': item_ids
                }
        
        return JsonResponse({
            'count': len(sources),
            'sources': sources
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_key_required
@require_POST
def log_scheduler_event(request):
    """
    Função para registrar eventos do scheduler no banco de dados.
    """
    try:
        # Carrega os dados do corpo da requisição JSON
        data = json.loads(request.body)
        message = data.get("message", "Empty message, try 'docker compose logs scheduler'")

        # Cria o log no banco de dados
        SchedulerLogs.objects.create(message=message)
        
        return JsonResponse({"status": "success", "message": "Log created successfully"}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_key_required
@require_http_methods(["GET"])
def get_items_to_price(request):
    """
    Endpoint que retorna uma lista de itens em portfólio (não vendidos)
    que não têm um preço Buff recente.
    """
    # 1. Pega todos os nomes de itens únicos que estão em aberto no portfólio
    open_portfolio_items = Trade.objects.filter(sell_price__isnull=True).values_list('item_name', flat=True).distinct()

    # 2. Pega os nomes de itens que JÁ TÊM um preço Buff recente (últimas 5 horas)
    recent_buff_items = ScannedItem.objects.filter(
        source='buff',
        name__in=open_portfolio_items,
        timestamp__gte=timezone.now() - timedelta(hours=8) # 3 vezes por dia
    ).values_list('name', flat=True)

    # 3. Filtra a lista de itens do portfólio para encontrar aqueles que PRECISAM de um novo preço
    items_needing_price = list(set(open_portfolio_items) - set(recent_buff_items))[:100]

    return JsonResponse({"items_to_price": items_needing_price})


@api_key_required
@require_POST
def scanner_api_add_items(request):
    """
    Endpoint da API para receber e salvar os itens iniciais do scanner (Dash).
    """
    try:
        data = json.loads(request.body)
        items = data.get("items")
        if not isinstance(items, list):
            return JsonResponse({"error": "Invalid payload format"}, status=400)

        ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p', 'brskins']).delete()
        items_to_create = [
            ScannedItem(name=item['name'], price=item['price'], source=item['source'], link=item['link'])
            for item in items
        ]
        ScannedItem.objects.bulk_create(items_to_create)
        return JsonResponse({"status": "success", "created_items": len(items_to_create)}, status=201)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_key_required
@require_http_methods(["GET"])
def get_items_to_update(request):
    """
    Endpoint que retorna uma lista de itens que precisam ter o preço do Buff atualizado.
    """
    dash_items_to_check = ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p', 'brskins'])
    buff_items_in_db = ScannedItem.objects.filter(source='buff', timestamp__gte=timezone.now() - timedelta(hours=3))
    blacklist_items = BlackList.objects.all().values_list('name', flat=True)

    dash_items_to_check = dash_items_to_check.exclude(name__in=blacklist_items)
    recent_buff_names = buff_items_in_db.values_list('name', flat=True)
    items_needing_update = dash_items_to_check.exclude(name__in=recent_buff_names)
    
    item_names = list(items_needing_update.values_list('name', flat=True))
    
    return JsonResponse({"items_to_update": item_names})

@api_key_required
@require_POST
def update_buff_prices(request):
    """
    Endpoint para receber e salvar os preços do Buff para itens específicos.
    """
    try:
        data = json.loads(request.body)
        items = data.get("items")
        if not isinstance(items, list):
            return JsonResponse({"error": "Invalid payload format"}, status=400)

        created_count = 0
        for item in items:
            ScannedItem.objects.create(
                name=item['name'],
                price=item['price'],
                offers=item['offers'],
                link=item['link'],
                source='buff'
            )
            created_count += 1
            if item.get('offers', 0) < 90:
                BlackList.objects.update_or_create(
                    name=item['name'],
                    defaults={'offers': item['offers']}
                )
        return JsonResponse({"status": "success", "updated_items": created_count}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_key_required
@require_POST
def calculate_differences(request):
    """
    Endpoint para acionar o cálculo da diferença de preços entre Dash e Buff.
    """
    dash_items_to_compare = ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p', 'brskins'])

    dash_items_to_compare = dash_items_to_compare.exclude(name__in=BlackList.objects.all().values_list('name', flat=True))

    items_processed = 0
    for dash_item in dash_items_to_compare:
        try:
            buff_item = ScannedItem.objects.filter(source='buff', name=dash_item.name, timestamp__gte=timezone.now() - timedelta(hours=3)).first()
            if buff_item and buff_item.price and dash_item.price and buff_item.price > 0 and dash_item.price > 0:
                buff_price = Decimal(buff_item.price)
                dash_price = Decimal(dash_item.price)
                diff = int((buff_price / dash_price - 1) * 100)
                if diff < -7:
                    diff = int((buff_price / (dash_price * Decimal('0.93')) - 1) * 100)
                
                dash_item.diff = diff
                buff_item.diff = diff
                dash_item.save()
                buff_item.save()
                items_processed += 1
        except Exception as e:
            continue
    return JsonResponse({"status": "success", "processed_items": items_processed})

@login_required
def scanner_view(request):
    """
    Busca, processa e agrupa os itens escaneados para exibição,
    além de calcular estatísticas do scanner.
    """
    dash_items = ScannedItem.objects.filter(
        source__in=['dash_bot', 'dash_p2p', 'brskins']
    ).exclude(diff__isnull=True).order_by('-diff')
    
    item_names = dash_items.values_list('name', flat=True)
    
    # Busca apenas o preço mais recente de cada item no Buff
    buff_prices_qs = ScannedItem.objects.filter(
        source='buff', 
        name__in=item_names
    ).order_by('name', '-timestamp').distinct('name')
    
    buff_data_map = {item.name: {'price': item.price, 'offers': item.offers, 'link': item.link} for item in buff_prices_qs}
    
    try:
        cny_brl_rate = _get_exchange_rate("CNY")
    except Exception:
        cny_brl_rate = None

    processed_items = []
    for item in dash_items:
        dash_price_cny = None
        # Se tivermos a taxa e o preço, calcula o valor em CNY
        if cny_brl_rate and item.price:
            try:
                # Converte BRL para CNY (preço_brl / taxa_cny_brl)
                dash_price_cny = (Decimal(item.price) / cny_brl_rate).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError):
                dash_price_cny = None

        processed_items.append({
            'name': item.name,
            'buff_price': buff_data_map.get(item.name, {}).get('price'),
            'buff_offers': buff_data_map.get(item.name, {}).get('offers'),
            'dash_price': item.price,
            'dash_price_cny': dash_price_cny,
            'diff': item.diff,
            'source': item.source,
            'link': item.link,
            'buff_link': buff_data_map.get(item.name, {}).get('link')
        })

    last_check = ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p', 'brskins']).order_by('-timestamp').first()
    last_check_time = last_check.timestamp if last_check else None
    next_run_in = None
    if last_check_time:
        next_run_time = last_check_time + timedelta(hours=1)
        time_difference = next_run_time - timezone.now()
        next_run_in = f"{int(time_difference.total_seconds() // 60)}m" if time_difference.total_seconds() > 0 else "Executando..."

    context = {
        'items': processed_items,
        'last_check_time': last_check_time,
        'total_items': len(processed_items),
        'next_run_in': next_run_in,
    }
    return render(request, 'scanner/scanner_list.html', context)

@api_key_required
@require_http_methods(["GET"])
@transaction.atomic
def get_items_for_pricing(request):
    """
    Endpoint da API para trabalhadores (workers) obterem um lote de itens para precificar.

    Busca 50 itens que (1) não têm preço (price=null) E (2) não estão "bloqueados" (price_time=null)
    OU (3) o bloqueio expirou (ex: worker falhou).
    """
    try:
        # 1. Carrega dependências (taxa de câmbio e dicionário de IDs)
        cny_brl_rate = _get_exchange_rate("CNY")
        if not cny_brl_rate:
            return JsonResponse({"error": "Não foi possível obter a taxa de câmbio CNY/BRL."}, status=500)
        
        try:
            id_dict = load_id_dict()
        except Exception as e:
            return JsonResponse({"error": f"Não foi possível carregar o dicionário de IDs: {e}"}, status=500)

        # Define um timeout para itens que provavelmente "ficaram presos"/falharam
        timeout_period = timezone.now() - timedelta(hours=6)

        # # 2. Busca 50 itens que:
        # #    - Ainda não têm preço (price__isnull=True)
        # #    - E (OU estão "novos" (price_time__isnull=True)
        # #    - OU o "bloqueio" expirou (price_time__lte=timeout_period))
        # items_to_process = Item.objects.filter(
        #     price__isnull=True
        # ).filter(
        #     Q(price_time__isnull=True) | Q(price_time__lte=timeout_period)
        # ).select_for_update(skip_locked=True)[:50]

        # 2. Busca 100 itens que:
        #    - Foram precificados há mais de 6 horas (price_time__lte=...)
        items_to_process = Item.objects.filter(
            Q(price_time__isnull=True) | Q(price_time__lte=timeout_period)
        ).select_for_update(skip_locked=True)[:100]

        if not items_to_process:
            return JsonResponse({"items_to_price": [], "cny_brl_rate": cny_brl_rate})

        # 3. Prepara a lista de trabalho, encontrando o ID do Buff para cada item
        work_batch = []
        item_ids_to_lock = []
        
        for item in items_to_process:
            cleared_name = clear_item_name(item.market_hash_name)
            buff_item_id = id_dict.get(cleared_name)
            
            if buff_item_id:
                work_batch.append({
                    "id": item.id,
                    "buff_item_id": buff_item_id
                })
                item_ids_to_lock.append(item.id)
            else:
                # Se não encontrar o ID, marca como "precificado" com 0 para não buscar de novo
                item.price = Decimal("0.00")
                item.offers = 0
                item.price_time = timezone.now()
                item.save() # Salva individualmente (raro)

        # 4. "Bloqueia" os itens que foram enviados para o worker
        if item_ids_to_lock:
            Item.objects.filter(id__in=item_ids_to_lock).update(price_time=timezone.now())

        # 5. Retorna a lista de trabalho e a taxa de câmbio
        return JsonResponse({
            "items_to_price": work_batch,
            "cny_brl_rate": cny_brl_rate
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_key_required
@require_POST
def submit_item_prices(request):
    """
    Endpoint da API para trabalhadores (workers) enviarem os preços encontrados.
    Espera um JSON no formato:
    {
        "prices": [
            {"id": "skin-123", "price_cny": 10.50, "offers": 120},
            {"id": "skin-456", "price_cny": 120.00, "offers": 50}
        ],
        "cny_brl_rate": "1.45" 
    }
    """
    try:
        data = json.loads(request.body)
        prices_data = data.get("prices")
        cny_brl_rate_str = data.get("cny_brl_rate")

        if not isinstance(prices_data, list) or not cny_brl_rate_str:
            return JsonResponse({"error": "Formato de payload inválido."}, status=400)
        
        rate = Decimal(cny_brl_rate_str)
        items_to_update = []
        now = timezone.now()

        for item_info in prices_data:
            item_id = item_info.get("id")
            price_cny = item_info.get("price_cny")
            offers = item_info.get("offers")
            
            if item_id and price_cny is not None and offers is not None:
                try:
                    # Converte o preço para BRL aqui no servidor
                    price_brl = (Decimal(price_cny) * rate).quantize(Decimal("0.01"))
                    
                    item = Item(
                        id=item_id, 
                        price=price_brl, 
                        offers=int(offers),
                        price_time=now
                    )
                    items_to_update.append(item)
                except (ValueError, TypeError, InvalidOperation):
                    continue # Pula dados inválidos

        # 2. Atualiza todos os itens de uma só vez
        if items_to_update:
            Item.objects.bulk_update(items_to_update, ['price', 'offers', 'price_time'])

        return JsonResponse({"status": "success", "updated_items": len(items_to_update)}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def scheduler_logs_view(request):
    """
    Exibe os logs do scheduler com paginação.
    """
    logs_list = SchedulerLogs.objects.all().order_by('-timestamp')
    paginator = Paginator(logs_list, 25) # Mostra 25 logs por página

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'scanner/scheduler_logs.html', context)