# calibration_manager.py

import random
import numpy as np
import pandas as pd
from typing import Callable, Dict, Any, List, Union, Tuple

# Attempt to import scikit-optimize
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    HAVE_SKOPT = True
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None
    HAVE_SKOPT = False


# -----------------------------------------------------------------------------
# A) Data Structures
# -----------------------------------------------------------------------------
class ParameterSpec:
    """
    Holds metadata for a single parameter:
      - name: the parameter identifier
      - min_value, max_value: numeric range
      - is_active: if this parameter is used in calibration
      - is_integer: whether the parameter should be integer-valued
      - categories: for categorical parameters (not fully implemented here)
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
        If is_integer=True, cast the result to int.
        If categories exist, picks from categories (not fully used here).
        """
        if self.categories is not None:
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
        self.values = values  # e.g. {"infiltration": 1.2, "occupancy": 25.0, ...}

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
    Convert a DataFrame with columns:
      'param_name', 'min_value', 'max_value', 'is_active', 'is_integer'
    into a list of ParameterSpec objects.
    """
    specs = []
    for _, row in df_params.iterrows():
        if active_only and (("is_active" in row) and (not row["is_active"])):
            continue

        name = row["param_name"]
        mn = row["min_value"]
        mx = row["max_value"]
        is_int = bool(row.get("is_integer", False))
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
    """Generate a random ParameterSet from a list of ParameterSpec."""
    values = {}
    for spec in param_specs:
        if not spec.is_active:
            continue
        values[spec.name] = spec.sample_random()
    return ParameterSet(values)


def clamp_param_set(param_set: ParameterSet,
                    param_specs: List[ParameterSpec]) -> ParameterSet:
    """
    Ensure each value in param_set is within [min_value, max_value].
    If is_integer, round or cast to int.
    """
    new_values = dict(param_set.values)
    spec_dict = {s.name: s for s in param_specs}
    for p_name, p_value in new_values.items():
        spec = spec_dict.get(p_name, None)
        if spec:
            clamped = max(spec.min_value, min(spec.max_value, p_value))
            if spec.is_integer:
                clamped = int(round(clamped))
            new_values[p_name] = clamped
    return ParameterSet(new_values)


def evaluate_param_set(param_set: ParameterSet, 
                       evaluation_func: Callable[[Dict[str, float]], float]) -> float:
    """
    Evaluate a ParameterSet by passing its dict to user-defined 'evaluation_func',
    which returns a scalar error or cost (to MINIMIZE). e.g. CV(RMSE).
    """
    return evaluation_func(param_set.values)


# -----------------------------------------------------------------------------
# C) Random Search
# -----------------------------------------------------------------------------
def random_search(param_specs: List[ParameterSpec],
                  evaluation_func: Callable[[dict], float],
                  n_iterations: int = 50) -> Tuple[ParameterSet, float]:
    """
    Simple random search calibration:
      - Sample n_iterations random param sets
      - Evaluate objective
      - Return best
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


# -----------------------------------------------------------------------------
# D) Genetic Algorithm (GA)
# -----------------------------------------------------------------------------
def ga_optimization(param_specs: List[ParameterSpec],
                    evaluation_func: Callable[[dict], float],
                    pop_size: int = 20,
                    max_generations: int = 10,
                    mutation_prob: float = 0.1) -> Tuple[ParameterSet, float]:
    """
    Basic GA approach:
      1. Initialize pop_size random param sets
      2. Evaluate each
      3. Repeat for max_generations:
         - Sort by score
         - Keep some elites
         - Reproduce via tournament selection & crossover
         - Mutate
      4. Return best
    """

    # 1) Initialize population
    population = []
    for _ in range(pop_size):
        pset = sample_random_param_set(param_specs)
        score = evaluate_param_set(pset, evaluation_func)
        population.append((pset, score))

    # 2) GA main loop
    for gen in range(max_generations):
        # Sort population by ascending score
        population.sort(key=lambda x: x[1])
        best_score = population[0][1]
        best_pset = population[0][0]
        print(f"[GA Generation {gen}] Best score: {best_score:.4f}")

        # Reproduce
        new_pop = []
        # keep top 2
        new_pop.extend(population[:2])

        # fill rest
        while len(new_pop) < pop_size:
            parent1 = tournament_select(population)
            parent2 = tournament_select(population)
            child_pset = crossover(parent1[0], parent2[0])
            child_pset = mutate(child_pset, param_specs, mutation_prob, evaluation_func)
            child_score = evaluate_param_set(child_pset, evaluation_func)
            new_pop.append((child_pset, child_score))

        population = new_pop

    # final best
    population.sort(key=lambda x: x[1])
    return population[0][0], population[0][1]


def tournament_select(population: List[Tuple[ParameterSet, float]], k: int = 3) -> Tuple[ParameterSet, float]:
    """Pick k random individuals, return best (lowest score)."""
    contenders = random.sample(population, k)
    contenders.sort(key=lambda x: x[1])
    return contenders[0]


def crossover(pset_a: ParameterSet, pset_b: ParameterSet) -> ParameterSet:
    """Uniform crossover: for each param, pick from parent A or B at 50% chance."""
    child_vals = {}
    for key in pset_a.values.keys():
        if random.random() < 0.5:
            child_vals[key] = pset_a.values[key]
        else:
            child_vals[key] = pset_b.values[key]
    return ParameterSet(child_vals)


def mutate(pset: ParameterSet,
           param_specs: List[ParameterSpec],
           mutation_prob: float,
           eval_func: Callable[[Dict[str, float]], float]) -> ParameterSet:
    """
    For each param, with probability mutation_prob, re-sample.
    Then clamp. 
    """
    new_vals = dict(pset.values)
    spec_dict = {s.name: s for s in param_specs}

    for key in new_vals.keys():
        if random.random() < mutation_prob:
            spec = spec_dict[key]
            new_vals[key] = spec.sample_random()

    child = ParameterSet(new_vals)
    child = clamp_param_set(child, param_specs)
    return child


# -----------------------------------------------------------------------------
# E) Bayesian (scikit-optimize)
# -----------------------------------------------------------------------------
def bayes_optimization(param_specs: List[ParameterSpec],
                       evaluation_func: Callable[[dict], float],
                       n_calls: int = 30) -> Tuple[ParameterSet, float]:
    """
    If scikit-optimize is installed, uses gp_minimize; else fallback to random_search.
    :return: (best_param_set, best_score)
    """
    if not HAVE_SKOPT:
        print("[WARN] scikit-optimize not installed. Fallback to random search.")
        return random_search(param_specs, evaluation_func, n_iterations=n_calls)

    # Build skopt space
    dimensions = []
    param_names = []
    for spec in param_specs:
        if spec.categories:
            raise NotImplementedError("Categorical not implemented in this snippet.")
        else:
            if spec.is_integer:
                dimensions.append(Integer(spec.min_value, spec.max_value, name=spec.name))
            else:
                dimensions.append(Real(spec.min_value, spec.max_value, name=spec.name))
        param_names.append(spec.name)

    def objective(params):
        # params is a list in same order as dimensions
        param_dict = {}
        for i, val in enumerate(params):
            param_dict[param_names[i]] = val

        pset = ParameterSet(param_dict)
        pset = clamp_param_set(pset, param_specs)
        score = evaluate_param_set(pset, evaluation_func)
        return score

    res = gp_minimize(objective, dimensions, n_calls=n_calls, random_state=42)
    best_score = res.fun
    best_vals = res.x
    best_dict = {}
    for i, val in enumerate(best_vals):
        best_dict[param_names[i]] = val
    best_pset = ParameterSet(best_dict)

    return best_pset, best_score


# -----------------------------------------------------------------------------
# F) Example Usage (Test)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example with 2D param space
    # f(x,y) = x^2 + y^2 -> minimum at (0,0)
    def test_eval_func(p: Dict[str, float]) -> float:
        return p["x"]**2 + p["y"]**2

    specs_demo = [
        ParameterSpec("x", -5, 5, True, False),
        ParameterSpec("y", -3, 3, True, False)
    ]

    # Random
    best_p_rand, best_score_rand = random_search(specs_demo, test_eval_func, n_iterations=30)
    print("[Random] best:", best_p_rand, "score:", best_score_rand)

    # GA
    best_p_ga, best_score_ga = ga_optimization(specs_demo, test_eval_func, pop_size=15, max_generations=5)
    print("[GA] best:", best_p_ga, "score:", best_score_ga)

    # Bayesian
    best_p_bayes, best_score_bayes = bayes_optimization(specs_demo, test_eval_func, n_calls=20)
    print("[Bayesian] best:", best_p_bayes, "score:", best_score_bayes)












