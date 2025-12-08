import os
from dotenv import load_dotenv

from preload import load_items, load_sources, precompute_outcomes, load_input_items
from genetic import run_genetic_algorithm

load_dotenv()


if __name__ == '__main__':
    API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
    API_KEY = os.getenv('SCANNER_API_KEY', '1q2q3q4q5q')
    
    print("Loading items...")
    load_items(API_URL, API_KEY)
    print("Loading sources...")
    load_sources(API_URL, API_KEY)
    
    # Pre-compute all outcomes for fast lookups
    precompute_outcomes()
    
    # Select input rarity
    # selected_inputs = load_input_items('Mil-Spec Grade', stattrak=False)
    # selected_inputs = load_input_items('Restricted', stattrak=False)
    selected_inputs = load_input_items('Classified', stattrak=False)
    # selected_inputs = load_input_items('Covert', stattrak=False)

    from preload import ITEMS, PRECOMPUTED_OUTCOMES
    
    # Determine number of items needed based on rarity (5 for Covert, 10 for others)
    first_item = ITEMS[selected_inputs[0]['id']]
    num_items = 5 if first_item['real_rarity'] == 'Covert' else 10
    
    print(f"\nContract configuration: {num_items} items per contract")
    print(f"Available input items: {len(selected_inputs)}")
    
    # Run genetic algorithm
    best_contract, best_roi, elapsed_time = run_genetic_algorithm(
        selected_inputs, ITEMS, PRECOMPUTED_OUTCOMES, num_items,
        population_size=1_000_000, generations=10, elite_size=10, keep_top_percentage=0.5
    )
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Best ROI: {best_roi:.2f}%")
    print(f"Time: {elapsed_time:.2f}s")
