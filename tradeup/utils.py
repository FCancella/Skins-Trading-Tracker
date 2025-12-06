import random
from decimal import Decimal
from typing import List
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

    @staticmethod
    def get_wear_from_name(name):
        for wear_name, wear_range in TradeUpCalculator.WEAR_RANGES.items():
            if f"({wear_name})" in name:
                return wear_range
        return (0.0, 1.0)

    @staticmethod
    def normalize_float(float_val, min_f, max_f):
        min_f = min_f or 0.0
        max_f = max_f or 1.0
        range_val = max_f - min_f
        if range_val == 0: return 0.0
        return (float_val - min_f) / range_val

    @staticmethod
    def calculate_output_float(avg_normalized_float, outcome_item: Item):
        out_min = outcome_item.min_float or 0.0
        out_max = outcome_item.max_float or 1.0
        return (avg_normalized_float * (out_max - out_min)) + out_min

    def calculate_contract(self, inputs: List[dict[Item, float]]):
        if not inputs or len(inputs) != 10:
            return {"error": "É necessário exatamente 10 itens."}

        total_price = sum(item['item'].price or 0 for item in inputs)
        
        # --- NOVO: Validação de StatTrak ---
        first_is_stt = inputs[0]['item'].stattrak
        
        input_rarity = inputs[0]['item'].real_rarity
        
        try:
            current_idx = self.RARITY_ORDER.index(input_rarity)
            if current_idx + 1 >= len(self.RARITY_ORDER):
                 return {"error": f"Raridade máxima atingida ({input_rarity})."}
            target_rarity = self.RARITY_ORDER[current_idx + 1]
        except ValueError:
            return {"error": f"Raridade desconhecida: {input_rarity}"}

        sum_normalized = 0
        potential_collections = [] 

        for entry in inputs:
            item: Item = entry['item']
            val_float = entry['float']
            
            # Validação: Raridade
            if item.real_rarity != input_rarity:
                return {"error": "Todos os itens devem ter a mesma raridade."}
            
            # --- NOVO: Validação de StatTrak (Mistura proibida) ---
            if item.stattrak != first_is_stt:
                return {"error": "Não é possível misturar itens StatTrak com itens normais."}

            norm = self.normalize_float(val_float, item.min_float, item.max_float)
            sum_normalized += norm
            if item.crates.exists():
                potential_collections.extend(list(item.crates.all()))
            else:
                potential_collections.extend(list(item.collections.all()))

        avg_normalized_float = sum_normalized / 10

        outcomes = []
        unique_sources = set(potential_collections)
        
        for source in unique_sources:
            count_source = potential_collections.count(source)
            source_probability = count_source / 10.0
            
            if hasattr(source, 'items'):
                possible_items = source.items.filter(
                    real_rarity=target_rarity,
                    stattrak=first_is_stt 
                ).distinct('name')
            else:
                possible_items = []

            if not possible_items.exists():
                continue

            real_possible_items = [] 
            for out_item in possible_items:
                final_float = self.calculate_output_float(avg_normalized_float, out_item)
                if out_item.real_min_float <= final_float and final_float <= out_item.real_max_float:
                    real_possible_items.append(out_item)

            num_outcomes = len(real_possible_items)
            item_probability = source_probability / num_outcomes

            for out_item in real_possible_items:
                final_float = self.calculate_output_float(avg_normalized_float, out_item)
                
                condition = "Unknown"
                for w_name, w_range in self.WEAR_RANGES.items():
                    if w_range[0] <= final_float < w_range[1]:
                        condition = w_name
                        break
                
                outcomes.append({
                    'item': out_item,
                    'float': final_float,
                    'condition': condition,
                    'probability': item_probability * 100,
                    'price': out_item.price or 0,
                    'image': out_item.image,
                    'stattrak': out_item.stattrak # Para exibir na UI
                })

        expected_value = sum((d['price'] * Decimal(d['probability']/100)) for d in outcomes)
        roi = ((expected_value - total_price) / total_price) * 100 if total_price > 0 else 0

        return {
            'input_price': total_price,
            'expected_output_value': expected_value,
            'roi': roi,
            'avg_normalized_float': avg_normalized_float,
            'is_stattrak': first_is_stt, # Informa se o contrato foi ST
            'outcomes': sorted(outcomes, key=lambda x: x['probability'], reverse=True)
        }