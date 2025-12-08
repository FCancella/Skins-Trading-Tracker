from typing import Dict, List, Optional
import math


def calculate_contract_roi_fast(
    input_items: List[Dict],
    items: Dict[str, Dict],
    precomputed_outcomes: Dict[str, Dict[bool, Dict[str, Dict[int, List[Dict]]]]]
) -> Optional[float]:
    """
    Calculate ROI for a contract using pre-computed outcomes.
    
    Args:
        input_items: List of dicts with 'id', 'float', 'price' keys
        items: Dictionary of all items by ID
        precomputed_outcomes: Pre-computed outcomes for all rarity/source/float combinations
    
    Returns:
        ROI as float, or None if calculation fails
    """
    # Get rarity and stattrak from first item
    first_item = items[input_items[0]['id']]
    input_rarity = first_item['real_rarity']
    stattrak = first_item['stattrak']
    
    # Calculate average normalized float
    sum_normalized = 0.0
    total_input_price = 0.0
    source_counts = {}
    
    for entry in input_items:
        item = items[entry['id']]
        
        # Normalize float
        item_min = item.get('min_float', 0.0) or 0.0
        item_max = item.get('max_float', 1.0) or 1.0
        range_val = item_max - item_min
        
        if range_val > 0:
            normalized = (entry['float'] - item_min) / range_val
        else:
            normalized = 0.0
        
        sum_normalized += normalized
        total_input_price += entry.get('price', 0.0) or 0.0
        
        # Get item sources
        for source_id in item['sources']:
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
    
    avg_normalized_float = sum_normalized / len(input_items)
    
    # Convert to discretized float factor (0-99)
    # Round to 2 decimals then multiply by 100, always rounding up
    float_factor_int = min(int(math.ceil(avg_normalized_float * 100) / 1), 99)
    
    # Calculate expected output value
    expected_value = 0.0
    
    for source_id, count in source_counts.items():
        source_probability = count / len(input_items)
        outcome_mean_price = precomputed_outcomes[input_rarity][stattrak][source_id][float_factor_int][0]

        expected_value += outcome_mean_price * source_probability
    
    # Calculate ROI
    roi = ((expected_value - total_input_price) / total_input_price) * 100

    return roi