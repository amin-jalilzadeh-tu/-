"""
calibration_main.py

Demonstrates a calibration workflow using 3 optimization approaches:
  1) Random Search
  2) Genetic Algorithm (GA)
  3) Bayesian Optimization (with scikit-optimize)

Integration points:
  - We load parameter specs from a CSV (similar to df_param_ranges).
  - We define an 'evaluation function' that returns a mismatch vs. real data.
    (This could call a surrogate model or the real E+ simulation.)
  - Then we run the chosen optimization method until we find the best match.

Dependencies:
  pip install numpy pandas scikit-optimize (if you want Bayesian) joblib
"""

import os
import numpy as np
import pandas as pd
import random
from typing import List, Dict, Any, Callable

try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    SKOPT_AVAILABLE = True
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None
    SKOPT_AVAILABLE = False


class ParameterSpec:
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
        self.categories = categories

    def sample_random(self) -> float:
        if self.categories is not None:
            return random.choice(self.categories)
        val = random.uniform(self.min_value, self.max_value)
        if self.is_integer:
            val = int(round(val))
        return val


class ParameterSet:
    def __init__(self, values: Dict[str, float]):
        self.values = values

    def copy(self):
        return ParameterSet(dict(self.values))

    def __repr__(self):
        return f"ParameterSet({self.values})"


def clamp_param_set(param_set: ParameterSet,
                    param_specs: List[ParameterSpec]) -> ParameterSet:
    new_values = dict(param_set.values)
    spec_dict = {s.name: s for s in param_specs}
    for p_name, p_value in new_values.items():
        spec = spec_dict[p_name]
        clamped = max(spec.min_value, min(spec.max_value, p_value))
        if spec.is_integer:
            clamped = int(round(clamped))
        new_values[p_name] = clamped
    return ParameterSet(new_values)


def sample_random_param_set(param_specs: List[ParameterSpec]) -> ParameterSet:
    values = {}
    for spec in param_specs:
        if not spec.is_active:
            continue
        values[spec.name] = spec.sample_random()
    return ParameterSet(values)


def evaluate_param_set(param_set: ParameterSet,
                       evaluation_func: Callable[[Dict[str, float]], float]) -> float:
    return evaluation_func(param_set.values)


def random_search(param_specs: List[ParameterSpec],
                  evaluation_func: Callable[[dict], float],
                  n_iterations: int = 50):
    best_score = float('inf')
    best_pset = None

    for _ in range(n_iterations):
        pset = sample_random_param_set(param_specs)
        score = evaluation_func(pset.values)
        if score < best_score:
            best_score = score
            best_pset = pset

    return best_pset, best_score


def ga_optimization(param_specs: List[ParameterSpec],
                    evaluation_func: Callable[[dict], float],
                    pop_size: int = 20,
                    max_generations: int = 10,
                    mutation_prob: float = 0.1):
    """
    Basic Genetic Algorithm:
      - Initialize population
      - Evaluate
      - Reproduce (selection, crossover, mutation)
      - Return best
    """
    # 1) Init population
    population = []
    for _ in range(pop_size):
        pset = sample_random_param_set(param_specs)
        score = evaluation_func(pset.values)
        population.append((pset, score))

    # 2) GA loop
    for gen in range(max_generations):
        # Sort by ascending score
        population.sort(key=lambda x: x[1])
        best_score = population[0][1]
        print(f"[GEN {gen}] best_score = {best_score:.4f}")

        # Reproduce new pop
        new_pop = []
        # Elitism: keep top 2
        new_pop.extend(population[:2])

        # Fill up population
        while len(new_pop) < pop_size:
            parent1 = tournament_select(population)
            parent2 = tournament_select(population)
            child_pset = crossover(parent1[0], parent2[0])
            child_pset = mutate(child_pset, param_specs, mutation_prob)
            child_score = evaluation_func(child_pset.values)
            new_pop.append((child_pset, child_score))

        population = new_pop

    population.sort(key=lambda x: x[1])
    return population[0][0], population[0][1]


def tournament_select(population: List[tuple], k: int = 3):
    contenders = random.sample(population, k)
    contenders.sort(key=lambda x: x[1])
    return contenders[0]


def crossover(psetA: ParameterSet, psetB: ParameterSet) -> ParameterSet:
    child_vals = {}
    for k in psetA.values.keys():
        if random.random() < 0.5:
            child_vals[k] = psetA.values[k]
        else:
            child_vals[k] = psetB.values[k]
    return ParameterSet(child_vals)


def mutate(pset: ParameterSet,
           param_specs: List[ParameterSpec],
           mutation_prob: float) -> ParameterSet:
    new_vals = dict(pset.values)
    spec_dict = {s.name: s for s in param_specs}

    for key in new_vals.keys():
        if random.random() < mutation_prob:
            # resample
            spec = spec_dict[key]
            new_vals[key] = spec.sample_random()

    child = ParameterSet(new_vals)
    child = clamp_param_set(child, param_specs)
    return child


def bayes_optimization(param_specs: List[ParameterSpec],
                       evaluation_func: Callable[[dict], float],
                       n_calls: int = 30):
    """
    If scikit-optimize is not installed, this defaults to random search.
    """
    if not SKOPT_AVAILABLE or gp_minimize is None:
        print("[WARN] scikit-optimize not installed. Fallback to random_search.")
        return random_search(param_specs, evaluation_func, n_iterations=n_calls)

    from skopt.space import Space, Categorical  # only if installed

    dims = []
    param_names = []
    for spec in param_specs:
        if spec.categories:
            # Not implemented in detail
            raise NotImplementedError("Categorical example not implemented.")
        else:
            if spec.is_integer:
                dims.append(Integer(spec.min_value, spec.max_value, name=spec.name))
            else:
                dims.append(Real(spec.min_value, spec.max_value, name=spec.name))
        param_names.append(spec.name)

    # Objective
    def objective(params_list):
        param_dict = {}
        for i, val in enumerate(params_list):
            param_dict[param_names[i]] = val
        pset = ParameterSet(param_dict)
        pset = clamp_param_set(pset, param_specs)
        return evaluation_func(pset.values)

    # run gp_minimize
    res = gp_minimize(
        objective,
        dims,
        n_calls=n_calls,
        random_state=42
    )

    best_score = res.fun
    best_solution = res.x
    best_vals = {}
    for i, val in enumerate(best_solution):
        best_vals[param_names[i]] = val
    best_pset = ParameterSet(best_vals)

    return best_pset, best_score


def load_param_specs(csv_file: str) -> List[ParameterSpec]:
    """
    Loads a CSV with columns like [param_name, min_value, max_value, is_active, is_integer].
    Returns a list of ParameterSpec.
    """
    df = pd.read_csv(csv_file)
    specs = []
    for _, row in df.iterrows():
        param_name = row["param_name"]
        mn = float(row["min_value"])
        mx = float(row["max_value"])
        is_act = row.get("is_active", True)
        is_int = row.get("is_integer", False)
        spec = ParameterSpec(
            name=param_name,
            min_value=mn,
            max_value=mx,
            is_active=is_act,
            is_integer=is_int
        )
        specs.append(spec)
    return specs


def mock_eplus_or_surrogate(param_dict: Dict[str, float]) -> float:
    """
    Example calibration objective function that returns
    a mismatch between model and real data.
    We'll do a contrived formula for demonstration.
    """
    total = sum(param_dict.values())
    noise = np.random.uniform(-0.1, 0.1)
    return abs(10.0 - total) + noise


def main():
    """
    Run a demo of the calibration workflow. 
    1) Create or load param specs from CSV
    2) Define an objective function
    3) Run three optimization strategies
    4) Compare results and save the best
    """
    param_specs_csv = "my_param_specs.csv"
    if not os.path.isfile(param_specs_csv):
        # Create a demo CSV if it doesn't exist
        data_demo = {
            "param_name": ["infiltration", "occupancy", "wall_u"],
            "min_value": [0.5, 10, 0.3],
            "max_value": [2.0, 40, 1.2],
            "is_active": [True, True, True],
            "is_integer": [False, True, False]
        }
        df_demo = pd.DataFrame(data_demo)
        df_demo.to_csv(param_specs_csv, index=False)
        print(f"[INFO] Created a demo param specs CSV => {param_specs_csv}")

    # 1) Load param specs
    specs = load_param_specs(param_specs_csv)
    print(f"[INFO] Loaded {len(specs)} parameter specs from {param_specs_csv}")

    # 2) Define objective function
    def calibration_objective(param_values: Dict[str, float]) -> float:
        return mock_eplus_or_surrogate(param_values)

    # 3) Run each method
    print("\n=== Running Random Search Calibration ===")
    best_set_rand, best_score_rand = random_search(specs, calibration_objective, n_iterations=20)
    print("[RANDOM] Best ParamSet:", best_set_rand, "Score:", best_score_rand)

    print("\n=== Running GA Calibration ===")
    best_set_ga, best_score_ga = ga_optimization(specs, calibration_objective,
                                                 pop_size=10, max_generations=5, mutation_prob=0.2)
    print("[GA] Best ParamSet:", best_set_ga, "Score:", best_score_ga)

    print("\n=== Running Bayesian Calibration ===")
    best_set_bayes, best_score_bayes = bayes_optimization(specs, calibration_objective, n_calls=15)
    print("[Bayes] Best ParamSet:", best_set_bayes, "Score:", best_score_bayes)

    # 4) Compare/choose the best
    results = [
        ("Random", best_set_rand, best_score_rand),
        ("GA", best_set_ga, best_score_ga),
        ("Bayesian", best_set_bayes, best_score_bayes)
    ]
    results.sort(key=lambda x: x[2])  # sort by score ascending
    best_method, best_params, best_score = results[0]
    print(f"\n=== Overall Best Among 3 ===")
    print(f"Method: {best_method}, Score: {best_score:.4f}, Params: {best_params}")

    out_csv = "calibration_best_params.csv"
    df_out = pd.DataFrame(list(best_params.values.items()), columns=["param_name", "param_value"])
    df_out["best_score"] = best_score
    df_out["method"] = best_method
    df_out.to_csv(out_csv, index=False)
    print(f"[INFO] Saved best param set to {out_csv}")


if __name__ == "__main__":
    main()
