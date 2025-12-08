from random import sample, choice, random, randint
from typing import Dict, List, Tuple
from multiprocessing import Pool, cpu_count
import time
import math
from tradeup_calc import calculate_contract_roi_fast
from preload import generate_float_values
from genetic import (
    GeneticAlgorithm, 
    normalize_contract, 
    remove_duplicate_contracts,
    print_contract_details
)


def run_island_worker(args) -> Tuple[int, List[Dict], float, List[List[Dict]]]:
    """Run evolution on a single island."""
    (island_id, selected_inputs, items, precomputed_outcomes, num_items,
     island_pop_size, generations_per_migration, elite_size, keep_top_percentage) = args
    
    ga = GeneticAlgorithm(items, precomputed_outcomes, num_items)
    
    # Initialize island population
    population = ga.initialize_population(selected_inputs, island_pop_size)
    
    best_island_contract = None
    best_island_roi = -float('inf')
    
    # Evolve for several generations before migration
    for gen in range(generations_per_migration):
        # Evaluate population
        fitness_scores = []
        for contract in population:
            roi = ga.evaluate_contract(contract)
            fitness_scores.append(roi)
        
        # Track best
        best_idx = fitness_scores.index(max(fitness_scores))
        best_roi = fitness_scores[best_idx]
        if best_roi > best_island_roi:
            best_island_roi = best_roi
            best_island_contract = population[best_idx]
        
        # Selection and reproduction
        top_contracts = ga.select_top_contracts(population, fitness_scores, elite_size)
        new_population = [top_contracts[0].copy()]
        
        num_to_keep = max(0, int((elite_size - 1) * keep_top_percentage))
        if num_to_keep > 0:
            kept_contracts = sample(top_contracts[1:], k=num_to_keep)
            new_population.extend([c.copy() for c in kept_contracts])
        
        num_to_generate = island_pop_size - len(new_population)
        
        for _ in range(num_to_generate):
            rand_value = random()
            
            if rand_value < 0.4:
                new_contract = ga.create_random_contract(selected_inputs)
            elif rand_value < 0.7:
                parent1 = choice(top_contracts)
                parent2 = choice(top_contracts)
                new_contract = ga.crossover(parent1, parent2)
            else:
                base_contract = choice(top_contracts)
                new_contract = ga.mutate(base_contract, selected_inputs)
            
            new_population.append(new_contract)
        
        population = remove_duplicate_contracts(new_population)
        while len(population) < island_pop_size:
            population.append(ga.create_random_contract(selected_inputs))
    
    # Return island ID, best contract, best ROI, and top contracts for migration
    top_for_migration = ga.select_top_contracts(population, 
                                                [ga.evaluate_contract(c) for c in population],
                                                min(5, elite_size))
    
    return island_id, best_island_contract, best_island_roi, top_for_migration


def run_island_genetic_algorithm(
    selected_inputs: List[Dict], 
    items: Dict[str, Dict],
    precomputed_outcomes: Dict, 
    num_items: int,
    num_islands: int = None,
    population_per_island: int = 2000,
    total_generations: int = 100,
    migration_interval: int = 10,
    migration_size: int = 3,
    elite_size: int = 100,
    keep_top_percentage: float = 0.5
) -> Tuple[List[Dict], float, float]:
    """
    Island Model Genetic Algorithm
    
    Args:
        num_islands: Number of islands (default: number of CPUs)
        population_per_island: Population size per island
        total_generations: Total generations to run
        migration_interval: How often to migrate between islands
        migration_size: Number of individuals to migrate
    """
    if num_islands is None:
        num_islands = cpu_count()
    
    print(f"\n{'='*80}")
    print(f"ISLAND MODEL GENETIC ALGORITHM")
    print(f"{'='*80}")
    print(f"Number of islands: {num_islands}")
    print(f"Population per island: {population_per_island:,}")
    print(f"Total population: {num_islands * population_per_island:,}")
    print(f"Generations: {total_generations}")
    print(f"Migration every: {migration_interval} generations")
    print(f"Migration size: {migration_size} individuals")
    print(f"Total evaluations: {num_islands * population_per_island * total_generations:,}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    best_overall_contract = None
    best_overall_roi = -float('inf')
    
    # Initialize islands
    print("Initializing islands...")
    island_populations = []
    ga = GeneticAlgorithm(items, precomputed_outcomes, num_items)
    
    for i in range(num_islands):
        island_pop = ga.initialize_population(selected_inputs, population_per_island)
        island_populations.append(island_pop)
    
    num_migrations = total_generations // migration_interval
    
    for migration_epoch in range(num_migrations):
        print(f"\n{'─'*80}")
        print(f"Migration Epoch {migration_epoch + 1}/{num_migrations}")
        print(f"{'─'*80}")
        
        # Prepare work for parallel execution
        work_items = []
        for island_id in range(num_islands):
            work_items.append((
                island_id,
                selected_inputs,
                items,
                precomputed_outcomes,
                num_items,
                population_per_island,
                migration_interval,
                elite_size,
                keep_top_percentage
            ))
        
        # Run islands in parallel
        print(f"Evolving {num_islands} islands for {migration_interval} generations...", flush=True)
        with Pool(processes=num_islands) as pool:
            results = pool.map(run_island_worker, work_items)
        
        # Process results
        island_best_contracts = []
        island_migrants = []
        
        for island_id, best_contract, best_roi, top_contracts in results:
            island_best_contracts.append((best_contract, best_roi))
            island_migrants.append(top_contracts[:migration_size])
            
            print(f"  Island {island_id + 1}: Best ROI = {best_roi:.2f}%")
            
            if best_roi > best_overall_roi:
                best_overall_roi = best_roi
                best_overall_contract = best_contract
        
        print(f"\n>>> Overall Best ROI: {best_overall_roi:.2f}% <<<")
        
        # Migration: Ring topology (each island sends to next island)
        if migration_epoch < num_migrations - 1:  # Don't migrate on last epoch
            print(f"\nMigrating {migration_size} individuals between islands...")
            
            # Reinitialize populations with migrants
            for i in range(num_islands):
                next_island = (i + 1) % num_islands
                
                # Get migrants from previous island
                prev_island = (i - 1) % num_islands
                migrants = island_migrants[prev_island]
                
                # Create new population for this island
                new_pop = ga.initialize_population(selected_inputs, 
                                                   population_per_island - len(migrants))
                
                # Add migrants
                new_pop.extend([m.copy() for m in migrants])
                island_populations[i] = new_pop
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"Completed in {elapsed_time:.3f} seconds")
    print(f"Evaluations per second: {(num_islands * population_per_island * total_generations) / elapsed_time:,.0f}")
    print(f"{'='*80}")
    
    # Gather all top contracts from all islands for final ranking
    print("\nGathering best contracts from all islands...")
    all_best_contracts = []
    
    for island_pop in island_populations:
        fitness_scores = [ga.evaluate_contract(c) for c in island_pop]
        top_5 = ga.select_top_contracts(island_pop, fitness_scores, 5)
        all_best_contracts.extend([(c, ga.evaluate_contract(c)) for c in top_5])
    
    # Sort and get top 5 overall
    all_best_contracts.sort(key=lambda x: x[1], reverse=True)
    top_5_contracts = all_best_contracts[:5]
    
    print("\n" + "#" * 80)
    print("TOP 5 BEST CONTRACTS (ACROSS ALL ISLANDS)")
    print("#" * 80)
    
    for rank, (contract, roi) in enumerate(top_5_contracts, 1):
        print_contract_details(contract, items, precomputed_outcomes, roi, rank)
    
    return best_overall_contract, best_overall_roi, elapsed_time


if __name__ == "__main__":
    # Example usage
    print("Island Model Genetic Algorithm - Example")
    print("Import this module and call run_island_genetic_algorithm()")
