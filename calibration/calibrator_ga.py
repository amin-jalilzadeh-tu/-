# calibration/calibrator_ga.py

import random
import copy
import pandas as pd

def ga_calibration(df_params: pd.DataFrame,
                   max_iterations=20,
                   threshold_cv_rmse=30.0,
                   population_size=10,
                   mutation_prob=0.1):
    """
    Genetic Algorithm approach to minimize CV(RMSE).
    """
    # 1) Initialize population
    population = []
    for _ in range(population_size):
        param_set = sample_param_set(df_params)
        cv_score = run_sim_and_validate(param_set)
        population.append((param_set, cv_score))

    generation = 0
    while generation < max_iterations:
        # Sort by CV(RMSE); best first
        population.sort(key=lambda x: x[1])
        best_cv = population[0][1]
        print(f"[GEN {generation}] Best CV(RMSE): {best_cv:.2f}")

        if best_cv < threshold_cv_rmse:
            print("[INFO] GA early-stopping, threshold reached!")
            break

        # 2) Breed next generation
        new_pop = []
        # Elitism: keep the top 2
        new_pop.extend(population[:2])

        # Fill rest by crossover + mutation
        while len(new_pop) < population_size:
            parent1 = tournament_select(population)
            parent2 = tournament_select(population)
            child = crossover(parent1[0], parent2[0])
            child = mutate(child, df_params, mutation_prob)
            cv = run_sim_and_validate(child)
            new_pop.append((child, cv))

        population = new_pop
        generation += 1

    # Return best
    population.sort(key=lambda x: x[1])
    return population[0][0]


def sample_param_set(df_params):
    param_set = {}
    for _, row in df_params.iterrows():
        pname = row["param_name"]
        mn = row["min_value"]
        mx = row["max_value"]
        val = row["assigned_value"]
        if pd.notnull(mn) and pd.notnull(mx):
            param_set[pname] = random.uniform(mn, mx)
        else:
            param_set[pname] = val
    return param_set


def run_sim_and_validate(param_set):
    # Identical approach to random search
    return random.uniform(10,50)  # placeholder

def tournament_select(population, k=3):
    """Pick k random individuals, return the best."""
    contenders = random.sample(population, k)
    # (param_set, cv_score), we want the smallest cv_score
    contenders.sort(key=lambda x: x[1])
    return contenders[0]  # best

def crossover(parentA, parentB):
    """One-point crossover or uniform crossover."""
    child = {}
    for p in parentA.keys():
        # 50% from A, 50% from B
        if random.random() < 0.5:
            child[p] = parentA[p]
        else:
            child[p] = parentB[p]
    return child

def mutate(child, df_params, mutation_prob):
    """Randomly mutate some child parameters within range."""
    for pname in child.keys():
        if random.random() < mutation_prob:
            row = df_params[df_params["param_name"] == pname]
            if not row.empty:
                mn = row["min_value"].values[0]
                mx = row["max_value"].values[0]
                if pd.notnull(mn) and pd.notnull(mx):
                    child[pname] = random.uniform(mn, mx)
    return child
