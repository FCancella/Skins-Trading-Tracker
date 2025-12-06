from django.shortcuts import render
from django.http import JsonResponse
from scanner.models import Item
from .utils import TradeUpCalculator
from rapidfuzz import process, fuzz

def search_items(request):
    """API para busca dinâmica filtrando por real_rarity e StatTrak"""
    query = request.GET.get('q', '')
    rarity = request.GET.get('rarity', '')
    stattrak_param = request.GET.get('stattrak', '') # 'true', 'false' ou vazio
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    items_qs = Item.objects.all()
    
    if rarity:
        items_qs = items_qs.filter(real_rarity=rarity)
    
    # NOVO: Filtro de StatTrak se especificado
    if stattrak_param == 'true':
        items_qs = items_qs.filter(stattrak=True)
    elif stattrak_param == 'false':
        items_qs = items_qs.filter(stattrak=False)
        
    # Fetch candidates for fuzzy search
    
    if not items_qs.exists():
        return JsonResponse([], safe=False)

    choices = [item.name for item in items_qs]
    
    # Fuzzy search
    matches = process.extract(query, choices, scorer=fuzz.token_set_ratio, limit=20)
    
    results = []
    for match in matches:
        # match is (choice, score, index)
        name, score, index = match
        item = items_qs[index]
        
        results.append({
            'id': item.id,
            'name': item.name,
            'original_name': item.name,
            'image': item.image,
            'min_float': item.min_float,
            'max_float': item.max_float,
            'rarity': item.real_rarity,
            'stattrak': item.stattrak,
            'real_min_float': item.real_min_float,
            'real_max_float': item.real_max_float
        })
        
    return JsonResponse(results, safe=False)

def tradeup_calculator(request):
    # (O restante da view tradeup_calculator permanece idêntico ao anterior)
    rarities = TradeUpCalculator.RARITY_ORDER[:-1] 
    
    context = {
        'rarities': rarities, 
        'range_10': range(10)
    }

    if request.method == 'POST':
        calc = TradeUpCalculator()
        inputs = []
        
        for i in range(10):
            item_id = request.POST.get(f'item_id_{i}')
            float_val = request.POST.get(f'float_val_{i}')
            
            if item_id and float_val:
                try:
                    item_obj = Item.objects.get(id=item_id)
                    inputs.append({
                        'item': item_obj,
                        'float': float(float_val)
                    })
                except (Item.DoesNotExist, ValueError):
                    continue

        if len(inputs) == 10:
            result = calc.calculate_contract(inputs)
            context['result'] = result
            if 'error' in result:
                context['error'] = result['error']
                context['result'] = None
        else:
            context['error'] = "Por favor, preencha todos os 10 slots."

    return render(request, 'tradeup/calculator.html', context)