"""
unified_sensitivity.py

Updated to handle multiple target variables for correlation-based sensitivity.
You can specify in your config:
    "target_variable": [
      "Heating:EnergyTransfer [J](Hourly)",
      "Cooling:EnergyTransfer [J](Hourly)",
      ...
    ]
or a single string (like "Heating:EnergyTransfer [J](Hourly)").

Author: Your Team
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, List

# Attempt SALib imports
try:
    from SALib.sample import morris as morris_sample
    from SALib.sample import saltelli
    from SALib.analyze import morris as morris_analyze
    from SALib.analyze import sobol
    HAVE_SALIB = True
except ImportError:
    HAVE_SALIB = False
    morris_sample = None
    morris_analyze = None
    saltelli = None
    sobol = None


###############################################################################
# 1) HELPERS FOR CATEGORICAL ENCODING & NAME BUILD
###############################################################################

def encode_categorical_if_known(param_name: str, param_value) -> Optional[float]:
    """
    Tries to interpret 'param_value' as numeric:
      1) Direct float conversion
      2) If that fails, attempt known label encodings
      3) Return None if unknown => skip param

    Modify or expand the logic as you see fit to cover more discrete strings.
    """
    if param_value is None or pd.isna(param_value):
        return None

    # (A) Try direct float conversion
    try:
        return float(param_value)
    except (ValueError, TypeError):
        pass  # not a direct float

    # (B) Attempt known label encodings

    # Example 1: "Electricity" -> 0.0, "Gas" -> 1.0
    if param_name.lower().endswith("fuel_type"):
        if param_value == "Electricity":
            return 0.0
        elif param_value == "Gas":
            return 1.0
        return None

    # Example 2: Roughness => "MediumRough" -> 2.0, etc.
    if "roughness" in param_name.lower():
        rough_map = {
            "Smooth": 0.0,
            "MediumSmooth": 1.0,
            "MediumRough": 2.0,
            "Rough": 3.0
        }
        if param_value in rough_map:
            return rough_map[param_value]
        return None

    # Example 3: "Yes"/"No" => 1.0 / 0.0
    if param_value in ["Yes", "No"]:
        return 1.0 if param_value == "Yes" else 0.0

    # Example 4: "SpectralAverage" => encode as 0.0, or skip
    if param_value == "SpectralAverage":
        return 0.0

    # Example 5: Generic "Electricity"/"Gas" if not caught above:
    if param_value == "Electricity":
        return 0.0
    elif param_value == "Gas":
        return 1.0

    # If we get here => no recognized encoding => skip
    return None


def build_unified_param_name(row: pd.Series) -> str:
    """
    Combine columns (zone_name, object_name, sub_key, param_name)
    to produce a single unique param_name in the final DataFrame.
    Modify to your preference.
    """
    base_name = str(row.get("param_name", "UnknownParam"))
    name_parts = []

    zname = row.get("zone_name", None)
    if pd.notna(zname) and isinstance(zname, str) and zname.strip():
        name_parts.append(zname.strip())

    oname = row.get("object_name", None)
    if pd.notna(oname) and isinstance(oname, str) and oname.strip():
        name_parts.append(oname.strip())

    skey = row.get("sub_key", None)
    if pd.notna(skey) and isinstance(skey, str) and skey.strip():
        name_parts.append(skey.strip())

    # Finally the base param_name
    name_parts.append(base_name)

    # Join with double underscore
    return "__".join(name_parts)


###############################################################################
# 2) LOADING SCENARIO PARAMS
###############################################################################

def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Reads scenario_params_*.csv from scenario_folder, merges them into
    a single DataFrame with columns:
      ["scenario_index", "param_name", "assigned_value", "param_min", "param_max", "ogc_fid", "source_file"]
    and attempts to convert assigned_value to float or a known label-encoded numeric.

    If it cannot be encoded => we skip that row.
    """
    scenario_files = [
        "scenario_params_dhw.csv",
        "scenario_params_elec.csv",
        "scenario_params_fenez.csv",
        "scenario_params_hvac.csv",
        "scenario_params_vent.csv"
    ]

    all_rows = []

    for fname in scenario_files:
        fpath = os.path.join(scenario_folder, fname)
        if not os.path.isfile(fpath):
            continue

        df_raw = pd.read_csv(fpath)
        if df_raw.empty:
            continue

        for _, row in df_raw.iterrows():
            scenario_index = row.get("scenario_index", None)
            unified_name = build_unified_param_name(row)

            # assigned_value might be 'assigned_value' or 'param_value'
            val = row.get("assigned_value", None)
            if val is None or pd.isna(val):
                val = row.get("param_value", None)

            # Attempt to convert/encode
            numeric_val = encode_categorical_if_known(unified_name, val)
            if numeric_val is None:
                print(f"[WARNING] Skipping param '{unified_name}' => "
                      f"no numeric encoding for value: {val}")
                continue

            # param_min / param_max
            pmin = row.get("param_min", np.nan)
            pmax = row.get("param_max", np.nan)

            # ogc_fid
            ogc_fid = row.get("ogc_fid", None)

            all_rows.append({
                "scenario_index": scenario_index,
                "param_name": unified_name,
                "assigned_value": numeric_val,
                "param_min": pmin,
                "param_max": pmax,
                "ogc_fid": ogc_fid,
                "source_file": fname
            })

    if not all_rows:
        print(f"[WARNING] No valid numeric parameters found in '{scenario_folder}' (all skipped?)")
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


###############################################################################
# 3) CORRELATION-BASED SENSITIVITY (SINGLE or MULTIPLE Variables)
###############################################################################

def correlation_sensitivity(
    df_scenarios: pd.DataFrame,
    df_results: pd.DataFrame,
    target_variables: Union[str, List[str]],
    scenario_index_col: str = "scenario_index",
    assigned_val_col: str = "assigned_value"
) -> pd.DataFrame:
    """
    Performs correlation-based sensitivity between each parameter and
    one or more target variables from the results.

    If target_variables is a single string, we produce a DF with:
       [Parameter, Correlation, AbsCorrelation]

    If target_variables is a list of strings, we produce one row per param,
    with correlation columns for each variable, e.g.:
       [Parameter,
        Corr_<var1>, AbsCorr_<var1>,
        Corr_<var2>, AbsCorr_<var2>, ...
       ]

    Steps:
      1) Pivot df_scenarios => wide (index=scenario_index, columns=param_name)
      2) Melt df_results => sum across days => pivot wide so each variable has
         its own column.
      3) Merge scenario pivot with results pivot
      4) Correlate each param col with each variable col

    Returns a DataFrame of correlation results.
    """
    # Normalize target_variables to a list
    if isinstance(target_variables, str):
        target_vars_list = [target_variables]
    elif isinstance(target_variables, list):
        target_vars_list = target_variables
    else:
        raise ValueError("target_variables must be a string or a list of strings.")

    # 1) Pivot scenario => wide
    pivot_df = df_scenarios.pivot_table(
        index=scenario_index_col,
        columns="param_name",
        values=assigned_val_col,
        aggfunc="first"
    ).reset_index()

    # 2) Melt results & sum across days
    if "BuildingID" in df_results.columns and scenario_index_col != "BuildingID":
        df_results = df_results.rename(columns={"BuildingID": scenario_index_col})

    melted = df_results.melt(
        id_vars=[scenario_index_col, "VariableName"],
        var_name="Day",
        value_name="Value"
    )
    daily_sum = melted.groupby([scenario_index_col, "VariableName"])["Value"].sum().reset_index()
    daily_sum.rename(columns={"Value": "SumValue"}, inplace=True)

    # 3) Pivot variables => each var a column
    #    If multiple target variables, we want them all to appear as columns
    #    in the pivot. If you have more variables than in target_vars_list,
    #    that's OK; we can keep them, or filter them.
    pivot_results = daily_sum.pivot(
        index=scenario_index_col,
        columns="VariableName",
        values="SumValue"
    ).reset_index()

    # If you want to filter pivot_results to only keep the target vars:
    all_cols = list(pivot_results.columns)
    # the first is scenario_index_col, so skip it
    keep_cols = [scenario_index_col]
    # keep only columns in target_vars_list if they exist
    for varname in target_vars_list:
        if varname in all_cols:
            keep_cols.append(varname)
    pivot_results = pivot_results[keep_cols]

    # 4) Merge scenario pivot with results pivot
    merged = pd.merge(
        pivot_df,
        pivot_results,
        on=scenario_index_col,
        how="inner"
    )

    # Now columns = [scenario_index, paramA, paramB, ..., var1, var2, ...]
    # We do correlation paramX vs. varY for each pair
    # param_cols are the scenario param columns, var_cols are the target variable columns
    var_cols = [c for c in pivot_results.columns if c != scenario_index_col]
    param_cols = [c for c in pivot_df.columns if c != scenario_index_col]

    # If there's only 1 target var, produce the old layout.
    if len(var_cols) == 1:
        var_col = var_cols[0]
        corr_list = []
        for col in param_cols:
            if pd.api.types.is_numeric_dtype(merged[col]):
                cval = merged[[col, var_col]].corr().iloc[0, 1]
                corr_list.append((col, cval))
            else:
                corr_list.append((col, np.nan))
        corr_df = pd.DataFrame(corr_list, columns=["Parameter", "Correlation"])
        corr_df["AbsCorrelation"] = corr_df["Correlation"].abs()
        corr_df.sort_values("AbsCorrelation", ascending=False, inplace=True)
        return corr_df

    # Else multiple variables => produce one row per param, with correlation columns for each var
    # e.g. param, Corr_var1, AbsCorr_var1, Corr_var2, AbsCorr_var2, ...
    corr_rows = []
    for col in param_cols:
        row_dict = {"Parameter": col}
        if not pd.api.types.is_numeric_dtype(merged[col]):
            # skip or store NaNs
            for v in var_cols:
                row_dict[f"Corr_{v}"] = np.nan
                row_dict[f"AbsCorr_{v}"] = np.nan
        else:
            # param is numeric
            for v in var_cols:
                if not pd.api.types.is_numeric_dtype(merged[v]):
                    row_dict[f"Corr_{v}"] = np.nan
                    row_dict[f"AbsCorr_{v}"] = np.nan
                else:
                    cval = merged[[col, v]].corr().iloc[0, 1]
                    row_dict[f"Corr_{v}"] = cval
                    row_dict[f"AbsCorr_{v}"] = abs(cval)
        corr_rows.append(row_dict)

    corr_df = pd.DataFrame(corr_rows)
    # Optionally you can sort by one variable's AbsCorr_ if you want:
    # e.g. if the first var is var_cols[0], sort by that
    # but let's just leave it unsorted or sort by "Parameter"
    corr_df.sort_values("Parameter", inplace=True)
    return corr_df


###############################################################################
# 4) SALib UTILS: EXTRACT RANGES, BUILD PROBLEM
###############################################################################

def extract_parameter_ranges(
    merged_df: pd.DataFrame,
    param_name_col: str = "param_name",
    assigned_val_col: str = "assigned_value",
    param_min_col: str = "param_min",
    param_max_col: str = "param_max"
) -> pd.DataFrame:
    """
    Builds DF [name, min_value, max_value].
    If param_min / param_max are missing/invalid, fallback to ±20% around assigned_value.
    """
    out_rows = []
    unique_params = merged_df[param_name_col].unique()
    for p in unique_params:
        sub = merged_df[merged_df[param_name_col] == p]
        row = sub.iloc[0]  # any row for param p

        assigned_val = row.get(assigned_val_col, np.nan)
        if pd.isna(assigned_val):
            continue

        pmin = row.get(param_min_col, np.nan)
        pmax = row.get(param_max_col, np.nan)
        try:
            pmin = float(pmin)
        except:
            pmin = np.nan
        try:
            pmax = float(pmax)
        except:
            pmax = np.nan

        if np.isnan(pmin) or np.isnan(pmax) or (pmin >= pmax):
            base = float(assigned_val)
            delta = abs(base) * 0.2
            pmin = base - delta
            pmax = base + delta
            if pmin >= pmax:
                pmax += 1e-4

        out_rows.append({
            "name": p,
            "min_value": pmin,
            "max_value": pmax
        })

    return pd.DataFrame(out_rows)


def build_salib_problem(params_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert DF [name, min_value, max_value] => SALib problem dict
    """
    return {
        "num_vars": len(params_df),
        "names": params_df["name"].tolist(),
        "bounds": [
            [row["min_value"], row["max_value"]]
            for _, row in params_df.iterrows()
        ]
    }


###############################################################################
# 5) SALib: MORRIS & SOBOL
###############################################################################

def default_simulation_function(param_dict: Dict[str, float]) -> float:
    """
    Example: sum of param_dict + random noise.
    Replace with your E+ or Surrogate call if you want real analysis.
    """
    base_sum = sum(param_dict.values())
    noise = np.random.uniform(-0.5, 0.5)
    return base_sum + noise


def run_morris_method(params_meta: pd.DataFrame, simulate_func, n_trajectories=10, num_levels=4):
    """
    SALib Morris
    """
    if not HAVE_SALIB:
        raise ImportError("SALib not installed. Cannot run Morris.")
    problem = build_salib_problem(params_meta)
    X = morris_sample.sample(problem, N=n_trajectories, num_levels=num_levels)
    Y = []
    for row in X:
        param_dict = {}
        for i, name in enumerate(problem["names"]):
            param_dict[name] = row[i]
        Y.append(simulate_func(param_dict))
    Y = np.array(Y)
    res = morris_analyze.analyze(problem, X, Y, conf_level=0.95, print_to_console=False)
    return res, X, Y


def run_sobol_method(params_meta: pd.DataFrame, simulate_func, n_samples=256):
    """
    SALib Sobol
    """
    if not HAVE_SALIB:
        raise ImportError("SALib not installed. Cannot run Sobol.")
    problem = build_salib_problem(params_meta)
    X = saltelli.sample(problem, n_samples, calc_second_order=True)
    Y = []
    for row in X:
        param_dict = {}
        for i, name in enumerate(problem["names"]):
            param_dict[name] = row[i]
        Y.append(simulate_func(param_dict))
    Y = np.array(Y)
    sres = sobol.analyze(problem, Y, calc_second_order=True, print_to_console=False)
    return sres, X, Y


###############################################################################
# 6) MAIN ORCHESTRATION
###############################################################################
def run_sensitivity_analysis(
    scenario_folder: str,
    method: str = "morris",
    results_csv: Optional[str] = None,
    target_variable: Union[str, List[str], None] = None,
    output_csv: str = "sensitivity_output.csv",
    n_morris_trajectories: int = 10,
    num_levels: int = 4,
    n_sobol_samples: int = 256
):
    """
    Called from main.py to do correlation, Morris, or Sobol sensitivity.
    Now supports multiple target variables in correlation-based approach.

    :param scenario_folder: path to folder with scenario_params_*.csv
    :param method: "correlation", "morris", or "sobol"
    :param results_csv: path to results CSV (for correlation)
    :param target_variable: string or list of strings (for correlation).
    :param output_csv: results file
    :param n_morris_trajectories: int
    :param num_levels: Morris design
    :param n_sobol_samples: int
    """
    print(f"[INFO] run_sensitivity_analysis => method={method}, folder='{scenario_folder}'")

    # 1) Load scenario parameters
    df_params = load_scenario_params(scenario_folder)
    if df_params.empty:
        print("[WARNING] No numeric scenario parameters => no analysis.")
        return

    # 2) If correlation-based
    if method.lower() == "correlation":
        if not results_csv or not os.path.isfile(results_csv):
            raise ValueError("For correlation-based, must provide a valid results_csv.")
        if not target_variable:
            raise ValueError("For correlation-based, must provide target_variable (string or list).")

        df_res = pd.read_csv(results_csv)
        corr_df = correlation_sensitivity(
            df_scenarios=df_params,
            df_results=df_res,
            target_variables=target_variable
        )
        corr_df.to_csv(output_csv, index=False)
        print(f"[INFO] Correlation-based results => {output_csv}")
        return

    # 3) SALib-based => extract ranges
    params_meta = extract_parameter_ranges(df_params)
    if params_meta.empty:
        print("[WARNING] All parameters were invalid or had no numeric data => no SALib analysis.")
        return

    # Replace with real E+ or surrogate
    simulate_func = default_simulation_function

    if method.lower() == "morris":
        # Morris
        res, X, Y = run_morris_method(
            params_meta=params_meta,
            simulate_func=simulate_func,
            n_trajectories=n_morris_trajectories,
            num_levels=num_levels
        )
        df_out = pd.DataFrame({
            "param": params_meta["name"].values,
            "mu_star": res["mu_star"],
            "mu_star_conf": res["mu_star_conf"],
            "sigma": res["sigma"]
        })
        df_out.to_csv(output_csv, index=False)
        print(f"[INFO] Morris sensitivity results => {output_csv}")

    elif method.lower() == "sobol":
        # Sobol
        sres, X, Y = run_sobol_method(
            params_meta=params_meta,
            simulate_func=simulate_func,
            n_samples=n_sobol_samples
        )
        df_out = pd.DataFrame({
            "param": params_meta["name"].values,
            "S1": sres["S1"],
            "S1_conf": sres["S1_conf"],
            "ST": sres["ST"],
            "ST_conf": sres["ST_conf"]
        })
        df_out.to_csv(output_csv, index=False)
        print(f"[INFO] Sobol sensitivity results => {output_csv}")

    else:
        raise ValueError(f"Unknown method='{method}'. Must be 'correlation','morris','sobol'.")
