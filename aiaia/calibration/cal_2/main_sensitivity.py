#!/usr/bin/env python3
# main_sensitivity.py

"""
Example script to demonstrate sensitivity analysis using SALib,
integrating scenario-based parameters and simulation/real data.

Requirements:
    pip install SALib
    pip install pandas
    pip install numpy

Data folder references:
    D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_*.csv
    D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv
    D:\Documents\E_Plus_2030_py\output\results\mock_merged_daily_mean.csv

Workflow:
  1) Load & merge scenario parameter CSVs
  2) Pivot to get columns for each param
  3) Build a SALib problem (skip or expand zero-variance params)
  4) Load sim & real data
  5) Run Morris or Sobol from SALib
  6) Print sensitivity indices
"""

import os
import numpy as np
import pandas as pd

# SALib (for Morris / Sobol)
from SALib.sample import saltelli, morris
from SALib.analyze import sobol, morris as morris_analyze


###############################################################################
# 1) LOAD & MERGE SCENARIO PARAMETERS
###############################################################################

def load_scenario_parameter_csvs(scenario_dir: str) -> pd.DataFrame:
    """
    Reads multiple scenario_params_*.csv files (dhw, elec, fenez, hvac, vent)
    from 'scenario_dir' and merges them into one DataFrame.

    Expects columns: [scenario_index, ogc_fid, param_name, assigned_value].
    Returns a single DataFrame with those columns merged from all files.
    """
    dfs = []
    for fname in os.listdir(scenario_dir):
        if fname.startswith("scenario_params_") and fname.endswith(".csv"):
            fpath = os.path.join(scenario_dir, fname)
            df_temp = pd.read_csv(fpath)
            # Quick check for columns
            required_cols = {"scenario_index", "ogc_fid", "param_name", "assigned_value"}
            missing = required_cols - set(df_temp.columns)
            if missing:
                raise ValueError(f"File '{fname}' is missing columns: {missing}")
            dfs.append(df_temp)

    if not dfs:
        raise FileNotFoundError(f"No scenario_params_*.csv files found in {scenario_dir}.")

    df_merged = pd.concat(dfs, ignore_index=True)
    return df_merged


def pivot_scenario_params(df_params: pd.DataFrame) -> pd.DataFrame:
    """
    Convert from long format (one row per param) into wide format,
    so each (scenario_index, ogc_fid) becomes a single row,
    with columns for each param_name and values = assigned_value.

    :return: pivoted DataFrame with columns:
             ['scenario_index', 'ogc_fid', 'param1', 'param2', ...]
    """
    df_pivot = df_params.pivot_table(
        index=["scenario_index", "ogc_fid"],
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()

    df_pivot.columns.name = None  # remove pivot naming
    return df_pivot

###############################################################################
# 2) LOAD SIMULATION & REAL DATA
###############################################################################

def load_sim_results(sim_csv: str) -> pd.DataFrame:
    """
    Example: load 'merged_daily_mean_mocked.csv'
    which has columns like:
      BuildingID | VariableName | 01-Jan | 02-Jan | 03-Jan | ...
    """
    return pd.read_csv(sim_csv)

def load_real_data(real_csv: str) -> pd.DataFrame:
    """
    Example: load 'mock_merged_daily_mean.csv'
    which has columns like:
      BuildingID | VariableName | 01-Jan | 02-Jan | 03-Jan | ...
    """
    return pd.read_csv(real_csv)

###############################################################################
# 3) SALib 'PROBLEM' & ZERO-VARIANCE HANDLING
###############################################################################

def build_salib_problem_from_pivoted(
    df_pivot: pd.DataFrame,
    exclude_cols: list = None
) -> dict:
    """
    Build a SALib 'problem' from the pivoted scenario DataFrame.
    We'll skip columns in exclude_cols and skip any parameter that is
    non-numeric or has zero variance (min == max).

    If min==max but not zero, we forcibly expand by ±5% for demonstration.
    If it's exactly 0.0 for all scenarios, we skip it or forcibly expand ±0.001.

    :param df_pivot: pivoted DataFrame with shape (n_scenarios, many_params)
    :param exclude_cols: e.g. ["scenario_index", "ogc_fid"]
    :return: SALib problem dict with keys: num_vars, names, bounds
    """
    if exclude_cols is None:
        exclude_cols = ["scenario_index", "ogc_fid"]

    param_cols = []
    bounds = []

    for col in df_pivot.columns:
        if col in exclude_cols:
            continue

        # Convert to numeric if possible, drop NaNs
        col_data = pd.to_numeric(df_pivot[col], errors="coerce").dropna()
        if col_data.empty:
            # No valid numeric data => skip
            print(f"[DEBUG] Skipping '{col}' - no numeric data.")
            continue

        col_min = col_data.min()
        col_max = col_data.max()

        # If exactly the same value
        if col_min == col_max:
            # Option: skip entirely
            # print(f"[INFO] Param '{col}' is constant at {col_min}. Skipping it.")
            # continue

            # Or forcibly expand
            if col_min == 0.0:
                col_min = -0.001
                col_max = 0.001
                print(f"[WARNING] Param '{col}' is 0.0 everywhere; forcing range ±0.001.")
            else:
                col_min *= 0.95
                col_max *= 1.05
                print(f"[WARNING] Param '{col}' was constant at {col_data.iloc[0]:.4f}; expanded ±5% to [{col_min:.4f}, {col_max:.4f}].")

        # Double-check legal range
        if col_min >= col_max:
            print(f"[WARNING] Param '{col}' has invalid range [{col_min}, {col_max}] -> skipping.")
            continue

        param_cols.append(col)
        bounds.append([float(col_min), float(col_max)])

    problem = {
        "num_vars": len(param_cols),
        "names": param_cols,
        "bounds": bounds
    }

    # Debug: Print them
    print("\n[SALib PROBLEM BOUNDS]")
    for pname, (low, high) in zip(problem["names"], problem["bounds"]):
        print(f"  {pname}: {low} -> {high}")

    return problem

###############################################################################
# 4) THE MISMATCH / MODEL FUNCTION
###############################################################################
def simulate_scenario_mismatch(param_dict: dict,
                               df_sim: pd.DataFrame,
                               df_real: pd.DataFrame) -> float:
    bldg_id = 0
    varname = "Electricity:Facility [J](Hourly)"

    # Filter to building 0 & that variable
    df_sim_sel = df_sim[
        (df_sim["BuildingID"] == bldg_id) &
        (df_sim["VariableName"] == varname)
    ]
    df_real_sel = df_real[
        (df_real["BuildingID"] == bldg_id) &
        (df_real["VariableName"] == varname)
    ]

    # If no rows, return penalty
    if df_sim_sel.empty or df_real_sel.empty:
        return 999999.0

    # Option B: Pick the first data column that isn't ID/VarName
    possible_day_cols = [c for c in df_sim_sel.columns if c not in ["BuildingID", "VariableName"]]
    if not possible_day_cols:
        return 999999.0

    day_col = possible_day_cols[0]  # e.g. "01-Jan" if it exists
    if day_col not in df_sim_sel.columns:
        return 999999.0

    sim_val = df_sim_sel[day_col].values[0]
    real_val = df_real_sel[day_col].values[0]

    diff = abs(sim_val - real_val)

    infiltration = param_dict.get("infiltration_base", 1.0)
    occupant_dens = param_dict.get("occupant_density_m2_per_person", 30.0)
    mismatch = diff * (infiltration / 1.0) * (occupant_dens / 30.0)

    return mismatch

###############################################################################
# 5) RUN SENSITIVITY (MORRIS OR SOBOL)
###############################################################################

def run_morris_sensitivity(problem: dict,
                           n_trajectories: int,
                           num_levels: int,
                           simulate_func,
                           df_sim: pd.DataFrame,
                           df_real: pd.DataFrame):
    """
    Perform Morris (Elementary Effects) with SALib on the 'problem' definition.
    :param problem: SALib problem with {num_vars, names, bounds}
    :param n_trajectories: number of Morris trajectories
    :param num_levels: e.g. 4
    :param simulate_func: function(param_dict, df_sim, df_real)->float
    :return: (morris_res, param_values, Y)
    """
    # 1) Generate samples
    param_values = morris.sample(
        problem,
        N=n_trajectories,
        num_levels=num_levels,
        optimal_trajectories=None,
        local_optimization=False
    )

    # 2) Evaluate each param set
    Y = []
    param_names = problem["names"]
    for row in param_values:
        p_dict = {param_names[i]: row[i] for i in range(len(param_names))}
        score = simulate_func(p_dict, df_sim, df_real)
        Y.append(score)
    Y = np.array(Y)

    # 3) Analyze
    morris_res = morris_analyze.analyze(
        problem,
        param_values,
        Y,
        conf_level=0.95,
        print_to_console=False
    )

    return morris_res, param_values, Y


def run_sobol_sensitivity(problem: dict,
                          n_samples: int,
                          simulate_func,
                          df_sim: pd.DataFrame,
                          df_real: pd.DataFrame):
    """
    Perform Sobol with SALib on the 'problem' definition.
    """
    param_values = saltelli.sample(
        problem,
        n_samples,
        calc_second_order=True
    )

    Y = []
    param_names = problem["names"]
    for row in param_values:
        p_dict = {param_names[i]: row[i] for i in range(len(param_names))}
        score = simulate_func(p_dict, df_sim, df_real)
        Y.append(score)
    Y = np.array(Y)

    sobol_res = sobol.analyze(
        problem,
        Y,
        calc_second_order=True,
        print_to_console=False
    )
    return sobol_res, param_values, Y

###############################################################################
# 6) MAIN
###############################################################################

def main():
    # Paths to scenario params, sim results, real data
    scenario_dir = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    sim_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"
    real_csv = r"D:\Documents\E_Plus_2030_py\output\results\mock_merged_daily_mean.csv"

    # --------------------------------------------------------------------------
    # A) Load scenario parameter data
    # --------------------------------------------------------------------------
    df_params_long = load_scenario_parameter_csvs(scenario_dir)
    print("[INFO] Loaded scenario param rows:", df_params_long.shape)

    # Pivot so each scenario_index => one row
    df_pivot = pivot_scenario_params(df_params_long)
    print("[INFO] Pivoted shape:", df_pivot.shape)
    print(df_pivot.head(5))

    # --------------------------------------------------------------------------
    # B) Build SALib problem, skipping or expanding zero-variance params
    # --------------------------------------------------------------------------
    problem = build_salib_problem_from_pivoted(df_pivot)
    print("\n[SALib Problem Created]")
    print("  num_vars:", problem["num_vars"])
    print("  names:", problem["names"])

    # --------------------------------------------------------------------------
    # C) Load simulation & real data
    # --------------------------------------------------------------------------
    df_sim = load_sim_results(sim_csv)
    df_real = load_real_data(real_csv)

    # --------------------------------------------------------------------------
    # D) Run Morris (or Sobol) Sensitivity
    # --------------------------------------------------------------------------
    n_trajectories = 10
    num_levels = 4

    print("\n=== Running Morris Sensitivity ===")
    morris_res, X_morris, Y_morris = run_morris_sensitivity(
        problem,
        n_trajectories=n_trajectories,
        num_levels=num_levels,
        simulate_func=simulate_scenario_mismatch,
        df_sim=df_sim,
        df_real=df_real
    )

    # Print Morris results
    print("[Morris] mu_star by param:")
    for i, pname in enumerate(problem["names"]):
        mu_star = morris_res["mu_star"][i]
        sigma = morris_res["sigma"][i]
        print(f"  Param: {pname:30s}  mu_star={mu_star:.4f}  sigma={sigma:.4f}")

    # ------------------
    # Optionally run Sobol if desired:
    # n_samples_sobol = 128
    # print("\n=== Running Sobol Sensitivity ===")
    # sobol_res, X_sobol, Y_sobol = run_sobol_sensitivity(
    #     problem,
    #     n_samples=n_samples_sobol,
    #     simulate_func=simulate_scenario_mismatch,
    #     df_sim=df_sim,
    #     df_real=df_real
    # )
    # for i, pname in enumerate(problem["names"]):
    #     st = sobol_res["ST"][i]
    #     print(f"[Sobol] {pname}: ST={st:.4f}")

    print("\n[INFO] Done with sensitivity analysis.")
    print("  - Inspect mu_star (or S1, ST) to see which parameters matter most.")
    print("  - Possibly refine param ranges or fix less influential params.")


if __name__ == "__main__":
    main()
