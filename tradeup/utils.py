import random
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from scanner.models import Item

class TradeUpCalculator:
    WEAR_RANGES = {
        'Factory New': (0.00, 0.07),
        'Minimal Wear': (0.07, 0.15),
        'Field-Tested': (0.15, 0.38),
        'Well-Worn': (0.38, 0.45),
        'Battle-Scarred': (0.45, 1.00),
    }

    RARITY_ORDER = [
        'Consumer Grade', 
        'Industrial Grade', 
        'Mil-Spec Grade', 
        'Restricted', 
        'Classified', 
        'Covert',
        'Gold'
    ]

    def __init__(self):
        """Initialize calculator with cache for repeated calculations"""
        self._rarity_index_cache = {rarity: idx for idx, rarity in enumerate(self.RARITY_ORDER)}

    @staticmethod
    def get_wear_from_float(float_val: float) -> str:
        """Optimized: Directly get wear condition from float value"""
        for wear_name, (min_w, max_w) in TradeUpCalculator.WEAR_RANGES.items():
            if min_w <= float_val < max_w:
                return wear_name
        return 'Battle-Scarred'  # Default for >= 1.0

    @staticmethod
    def normalize_float(float_val: float, min_f: Optional[float], max_f: Optional[float]) -> float:
        """Optimized: Handle None values efficiently and avoid division by zero"""
        min_f = 0.0 if min_f is None else min_f
        max_f = 1.0 if max_f is None else max_f
        range_val = max_f - min_f
        if range_val <= 0.0:
            return 0.0
        return (float_val - min_f) / range_val

    @staticmethod
    def calculate_output_float(avg_normalized_float: float, out_min: float, out_max: float) -> float:
        """Optimized: Inline calculation without Item object overhead"""
        return (avg_normalized_float * (out_max - out_min)) + out_min

    @staticmethod
    def _get_real_float_range(item) -> Tuple[float, float]:
        """Cache-friendly calculation of real min/max float to avoid repeated @property calls"""
        item_min = item.min_float if item.min_float is not None else 0.0
        item_max = item.max_float if item.max_float is not None else 1.0
        
        # Check market_hash_name once for wear condition
        market_name = item.market_hash_name
        for wear, (min_w, max_w) in TradeUpCalculator.WEAR_RANGES.items():
            if wear in market_name:
                return (max(item_min, min_w), min(item_max, max_w))
        
        return (item_min, item_max)

    def calculate_contract(self, inputs: List[Dict]) -> Dict:
        """
        Optimized contract calculation for genetic algorithms.
        
        Args:
            inputs: List of dicts with 'item' (Item object) and 'float' (float value)
        
        Returns:
            Dict with calculation results or error
        """
        num_items = len(inputs)
        
        # Fast validation
        if num_items not in (5, 10):
            return {"error": "É necessário exatamente 5 ou 10 itens."}

        # Extract first item properties for validation
        first_item = inputs[0]['item']
        first_is_stt = first_item.stattrak
        input_rarity = first_item.real_rarity
        
        # Get target rarity using cached index
        current_idx = self._rarity_index_cache.get(input_rarity)
        if current_idx is None:
            return {"error": f"Raridade desconhecida: {input_rarity}"}
        
        if current_idx + 1 >= len(self.RARITY_ORDER):
            return {"error": f"Raridade máxima atingida ({input_rarity})."}
        
        target_rarity = self.RARITY_ORDER[current_idx + 1]
        
        # Validate contract size based on rarity
        if input_rarity == 'Covert':
            if num_items != 5:
                return {"error": "Contratos Covert → Gold requerem exatamente 5 itens."}
        elif num_items != 10:
            return {"error": "Contratos deste nível requerem exatamente 10 itens."}

        # Pre-allocate
        sum_normalized = 0.0
        total_price = Decimal('0')
        source_counts = {}  # Use dict directly instead of list
        
        # Single pass validation and calculation
        for entry in inputs:
            item = entry['item']
            val_float = entry['float']
            
            # Validate rarity and StatTrak
            if item.real_rarity != input_rarity:
                return {"error": "Todos os itens devem ter a mesma raridade."}
            if item.stattrak != first_is_stt:
                return {"error": "Não é possível misturar itens StatTrak com itens normais."}

            # Accumulate
            sum_normalized += self.normalize_float(val_float, item.min_float, item.max_float)
            total_price += item.price or Decimal('0')
            
            # Count sources directly (avoid intermediate list)
            # Access prefetched data without additional queries
            crates_list = [c for c in item.crates.all() if 'Souvenir' not in c.name]
            sources = crates_list if crates_list else list(item.collections.all())
            
            for source in sources:
                source_counts[source] = source_counts.get(source, 0) + 1

        avg_normalized_float = sum_normalized / num_items

        # Collect all source IDs for single batch query
        source_ids = list(source_counts.keys())
        if not source_ids:
            return {
                'input_price': total_price,
                'expected_output_value': Decimal('0'),
                'roi': Decimal('-100'),
                'profit_chance': 0,
                'avg_normalized_float': avg_normalized_float,
                'is_stattrak': first_is_stt,
                'outcomes': []
            }
        
        # CRITICAL OPTIMIZATION: Single query for ALL possible outcome items
        from django.db.models import Q
        from scanner.models import Crate, Collection
        
        # Separate crates and collections for proper querying
        crate_sources = [s for s in source_ids if isinstance(s, Crate)]
        collection_sources = [s for s in source_ids if isinstance(s, Collection)]
        
        # Build Q filter for both types
        q_filter = Q()
        if crate_sources:
            q_filter |= Q(crates__in=crate_sources)
        if collection_sources:
            q_filter |= Q(collections__in=collection_sources)
        
        # Fetch all possible outcomes in ONE query with prefetch
        all_possible_items = list(Item.objects.filter(
            q_filter,
            souvenir=False,
            real_rarity=target_rarity,
            stattrak=first_is_stt
        ).prefetch_related('crates', 'collections').distinct())
        
        # Pre-compute real float ranges for all outcome items (avoid @property overhead)
        item_float_ranges = {}
        for item in all_possible_items:
            item_float_ranges[item.id] = self._get_real_float_range(item)
        
        # Pre-build item-to-sources mapping (avoid repeated .all() calls)
        item_sources_map = {}
        for item in all_possible_items:
            item_crates = set(item.crates.all())
            item_collections = set(item.collections.all())
            item_sources_map[item.id] = item_crates | item_collections
        
        # Build outcomes
        outcomes = []
        
        for source, count_source in source_counts.items():
            source_probability = count_source / num_items
            
            # Filter items belonging to this source using pre-built map
            source_items = [item for item in all_possible_items 
                           if source in item_sources_map.get(item.id, set())]

            if not source_items:
                continue

            # Filter by float range using pre-computed values
            valid_outcomes = []
            for out_item in source_items:
                out_min = out_item.min_float or 0.0
                out_max = out_item.max_float or 1.0
                final_float = self.calculate_output_float(avg_normalized_float, out_min, out_max)
                
                # Use pre-computed float ranges
                real_min, real_max = item_float_ranges.get(out_item.id, (out_min, out_max))
                
                if real_min <= final_float <= real_max:
                    valid_outcomes.append((out_item, final_float))

            if not valid_outcomes:
                continue

            item_probability = source_probability / len(valid_outcomes)

            # Build outcome list
            for out_item, final_float in valid_outcomes:
                condition = self.get_wear_from_float(final_float)
                
                outcomes.append({
                    'item': out_item,
                    'float': final_float,
                    'condition': condition,
                    'probability': item_probability * 100,
                    'price': out_item.price or Decimal('0'),
                    'image': out_item.image,
                    'stattrak': out_item.stattrak
                })

        # Calculate metrics
        expected_value = sum((d['price'] * Decimal(d['probability'] / 100)) for d in outcomes)
        roi = ((expected_value - total_price) / total_price) * 100 if total_price > 0 else Decimal('0')
        profit_chance = sum(d['probability'] for d in outcomes if d['price'] > total_price)

        return {
            'input_price': total_price,
            'expected_output_value': expected_value,
            'roi': roi,
            'profit_chance': profit_chance,
            'avg_normalized_float': avg_normalized_float,
            'is_stattrak': first_is_stt,
            'outcomes': sorted(outcomes, key=lambda x: x['probability'], reverse=True)
        }

    def calculate_contract_fast(self, item_ids: List[int], float_values: List[float]) -> Dict:
        """
        Optimized version that minimizes database queries.
        
        Args:
            item_ids: List of Item IDs
            float_values: Corresponding float values
        
        Returns:
            Dict with calculation results or error
        """
        num_items = len(item_ids)
        
        if num_items != len(float_values):
            return {"error": "Item count doesn't match float values count"}
        
        if num_items not in (5, 10):
            return {"error": "Exactly 5 or 10 items required"}
        
        # Single optimized query with prefetch
        unique_item_ids = set(item_ids)
        item_dict = Item.objects.filter(id__in=unique_item_ids).prefetch_related(
            'crates',
            'collections'
        ).in_bulk()
        
        # Validate all IDs were found
        if missing := unique_item_ids - item_dict.keys():
            return {"error": f"Items not found in database: {missing}"}
        
        # Build input list in correct order (allows duplicate items)
        inputs = []
        for item_id, float_val in zip(item_ids, float_values):
            item = item_dict.get(item_id)
            if not item:
                return {"error": f"Item {item_id} not found"}
            inputs.append({'item': item, 'float': float_val})
        
        # Use standard calculation
        return self.calculate_contract(inputs)