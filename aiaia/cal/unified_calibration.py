"""
unified_calibration.py

A single script unifying calibration with three approaches:
  1) Random Search
  2) Genetic Algorithm (GA)
  3) Bayesian Optimization (scikit-optimize if available)

Steps:
1) Load scenario parameter CSVs from a folder (scenario_params_dhw.csv, etc.).
2) Extract or define param_min, param_max for each param_name.
3) Build a ParamSpec list (param_space).
4) Provide an evaluation function that:
   - uses param values to run either direct E+ or a surrogate,
   - compares to real data,
   - returns an error metric (lower is better).
5) Run calibration method to minimize that error.

Author: Example
"""

import os
import csv
import random
import copy
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Callable

# Attempt to import scikit-optimize globally
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    from skopt.utils import use_named_args
    HAVE_SKOPT = True
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None
    use_named_args = None
    HAVE_SKOPT = False


# -------------------------------------------------------------------------
# 1) ParamSpec Class & Reading from Scenario CSV
# -------------------------------------------------------------------------

class ParamSpec:
    """
    Defines one parameter:
      - name: string
      - min_value, max_value: numeric
      - is_integer: bool
    """
    def __init__(
        self,
        name: str,
        min_value: float,
        max_value: float,
        is_integer: bool = False
    ):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.is_integer = is_integer

    def sample_random(self) -> float:
        """
        Return a single random sample from [min_value, max_value].
        If is_integer is True, round to an integer.
        """
        val = random.uniform(self.min_value, self.max_value)
        if self.is_integer:
            val = int(round(val))
        return val


def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Reads scenario_params_*.csv (dhw, elec, fenez, hvac, vent) from a folder,
    merges into a single DataFrame, expecting columns:
      [scenario_index, param_name, assigned_value, param_min, param_max, ...]
    """
    scenario_files = [
        "scenario_params_dhw.csv",
        "scenario_params_elec.csv",
        "scenario_params_fenez.csv",
        "scenario_params_hvac.csv",
        "scenario_params_vent.csv"
    ]

    dfs = []
    for fname in scenario_files:
        fpath = os.path.join(scenario_folder, fname)
        if os.path.isfile(fpath):
            df_temp = pd.read_csv(fpath)
            df_temp["source_file"] = fname
            dfs.append(df_temp)
        else:
            print(f"[INFO] Not found: {fpath}, skipping.")
    if not dfs:
        raise FileNotFoundError(f"No scenario_params_*.csv found in {scenario_folder}")

    merged = pd.concat(dfs, ignore_index=True)
    return merged


def build_param_specs_from_scenario(
    df_scen: pd.DataFrame,
    param_min_col: str = "param_min",
    param_max_col: str = "param_max"
) -> List[ParamSpec]:
    """
    For each unique param_name in df_scen, define a ParamSpec:
      - name = param_name
      - min_value, max_value from param_min/param_max
      - fallback if missing or invalid
    If min_value == max_value, forcibly expand a small range.
    Currently not handling is_integer logic automatically; you can adjust if needed.
    """
    param_names = df_scen["param_name"].unique().tolist()
    specs = []

    for pname in param_names:
        sub = df_scen[df_scen["param_name"] == pname]
        if sub.empty:
            continue

        row0 = sub.iloc[0]
        mn = row0.get(param_min_col, np.nan)
        mx = row0.get(param_max_col, np.nan)

        # Check if missing or invalid
        if pd.isna(mn) or pd.isna(mx) or (mn >= mx):
            # fallback approach: e.g. ±20% around assigned_value
            val = row0.get("assigned_value", 1.0)
            if pd.isna(val):
                val = 1.0
            base = float(val)
            mn = base * 0.8
            mx = base * 1.2
            if mn >= mx:
                mx = mn + 1e-4

        # If still invalid
        if mn >= mx:
            mn, mx = 0.0, 1.0

        # is_integer = (row0.get("is_integer", False) == True)
        is_integer = False

        spec = ParamSpec(
            name=pname,
            min_value=float(mn),
            max_value=float(mx),
            is_integer=is_integer
        )
        specs.append(spec)

    return specs


# -------------------------------------------------------------------------
# 2) The Evaluate Function (Placeholder)
# -------------------------------------------------------------------------

def simulate_or_surrogate(param_dict: Dict[str, float]) -> float:
    """
    Placeholder: runs E+ or calls a surrogate, returns mismatch error (lower=better).
    We'll do sum of param values vs. 50.0 + noise for demonstration.

    In a real pipeline:
      1) param_dict => build IDF or call a surrogate
      2) compute mismatch => float
      3) return mismatch (lower=better)
    """
    val_sum = sum(param_dict.values())
    noise = random.uniform(-0.5, 0.5)
    return abs(val_sum - 50.0) + noise


# -------------------------------------------------------------------------
# 3) Random Search
# -------------------------------------------------------------------------

def random_search_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    n_iterations: int = 50
) -> Tuple[Dict[str, float], float, list]:
    """
    1) Randomly sample param sets
    2) Evaluate them
    3) Keep track of the best (lowest error)
    Also returns a history of (param_dict, error).
    """
    best_params = None
    best_error = float("inf")
    history = []

    for _ in range(n_iterations):
        p_dict = {}
        for spec in param_specs:
            p_dict[spec.name] = spec.sample_random()

        err = eval_func(p_dict)
        history.append((p_dict, err))

        if err < best_error:
            best_error = err
            best_params = p_dict

    return best_params, best_error, history


# -------------------------------------------------------------------------
# 4) Genetic Algorithm
# -------------------------------------------------------------------------

def ga_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    pop_size: int = 20,
    generations: int = 10,
    crossover_prob: float = 0.7,
    mutation_prob: float = 0.2
) -> Tuple[Dict[str, float], float, list]:
    """
    Basic GA approach. returns (best_params, best_error, history).
    history is a list of (param_dict, error).
    """

    def random_individual():
        d = {}
        for spec in param_specs:
            d[spec.name] = spec.sample_random()
        return d

    def evaluate(ind: Dict[str, float]) -> Tuple[float, float]:
        err = eval_func(ind)
        # we define fitness as 1/(1+err) to invert the problem
        fit = 1.0 / (1.0 + err)
        return fit, err

    def tournament_select(pop, k=3):
        contenders = random.sample(pop, k)
        best = max(contenders, key=lambda x: x["fitness"])
        return copy.deepcopy(best)

    def crossover(p1: Dict[str, float], p2: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
        c1 = {}
        c2 = {}
        for key in p1.keys():
            if random.random() < 0.5:
                c1[key] = p1[key]
                c2[key] = p2[key]
            else:
                c1[key] = p2[key]
                c2[key] = p1[key]
        return c1, c2

    def mutate(p: Dict[str, float]):
        for spec in param_specs:
            if random.random() < mutation_prob:
                p[spec.name] = spec.sample_random()

    # Initialize population
    population = []
    history = []
    for _ in range(pop_size):
        ind_params = random_individual()
        fit, err = evaluate(ind_params)
        population.append({"params": ind_params, "fitness": fit, "error": err})
        history.append((ind_params, err))

    # Evolve over generations
    for gen in range(generations):
        new_pop = []
        while len(new_pop) < pop_size:
            parent_a = tournament_select(population)
            parent_b = tournament_select(population)

            if random.random() < crossover_prob:
                c1, c2 = crossover(parent_a["params"], parent_b["params"])
            else:
                c1 = parent_a["params"]
                c2 = parent_b["params"]

            mutate(c1)
            mutate(c2)

            f1, e1 = evaluate(c1)
            f2, e2 = evaluate(c2)
            new_pop.append({"params": c1, "fitness": f1, "error": e1})
            new_pop.append({"params": c2, "fitness": f2, "error": e2})
            history.append((c1, e1))
            history.append((c2, e2))

        # Keep top 'pop_size'
        new_pop.sort(key=lambda x: x["fitness"], reverse=True)
        population = new_pop[:pop_size]

        best_ind = max(population, key=lambda x: x["fitness"])
        print(f"[GA gen={gen}] best error={best_ind['error']:.4f}")

    # Final best
    best_ind = max(population, key=lambda x: x["fitness"])
    return best_ind["params"], best_ind["error"], history


# -------------------------------------------------------------------------
# 5) Bayesian Optimization (scikit-optimize)
# -------------------------------------------------------------------------

def bayes_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    n_calls: int = 30
) -> Tuple[Dict[str, float], float, list]:
    """
    If scikit-optimize is not installed, fallback to random_search.
    returns (best_params, best_error, history)
    """
    if not HAVE_SKOPT or gp_minimize is None:
        print("[WARN] scikit-optimize not installed, fallback to random.")
        bp, be, hist = random_search_calibration(param_specs, eval_func, n_iterations=n_calls)
        return bp, be, hist

    # Build dimension space
    skopt_dims = []
    param_names = []
    for spec in param_specs:
        param_names.append(spec.name)
        if spec.is_integer:
            skopt_dims.append(Integer(spec.min_value, spec.max_value, name=spec.name))
        else:
            skopt_dims.append(Real(spec.min_value, spec.max_value, name=spec.name))

    @use_named_args(skopt_dims)
    def objective(**kwargs):
        return eval_func(kwargs)

    res = gp_minimize(
        func=objective,
        dimensions=skopt_dims,
        n_calls=n_calls,
        n_initial_points=5,
        random_state=42
    )

    best_error = res.fun
    best_x = res.x
    best_params = {}
    for i, val in enumerate(best_x):
        best_params[param_names[i]] = val

    # Build history
    history = []
    for i, xlist in enumerate(res.x_iters):
        param_dict = {}
        for j, val in enumerate(xlist):
            param_dict[param_names[j]] = val
        err = res.func_vals[i]
        history.append((param_dict, err))

    return best_params, best_error, history


# -------------------------------------------------------------------------
# 6) CalibrationManager
# -------------------------------------------------------------------------

class CalibrationManager:
    """
    Provides a single interface for random, ga, or bayes calibration.
    """

    def __init__(self, param_specs: List[ParamSpec], eval_func: Callable[[Dict[str, float]], float]):
        self.param_specs = param_specs
        self.eval_func = eval_func

    def run_calibration(
        self,
        method: str = "random",
        **kwargs
    ) -> Tuple[Dict[str, float], float, list]:
        """
        method can be: "random", "ga", or "bayes".
        returns (best_params, best_error, history).
        """
        if method == "random":
            n_iter = kwargs.get("n_iterations", 50)
            return random_search_calibration(self.param_specs, self.eval_func, n_iter)

        elif method == "ga":
            pop_size = kwargs.get("pop_size", 20)
            generations = kwargs.get("generations", 10)
            crossover_prob = kwargs.get("crossover_prob", 0.7)
            mutation_prob = kwargs.get("mutation_prob", 0.2)
            return ga_calibration(
                self.param_specs,
                self.eval_func,
                pop_size=pop_size,
                generations=generations,
                crossover_prob=crossover_prob,
                mutation_prob=mutation_prob
            )

        elif method == "bayes":
            n_calls = kwargs.get("n_calls", 30)
            return bayes_calibration(self.param_specs, self.eval_func, n_calls)
        else:
            raise ValueError(f"Unknown method: {method}")


# -------------------------------------------------------------------------
# 7) Utility to Save History to CSV
# -------------------------------------------------------------------------

def save_history_to_csv(history: list, filename: str):
    """
    history is a list of (param_dict, error).
    Write to CSV => columns: param1, param2, ..., error
    """
    if not history:
        print(f"[WARN] No history to save in {filename}.")
        return

    rows = []
    all_params = set()
    for (pdict, err) in history:
        rows.append((pdict, err))
        all_params.update(list(pdict.keys()))

    all_params = sorted(list(all_params))
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        header = list(all_params) + ["error"]
        writer.writerow(header)

        for (pdict, err) in rows:
            rowdata = []
            for p in all_params:
                val = pdict.get(p, "")
                rowdata.append(val)
            rowdata.append(err)
            writer.writerow(rowdata)

    print(f"[INFO] Saved calibration history to {filename}")
