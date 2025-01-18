"""
optimization_manager.py

STEP 1 of 2: 
- Defines core data structures and helper functions for an optimization-based calibration workflow.
- In Step 2, we will add the actual optimization algorithms (GA, Random, Bayesian, etc.) 
  that use these helpers.
"""

import random
import numpy as np
import pandas as pd
from typing import Callable, Dict, Any, List, Union

# -----------------------------------------------------------------------------
# A) Data Structures
# -----------------------------------------------------------------------------
class ParameterSpec:
    """
    Holds metadata for a single parameter:
      - name: the parameter identifier
      - min_value, max_value: numeric range
      - is_active: if this parameter is used in optimization
      - is_integer: whether the parameter should be integer-valued
      - categories: for categorical parameters (future extension)
    """
    def __init__(self, 
                 name: str, 
                 min_value: float,
                 max_value: float,
                 is_active: bool = True,
                 is_integer: bool = False,
                 categories: List[str] = None):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.is_active = is_active
        self.is_integer = is_integer
        self.categories = categories  # For categorical or enumerated values

    def sample_random(self) -> float:
        """
        Returns a random sample in [min_value, max_value].
        If is_integer=True, we cast the result to int.
        If categories exist, we randomly pick from categories (not used in this step).
        """
        if self.categories is not None:
            # E.g., pick a random item from categories
            return random.choice(self.categories)

        val = random.uniform(self.min_value, self.max_value)
        if self.is_integer:
            val = int(round(val))
        return val


class ParameterSet:
    """
    Represents a set of parameter values, stored as {param_name: numeric_value}.
    """
    def __init__(self, values: Dict[str, float]):
        self.values = values  # e.g., {"infiltration": 1.2, "occupancy": 25.0, ...}

    def copy(self):
        return ParameterSet(dict(self.values))

    def __repr__(self):
        return f"ParameterSet({self.values})"


# -----------------------------------------------------------------------------
# B) Helper Functions
# -----------------------------------------------------------------------------
def create_param_specs_from_df(df_params: pd.DataFrame,
                               active_only: bool = True) -> List[ParameterSpec]:
    """
    Convert a DataFrame with columns like:
      'param_name', 'min_value', 'max_value', 'is_active', 'is_integer'
    into a list of ParameterSpec objects.
    
    :param df_params: DataFrame with param definition
    :param active_only: If True, only create specs for rows where is_active=True
    :return: list of ParameterSpec
    """
    specs = []
    for _, row in df_params.iterrows():
        if active_only and (("is_active" in row) and (not row["is_active"])):
            continue

        name = row["param_name"]
        mn = row["min_value"]
        mx = row["max_value"]
        is_int = bool(row.get("is_integer", False))
        # is_active is deduce from row or default True if missing
        is_act = row.get("is_active", True)

        spec = ParameterSpec(
            name=name,
            min_value=mn,
            max_value=mx,
            is_active=is_act,
            is_integer=is_int
        )
        specs.append(spec)
    return specs


def sample_random_param_set(param_specs: List[ParameterSpec]) -> ParameterSet:
    """
    Generate a random ParameterSet from a list of ParameterSpec.
    :return: ParameterSet
    """
    values = {}
    for spec in param_specs:
        if not spec.is_active:
            continue
        values[spec.name] = spec.sample_random()
    return ParameterSet(values)


def clamp_param_set(param_set: ParameterSet,
                    param_specs: List[ParameterSpec]) -> ParameterSet:
    """
    Ensure that each value in param_set is within [min_value, max_value].
    If is_integer, round or cast to int.
    """
    new_values = dict(param_set.values)
    spec_dict = {s.name: s for s in param_specs}
    for p_name, p_value in new_values.items():
        spec = spec_dict[p_name]
        clamped = max(spec.min_value, min(spec.max_value, p_value))
        if spec.is_integer:
            clamped = int(round(clamped))
        new_values[p_name] = clamped
    return ParameterSet(new_values)


# -----------------------------------------------------------------------------
# C) Objective (Placeholder) 
# -----------------------------------------------------------------------------
def evaluate_param_set(param_set: ParameterSet, 
                       evaluation_func: Callable[[Dict[str, float]], float]) -> float:
    """
    Evaluate a ParameterSet by passing its dict to a user-defined evaluation_func.
    The evaluation_func is expected to return a scalar 'score' or 'error' 
    that we want to MINIMIZE. For example, CV(RMSE) from a surrogate or real simulation.
    """
    return evaluation_func(param_set.values)


# -----------------------------------------------------------------------------
# D) Example Usage (Test for Step 1)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Suppose we have a small DataFrame describing parameters
    data = {
        "param_name": ["infiltration", "occupancy", "u_wall"],
        "min_value": [0.5, 10, 0.3],
        "max_value": [2.0, 40, 1.2],
        "is_active": [True, True, True],
        "is_integer": [False, True, False]
    }
    df_example = pd.DataFrame(data)

    # 1) Convert to ParameterSpec
    specs = create_param_specs_from_df(df_example)
    print("[DEBUG] Created ParameterSpecs:")
    for s in specs:
        print(f"  {s.name}: [{s.min_value}, {s.max_value}], integer={s.is_integer}")

    # 2) Sample random param set
    rand_set = sample_random_param_set(specs)
    print("\n[DEBUG] Random ParamSet:", rand_set)

    # 3) Evaluate param set with a placeholder function
    def mock_eval_func(values: Dict[str, float]) -> float:
        # e.g. compute a "score" = infiltration + occupancy/5 + (1/u_wall)*2 
        # just for demonstration
        infiltration = values["infiltration"]
        occupancy = values["occupancy"]
        u_wall = values["u_wall"]
        score = infiltration + (occupancy / 5.0) + (2.0 / u_wall)
        return score

    score_rand = evaluate_param_set(rand_set, mock_eval_func)
    print("[DEBUG] Score of random set:", score_rand)

    # 4) Clamping demonstration
    # Let's artificially set infiltration=100, occupant= -10
    test_values = {"infiltration": 100, "occupancy": -10, "u_wall": 0.7}
    test_pset = ParameterSet(test_values)
    test_clamped = clamp_param_set(test_pset, specs)
    print("\n[DEBUG] Clamped param set:", test_clamped)


"""
optimization_algorithms.py

STEP 2 of 2:
Implements example optimization algorithms that use the 
helper functions from Step 1 (ParameterSpec, ParameterSet, etc.).

Algorithms included:
  1) Random Search
  2) Genetic Algorithm (GA)
  3) Bayesian Optimization (with scikit-optimize)
  
Requires:
  - from optimization_manager import (ParameterSpec, ParameterSet,
    sample_random_param_set, clamp_param_set, evaluate_param_set)
  - scikit-optimize (for the Bayesian example): pip install scikit-optimize
"""

import random
from typing import List, Callable, Tuple

import numpy as np
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None

from optimization_manager import (
    ParameterSpec,
    ParameterSet,
    sample_random_param_set,
    clamp_param_set,
    evaluate_param_set
)


# ------------------------------------------------------------------------------
# 1) RANDOM SEARCH
# ------------------------------------------------------------------------------
def random_search(param_specs: List[ParameterSpec],
                  evaluation_func: Callable[[dict], float],
                  n_iterations: int = 50) -> Tuple[ParameterSet, float]:
    """
    Simple random search: 
      - Sample n_iterations random param sets
      - Evaluate the objective
      - Return the best found

    :param param_specs: list of ParameterSpec
    :param evaluation_func: function that returns a scalar "score" for a param dict
    :param n_iterations: number of random draws
    :return: (best_parameter_set, best_score)
    """
    best_score = float('inf')
    best_set = None

    for _ in range(n_iterations):
        pset = sample_random_param_set(param_specs)
        score = evaluate_param_set(pset, evaluation_func)
        if score < best_score:
            best_score = score
            best_set = pset

    return best_set, best_score


# ------------------------------------------------------------------------------
# 2) GENETIC ALGORITHM (GA)
# ------------------------------------------------------------------------------
def ga_optimization(param_specs: List[ParameterSpec],
                    evaluation_func: Callable[[dict], float],
                    pop_size: int = 20,
                    max_generations: int = 10,
                    mutation_prob: float = 0.1) -> Tuple[ParameterSet, float]:
    """
    A basic Genetic Algorithm (GA) approach:
      - Initialize a population of random param sets
      - Evaluate each
      - Reproduce via tournament selection & crossover
      - Mutate
      - Repeat for max_generations
      - Return best solution found

    :param param_specs: list of ParameterSpec
    :param evaluation_func: function returning a scalar objective to MINIMIZE
    :param pop_size: number of individuals in the population
    :param max_generations: max GA iterations
    :param mutation_prob: chance of mutation per gene
    :return: (best_parameter_set, best_score)
    """

    # --- 2.1 Initialize population ---
    population = []
    for _ in range(pop_size):
        pset = sample_random_param_set(param_specs)
        score = evaluate_param_set(pset, evaluation_func)
        population.append((pset, score))

    # --- 2.2 GA main loop ---
    for gen in range(max_generations):
        # Sort population by ascending score (best first)
        population.sort(key=lambda x: x[1])
        best_score = population[0][1]
        best_pset = population[0][0]
        print(f"[GEN {gen}] Best score so far: {best_score:.4f}")

        # Early stopping optional
        # if best_score < some_threshold:
        #     break

        # Reproduce new population
        new_population = []
        # Elitism: keep top 2
        new_population.extend(population[:2])

        # Fill the rest with children
        while len(new_population) < pop_size:
            parent1 = tournament_select(population)
            parent2 = tournament_select(population)
            child_pset = crossover(parent1[0], parent2[0])
            child_pset = mutate(child_pset, param_specs, mutation_prob)
            score_child = evaluate_param_set(child_pset, evaluation_func)
            new_population.append((child_pset, score_child))

        population = new_population

    # Return the best from the final population
    population.sort(key=lambda x: x[1])
    return population[0][0], population[0][1]


def tournament_select(population: List[Tuple[ParameterSet, float]],
                      k: int = 3) -> Tuple[ParameterSet, float]:
    """
    Pick k random individuals from the population,
    return the one with the best (lowest) score.
    """
    contenders = random.sample(population, k)
    contenders.sort(key=lambda x: x[1])
    return contenders[0]  # (pset, score)


def crossover(pset_a: ParameterSet, pset_b: ParameterSet) -> ParameterSet:
    """
    One-point or uniform crossover. We'll do uniform crossover:
      For each param, 50% from A, 50% from B.
    """
    child_values = {}
    for key in pset_a.values.keys():
        if random.random() < 0.5:
            child_values[key] = pset_a.values[key]
        else:
            child_values[key] = pset_b.values[key]
    return ParameterSet(child_values)


def mutate(pset: ParameterSet,
           param_specs: List[ParameterSpec],
           mutation_prob: float) -> ParameterSet:
    """
    For each parameter, with probability mutation_prob,
    re-sample from that parameter's range.
    Then clamp to ensure within [min_value, max_value].
    """
    new_values = dict(pset.values)
    spec_dict = {s.name: s for s in param_specs}
    for key in new_values.keys():
        if random.random() < mutation_prob:
            spec = spec_dict[key]
            new_values[key] = spec.sample_random()

    child_pset = ParameterSet(new_values)
    child_pset = clamp_param_set(child_pset, param_specs)
    return child_pset


# ------------------------------------------------------------------------------
# 3) BAYESIAN / SCIKIT-OPTIMIZE
# ------------------------------------------------------------------------------
def bayes_optimization(param_specs: List[ParameterSpec],
                       evaluation_func: Callable[[dict], float],
                       n_calls: int = 30) -> Tuple[ParameterSet, float]:
    """
    Bayesian optimization using scikit-optimize (gp_minimize).
    We build a skopt "space" from param_specs. 
    Then define an objective function that calls evaluation_func.
    If scikit-optimize isn't installed, we fallback to random search.

    :param param_specs: list of ParameterSpec
    :param evaluation_func: objective function returning float 
                           (score to MINIMIZE)
    :param n_calls: number of optimization iterations
    :return: (best_param_set, best_score)
    """
    if gp_minimize is None or Real is None:
        print("[WARN] scikit-optimize not installed. Fallback to random search.")
        return random_search(param_specs, evaluation_func, n_iterations=n_calls)

    # Build skopt Space
    dimensions = []
    param_names = []
    for spec in param_specs:
        if spec.categories:
            # Not implementing categorical in this snippet, but you can use 
            # skopt.space.Categorical for categories
            raise NotImplementedError("Categorical variables not implemented here.")
        else:
            # If integer
            if spec.is_integer:
                dimensions.append(Integer(spec.min_value, spec.max_value, name=spec.name))
            else:
                dimensions.append(Real(spec.min_value, spec.max_value, name=spec.name))
        param_names.append(spec.name)

    # Define the objective for gp_minimize
    def objective(params):
        # params is a list of floats/ints in the same order as dimensions
        param_dict = {}
        for i, val in enumerate(params):
            param_dict[param_names[i]] = val

        # clamp or convert param_dict if needed
        pset = ParameterSet(param_dict)
        pset = clamp_param_set(pset, param_specs)

        score = evaluate_param_set(pset, evaluation_func)
        return score

    # Run gp_minimize
    res = gp_minimize(
        objective,
        dimensions,
        n_calls=n_calls,
        random_state=42
    )

    best_score = res.fun
    best_params = res.x

    # Rebuild a ParameterSet from best_params
    best_values = {}
    for i, val in enumerate(best_params):
        best_values[param_names[i]] = val
    best_pset = ParameterSet(best_values)

    return best_pset, best_score


# ------------------------------------------------------------------------------
# Example usage in main
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal demonstration with a 2-parameter scenario
    from optimization_manager import ParameterSpec, ParameterSet

    # 1) Define parameter specs
    specs_demo = [
        ParameterSpec(name="x", min_value=-5, max_value=5, is_active=True, is_integer=False),
        ParameterSpec(name="y", min_value=-2, max_value=2, is_active=True, is_integer=False)
    ]

    # 2) Example objective function => let's do a simple: f(x,y) = (x^2 + y^2)
    # We want to MINIMIZE this (best solution is x=0,y=0 -> score=0)
    def sphere_obj(pdict):
        return pdict["x"]**2 + pdict["y"]**2

    # [A] Random Search
    best_pset_random, best_score_random = random_search(specs_demo, sphere_obj, n_iterations=50)
    print("[Random] Best found:", best_pset_random, "Score:", best_score_random)

    # [B] GA 
    best_pset_ga, best_score_ga = ga_optimization(specs_demo, sphere_obj, pop_size=10, max_generations=5)
    print("[GA] Best found:", best_pset_ga, "Score:", best_score_ga)

    # [C] Bayesian (skopt) if installed
    best_pset_bayes, best_score_bayes = bayes_optimization(specs_demo, sphere_obj, n_calls=20)
    print("[Bayes] Best found:", best_pset_bayes, "Score:", best_score_bayes)
