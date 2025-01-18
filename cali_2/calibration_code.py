import random
import copy
import csv
import pandas as pd
from typing import List, Dict, Tuple

# For Bayesian Optimization
from skopt import gp_minimize
from skopt.space import Real, Integer
from skopt.utils import use_named_args


# -------------------------------------------------------------------------
# 1) DEFINE PARAM SPACE AND SIMULATION/ERROR FUNCTION
# -------------------------------------------------------------------------

def simulate_or_surrogate(params: Dict[str, float]) -> float:
    """
    Placeholder function:
      1) Takes a param dictionary, e.g. {'infiltration': 0.9, 'occupant_density': 30, ...}
      2) Runs either a direct E+ simulation OR calls your surrogate
      3) Compares results to real data (MBE, CV(RMSE), or custom objective)
      4) Returns a scalar error (lower is better)

    TODO: Implement your actual logic here.
    """
    # For demonstration, produce a random error:
    return random.uniform(0, 100)


# Example param space
PARAM_SPACE = [
    {"name": "infiltration_base", "type": "float", "low": 0.5, "high": 1.3},
    {"name": "occupant_density",  "type": "float", "low": 20.0, "high": 40.0},
    {"name": "heating_setpoint",  "type": "float", "low": 19.0, "high": 24.0},
]


# -------------------------------------------------------------------------
# 2) RANDOM SEARCH
# -------------------------------------------------------------------------

def random_search_calibration(
    param_space: List[Dict],
    n_iterations: int = 50,
) -> Tuple[Dict[str, float], float, list]:
    """
    1) Randomly sample N sets of parameters from the param_space
    2) Evaluate error for each
    3) Return best param set, best error, and a history list

    :param param_space: list of dicts describing each param's name, type, low/high
    :param n_iterations: how many random draws
    :return: (best_params, best_error, history)
             history is a list of (param_dict, error)
    """
    best_params = None
    best_error = float("inf")
    history = []

    for i in range(n_iterations):
        # sample a random param set
        candidate = {}
        for pspec in param_space:
            if pspec["type"] == "float":
                val = random.uniform(pspec["low"], pspec["high"])
            elif pspec["type"] == "int":
                val = random.randint(pspec["low"], pspec["high"])
            else:
                # Handle categories or fallback
                val = pspec["low"]  
            candidate[pspec["name"]] = val

        # simulate
        error = simulate_or_surrogate(candidate)
        history.append((candidate, error))

        if error < best_error:
            best_error = error
            best_params = candidate

    return best_params, best_error, history


# -------------------------------------------------------------------------
# 3) GENETIC ALGORITHM (GA)
# -------------------------------------------------------------------------

def ga_calibration(
    param_space: List[Dict],
    pop_size: int = 20,
    generations: int = 10,
    crossover_prob: float = 0.7,
    mutation_prob: float = 0.2,
) -> Tuple[Dict[str, float], float, list]:
    """
    Basic GA:
     - Initialize population of random solutions
     - Evaluate fitness (1/error)
     - Selection (tournament)
     - Crossover
     - Mutation
     - Return best solution
    Also keep a history of tested individuals across generations.

    :return: (best_params, best_error, history)
             where history is list of (param_dict, error)
    """

    def random_individual():
        ind = {}
        for pspec in param_space:
            if pspec["type"] == "float":
                val = random.uniform(pspec["low"], pspec["high"])
            elif pspec["type"] == "int":
                val = random.randint(pspec["low"], pspec["high"])
            else:
                val = pspec["low"]
            ind[pspec["name"]] = val
        return ind

    def evaluate(ind):
        err = simulate_or_surrogate(ind)
        return 1.0 / (1.0 + err), err  # (fitness, error)

    def tournament_select(pop, k=3):
        # pick k random
        contenders = random.sample(pop, k)
        # highest fitness
        best = max(contenders, key=lambda x: x["fitness"])
        return copy.deepcopy(best)

    def crossover(parent1, parent2):
        child1 = {}
        child2 = {}
        for key in parent1["params"].keys():
            if random.random() < 0.5:
                child1[key] = parent1["params"][key]
                child2[key] = parent2["params"][key]
            else:
                child1[key] = parent2["params"][key]
                child2[key] = parent1["params"][key]
        return child1, child2

    def mutate(ind_params):
        for pspec in param_space:
            if random.random() < mutation_prob:
                if pspec["type"] == "float":
                    ind_params[pspec["name"]] = random.uniform(pspec["low"], pspec["high"])
                elif pspec["type"] == "int":
                    ind_params[pspec["name"]] = random.randint(pspec["low"], pspec["high"])

    # INITIAL POP
    population = []
    history = []
    for _ in range(pop_size):
        params = random_individual()
        fit, err = evaluate(params)
        population.append({"params": params, "fitness": fit, "error": err})
        history.append((params, err))

    # EVOLVE
    for gen in range(generations):
        new_pop = []
        while len(new_pop) < pop_size:
            parent_a = tournament_select(population)
            parent_b = tournament_select(population)
            if random.random() < crossover_prob:
                c1, c2 = crossover(parent_a, parent_b)
            else:
                c1 = parent_a["params"]
                c2 = parent_b["params"]
            mutate(c1)
            mutate(c2)
            f1, e1 = evaluate(c1)
            f2, e2 = evaluate(c2)
            new_pop.append({"params": c1, "fitness": f1, "error": e1})
            new_pop.append({"params": c2, "fitness": f2, "error": e2})
            # record to history
            history.append((c1, e1))
            history.append((c2, e2))

        # keep best pop_size
        new_pop.sort(key=lambda x: x["fitness"], reverse=True)
        population = new_pop[:pop_size]

        best_ind = max(population, key=lambda x: x["fitness"])
        print(f"GA gen={gen}, best error={best_ind['error']:.3f}")

    best_ind = max(population, key=lambda x: x["fitness"])
    return best_ind["params"], best_ind["error"], history


# -------------------------------------------------------------------------
# 4) BAYESIAN OPTIMIZATION
# -------------------------------------------------------------------------

def bayes_calibration(
    param_space: List[Dict],
    n_calls: int = 30,
) -> Tuple[Dict[str, float], float, list]:
    """
    Bayesian Optimization with gp_minimize. 
    We'll keep track of 'history' by hooking into res.x_iters and res.func_vals.

    :return: (best_params, best_error, history)
    """
    # Convert param_space -> skopt
    skopt_dims = []
    param_names = []
    for pspec in param_space:
        param_names.append(pspec["name"])
        if pspec["type"] == "float":
            skopt_dims.append(Real(pspec["low"], pspec["high"], name=pspec["name"]))
        elif pspec["type"] == "int":
            skopt_dims.append(Integer(pspec["low"], pspec["high"], name=pspec["name"]))
        else:
            # handle categories or fallback
            skopt_dims.append(Real(pspec["low"], pspec["high"], name=pspec["name"]))

    @use_named_args(skopt_dims)
    def objective(**kwargs):
        err = simulate_or_surrogate(kwargs)
        return err

    res = gp_minimize(
        func=objective,
        dimensions=skopt_dims,
        n_calls=n_calls,
        n_initial_points=5,
        random_state=0
    )

    best_error = res.fun
    best_x = res.x

    # convert best_x -> dict
    best_params = {}
    for i, val in enumerate(best_x):
        best_params[param_names[i]] = val

    # Build a 'history' from x_iters + func_vals
    history = []
    for i, xlist in enumerate(res.x_iters):
        param_dict = {}
        for j, val in enumerate(xlist):
            param_dict[param_names[j]] = val
        err = res.func_vals[i]
        history.append((param_dict, err))

    return best_params, best_error, history


# -------------------------------------------------------------------------
# 5) CALIBRATION MANAGER
# -------------------------------------------------------------------------

class CalibrationManager:
    """
    A manager to unify the interface. 
    usage:

        manager = CalibrationManager(param_space=PARAM_SPACE)
        best_params, best_err, history = manager.run_calibration(method="random")
    """
    def __init__(self, param_space: List[Dict]):
        self.param_space = param_space

    def run_calibration(
        self,
        method: str = "random",
        **kwargs
    ) -> Tuple[Dict[str, float], float, list]:
        """
        method can be: "random", "ga", or "bayes"
        returns (best_params, best_error, history)
        """
        if method == "random":
            n_iter = kwargs.get("n_iterations", 50)
            bp, be, hist = random_search_calibration(self.param_space, n_iter)
            return bp, be, hist

        elif method == "ga":
            pop_size = kwargs.get("pop_size", 20)
            generations = kwargs.get("generations", 10)
            crossover_prob = kwargs.get("crossover_prob", 0.7)
            mutation_prob = kwargs.get("mutation_prob", 0.2)
            bp, be, hist = ga_calibration(
                self.param_space,
                pop_size=pop_size,
                generations=generations,
                crossover_prob=crossover_prob,
                mutation_prob=mutation_prob,
            )
            return bp, be, hist

        elif method == "bayes":
            n_calls = kwargs.get("n_calls", 30)
            bp, be, hist = bayes_calibration(self.param_space, n_calls)
            return bp, be, hist

        else:
            raise ValueError(f"Unknown method: {method}")


# -------------------------------------------------------------------------
# 6) CSV LOGGING UTILITY
# -------------------------------------------------------------------------

def save_history_to_csv(history: list, filename: str):
    """
    Save a calibration history to CSV.
    `history` is a list of (param_dict, error).
    We'll create columns for each param + 'error'.
    """
    if not history:
        print(f"[WARN] No history to save for {filename}.")
        return

    # Build a list of dicts
    rows = []
    for (pdict, err) in history:
        row = dict(**pdict)
        row["error"] = err
        rows.append(row)

    # Convert to DataFrame for easy CSV
    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)
    print(f"[INFO] Saved calibration history to {filename}")
