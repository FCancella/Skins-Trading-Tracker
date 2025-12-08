from random import sample, choice, random, randint
from typing import Dict, List, Tuple
from multiprocessing import Pool, cpu_count
import time
import math
from tradeup_calc import calculate_contract_roi_fast
from preload import generate_float_values


def print_contract_details(contract: List[Dict], items: Dict[str, Dict], 
                          precomputed_outcomes: Dict, roi: float, rank: int):
    """Print detailed information about a contract."""
    print(f"\n{'='*80}")
    print(f"Rank #{rank} - ROI: {roi:.2f}%")
    print(f"{'='*80}")
    
    total_input_price = 0.0
    source_counts = {}
    
    print("\nInput Items:")
    for i, item_entry in enumerate(contract, 1):
        item = items[item_entry['id']]
        item_price = item_entry.get('price', 0.0) or 0.0
        total_input_price += item_price
        
        print(f"{i:2d}. {item['name']:50s} ${item_price/5.4:6.2f} (Float: {item_entry['float']:.4f})")
        
        for source_id in item['sources']:
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
    
    print(f"\nTotal Input Cost: ${total_input_price/5.4:.2f}")
    
    # Calculate outcomes
    first_item = items[contract[0]['id']]
    input_rarity = first_item['real_rarity']
    stattrak = first_item['stattrak']
    
    # Calculate average normalized float
    sum_normalized = 0.0
    for entry in contract:
        item = items[entry['id']]
        item_min = item.get('min_float', 0.0) or 0.0
        item_max = item.get('max_float', 1.0) or 1.0
        range_val = item_max - item_min
        
        if range_val > 0:
            normalized = (entry['float'] - item_min) / range_val
        else:
            normalized = 0.0
        sum_normalized += normalized
    
    avg_normalized_float = sum_normalized / len(contract)
    float_factor_int = min(int(math.ceil(avg_normalized_float * 100) / 1), 99)
    
    print(f"\nAverage Normalized Float: {avg_normalized_float:.4f} (Factor: {float_factor_int})")
    
    outcomes_prob = {}
    for source_id, count in source_counts.items():
        source_prob = count / len(contract)
        outcomes = precomputed_outcomes[input_rarity][stattrak][source_id][float_factor_int][1:]
        prob_each = source_prob / len(outcomes) if outcomes else 0
        
        for outcome in outcomes:
            outcome_id = outcome['item_id']
            outcomes_prob[outcome_id] = outcomes_prob.get(outcome_id, 0) + prob_each
    
    print("\nPossible Outcomes:")
    profit_chance = 0.0
    for outcome_id, prob in sorted(outcomes_prob.items(), key=lambda x: x[1], reverse=True):
        outcome_price = items[outcome_id]['price']
        print(f"  {items[outcome_id]['name']:50s} ${outcome_price/5.4:6.2f} ({prob*100:5.2f}%)")
        
        if outcome_price > total_input_price:
            profit_chance += prob
    
    expected_value = sum(items[oid]['price'] * prob for oid, prob in outcomes_prob.items())
    print(f"\nExpected Output Value: ${expected_value/5.4:.2f}")
    print(f"Profit Chance: {profit_chance*100:.2f}%")


class GeneticAlgorithm:
    """Genetic algorithm for optimizing trade-up contracts."""
    
    def __init__(self, items: Dict[str, Dict], precomputed_outcomes: Dict, num_items: int = 10):
        self.items = items
        self.precomputed_outcomes = precomputed_outcomes
        self.num_items = num_items
    
    def create_random_contract(self, input_items: List[Dict]) -> List[Dict]:
        return sample(input_items, k=self.num_items)
    
    def evaluate_contract(self, contract: List[Dict]) -> float:
        return calculate_contract_roi_fast(contract, self.items, self.precomputed_outcomes)
    
    def initialize_population(self, input_items: List[Dict], population_size: int) -> List[List[Dict]]:
        """Initialize population with unique contracts."""
        population = []
        seen = set()
        max_attempts = population_size * 10  # Prevent infinite loops
        attempts = 0
        
        while len(population) < population_size and attempts < max_attempts:
            contract = self.create_random_contract(input_items)
            sig = normalize_contract(contract)
            
            if sig not in seen:
                seen.add(sig)
                population.append(contract)
            
            attempts += 1
        
        # If we couldn't generate enough unique contracts, fill with random ones
        while len(population) < population_size:
            population.append(self.create_random_contract(input_items))
        
        return population
    
    def select_top_contracts(self, population: List[List[Dict]], fitness_scores: List[float], top_n: int) -> List[List[Dict]]:
        contracts_with_scores = list(zip(population, fitness_scores))
        contracts_with_scores.sort(key=lambda x: x[1], reverse=True)
        return [contract for contract, _ in contracts_with_scores[:top_n]]
    
    def crossover(self, parent1: List[Dict], parent2: List[Dict]) -> List[Dict]:
        num_from_parent1 = randint(1, self.num_items//2 - 1)
        num_from_parent2 = self.num_items - num_from_parent1
        
        items_from_parent1 = sample(parent1, k=num_from_parent1)
        items_from_parent2 = sample(parent2, k=num_from_parent2)
        
        return items_from_parent1 + items_from_parent2
    
    def mutate(self, contract: List[Dict], input_items: List[Dict]) -> List[Dict]:
        mutated = contract.copy()
        
        # Mutation 1: Replace 1 - 1/3 items (50% from input_items, 50% from within contract)
        if random() < 0.5:
            num_to_replace = randint(1, len(contract)//3)
            for _ in range(num_to_replace):
                pos = randint(0, self.num_items - 1)
                mutated[pos] = choice(input_items) if random() < 0.5 else choice(mutated)
        
        # Mutation 2: Change float value of 1 item
        if random() < 0.5:
            pos = randint(0, self.num_items - 1)
            item_id = mutated[pos]['id']
            item_data = self.items[item_id]
            
            float_price_tuples = generate_float_values(
                item_data['real_min_float'],
                item_data['real_max_float']
            )
            new_float, price_mult = choice(float_price_tuples)
            base_price = item_data.get('price', 0.0) or 0.0
            
            mutated[pos] = {
                'id': item_id,
                'float': new_float,
                'price': base_price * price_mult
            }
        
        return mutated


def evaluate_population_worker(args) -> List[Tuple[int, float]]:
    contracts, items, precomputed_outcomes, num_items, batch_start_idx = args
    ga = GeneticAlgorithm(items, precomputed_outcomes, num_items)
    results = []
    
    for i, contract in enumerate(contracts):
        roi = ga.evaluate_contract(contract)
        results.append((batch_start_idx + i, roi))
    
    return results


def evaluate_population_parallel(population: List[List[Dict]], items: Dict[str, Dict],
                                precomputed_outcomes: Dict, num_items: int,
                                num_processes: int) -> List[float]:
    population_size = len(population)
    batch_size = population_size // num_processes

    with Pool(processes=num_processes) as pool:
        work_items = []
        for i in range(num_processes):
            start_idx = i * batch_size
            end_idx = start_idx + batch_size if i < num_processes - 1 else population_size
            batch = population[start_idx:end_idx]
            work_items.append((batch, items, precomputed_outcomes, num_items, start_idx))
        
        results = pool.map(evaluate_population_worker, work_items)
    
    all_results = []
    for batch_results in results:
        all_results.extend(batch_results)
    
    all_results.sort(key=lambda x: x[0])
    return [roi for _, roi in all_results]


def normalize_contract(contract: List[Dict]) -> tuple:
    """Create a normalized signature for a contract (order-independent).
    Sorts by item ID and float value to create a canonical representation.
    """
    return tuple(sorted((item['id'], item['float']) for item in contract))


def remove_duplicate_contracts(contracts: List[List[Dict]]) -> List[List[Dict]]:
    """Remove duplicate contracts from a list, keeping the first occurrence."""
    seen = set()
    unique_contracts = []
    
    for contract in contracts:
        sig = normalize_contract(contract)
        if sig not in seen:
            seen.add(sig)
            unique_contracts.append(contract)
    
    return unique_contracts


def calculate_diversity(current_top: List[List[Dict]], previous_top: List[List[Dict]]) -> float:
    # contract_sig = lambda c: tuple(sorted(item['id'] for item in c))
    # prev_sigs = {contract_sig(c) for c in previous_top}
    # curr_sigs = {contract_sig(c) for c in current_top}
    # common = len(prev_sigs & curr_sigs)
    """Calculate diversity by comparing contracts including both item IDs and float values."""
    prev_sigs = {normalize_contract(c) for c in previous_top}
    curr_sigs = {normalize_contract(c) for c in current_top}
    common = len(prev_sigs & curr_sigs)
    return ((len(current_top) - common) / len(current_top)) * 100


def run_genetic_algorithm(selected_inputs: List[Dict], items: Dict[str, Dict], 
                          precomputed_outcomes: Dict, num_items: int,
                          population_size: int = 10000, generations: int = 100, elite_size: int = 100, keep_top_percentage: float = 0.5) -> Tuple[List[Dict], float, float]:
    num_processes = cpu_count()
    
    print(f"\nRunning genetic algorithm...")
    print(f"Population size: {population_size:,}")
    print(f"Generations: {generations}")
    print(f"Elite size: {elite_size} (keeping best + {keep_top_percentage*100:.0f}% of rest)")
    print(f"Total evaluations: {population_size * generations:,}")
    
    start_time = time.time()
    
    ga = GeneticAlgorithm(items, precomputed_outcomes, num_items)
    
    best_overall_contract = None
    best_overall_roi = -float('inf')
    previous_top_contracts = None
    print("-" * 30, "Initializing Population", "-" * 30)
    population = ga.initialize_population(selected_inputs, population_size)
    initial_unique = len(population)
    print(f"Initial population: {initial_unique} unique contracts")
    
    for generation in range(generations):
        print(".", end="", flush=True)
        fitness_scores = evaluate_population_parallel(
            population, items, precomputed_outcomes, num_items, num_processes
        )
        print("-", end=" ", flush=True)
        
        best_idx = fitness_scores.index(max(fitness_scores))
        best_roi = fitness_scores[best_idx]
        best_contract = population[best_idx]
        
        if best_roi > best_overall_roi:
            best_overall_roi = best_roi
            best_overall_contract = best_contract
        
        top_contracts = ga.select_top_contracts(population, fitness_scores, elite_size)
        
        diversity_metric = calculate_diversity(top_contracts, previous_top_contracts) if previous_top_contracts else 0.0
        previous_top_contracts = [contract.copy() for contract in top_contracts]
        
        avg_roi = sum(fitness_scores) / len(fitness_scores)
        if generation == 0:
            print(f"Generation {generation + 1}/{generations}: Best ROI = {best_roi:.2f}% | Avg ROI = {avg_roi:.2f}% | Overall Best = {best_overall_roi:.2f}%")
        else:
            print(f"Generation {generation + 1}/{generations}: Best ROI = {best_roi:.2f}% | Avg ROI = {avg_roi:.2f}% | Overall Best = {best_overall_roi:.2f}% | New Contracts = {diversity_metric:.1f}%")
        
        if generation < generations - 1:
            top_contracts = ga.select_top_contracts(population, fitness_scores, elite_size)
            
            new_population = [top_contracts[0].copy()]
            
            num_to_keep = max(0, int((elite_size - 1) * keep_top_percentage))
            if num_to_keep > 0:
                kept_contracts = sample(top_contracts[1:], k=num_to_keep)
                new_population.extend([c.copy() for c in kept_contracts])
            
            num_to_generate = population_size - len(new_population)
            
            for _ in range(num_to_generate):
                rand_value = random()
                
                if rand_value < 0.4:
                    # 40%: Random contract
                    new_contract = ga.create_random_contract(selected_inputs)
                elif rand_value < 0.7:
                    # 30%: Crossover
                    parent1 = choice(top_contracts)
                    parent2 = choice(top_contracts)
                    new_contract = ga.crossover(parent1, parent2)
                else:
                    # 30%: Mutation
                    base_contract = choice(top_contracts)
                    new_contract = ga.mutate(base_contract, selected_inputs)
                
                new_population.append(new_contract)
            
            # Remove duplicates from the new population
            unique_population = remove_duplicate_contracts(new_population)
            
            # If we have fewer unique contracts than desired, fill with random ones
            while len(unique_population) < population_size:
                new_contract = ga.create_random_contract(selected_inputs)
                unique_population.append(new_contract)
            
            # If we have more, truncate (shouldn't happen but just in case)
            population = unique_population[:population_size]
    
    elapsed_time = time.time() - start_time
    
    print(f"\nCompleted in {elapsed_time:.3f} seconds")
    print(f"Evaluations per second: {(population_size * generations) / elapsed_time:,.0f}")
    
    # Get top 5 contracts
    final_fitness_scores = evaluate_population_parallel(
        population, items, precomputed_outcomes, num_items, num_processes
    )
    
    contracts_with_scores = list(zip(population, final_fitness_scores))
    contracts_with_scores.sort(key=lambda x: x[1], reverse=True)
    top_5_contracts = contracts_with_scores[:5]
    
    print("\n" + "#" * 80)
    print("TOP 5 BEST CONTRACTS")
    print("#" * 80)
    
    for rank, (contract, roi) in enumerate(top_5_contracts, 1):
        print_contract_details(contract, items, precomputed_outcomes, roi, rank)
    
    return best_overall_contract, best_overall_roi, elapsed_time
