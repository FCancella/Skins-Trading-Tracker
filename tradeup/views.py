from django.shortcuts import render
from django.http import JsonResponse
from scanner.models import Item
from .utils import TradeUpCalculator
from rapidfuzz import process, fuzz
import random

def search_items(request):
    """API para busca dinâmica filtrando por real_rarity e StatTrak"""
    query = request.GET.get('q', '')
    rarity = request.GET.get('rarity', '')
    stattrak_param = request.GET.get('stattrak', '') # 'true', 'false' ou vazio
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    items_qs = Item.objects.all().filter(souvenir=False)
    
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
            'real_max_float': item.real_max_float,
            'price': float(item.price) if item.price else 0.0
        })
        
    return JsonResponse(results, safe=False)

def tradeup_calculator(request):
    """Simple page view that renders the calculator template"""
    rarities = TradeUpCalculator.RARITY_ORDER[:-1]
    
    context = {
        'rarities': rarities,
    }
    
    return render(request, 'tradeup/calculator.html', context)


def calculate_contract_api(request):
    """API endpoint that receives contract data and returns calculation results as JSON"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        items = data.get('items', [])
        
        if len(items) not in [5, 10]:
            return JsonResponse({'error': 'Exactly 5 or 10 items are required'}, status=400)
        
        # Extract item IDs and float values
        item_ids = []
        float_values = []
        
        for item_data in items:
            item_id = item_data.get('item_id')
            float_val = item_data.get('float_val')
            
            if not item_id or float_val is None:
                return JsonResponse({'error': 'Missing item_id or float_val'}, status=400)
            
            try:
                item_ids.append(item_id)
                float_values.append(float(float_val))
            except ValueError:
                return JsonResponse({'error': 'Invalid float value'}, status=400)
        
        # Use optimized calculator
        calc = TradeUpCalculator()
        result = calc.calculate_contract_fast(item_ids, float_values)
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        # Convert Decimal values to float for JSON serialization
        input_price = float(result['input_price'])
        response_data = {
            'input_price': input_price,
            'expected_output_value': float(result['expected_output_value']),
            'roi': float(result['roi']),
            'profit_chance': float(result['profit_chance']),
            'avg_normalized_float': result['avg_normalized_float'],
            'is_stattrak': result['is_stattrak'],
            'outcomes': [
                {
                    'item_id': out['item'].id,
                    'item_name': out['item'].name,
                    'image': out['image'],
                    'float': out['float'],
                    'condition': out['condition'],
                    'probability': out['probability'],
                    'price': float(out['price']),
                    'profitability': ((float(out['price']) - input_price) / input_price * 100) if input_price > 0 else 0,
                    'stattrak': out['stattrak'],
                    'rarity': out['item'].real_rarity
                }
                for out in result['outcomes']
            ]
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def random_item(request):
    """API endpoint that returns a random item matching rarity and StatTrak filters"""
    rarity = request.GET.get('rarity', '')
    stattrak_param = request.GET.get('stattrak', '')
    
    if not rarity:
        return JsonResponse({'error': 'Rarity is required'}, status=400)
    
    items_qs = Item.objects.filter(souvenir=False, real_rarity=rarity)
    
    if stattrak_param == 'true':
        items_qs = items_qs.filter(stattrak=True)
    elif stattrak_param == 'false':
        items_qs = items_qs.filter(stattrak=False)
    
    if not items_qs.exists():
        return JsonResponse({'error': 'Nenhum item encontrado com os critérios selecionados'}, status=404)
    
    # Get random item
    random_item = random.choice(list(items_qs))
    
    return JsonResponse({
        'id': random_item.id,
        'name': random_item.name,
        'original_name': random_item.name,
        'image': random_item.image,
        'min_float': random_item.min_float,
        'max_float': random_item.max_float,
        'rarity': random_item.real_rarity,
        'stattrak': random_item.stattrak,
        'real_min_float': random_item.real_min_float,
        'real_max_float': random_item.real_max_float,
        'price': float(random_item.price) if random_item.price else 0.0
    })