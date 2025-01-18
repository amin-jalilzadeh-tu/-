"""
sensitivity_analysis.py

Demonstrates how to perform global sensitivity analysis (Sobol, Morris)
using SALib. We'll assume we have a 'model_function' that accepts
a set of parameter values and returns a single scalar output.
"""

import numpy as np
import pandas as pd

from SALib.sample import saltelli, morris
from SALib.analyze import sobol, morris as morris_analyze
from typing import Callable, Dict, Any

###############################################################################
# 1) Define the Parameter Ranges for SALib
###############################################################################
def build_problem_dict(params_meta: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert a DataFrame describing parameter ranges into
    a SALib 'problem' dictionary.
    
    Expected columns in params_meta:
      - name: str (unique param name)
      - min_value: float
      - max_value: float

    Returns a dictionary:
      {
        'num_vars': int,
        'names': [list of param names],
        'bounds': [[min, max], [min, max], ...]
      }
    """
    problem = {
        'num_vars': len(params_meta),
        'names': params_meta['name'].tolist(),
        'bounds': []
    }

    for _, row in params_meta.iterrows():
        problem['bounds'].append([row['min_value'], row['max_value']])

    return problem


###############################################################################
# 2) The Model or "Simulation" Function
###############################################################################
def model_function(param_values: np.ndarray,
                   problem_dict: Dict[str, Any],
                   simulate_func: Callable[[Dict[str, float]], float]
                  ) -> np.ndarray:
    """
    Evaluate a user-provided 'simulate_func' for each row in param_values.
    
    :param param_values: 2D array of size (N, D) 
                        where N is number of samples,
                        D is number of parameters.
    :param problem_dict: SALib problem dict with param names
    :param simulate_func: function that takes a dict of {param_name: value} 
                         and returns a scalar output (float).
    :return: np.ndarray of shape (N,) with the output for each row.
    """
    results = []
    param_names = problem_dict['names']

    for row in param_values:
        # Build param_set dict: { "param_name": value, ...}
        param_set = {}
        for i, p_name in enumerate(param_names):
            param_set[p_name] = row[i]

        # Evaluate your function/simulation
        out_value = simulate_func(param_set)
        results.append(out_value)

    return np.array(results)


###############################################################################
# 3) Morris Sensitivity
###############################################################################
def run_morris_sensitivity(params_meta: pd.DataFrame,
                           simulate_func: Callable[[Dict[str, float]], float],
                           n_trajectories: int = 10,
                           num_levels: int = 4
                          ):
    """
    Perform a Morris (Elementary Effects) sensitivity analysis.
    
    :param params_meta: DataFrame describing parameter ranges 
                       (with columns 'name', 'min_value', 'max_value').
    :param simulate_func: user-defined function that returns a scalar 
                          for each param set.
    :param n_trajectories: number of trajectories for the Morris method.
    :param num_levels: number of grid levels (typical choices are 4, 6, or 10).
    :return: (morris_indices, sample_values, Y) 
             where 'morris_indices' is the result of SALib's Morris analyzer,
             'sample_values' is the input array,
             'Y' is the output array.
    """
    problem_dict = build_problem_dict(params_meta)

    # 1) Generate Morris samples
    sample_values = morris.sample(problem_dict,
                                  N=n_trajectories,
                                  num_levels=num_levels,
                                  optimal_trajectories=None,  # optional
                                  local_optimization=False)

    # 2) Evaluate model
    Y = model_function(sample_values, problem_dict, simulate_func)

    # 3) Analyze
    morris_result = morris_analyze.analyze(problem_dict,
                                           sample_values,
                                           Y,
                                           conf_level=0.95,
                                           print_to_console=False)

    # The Morris result typically contains 'mu', 'mu_star', 'sigma', 'mu_star_conf'
    # Example: morris_result['mu_star'][i] -> measure of overall sensitivity for param i

    return morris_result, sample_values, Y


###############################################################################
# 4) Sobol Sensitivity
###############################################################################
def run_sobol_sensitivity(params_meta: pd.DataFrame,
                          simulate_func: Callable[[Dict[str, float]], float],
                          n_samples: int = 1000):
    """
    Perform a Sobol sensitivity analysis using Saltelli's sampler.
    
    :param params_meta: DataFrame describing parameter ranges
                       (with columns 'name', 'min_value', 'max_value').
    :param simulate_func: user-defined function that returns a scalar.
    :param n_samples: Base sample size for Saltelli. The total number 
                      of function evaluations is (2D+2)*n_samples
                      (where D is the number of parameters).
    :return: (sobol_indices, sample_values, Y) 
             sobol_indices -> result of SALib's sobol.analyze
             sample_values -> the matrix of inputs
             Y -> model outputs
    """
    problem_dict = build_problem_dict(params_meta)

    # 1) Generate Sobol samples via Saltelli
    sample_values = saltelli.sample(problem_dict, 
                                    n_samples, 
                                    calc_second_order=True)

    # 2) Evaluate model
    Y = model_function(sample_values, problem_dict, simulate_func)

    # 3) Sobol analysis
    sobol_result = sobol.analyze(problem_dict, 
                                 Y, 
                                 calc_second_order=True,
                                 print_to_console=False)

    # The sobol_result will have keys for "S1", "S1_conf", "S2", "S2_conf", "ST", "ST_conf"
    return sobol_result, sample_values, Y


###############################################################################
# 5) Example / Testing
###############################################################################
if __name__ == "__main__":
    # EXAMPLE: Suppose we have 3 parameters: infiltration, occupant_density, wall_u
    # Create a small DataFrame describing them:
    data = {
        "name": ["infiltration_base", "occupant_density", "wall_u_value"],
        "min_value": [0.5, 10, 0.3],
        "max_value": [2.0, 40, 1.2]
    }
    df_params = pd.DataFrame(data)

    # Example: define a simple simulation function that returns "energy use" 
    # as a made-up formula
    def mock_sim_func(param_set: Dict[str, float]) -> float:
        """
        A contrived function that 'simulates' energy usage.
        For illustration: E = infiltration * occupant_density^0.5 * 1/wall_u
        """
        infiltration = param_set["infiltration_base"]
        density = param_set["occupant_density"]
        wall_u = param_set["wall_u_value"]
        energy = infiltration * (density ** 0.5) * (1.0 / wall_u)
        return energy

    print("==== Running Morris Sensitivity ====")
    morris_res, X_morris, Y_morris = run_morris_sensitivity(df_params, mock_sim_func,
                                                            n_trajectories=10, 
                                                            num_levels=4)
    print("[Morris] mu_star:", morris_res["mu_star"])
    print("[Morris] param order:", df_params["name"].tolist())

    print("\n==== Running Sobol Sensitivity ====")
    sobol_res, X_sobol, Y_sobol = run_sobol_sensitivity(df_params, mock_sim_func, 
                                                       n_samples=256)
    print("[Sobol] S1:", sobol_res["S1"])
    print("[Sobol] ST:", sobol_res["ST"])
    print("[Sobol] param order:", df_params["name"].tolist())
