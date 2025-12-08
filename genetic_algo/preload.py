import requests
import time
from typing import Dict, List, Tuple

# Global data stores
ITEMS: Dict[str, Dict] = {}
ITEMS_BY_RARITY: Dict[str, Dict[bool, List[str]]] = {}
SOURCES: Dict[str, Dict] = {}
SOURCE_OUTCOMES: Dict[str, Dict[str, List[str]]] = {}

# Pre-computed outcomes: {rarity: {stattrak: {source_id: {float_factor: [valid_outcomes]}}}}
# float_factor is discretized to 0.00, 0.01, 0.02, ..., 0.99
PRECOMPUTED_OUTCOMES: Dict[str, Dict[bool, Dict[str, Dict[int, List[Dict]]]]] = {}

MINIMUM_OFFERS = 50

RARITY_ORDER = [
    'Consumer Grade', 'Industrial Grade', 'Mil-Spec Grade', 
    'Restricted', 'Classified', 'Covert', 'Gold'
]


def generate_float_values(real_min: float, real_max: float) -> Tuple[float, float, float]:
    """Generate three float values at 25%, 50%, and 80% of the range."""
    float_range = real_max - real_min
    return (
        round(real_min + float_range * 0.25, 3),
        round(real_min + float_range * 0.50, 3),
        round(real_min + float_range * 0.80, 3)
    )


def load_items(api_url: str, api_key: str):
    """Load items from API and populate ITEMS and ITEMS_BY_RARITY global stores."""
    global ITEMS, ITEMS_BY_RARITY
    
    headers = {'X-API-KEY': api_key}
    params = {'merge_duplicates': 'true'}
    response = requests.get(f"{api_url}/api/scanner/items/", headers=headers, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch items: {response.status_code}")
    
    data = response.json()
    
    ITEMS.clear()
    ITEMS_BY_RARITY.clear()
    
    for item in data['items']:
        item_id = item['id']
        ITEMS[item_id] = item
        
        rarity = item['real_rarity']
        stattrak = item['stattrak']
        
        if rarity not in ITEMS_BY_RARITY:
            ITEMS_BY_RARITY[rarity] = {True: [], False: []}
        
        ITEMS_BY_RARITY[rarity][stattrak].append(item_id)


def load_sources(api_url: str, api_key: str):
    """Load sources from API and build reverse mapping for outcomes."""
    global SOURCES, SOURCE_OUTCOMES
    
    headers = {'X-API-KEY': api_key}
    params = {'merge_duplicates': 'true'}
    response = requests.get(f"{api_url}/api/scanner/sources/", headers=headers, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch sources: {response.status_code}")
    
    data = response.json()
    SOURCES = data['sources']
    
    # Build reverse mapping: source_id -> {rarity -> {stattrak -> [item_ids]}}
    SOURCE_OUTCOMES.clear()
    for source_id, source_data in SOURCES.items():
        SOURCE_OUTCOMES[source_id] = {}
        
        for item_id in source_data['items']:
            item = ITEMS.get(item_id)
            if not item:
                continue
            
            rarity = item['real_rarity']
            stattrak = item['stattrak']
            
            if rarity not in SOURCE_OUTCOMES[source_id]:
                SOURCE_OUTCOMES[source_id][rarity] = {True: [], False: []}
            
            SOURCE_OUTCOMES[source_id][rarity][stattrak].append(item_id)


def precompute_outcomes():
    """
    Pre-compute all possible outcome combinations for each source and float factor.
    This dramatically speeds up the genetic algorithm by avoiding repeated calculations.
    
    For each rarity -> stattrak -> source -> float_factor combination:
    - Calculate the final float for each possible output item
    - Filter out items where final float is outside their real_min/real_max range
    - Store valid outcomes with their probabilities and prices
    
    Float factors are discretized to 100 values (0.00 to 0.99 in steps of 0.01)
    """
    global PRECOMPUTED_OUTCOMES
    
    print("Pre-computing outcomes for all source/float combinations...")
    start_time = time.time()
    
    PRECOMPUTED_OUTCOMES.clear()
    
    # Iterate through each input rarity (output will be next rarity up)
    for rarity_idx, input_rarity in enumerate(RARITY_ORDER[:-1]):
        output_rarity = RARITY_ORDER[rarity_idx + 1]
        
        #print(f"Processing {input_rarity} -> {output_rarity}...")
        
        for stattrak in [False, True]:
            if input_rarity not in PRECOMPUTED_OUTCOMES:
                PRECOMPUTED_OUTCOMES[input_rarity] = {}
            if stattrak not in PRECOMPUTED_OUTCOMES[input_rarity]:
                PRECOMPUTED_OUTCOMES[input_rarity][stattrak] = {}
            
            # Get all sources that contain items of input rarity and stattrak
            relevant_sources = set()
            for source_id, rarity_map in SOURCE_OUTCOMES.items():
                if input_rarity in rarity_map and stattrak in rarity_map[input_rarity]:
                    if rarity_map[input_rarity][stattrak]:  # Has items
                        relevant_sources.add(source_id)
            
            # For each relevant source
            for source_id in relevant_sources:
                PRECOMPUTED_OUTCOMES[input_rarity][stattrak][source_id] = {}
                
                # Get all possible output items from this source
                output_item_ids = []
                if output_rarity in SOURCE_OUTCOMES[source_id]:
                    if stattrak in SOURCE_OUTCOMES[source_id][output_rarity]:
                        output_item_ids = SOURCE_OUTCOMES[source_id][output_rarity][stattrak]
                
                if not output_item_ids:
                    continue
                
                output_items = [ITEMS[item_id] for item_id in output_item_ids]
                
                # For each float factor from 0.00 to 0.99 (discretized to 100 steps)
                for ff_int in range(100):
                    float_factor = ff_int / 100.0  # 0.00, 0.01, 0.02, ..., 0.99
                    
                    valid_outcomes = []
                    
                    for out_item in output_items:
                        # Calculate final float using item's min/max float (NOT real_min/real_max)
                        item_min = out_item.get('min_float', 0.0) or 0.0
                        item_max = out_item.get('max_float', 1.0) or 1.0
                        
                        final_float = float_factor * (item_max - item_min) + item_min
                        
                        # Check if final float is within real_min/real_max range
                        real_min = out_item.get('real_min_float', item_min)
                        real_max = out_item.get('real_max_float', item_max)
                        
                        if real_min <= final_float <= real_max:
                            valid_outcomes.append({
                                'item_id': out_item['id'],
                                'final_float': final_float,
                                'price': out_item.get('price', 0.0) if out_item.get('offers', 0) > MINIMUM_OFFERS else 0.0,
                            })
                    
                    # Store valid outcomes for this float factor
                    if valid_outcomes:
                        mean_price = sum([vo['price'] for vo in valid_outcomes]) / len(valid_outcomes)
                        PRECOMPUTED_OUTCOMES[input_rarity][stattrak][source_id][ff_int] = [mean_price] + valid_outcomes
    
    elapsed = time.time() - start_time
    #print(f"Pre-computation completed in {elapsed:.2f} seconds")
    
    # Print statistics
    total_combinations = 0
    for rarity in PRECOMPUTED_OUTCOMES:
        for stattrak in PRECOMPUTED_OUTCOMES[rarity]:
            for source in PRECOMPUTED_OUTCOMES[rarity][stattrak]:
                total_combinations += len(PRECOMPUTED_OUTCOMES[rarity][stattrak][source])
    
    print(f"Total pre-computed combinations: {total_combinations}")


def load_input_items(rarity: str, stattrak: bool = False) -> List[Dict]:
    """
    Returns list of item dicts with assigned float values for genetic algorithm.
    Each item is triplicated with equally spaced float values.
    Filters out items whose sources don't have any outcomes in the next rarity tier.
    """
    if rarity not in ITEMS_BY_RARITY:
        return []
    
    # Get the next rarity tier for validation
    try:
        current_idx = RARITY_ORDER.index(rarity)
        if current_idx + 1 >= len(RARITY_ORDER):
            return []  # No next rarity tier exists
        next_rarity = RARITY_ORDER[current_idx + 1]
    except ValueError:
        return []  # Invalid rarity
    
    item_ids = ITEMS_BY_RARITY[rarity][stattrak]
    result = []
    
    for item_id in item_ids:
        item = ITEMS[item_id]
        
        # Check if item has valid price and offers
        item_price = item.get('price', 0.0) or 0.0
        item_offers = item.get('offers', 0) or 0
        if item_price <= 0 or item_offers <= MINIMUM_OFFERS:
            continue
        
        # Check if any source of this item has outcomes in the next rarity tier
        has_valid_source = False
        for source_id in SOURCES:
            # Check if this item belongs to this source
            if rarity in SOURCE_OUTCOMES.get(source_id, {}):
                if item_id in SOURCE_OUTCOMES[source_id][rarity][stattrak]:
                    # Check if this source has any items in the next rarity tier
                    if next_rarity in SOURCE_OUTCOMES.get(source_id, {}):
                        if SOURCE_OUTCOMES[source_id][next_rarity][stattrak]:
                            has_valid_source = True
                            break
        
        # Skip items that don't have any valid sources with next tier outcomes
        if not has_valid_source:
            continue
        
        real_min = item['real_min_float']
        real_max = item['real_max_float']
        
        float_low, float_mid, float_high = generate_float_values(real_min, real_max)
        
        # Return items with structure needed for fast calculation
        result.append({
            'id': item_id,
            'float': float_low,
            'price': item.get('price', 0.0) or 0.0
        })
        result.append({
            'id': item_id,
            'float': float_mid,
            'price': item.get('price', 0.0) or 0.0
        })
        result.append({
            'id': item_id,
            'float': float_high,
            'price': item.get('price', 0.0) or 0.0
        })
    
    return result
