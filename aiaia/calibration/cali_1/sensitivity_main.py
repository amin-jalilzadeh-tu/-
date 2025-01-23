import os
import numpy as np
import pandas as pd
from typing import Dict, Any

# SALib imports
from SALib.sample import saltelli, morris
from SALib.analyze import sobol, morris as morris_analyze

##############################################################################
# 1) Read and Merge Scenario Parameter CSVs
##############################################################################

def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Reads scenario CSV files (dhw, elec, fenez, hvac, vent, etc.)
    from the specified folder, merges them into one DataFrame
    with columns: [scenario_index, ogc_fid, param_name, assigned_value].
    
    Returns the merged DataFrame.
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
            df = pd.read_csv(fpath)
            df["source_file"] = fname  # keep track of which file or system
            dfs.append(df)
        else:
            print(f"[WARNING] File not found: {fpath}")

    if not dfs:
        raise FileNotFoundError("No scenario parameter CSVs found in the folder.")

    merged_df = pd.concat(dfs, ignore_index=True)
    return merged_df


##############################################################################
# 2) Extract Param Ranges (Enforce param_min < param_max)
##############################################################################


def extract_parameter_ranges(merged_df: pd.DataFrame,
                             param_min_col: str = "param_min",
                             param_max_col: str = "param_max") -> pd.DataFrame:
    """
    Creates a DataFrame with columns ['name', 'min_value', 'max_value'].
    If param_min/param_max do not exist (or are NaN / invalid),
    fallback logic uses assigned_value with +/- 20% or a small epsilon
    to ensure min < max.

    Handles the case where assigned_value is non-numeric (e.g. "AlwaysOnSched"):
      - Either skip that param_name entirely
      - Or assign a dummy numeric range [0, 1]
    """

    # Helper function to attempt float conversion
    def safe_float(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    # Check if user-defined columns exist in the DataFrame
    has_param_min = (param_min_col in merged_df.columns)
    has_param_max = (param_max_col in merged_df.columns)

    # If param_min/param_max do NOT exist, fallback to assigned_value
    if not has_param_min or not has_param_max:
        print("[INFO] param_min/param_max columns not found. Using fallback approach...")

        param_names = merged_df["param_name"].unique()
        rows = []
        for p in param_names:
            subset = merged_df[merged_df["param_name"] == p]
            if subset.empty:
                continue

            val_raw = subset.iloc[0].get("assigned_value", 0)
            val_num = safe_float(val_raw)
            if val_num is None:
                # ============== Approach A: skip non-numeric ==============
                print(f"[INFO] Skipping non-numeric param '{p}' with assigned_value='{val_raw}'")
                continue

                # ============== Approach B: dummy range for non-numeric ==============
                # print(f"[INFO] Non-numeric param '{p}' => using dummy range [0,1].")
                # rows.append({"name": p, "min_value": 0.0, "max_value": 1.0})
                # continue

            base_val = val_num
            minv = base_val * 0.8
            maxv = base_val * 1.2
            if minv >= maxv:
                maxv = minv + 1e-4  # enforce strictly less

            rows.append({"name": p, "min_value": minv, "max_value": maxv})

        return pd.DataFrame(rows)

    # If param_min/param_max DO exist, group them by param_name
    grouped = merged_df.groupby("param_name")[[param_min_col, param_max_col]].first().reset_index()
    grouped.rename(columns={
        "param_name": "name",
        param_min_col: "min_value",
        param_max_col: "max_value"
    }, inplace=True)

    out_rows = []
    for _, row in grouped.iterrows():
        name = row["name"]
        minv = row["min_value"]
        maxv = row["max_value"]

        # Check validity
        if pd.isna(minv) or pd.isna(maxv) or (minv >= maxv):
            # fallback
            sample = merged_df.loc[merged_df["param_name"] == name, "assigned_value"]
            if not sample.empty and not pd.isna(sample.iloc[0]):
                val_raw = sample.iloc[0]
                val_num = safe_float(val_raw)
                if val_num is not None:
                    # numeric => fallback ±20%
                    minv = val_num * 0.8
                    maxv = val_num * 1.2
                    if minv >= maxv:
                        maxv = minv + 1e-4
                else:
                    # Non-numeric => skip or dummy
                    print(f"[INFO] Non-numeric param '{name}' => using dummy [0,1].")
                    minv, maxv = 0.0, 1.0
            else:
                # If we can't fix it, default to [0,1]
                minv, maxv = 0.0, 1.0

        out_rows.append({"name": name, "min_value": minv, "max_value": maxv})

    return pd.DataFrame(out_rows)


##############################################################################
# 3) Build SALib 'problem' dict
##############################################################################

def build_problem_dict(params_meta: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert a DataFrame [name, min_value, max_value] into SALib 'problem' dict.
    """
    problem = {
        'num_vars': len(params_meta),
        'names': params_meta['name'].tolist(),
        'bounds': []
    }
    for _, row in params_meta.iterrows():
        problem['bounds'].append([row['min_value'], row['max_value']])

    return problem


##############################################################################
# 4) Mock or Real Simulation
##############################################################################

def eplus_simulation_func(param_set: Dict[str, float]) -> float:
    """
    Replace this mock with your real E+ run or scenario-based IDF generation.
    param_set: { 'infiltration_base': 1.2, 'occupant_density': 25, ... }

    For demonstration, we do:
      energy = infiltration_base * occupant_density * (1/wall_u_value)
    """
    infiltration = param_set.get("infiltration_base", 1.0)
    occupant_density = param_set.get("occupant_density_m2_per_person", 30.0)
    wall_u = param_set.get("exterior_wall_U_value", 0.5)

    # If wall_u = 0 => avoid div by zero
    energy = infiltration * occupant_density * (1.0 / max(0.001, wall_u))
    return energy


def model_function(sample_values: np.ndarray,
                   problem_dict: Dict[str, Any],
                   simulate_func) -> np.ndarray:
    """
    Evaluate simulate_func for each row in sample_values.
    
    sample_values: 2D array of shape (N, D)
    problem_dict: SALib problem dict
    simulate_func: user-defined function returning a float (energy usage, etc.)
    """
    results = []
    param_names = problem_dict['names']

    for row in sample_values:
        param_set = {}
        for i, p_name in enumerate(param_names):
            param_set[p_name] = row[i]

        out_val = simulate_func(param_set)
        results.append(out_val)

    return np.array(results)


##############################################################################
# 5) Morris & Sobol routines
##############################################################################

def run_morris_sensitivity(params_meta: pd.DataFrame,
                           simulate_func,
                           n_trajectories: int = 10,
                           num_levels: int = 4):
    """
    Perform a Morris (Elementary Effects) sensitivity analysis using SALib.

    returns: (morris_result, sample_values, Y)
    """
    problem_dict = build_problem_dict(params_meta)

    # Generate Morris samples
    sample_values = morris.sample(
        problem_dict,
        N=n_trajectories,
        num_levels=num_levels,
        optimal_trajectories=None,
        local_optimization=False
    )

    # Evaluate model
    Y = model_function(sample_values, problem_dict, simulate_func)

    # Morris analysis
    morris_result = morris_analyze.analyze(
        problem_dict,
        sample_values,
        Y,
        conf_level=0.95,
        print_to_console=False
    )

    return morris_result, sample_values, Y


def run_sobol_sensitivity(params_meta: pd.DataFrame,
                          simulate_func,
                          n_samples: int = 256):
    """
    Perform a Sobol (global) sensitivity analysis with SALib's Saltelli sampler.

    returns: (sobol_result, sample_values, Y)
    """
    problem_dict = build_problem_dict(params_meta)

    # Generate Sobol samples
    sample_values = saltelli.sample(problem_dict,
                                    n_samples,
                                    calc_second_order=True)

    # Evaluate model
    Y = model_function(sample_values, problem_dict, simulate_func)

    # Sobol analysis
    sobol_result = sobol.analyze(
        problem_dict,
        Y,
        calc_second_order=True,
        print_to_console=False
    )

    return sobol_result, sample_values, Y


##############################################################################
# 6) Main Orchestrator for Sensitivity
##############################################################################

def run_sensitivity_analysis(
    scenario_folder: str,
    method: str = "morris",
    output_csv: str = "sensitivity_results.csv"
):
    """
    Orchestrates the entire sensitivity process:
      1) Load scenario params from CSVs
      2) Extract valid param ranges
      3) Run Morris or Sobol
      4) Print & save results to CSV
    """
    print(f"=== Running Sensitivity Analysis with method={method} ===")

    # 1) Read scenario CSVs
    merged_df = load_scenario_params(scenario_folder)

    # 2) Extract param ranges with fallback
    params_meta = extract_parameter_ranges(merged_df)

    # 3) Decide method
    if method.lower() == "morris":
        morris_res, X, Y = run_morris_sensitivity(params_meta, eplus_simulation_func)
        # Morris has keys: 'mu', 'mu_star', 'sigma', 'mu_star_conf'
        print("[Morris] mu_star =>", morris_res["mu_star"])
        print("[Morris] sigma   =>", morris_res["sigma"])
        param_list = params_meta["name"].tolist()
        print("Parameters:", param_list)

        # Save to CSV
        df_out = pd.DataFrame({
            "param": param_list,
            "mu_star": morris_res["mu_star"],
            "mu_star_conf": morris_res["mu_star_conf"],
            "sigma": morris_res["sigma"]
        })
        df_out.to_csv(output_csv, index=False)
        print(f"[INFO] Morris results saved => {output_csv}")

    elif method.lower() == "sobol":
        sobol_res, X, Y = run_sobol_sensitivity(params_meta, eplus_simulation_func)
        s1 = sobol_res["S1"]
        st = sobol_res["ST"]
        s2 = sobol_res["S2"]
        param_list = params_meta["name"].tolist()

        print("[Sobol] S1 =>", s1)
        print("[Sobol] ST =>", st)
        print("[Sobol] S2 =>", s2)
        print("Parameters:", param_list)

        # Save to CSV
        df_out = pd.DataFrame({
            "param": param_list,
            "S1": s1,
            "ST": st
        })
        # s2 is a matrix, you can flatten it or omit it
        df_out.to_csv(output_csv, index=False)
        print(f"[INFO] Sobol results saved => {output_csv}")

    else:
        raise ValueError(f"Unknown method={method}, must be 'morris' or 'sobol'")

    print("=== Sensitivity Analysis Complete ===")


##############################################################################
# 7) Example Usage (If run directly)
##############################################################################

if __name__ == "__main__":
    # Provide the path to your scenario CSVs folder
    scenario_path = r"D:\Documents\E_Plus_2030_py\output\scenarios"

    # Example 1: Morris analysis
    run_sensitivity_analysis(
        scenario_folder=scenario_path,
        method="morris",
        output_csv="morris_sensitivity_results.csv"
    )

    # Example 2: Sobol analysis (uncomment to run)
    run_sensitivity_analysis(
         scenario_folder=scenario_path,
         method="sobol",
         output_csv="sobol_sensitivity_results.csv"
    )
