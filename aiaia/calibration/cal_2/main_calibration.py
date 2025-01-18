#!/usr/bin/env python3
# main_calibration.py

"""
Calibration script with three optimization methods:
  1) Random Search
  2) Genetic Algorithm (GA)
  3) Bayesian Optimization (via scikit-optimize)

Additionally:
  - Saves the best parameters + score to a .joblib file
  - Also saves them to a CSV file

Instructions:
  1) Modify 'scenario_dir' to point to your scenario_params_*.csv location.
  2) Adjust 'objective_function' with your real mismatch or calibration logic.
  3) Set 'method' = "random", "ga", or "bayes" to choose the algorithm.
  4) Run script directly or via man.py: python man.py
"""

import os
import csv
import random
import joblib
import numpy as np
import pandas as pd

from typing import List, Tuple, Dict, Callable

# Bayesian optimization tools (scikit-optimize)
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None


##############################################################################
# 1) LOAD SCENARIO PARAMS
##############################################################################

def load_scenario_parameter_csvs(scenario_dir: str) -> pd.DataFrame:
    """
    Reads scenario_params_*.csv from scenario_dir, merges them into one DataFrame.
    Expects columns: [scenario_index, param_name, assigned_value].
    """
    dfs = []
    for fname in os.listdir(scenario_dir):
        if fname.startswith("scenario_params_") and fname.endswith(".csv"):
            fpath = os.path.join(scenario_dir, fname)
            if not os.path.isfile(fpath):
                continue
            df_temp = pd.read_csv(fpath)
            required = {"scenario_index", "param_name", "assigned_value"}
            missing = required - set(df_temp.columns)
            if missing:
                print(f"[WARNING] {fname} missing {missing}, skipping.")
                continue
            dfs.append(df_temp)
    if not dfs:
        raise FileNotFoundError(f"No scenario_params_*.csv found in {scenario_dir}.")
    df_merged = pd.concat(dfs, ignore_index=True)
    return df_merged


def pivot_scenario_params(df_params: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot => one row per scenario_index, columns=param_name, values=assigned_value
    """
    df_pivot = df_params.pivot_table(
        index="scenario_index",
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()
    df_pivot.columns.name = None
    return df_pivot


##############################################################################
# 2) DEFINE PARAMETER SPEC + HELPER
##############################################################################

class ParameterSpec:
    """
    Holds metadata for a single calibration parameter:
      - name
      - min_value, max_value
      - is_integer
    """
    def __init__(self, name: str, min_value: float, max_value: float,
                 is_integer: bool = False):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.is_integer = is_integer

    def sample_random(self) -> float:
        val = random.uniform(self.min_value, self.max_value)
        if self.is_integer:
            val = int(round(val))
        return val


def build_param_specs_from_pivot(
    df_pivot: pd.DataFrame,
    exclude_cols: List[str] = None
) -> List[ParameterSpec]:
    """
    For each numeric column (except exclude_cols), create a ParameterSpec.
    We guess a range from (col.min, col.max). If min==max, expand slightly.
    """
    if exclude_cols is None:
        exclude_cols = ["scenario_index"]

    specs = []
    for col in df_pivot.columns:
        if col in exclude_cols:
            continue
        # Convert to numeric
        series = pd.to_numeric(df_pivot[col], errors="coerce").dropna()
        if series.empty:
            continue

        cmin = series.min()
        cmax = series.max()
        if cmin == cmax:
            # forcibly expand
            if cmin == 0.0:
                cmin = -0.001
                cmax = 0.001
            else:
                cmin *= 0.95
                cmax *= 1.05

        is_int = False  # Adjust if you need integer parameters
        specs.append(ParameterSpec(col, float(cmin), float(cmax), is_int))
    return specs


##############################################################################
# 3) DEFINE OBJECTIVE (MISMATCH)
##############################################################################

def objective_function(param_dict: Dict[str, float]) -> float:
    """
    A placeholder objective for calibration.
    In a real scenario, you'd:
      - Build an IDF from param_dict
      - Run E+ 
      - Compare vs. real data => compute CV(RMSE) or MBE
    Here, we do a contrived formula:
       mismatch = sum( (param_value - 10)^2 ).
    Return the scalar "score" to MINIMIZE.
    """
    mismatch = 0.0
    for val in param_dict.values():
        mismatch += (val - 10.0) ** 2
    return mismatch


##############################################################################
# 4) CALIBRATION ALGORITHMS
##############################################################################

# 4A) Random Search
def random_search(
    param_specs: List[ParameterSpec],
    objective_func: Callable[[Dict[str, float]], float],
    n_iterations: int = 50
) -> Tuple[Dict[str, float], float]:
    """
    Randomly sample param sets within [min, max], evaluate objective.
    Returns best param_dict + best_score.
    """
    best_score = float("inf")
    best_params = None
    for _ in range(n_iterations):
        p_dict = {}
        for spec in param_specs:
            p_dict[spec.name] = spec.sample_random()
        score = objective_func(p_dict)
        if score < best_score:
            best_score = score
            best_params = p_dict
    return best_params, best_score


# 4B) Genetic Algorithm
def ga_optimize(
    param_specs: List[ParameterSpec],
    objective_func: Callable[[Dict[str, float]], float],
    pop_size: int = 20,
    max_generations: int = 10,
    mutation_prob: float = 0.1
) -> Tuple[Dict[str, float], float]:
    """
    Basic GA approach:
      - Initialize population randomly
      - Evaluate
      - Tournament selection, crossover, mutate
      - Repeat for max_generations
      - Return best param_dict + best_score
    """

    # Initialize population
    population = []
    for _ in range(pop_size):
        p_dict = {}
        for spec in param_specs:
            p_dict[spec.name] = spec.sample_random()
        score = objective_func(p_dict)
        population.append((p_dict, score))

    def tournament_select(pop: List[Tuple[Dict[str, float], float]], k=3):
        contenders = random.sample(pop, k)
        contenders.sort(key=lambda x: x[1])
        return contenders[0]  # best is lowest score

    def crossover(pA: Dict[str, float], pB: Dict[str, float]) -> Dict[str, float]:
        child = {}
        for k in pA.keys():
            if random.random() < 0.5:
                child[k] = pA[k]
            else:
                child[k] = pB[k]
        return child

    def mutate(p: Dict[str, float]) -> Dict[str, float]:
        c = dict(p)
        for spec in param_specs:
            if random.random() < mutation_prob:
                c[spec.name] = spec.sample_random()
        return c

    for gen in range(max_generations):
        # sort by ascending score
        population.sort(key=lambda x: x[1])
        print(f"[GA Gen {gen}] best score = {population[0][1]:.4f}")

        # elitism: keep top 2
        new_pop = population[:2]

        # fill up new_pop
        while len(new_pop) < pop_size:
            pA = tournament_select(population)
            pB = tournament_select(population)
            child_params = crossover(pA[0], pB[0])
            child_params = mutate(child_params)
            child_score = objective_func(child_params)
            new_pop.append((child_params, child_score))

        population = new_pop

    population.sort(key=lambda x: x[1])
    best_params, best_score = population[0]
    return best_params, best_score


# 4C) Bayesian Optimization
def bayes_optimize(
    param_specs: List[ParameterSpec],
    objective_func: Callable[[Dict[str, float]], float],
    n_calls: int = 30
) -> Tuple[Dict[str, float], float]:
    """
    Use scikit-optimize's gp_minimize for Bayesian optimization.
    If it's unavailable, fallback to random_search.
    """
    if gp_minimize is None or Real is None:
        print("[WARN] scikit-optimize not installed. Fallback to random search.")
        return random_search(param_specs, objective_func, n_iterations=n_calls)

    # Build dimension space
    param_names = []
    dimensions = []
    for spec in param_specs:
        param_names.append(spec.name)
        if spec.is_integer:
            dimensions.append(Integer(spec.min_value, spec.max_value, name=spec.name))
        else:
            dimensions.append(Real(spec.min_value, spec.max_value, name=spec.name))

    def skopt_obj(x):
        p_dict = {}
        for i, nm in enumerate(param_names):
            p_dict[nm] = x[i]
        return objective_func(p_dict)

    res = gp_minimize(
        skopt_obj,
        dimensions,
        n_calls=n_calls,
        random_state=42
    )
    best_score = res.fun
    best_x = res.x
    best_params = {nm: bx for nm, bx in zip(param_names, best_x)}
    return best_params, best_score


##############################################################################
# 5) MAIN DEMO
##############################################################################

def main():
    # 1) load scenario params
    scenario_dir = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    df_params_long = load_scenario_parameter_csvs(scenario_dir)
    df_params_pivot = pivot_scenario_params(df_params_long)
    print("[INFO] pivot shape:", df_params_pivot.shape)
    print(df_params_pivot.head(3))

    # 2) build param specs
    param_specs = build_param_specs_from_pivot(df_params_pivot, exclude_cols=["scenario_index"])
    print("[INFO] Number of param specs:", len(param_specs))
    for s in param_specs[:5]:
        print(f"  {s.name}: min={s.min_value:.4f}, max={s.max_value:.4f}, int={s.is_integer}")

    # 3) choose method: "random", "ga", or "bayes"
    method = "bayes"

    # 4) run the chosen method
    if method == "random":
        best_params, best_score = random_search(param_specs, objective_function, n_iterations=50)
    elif method == "ga":
        best_params, best_score = ga_optimize(param_specs, objective_function, pop_size=20, max_generations=5)
    elif method == "bayes":
        best_params, best_score = bayes_optimize(param_specs, objective_function, n_calls=20)
    else:
        raise ValueError(f"Unknown method: {method}")

    print(f"\n=== Calibration via {method} finished ===")
    print("Best score:", best_score)
    print("Best params:")
    for k, v in best_params.items():
        print(f"  {k} = {v:.4f}")

    # 5) Save results to joblib
    best_params_path = f"best_params_{method}.joblib"
    joblib.dump(best_params, best_params_path)
    print(f"[INFO] Saved best params to {best_params_path}")

    # 6) Also save to CSV
    best_params_csv = f"best_params_{method}.csv"
    with open(best_params_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Method", "ParamName", "ParamValue", "BestScore"])
        for param_name, param_value in best_params.items():
            writer.writerow([method, param_name, f"{param_value:.4f}", f"{best_score:.4f}"])

    print(f"[INFO] Also saved best params to {best_params_csv}")


if __name__ == "__main__":
    main()
