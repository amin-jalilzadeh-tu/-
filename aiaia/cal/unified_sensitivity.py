"""
unified_sensitivity.py

A single, merged Python script that unifies correlation-based
and SALib-based sensitivity analysis (Morris or Sobol) for
scenario-based parameters.

It expects:
  1) A folder with scenario CSV files like:
       scenario_params_dhw.csv
       scenario_params_elec.csv
       scenario_params_fenez.csv
       scenario_params_hvac.csv
       scenario_params_vent.csv
     each having columns: [scenario_index, ogc_fid, param_name,
                           assigned_value, param_min, param_max, ...]

  2) Possibly a results CSV (like merged_daily_mean_mocked.csv)
     if you want to do correlation-based analysis vs. "TotalEnergy_J" or similar.

  3) If param_min / param_max do not exist, it falls back to
     e.g. ±20% around assigned_value or a small default.

This script can do:
  - correlation-based sensitivity (merging scenario params with results)
  - SALib Morris
  - SALib Sobol

Author: Example
"""

import os
import re
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# SALib for Morris / Sobol
try:
    from SALib.sample import saltelli, morris
    from SALib.analyze import sobol, morris as morris_analyze
    HAVE_SALIB = True
except ImportError:
    HAVE_SALIB = False


##############################################################################
# 1) LOAD SCENARIO PARAM CSVs
##############################################################################

def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Reads scenario CSV files (dhw, elec, fenez, hvac, vent, etc.)
    from `scenario_folder`. Merges them into one DataFrame with columns:
      [scenario_index, ogc_fid, param_name, assigned_value, param_min, param_max, ...]

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
            # Track the source file (optional)
            df["source_file"] = fname
            dfs.append(df)
        else:
            print(f"[INFO] Not found: {fpath} (skip if not needed).")

    if not dfs:
        raise FileNotFoundError("No scenario parameter CSVs found in the folder.")

    merged_df = pd.concat(dfs, ignore_index=True)
    return merged_df


##############################################################################
# 2) EXTRACT PARAMETER RANGES
##############################################################################

def extract_parameter_ranges(
    merged_df: pd.DataFrame,
    param_name_col: str = "param_name",
    assigned_val_col: str = "assigned_value",
    param_min_col: str = "param_min",
    param_max_col: str = "param_max"
) -> pd.DataFrame:
    """
    Creates a DataFrame with columns: ['name', 'min_value', 'max_value'].

    If 'param_min' / 'param_max' columns exist and are valid, we use them.
    If they do not exist or are NaN / invalid, we fallback to ±20% around
    the 'assigned_value', or [0,1] as a last resort, ensuring min < max.

    If param_min >= param_max, we also fallback.

    The final DataFrame is used by SALib for Morris/Sobol.
    """
    # Check presence
    has_min = (param_min_col in merged_df.columns)
    has_max = (param_max_col in merged_df.columns)

    param_names = merged_df[param_name_col].unique()
    out_rows = []

    for p in param_names:
        sub = merged_df[merged_df[param_name_col] == p]

        # Grab first row's param_min, param_max if available
        if sub.empty:
            continue
        if has_min and not pd.isna(sub[param_min_col].iloc[0]):
            mn = sub[param_min_col].iloc[0]
        else:
            mn = np.nan
        if has_max and not pd.isna(sub[param_max_col].iloc[0]):
            mx = sub[param_max_col].iloc[0]
        else:
            mx = np.nan

        # If param_min/param_max are missing or invalid
        if pd.isna(mn) or pd.isna(mx) or (mn >= mx):
            # fallback: use assigned_value
            val = sub[assigned_val_col].iloc[0]
            if pd.isna(val):
                val = 1.0  # fallback
            base = float(val)
            mn = base * 0.8
            mx = base * 1.2
            # ensure strictly <
            if mn >= mx:
                mx = mn + 1e-4

        # If still invalid, fallback [0,1]
        if mn >= mx:
            mn, mx = 0.0, 1.0

        out_rows.append({"name": p, "min_value": mn, "max_value": mx})

    return pd.DataFrame(out_rows)


##############################################################################
# 3) BUILD SALib problem
##############################################################################

def build_salib_problem(params_meta: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert a DataFrame with columns [name, min_value, max_value]
    into a SALib 'problem' dict.
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
# 4) CORRELATION-BASED SENSITIVITY
##############################################################################

def correlation_sensitivity(
    df_scenarios: pd.DataFrame,
    df_results: pd.DataFrame,
    target_variable: str = "Heating:EnergyTransfer [J](Hourly)",
    scenario_index_col: str = "scenario_index",
    assigned_val_col: str = "assigned_value"
) -> pd.DataFrame:
    """
    Example correlation-based approach:
      1) pivot scenario data => wide form
      2) merge with results, which have columns [BuildingID, VariableName, ... daily or total columns ...]
      3) sum daily columns => 'TotalEnergy_J' or pick a single column
      4) correlation vs. each parameter

    Returns a DataFrame with ["Parameter", "Correlation", "AbsCorrelation"] sorted desc.
    """
    # Pivot scenario => each row is scenario_index, each column is param_name
    pivot_df = df_scenarios.pivot_table(
        index=[scenario_index_col, "ogc_fid"],
        columns="param_name",
        values=assigned_val_col,
        aggfunc="first"
    ).reset_index()

    # Merge with results. We assume scenario_index ~ BuildingID
    pivot_df.rename(columns={scenario_index_col: "BuildingID"}, inplace=True)

    # If results has daily columns, sum them to get a single measure
    # or filter for target_variable
    melted = df_results.melt(
        id_vars=["BuildingID", "VariableName"],
        var_name="Day",
        value_name="Value"
    )
    daily_sum = melted.groupby(["BuildingID", "VariableName"])["Value"].sum().reset_index()
    daily_sum.rename(columns={"Value": "TotalEnergy_J"}, inplace=True)

    # Filter for target_variable
    daily_sum = daily_sum[daily_sum["VariableName"] == target_variable]

    # Merge
    merged = pd.merge(
        pivot_df,
        daily_sum,
        on="BuildingID",
        how="inner"
    )

    # Now we have param columns + "TotalEnergy_J"
    exclude_cols = ["BuildingID", "ogc_fid", "VariableName", "TotalEnergy_J"]
    param_cols = [c for c in merged.columns if c not in exclude_cols]

    corr_list = []
    for col in param_cols:
        # must be numeric
        if pd.api.types.is_numeric_dtype(merged[col]):
            cval = merged[[col, "TotalEnergy_J"]].corr().iloc[0, 1]
            corr_list.append((col, cval))
        else:
            corr_list.append((col, np.nan))

    corr_df = pd.DataFrame(corr_list, columns=["Parameter", "Correlation"])
    corr_df["AbsCorrelation"] = corr_df["Correlation"].abs()
    corr_df.sort_values("AbsCorrelation", ascending=False, inplace=True)
    return corr_df


##############################################################################
# 5) SALib-based Morris
##############################################################################

def run_morris(
    params_meta: pd.DataFrame,
    simulate_func,
    n_trajectories: int = 10,
    num_levels: int = 4
):
    """
    Perform a Morris screening using SALib.

    :param params_meta: DataFrame with ['name', 'min_value', 'max_value']
    :param simulate_func: user function that takes {param_name: value} -> float
    :param n_trajectories: number of trajectories (N in SALib's morris.sample)
    :param num_levels: levels in the Morris design
    :return: (morris_res, X, Y) where
         morris_res is SALib's analysis result,
         X is the sample array,
         Y is the model outputs array
    """
    if not HAVE_SALIB:
        raise ImportError("SALib is not installed. Cannot run Morris.")
    problem = build_salib_problem(params_meta)
    # sample
    X = morris.sample(
        problem,
        N=n_trajectories,
        num_levels=num_levels
    )
    # evaluate
    Y = []
    for row in X:
        param_dict = {}
        for i, name in enumerate(problem["names"]):
            param_dict[name] = row[i]
        val = simulate_func(param_dict)
        Y.append(val)
    Y = np.array(Y)
    # analyze
    morris_res = morris_analyze.analyze(
        problem,
        X,
        Y,
        conf_level=0.95,
        print_to_console=False
    )
    return morris_res, X, Y


##############################################################################
# 6) SALib-based Sobol
##############################################################################

def run_sobol(
    params_meta: pd.DataFrame,
    simulate_func,
    n_samples: int = 256
):
    """
    Perform a Sobol analysis using SALib.

    :param params_meta: DataFrame with ['name', 'min_value', 'max_value']
    :param simulate_func: user function that takes {param_name: value} -> float
    :param n_samples: base sample size for Saltelli sampler
    :return: (sobol_res, X, Y) where
         sobol_res is SALib's analysis result,
         X is the sample array,
         Y is the model outputs array
    """
    if not HAVE_SALIB:
        raise ImportError("SALib is not installed. Cannot run Sobol.")
    problem = build_salib_problem(params_meta)
    X = saltelli.sample(
        problem,
        n_samples,
        calc_second_order=True
    )
    Y = []
    for row in X:
        param_dict = {}
        for i, name in enumerate(problem["names"]):
            param_dict[name] = row[i]
        val = simulate_func(param_dict)
        Y.append(val)
    Y = np.array(Y)
    # analyze
    sobol_res = sobol.analyze(
        problem,
        Y,
        calc_second_order=True,
        print_to_console=False
    )
    return sobol_res, X, Y


##############################################################################
# 7) EXAMPLE SIMULATION FUNCTION
##############################################################################

def default_simulate_func(param_dict: Dict[str, float]) -> float:
    """
    A placeholder for your real or surrogate-based simulation.
    We'll sum param_dict values + some random noise.

    In practice, you would:
      - write param_dict to an IDF or call your surrogate
      - compute a mismatch vs. real data
      - return that mismatch.
    """
    base_sum = sum(param_dict.values())
    noise = np.random.uniform(-0.5, 0.5)
    return base_sum + noise


##############################################################################
# 8) MAIN ORCHESTRATOR
##############################################################################

def run_sensitivity_analysis(
    scenario_folder: str,
    method: str = "morris",
    param_min_col: str = "param_min",
    param_max_col: str = "param_max",
    output_csv: str = "sensitivity_results.csv",
    results_csv: Optional[str] = None,
    target_variable: Optional[str] = None,
    n_morris_trajectories: int = 10,
    num_levels: int = 4,
    n_sobol_samples: int = 256
):
    """
    Orchestrate the entire sensitivity process. We handle:
      1) correlation-based OR SALib-based (morris/sobol)
      2) reading scenario CSVs from scenario_folder
      3) extracting param ranges if param_min / param_max exist
      4) fallback if missing
      5) run the chosen method
      6) save results to output_csv

    :param scenario_folder: folder with scenario_params_*.csv
    :param method: "correlation", "morris", or "sobol"
    :param param_min_col: name of col with min. Typically "param_min"
    :param param_max_col: name of col with max. Typically "param_max"
    :param output_csv: where to store results
    :param results_csv: if using correlation, we need the simulation results
    :param target_variable: if correlation-based, pick a variable
    :param n_morris_trajectories: how many Morris trajectories
    :param num_levels: Morris levels
    :param n_sobol_samples: how many Saltelli samples for Sobol
    """
    print(f"=== Running Sensitivity: method={method} ===")

    # 1) load scenario data
    merged_df = load_scenario_params(scenario_folder)

    # If correlation-based, we need results_csv & target_variable
    if method.lower() == "correlation":
        if not results_csv:
            raise ValueError("Must provide results_csv for correlation-based analysis.")
        if not target_variable:
            raise ValueError("Must provide target_variable for correlation-based analysis.")

        df_results = pd.read_csv(results_csv)
        corr_df = correlation_sensitivity(
            df_scenarios=merged_df,
            df_results=df_results,
            target_variable=target_variable
        )
        print("\n=== Correlation-based Sensitivity ===")
        print(corr_df.head(20))

        corr_df.to_csv(output_csv, index=False)
        print(f"[INFO] Correlation results => {output_csv}")
        return

    # else we do SALib-based (morris or sobol)
    # 2) extract param ranges
    params_meta = extract_parameter_ranges(
        merged_df,
        param_min_col=param_min_col,
        param_max_col=param_max_col
    )

    # define a local function for simulation
    def local_sim_func(param_dict: Dict[str, float]) -> float:
        # user can replace this with their real approach
        return default_simulate_func(param_dict)

    if method.lower() == "morris":
        if not HAVE_SALIB:
            raise ImportError("SALib not installed. Cannot run Morris.")
        morris_res, X, Y = run_morris(
            params_meta, local_sim_func,
            n_trajectories=n_morris_trajectories,
            num_levels=num_levels
        )
        # Build DataFrame of results
        df_out = pd.DataFrame({
            "param": params_meta["name"],
            "mu_star": morris_res["mu_star"],
            "mu_star_conf": morris_res["mu_star_conf"],
            "sigma": morris_res["sigma"]
        })
        df_out.to_csv(output_csv, index=False)
        print(f"[INFO] Morris results => {output_csv}")
        # Print short summary
        print("[Morris] mu_star:", morris_res['mu_star'])
        print("[Morris] sigma  :", morris_res['sigma'])

    elif method.lower() == "sobol":
        if not HAVE_SALIB:
            raise ImportError("SALib not installed. Cannot run Sobol.")
        sobol_res, X, Y = run_sobol(
            params_meta, local_sim_func,
            n_samples=n_sobol_samples
        )
        # Build DataFrame
        df_out = pd.DataFrame({
            "param": params_meta["name"],
            "S1": sobol_res["S1"],
            "ST": sobol_res["ST"]
        })
        # s2 is a matrix in sobol_res["S2"], etc.
        df_out.to_csv(output_csv, index=False)
        print(f"[INFO] Sobol results => {output_csv}")
        # Print summary
        print("[Sobol] S1 =>", sobol_res["S1"])
        print("[Sobol] ST =>", sobol_res["ST"])

    else:
        raise ValueError(f"Unknown method: {method}. Choose 'correlation', 'morris', or 'sobol'.")
