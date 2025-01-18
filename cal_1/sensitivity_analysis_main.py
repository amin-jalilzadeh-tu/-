"""
sensitivity_analysis_main.py

A full example script that:
  1) Reads scenario parameter CSV files (DHW, Elec, Fenez, HVAC, Vent).
  2) Merges them into a single DataFrame of param_name => assigned_value.
  3) Creates SALib parameter ranges for each param_name (fixing or bounding
     zero or negative values to avoid illegal bounds).
  4) Runs SALib's Morris and Sobol sensitivity analyses using the routines below.
  5) Outputs results for further analysis or calibration steps.
"""

import os
import numpy as np
import pandas as pd

# SALib imports
from SALib.sample import saltelli, morris
from SALib.analyze import sobol, morris as morris_analyze
from typing import Dict, Any


###############################################################################
# 1) SALib Helper Functions
###############################################################################
def build_problem_dict(params_meta: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert a DataFrame describing parameter ranges into
    a SALib 'problem' dictionary.

    Expected columns in params_meta:
      - name: str (unique param name)
      - min_value: float
      - max_value: float
    """
    problem = {
        'num_vars': len(params_meta),
        'names': params_meta['name'].tolist(),
        'bounds': []
    }

    for _, row in params_meta.iterrows():
        problem['bounds'].append([row['min_value'], row['max_value']])

    return problem


def model_function(
    param_values: np.ndarray,
    problem_dict: Dict[str, Any],
    simulate_func
) -> np.ndarray:
    """
    Evaluate a user-provided 'simulate_func' for each row in param_values.

    :param param_values: 2D array (N x D) of parameter samples
    :param problem_dict: SALib problem dict with param names
    :param simulate_func: function taking {param_name: value} => float
    :return: np.array of shape (N,) with the output for each row
    """
    results = []
    param_names = problem_dict['names']

    for row in param_values:
        # Build the {param_name: value} dict
        param_set = {}
        for i, p_name in enumerate(param_names):
            param_set[p_name] = row[i]

        # Evaluate user simulation or mock function
        val = simulate_func(param_set)
        results.append(val)

    return np.array(results)


def run_morris_sensitivity(
    params_meta: pd.DataFrame,
    simulate_func,
    n_trajectories: int = 10,
    num_levels: int = 4
):
    """
    Perform a Morris (Elementary Effects) sensitivity analysis using SALib.
    """
    problem_dict = build_problem_dict(params_meta)

    # 1) Generate Morris samples
    sample_values = morris.sample(
        problem_dict,
        N=n_trajectories,
        num_levels=num_levels,
        optimal_trajectories=None,
        local_optimization=False
    )

    # 2) Evaluate
    Y = model_function(sample_values, problem_dict, simulate_func)

    # 3) Analyze
    morris_result = morris_analyze.analyze(
        problem_dict,
        sample_values,
        Y,
        conf_level=0.95,
        print_to_console=False
    )
    return morris_result, sample_values, Y


def run_sobol_sensitivity(
    params_meta: pd.DataFrame,
    simulate_func,
    n_samples: int = 1000
):
    """
    Perform a Sobol (Saltelli) sensitivity analysis using SALib.
    """
    problem_dict = build_problem_dict(params_meta)

    # 1) Generate Sobol samples
    sample_values = saltelli.sample(
        problem_dict,
        n_samples,
        calc_second_order=True
    )

    # 2) Evaluate
    Y = model_function(sample_values, problem_dict, simulate_func)

    # 3) Analyze
    sobol_result = sobol.analyze(
        problem_dict,
        Y,
        calc_second_order=True,
        print_to_console=False
    )
    return sobol_result, sample_values, Y


###############################################################################
# 2) Code that reads scenario CSVs and merges them
###############################################################################
def load_scenario_params(
    dhw_csv: str,
    elec_csv: str,
    fenez_csv: str,
    hvac_csv: str,
    vent_csv: str,
    scenario_index_filter=0
) -> pd.DataFrame:
    """
    Reads multiple scenario parameter CSVs (DHW, Elec, Fenez, HVAC, Vent).
    Filters by scenario_index if desired.
    Returns a single DataFrame with columns:
      [param_name, assigned_value]
    We'll define min_value/max_value in another function.
    """
    # 1) Load each CSV
    df_dhw   = pd.read_csv(dhw_csv)
    df_elec  = pd.read_csv(elec_csv)
    df_fenez = pd.read_csv(fenez_csv)
    df_hvac  = pd.read_csv(hvac_csv)
    df_vent  = pd.read_csv(vent_csv)

    # 2) Filter by scenario_index if provided
    if scenario_index_filter is not None:
        df_dhw   = df_dhw[df_dhw["scenario_index"] == scenario_index_filter]
        df_elec  = df_elec[df_elec["scenario_index"] == scenario_index_filter]
        df_fenez = df_fenez[df_fenez["scenario_index"] == scenario_index_filter]
        df_hvac  = df_hvac[df_hvac["scenario_index"] == scenario_index_filter]
        df_vent  = df_vent[df_vent["scenario_index"] == scenario_index_filter]

    # 3) Concatenate them
    df_all = pd.concat([df_dhw, df_elec, df_fenez, df_hvac, df_vent],
                       ignore_index=True)

    # We'll keep only relevant columns: "param_name", "assigned_value"
    df_all = df_all[["param_name", "assigned_value"]]

    return df_all


def create_parameter_ranges(
    df_params: pd.DataFrame,
    default_min: float = 0.5,
    default_max: float = 2.0
) -> pd.DataFrame:
    """
    Given a DataFrame of param_name => assigned_value from scenario CSVs,
    define a 'min_value' and 'max_value' for each unique param_name.

    **Fix**: ensure min_value < max_value to avoid SALib "Bounds are not legal".
    If assigned_value <= 0, we fallback to default_min..default_max.

    Returns a DataFrame with columns:
      [name, min_value, max_value]
    """
    param_names = df_params["param_name"].unique()
    rows = []

    # Group by param_name and take mean assigned_value
    grouped = df_params.groupby("param_name")["assigned_value"].mean().reset_index()

    for _, row_grp in grouped.iterrows():
        pname = row_grp["param_name"]
        val   = row_grp["assigned_value"]

        # If val is NaN or <= 0 => fallback
        if pd.isna(val) or val <= 0:
            mn, mx = default_min, default_max
        else:
            # e.g. ±50% around 'val'
            mn = val * 0.5
            mx = val * 1.5

            # If that yields something invalid (mn >= mx), fix it
            if mn >= mx:
                # We'll bump up mx slightly
                mx = mn + abs(mn) * 0.1 + 0.001  # e.g. 10% more than mn

            # If either is negative or zero (in case val < 1):
            if mn <= 0:
                mn = 0.01
            if mx <= mn:
                mx = mn + 0.1

            # Also, as a final check, if somehow mn >= mx, do fallback
            if mn >= mx:
                mn, mx = default_min, default_max

        rows.append({"name": pname, "min_value": mn, "max_value": mx})

    df_ranges = pd.DataFrame(rows)
    return df_ranges


###############################################################################
# 3) Mock simulation function
###############################################################################
def mock_simulation_function(param_dict: Dict[str, float]) -> float:
    """
    Placeholder for your real or surrogate simulation.
    We'll create a random "energy" = sum(param_dict.values()) + noise.
    In reality, you'd:
      - Write param_dict to an IDF, run EnergyPlus, parse results => single float
      OR
      - Evaluate a surrogate model that approximates E+ results
    """
    base_sum = sum(param_dict.values())
    noise = np.random.uniform(-0.5, 0.5)
    return base_sum + noise


###############################################################################
# 4) Main logic function (so we can call it from elsewhere)
###############################################################################
def run_sensitivity_analyses(
    dhw_csv: str,
    elec_csv: str,
    fenez_csv: str,
    hvac_csv: str,
    vent_csv: str,
    scenario_index: int = 0,
    n_morris_trajectories: int = 10,
    n_sobol_samples: int = 128
):
    """
    Runs both Morris and Sobol sensitivity analyses and prints or saves results.

    :param dhw_csv: CSV path for DHW scenario parameters
    :param elec_csv: CSV path for Elec scenario parameters
    :param fenez_csv: CSV path for Fenestration scenario parameters
    :param hvac_csv: CSV path for HVAC scenario parameters
    :param vent_csv: CSV path for Vent scenario parameters
    :param scenario_index: which scenario_index to filter
    :param n_morris_trajectories: N for Morris sampling
    :param n_sobol_samples: N for Sobol sampling
    """
    # ------------------------------------------------------------------------
    # A) Load scenario params & create param ranges
    # ------------------------------------------------------------------------
    df_scen = load_scenario_params(
        dhw_csv,
        elec_csv,
        fenez_csv,
        hvac_csv,
        vent_csv,
        scenario_index_filter=scenario_index
    )
    print("[INFO] Merged scenario param count:", len(df_scen))
    print(df_scen.head(10))

    df_param_ranges = create_parameter_ranges(df_scen)
    print("\n[INFO] Parameter Ranges for Sensitivity:")
    print(df_param_ranges)

    # ------------------------------------------------------------------------
    # B) MORRIS Sensitivity
    # ------------------------------------------------------------------------
    print("\n=== Running MORRIS Sensitivity Analysis ===")
    morris_res, X_morris, Y_morris = run_morris_sensitivity(
        df_param_ranges,
        mock_simulation_function,
        n_trajectories=n_morris_trajectories,
        num_levels=4
    )

    print("[MORRIS] mu_star:", morris_res['mu_star'])
    print("[MORRIS] sigma:", morris_res['sigma'])
    print("[MORRIS] param order:", df_param_ranges["name"].tolist())

    # (Optional) Save Morris results
    df_morris = pd.DataFrame({
        "param_name": df_param_ranges["name"],
        "mu_star": morris_res["mu_star"],
        "sigma": morris_res["sigma"]
    })
    df_morris.to_csv("morris_sensitivity_results.csv", index=False)
    print("[MORRIS] Results saved to morris_sensitivity_results.csv")

    # ------------------------------------------------------------------------
    # C) SOBOL Sensitivity
    # ------------------------------------------------------------------------
    print("\n=== Running SOBOL Sensitivity Analysis ===")
    sobol_res, X_sobol, Y_sobol = run_sobol_sensitivity(
        df_param_ranges,
        mock_simulation_function,
        n_samples=n_sobol_samples
    )
    print("[SOBOL] S1:", sobol_res["S1"])
    print("[SOBOL] ST:", sobol_res["ST"])
    print("[SOBOL] param order:", df_param_ranges["name"].tolist())

    # (Optional) Save Sobol results
    df_sobol = pd.DataFrame({
        "param_name": df_param_ranges["name"],
        "S1": sobol_res["S1"],
        "ST": sobol_res["ST"]
    })
    df_sobol.to_csv("sobol_sensitivity_results.csv", index=False)
    print("[SOBOL] Results saved to sobol_sensitivity_results.csv")

    print("\n[INFO] Done with sensitivity analysis!")
