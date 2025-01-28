"""
unified_surrogate.py

Purpose:
  1) Loads scenario-based parameter CSVs (dhw, elec, fenez, hvac, vent) from 
     the scenario_folder, converting any known categorical text (e.g. "Electricity") 
     to numeric. Skips unknown text values.
  2) Pivots them so each scenario is one row, each parameter is one column.
  3) Loads simulation results (like merged_daily_mean_mocked.csv) which 
     has columns [BuildingID, VariableName, Day1, Day2, ...].
  4) Sums daily columns => "TotalEnergy_J" per (BuildingID, VariableName).
  5) Merges scenario data with E+ results, focusing on a single or multiple 
     target_variable(s).
  6) Trains a RandomForest surrogate (single-output if target_variable is a string, 
     multi-output if it's a list).
  7) Saves the fitted model and the list of feature columns for future predictions.

Typical usage in main.py:
    if sur_cfg.get("perform_surrogate", False):
        df_scen = sur_load_scenario_params(scenario_folder)
        pivot_df = pivot_scenario_params(df_scen)
        # optional: pivot_df = filter_top_parameters(pivot_df, "morris_sensitivity.csv", top_n=5)
        df_sim = load_sim_results(results_csv)
        df_agg = aggregate_results(df_sim)
        merged_df = merge_params_with_results(pivot_df, df_agg, target_var)
        build_and_save_surrogate(
            df_data=merged_df,
            target_col=target_var,
            model_out_path=model_out,
            columns_out_path=cols_out,
            test_size=test_size
        )

Author: Your Team
"""

import os
import pandas as pd
import numpy as np
import joblib
from typing import Optional, List, Union
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import r2_score, mean_absolute_error


###############################################################################
# 1) HELPER: Encode known text -> numeric
###############################################################################

def encode_categorical_if_known(param_name: str, param_value) -> Optional[float]:
    """
    1) Attempt float conversion
    2) If fails, check known label encodings
    3) If still unknown => return None => skip row

    Modify or expand to handle your typical discrete strings.
    """
    if param_value is None or pd.isna(param_value):
        return None

    # (A) Direct float conversion
    try:
        return float(param_value)
    except (ValueError, TypeError):
        pass

    # (B) Known label encodings

    # Example: "Electricity" => 0.0, "Gas" => 1.0
    if param_value == "Electricity":
        return 0.0
    elif param_value == "Gas":
        return 1.0

    # Example: Roughness
    rough_map = {
        "Smooth": 0.0,
        "MediumSmooth": 1.0,
        "MediumRough": 2.0,
        "Rough": 3.0
    }
    if param_value in rough_map:
        return rough_map[param_value]

    # Example: "Yes"/"No" => 1.0 / 0.0
    if param_value in ["Yes", "No"]:
        return 1.0 if param_value == "Yes" else 0.0

    # Not recognized => skip
    return None


###############################################################################
# 2) SCENARIO LOADING & PIVOT
###############################################################################

def load_scenario_file(filepath: str) -> pd.DataFrame:
    """
    Reads one scenario CSV, ensures a column 'assigned_value' which is numeric.
    If row can't be converted => skip. Returns a numeric-only DataFrame for that file.
    """
    df_in = pd.read_csv(filepath)

    # unify to 'assigned_value'
    if "assigned_value" not in df_in.columns and "param_value" in df_in.columns:
        df_in.rename(columns={"param_value": "assigned_value"}, inplace=True)

    # We'll keep only rows that produce a numeric assigned_value
    rows_out = []
    for _, row in df_in.iterrows():
        val = row.get("assigned_value", None)
        if val is None or pd.isna(val):
            continue

        # Attempt numeric or known label
        param_name = str(row.get("param_name", ""))
        num_val = encode_categorical_if_known(param_name, val)
        if num_val is None:
            # skip
            continue

        new_row = row.copy()
        new_row["assigned_value"] = num_val
        rows_out.append(new_row)

    if not rows_out:
        return pd.DataFrame()

    return pd.DataFrame(rows_out)


def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Merges scenario_params_{dhw, elec, fenez, hvac, vent}.csv from scenario_folder.
    Each file is label-encoded. Unknown text -> skipped.
    Returns a unified DataFrame with columns like:
      [scenario_index, param_name, assigned_value, ogc_fid, ...]
    """
    scenario_files = [
        "scenario_params_dhw.csv",
        "scenario_params_elec.csv",
        "scenario_params_fenez.csv",
        "scenario_params_hvac.csv",
        "scenario_params_vent.csv"
    ]

    all_dfs = []
    for fname in scenario_files:
        fpath = os.path.join(scenario_folder, fname)
        if not os.path.isfile(fpath):
            print(f"[INFO] Not found => {fpath}")
            continue

        df_scenario = load_scenario_file(fpath)
        if df_scenario.empty:
            print(f"[WARN] No numeric row data in => {fpath} (skipped all).")
        else:
            # Optionally add a 'source_file' column
            df_scenario["source_file"] = fname
            all_dfs.append(df_scenario)

    if not all_dfs:
        raise FileNotFoundError(f"[ERROR] No scenario CSV with numeric data found in '{scenario_folder}'.")
    return pd.concat(all_dfs, ignore_index=True)


def pivot_scenario_params(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots so each scenario_index is a row, each param_name is a column, assigned_value are cells.
    Also preserves 'ogc_fid' if present.

    Example final columns:
      scenario_index, ogc_fid, paramA, paramB, ...
    """
    if "scenario_index" not in df.columns or "param_name" not in df.columns or "assigned_value" not in df.columns:
        raise ValueError("DataFrame must have columns: scenario_index, param_name, assigned_value")

    if "ogc_fid" not in df.columns:
        df["ogc_fid"] = 0

    pivot_df = df.pivot_table(
        index=["scenario_index", "ogc_fid"],
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()

    pivot_df.columns.name = None
    return pivot_df


def filter_top_parameters(
    df_pivot: pd.DataFrame,
    sensitivity_csv: str,
    top_n: int,
    param_col: str = "param",
    metric_col: str = "mu_star"
) -> pd.DataFrame:
    """
    Reads a Morris sensitivity CSV, picks top_n 'param' by mu_star, 
    filters df_pivot to only those columns plus scenario_index, ogc_fid.
    """
    if not os.path.isfile(sensitivity_csv):
        print(f"[INFO] Sensitivity file '{sensitivity_csv}' not found => skipping filter.")
        return df_pivot

    sens_df = pd.read_csv(sensitivity_csv)
    if param_col not in sens_df.columns or metric_col not in sens_df.columns:
        print(f"[ERROR] param_col='{param_col}' or metric_col='{metric_col}' not in {sensitivity_csv}.")
        return df_pivot

    top_params = sens_df.sort_values(metric_col, ascending=False)[param_col].head(top_n).tolist()
    keep_cols = ["scenario_index", "ogc_fid"] + [p for p in top_params if p in df_pivot.columns]
    filtered = df_pivot[keep_cols].copy()
    print(f"[INFO] Filtered pivot from {df_pivot.shape} -> {filtered.shape} using top {top_n} params.")
    return filtered


###############################################################################
# 3) LOADING & AGGREGATING SIM RESULTS
###############################################################################

def load_sim_results(results_csv: str) -> pd.DataFrame:
    """
    Typically: [BuildingID, VariableName, Day1, Day2, ...]
    """
    return pd.read_csv(results_csv)


def aggregate_results(df_sim: pd.DataFrame) -> pd.DataFrame:
    """
    Sums across days => [BuildingID, VariableName, TotalEnergy_J].
    Ensures we have "BuildingID", "VariableName".
    """
    needed = {"BuildingID", "VariableName"}
    if not needed.issubset(df_sim.columns):
        raise ValueError("df_sim must have columns BuildingID, VariableName plus day columns.")
    melted = df_sim.melt(
        id_vars=["BuildingID", "VariableName"],
        var_name="Day",
        value_name="Value"
    )
    daily_sum = melted.groupby(["BuildingID", "VariableName"])["Value"].sum().reset_index()
    daily_sum.rename(columns={"Value": "TotalEnergy_J"}, inplace=True)
    return daily_sum


def merge_params_with_results(
    pivot_df: pd.DataFrame,
    df_agg: pd.DataFrame,
    target_var: Union[str, List[str], None] = None
) -> pd.DataFrame:
    """
    Merges pivoted scenario data (with columns [scenario_index->BuildingID, paramA..])
    + aggregated results => single DataFrame for model training.

    If target_var is None => merges all "VariableName" => multiple rows per building.
    If str => picks that var => single column => rename to var name => merges one row per building
    If list => pivot each var => multi columns => merges one row per building => multi-output
    """
    merged = pivot_df.copy()
    # rename scenario_index => BuildingID
    merged.rename(columns={"scenario_index": "BuildingID"}, inplace=True)

    if target_var is None:
        # Just join, no filtering => multiple rows
        return pd.merge(merged, df_agg, on="BuildingID", how="inner")

    if isinstance(target_var, str):
        # single var => one column
        df_sub = df_agg[df_agg["VariableName"] == target_var].copy()
        df_sub.rename(columns={"TotalEnergy_J": target_var}, inplace=True)
        df_sub.drop(columns=["VariableName"], inplace=True, errors="ignore")
        return pd.merge(merged, df_sub, on="BuildingID", how="inner")

    if isinstance(target_var, list):
        # multi-output => pivot each var => multiple columns
        df_sub = df_agg[df_agg["VariableName"].isin(target_var)]
        pivot_vars = df_sub.pivot(
            index="BuildingID",
            columns="VariableName",
            values="TotalEnergy_J"
        ).reset_index()
        return pd.merge(merged, pivot_vars, on="BuildingID", how="inner")

    raise ValueError("target_var must be None, str, or list[str].")


###############################################################################
# 4) SURROGATE TRAINING
###############################################################################

def build_and_save_surrogate(
    df_data: pd.DataFrame,
    target_col: Union[str, List[str]] = "TotalEnergy_J",
    model_out_path: str = "surrogate_model.joblib",
    columns_out_path: str = "surrogate_columns.joblib",
    test_size: float = 0.3,
    random_state: int = 42
):
    """
    1) Splits data into X,y. If target_col is a single string => single-output.
       If list => multi-output.
    2) Builds a RandomForest via RandomizedSearchCV => best params.
    3) If multi-output => wraps in MultiOutputRegressor.
    4) Saves model + list of feature columns.

    Returns (model, feature_cols).
    """
    # 1) Determine target columns
    if isinstance(target_col, str):
        if target_col not in df_data.columns:
            print(f"[ERROR] target_col '{target_col}' not in df_data.")
            return None, None
        y_data = df_data[[target_col]].copy()
        multi_output = False
    elif isinstance(target_col, list):
        missing = [t for t in target_col if t not in df_data.columns]
        if missing:
            print(f"[ERROR] Some target columns missing: {missing}")
            return None, None
        y_data = df_data[target_col].copy()
        multi_output = (len(target_col) > 1)
    else:
        print("[ERROR] target_col must be str or list[str].")
        return None, None

    # 2) Build features
    exclude_cols = ["BuildingID", "ogc_fid", "VariableName", "source_file"]
    if multi_output:
        exclude_cols.extend(target_col)
    else:
        exclude_cols.append(target_col)

    candidate_cols = [c for c in df_data.columns if c not in exclude_cols]
    # Keep only numeric columns
    numeric_cols = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df_data[c])]

    if not numeric_cols:
        print("[ERROR] No numeric feature columns found => can't train surrogate.")
        return None, None

    # Drop rows with any NaN in X or y
    full_df = df_data[numeric_cols + list(y_data.columns)].dropna()
    if full_df.empty:
        print("[ERROR] All data is NaN => can't train surrogate.")
        return None, None

    X_data = full_df[numeric_cols]
    Y_data = full_df[y_data.columns]

    # Must have enough rows
    if len(X_data) < 5:
        print(f"[ERROR] Not enough data => only {len(X_data)} row(s).")
        return None, None

    # 3) Train/test split
    X_train, X_test, Y_train, Y_test = train_test_split(
        X_data, Y_data, test_size=test_size, random_state=random_state
    )

    # 4) RandomizedSearchCV for best RF params
    param_dist = {
        "n_estimators": [50, 100, 200],
        "max_depth": [None, 5, 10, 20],
        "max_features": ["auto", "sqrt", 0.5]
    }
    base_rf = RandomForestRegressor(random_state=random_state)
    search = RandomizedSearchCV(
        base_rf,
        param_distributions=param_dist,
        n_iter=10,
        cv=3,
        random_state=random_state,
        n_jobs=-1
    )

    if multi_output:
        # Use only first target col for the hyperparam search 
        # (or do a multi-object approach if you prefer).
        first_col = Y_train.columns[0]
        search.fit(X_train, Y_train[first_col].values.ravel())
        best_params = search.best_params_

        # Then train multi-output
        best_rf = RandomForestRegressor(random_state=random_state, **best_params)
        model = MultiOutputRegressor(best_rf)
        model.fit(X_train, Y_train)
    else:
        # Single-output
        search.fit(X_train, Y_train.values.ravel())
        best_params = search.best_params_
        best_rf = RandomForestRegressor(random_state=random_state, **best_params)
        best_rf.fit(X_train, Y_train.values.ravel())
        model = best_rf

    # 5) Evaluate
    Y_pred_train = model.predict(X_train)
    Y_pred_test  = model.predict(X_test)

    # Ensure shape for multi-output
    if not multi_output:
        Y_pred_train = Y_pred_train.reshape(-1, 1)
        Y_pred_test  = Y_pred_test.reshape(-1, 1)

    print("\n[Surrogate Training Summary]")
    print(f"Best Params: {best_params}")

    for i, col_name in enumerate(Y_data.columns):
        r2_train = r2_score(Y_train.iloc[:, i], Y_pred_train[:, i])
        r2_test  = r2_score(Y_test.iloc[:, i],  Y_pred_test[:, i])
        mae_test = mean_absolute_error(Y_test.iloc[:, i], Y_pred_test[:, i])
        print(f"Target='{col_name}': Train R2={r2_train:.3f},  Test R2={r2_test:.3f},  MAE={mae_test:.3f}")

    # 6) Save model & columns
    joblib.dump(model, model_out_path)
    joblib.dump(numeric_cols, columns_out_path)
    print(f"[INFO] Saved surrogate model => {model_out_path}")
    print(f"[INFO] Saved columns => {columns_out_path}")

    return model, numeric_cols


###############################################################################
# 5) LOADING A TRAINED SURROGATE, PREDICTING
###############################################################################

def load_surrogate_and_predict(
    model_path: str,
    columns_path: str,
    sample_features: dict
):
    """
    1) Load trained model + feature columns
    2) Convert sample_features => row DataFrame with the same columns
    3) predict => returns array
    """
    # Load
    model = joblib.load(model_path)
    feature_cols = joblib.load(columns_path)

    # Construct DF
    df_sample = pd.DataFrame([sample_features])
    # Insert missing columns
    for col in feature_cols:
        if col not in df_sample.columns:
            df_sample[col] = 0.0  # or np.nan

    df_sample = df_sample[feature_cols].fillna(0.0)

    # Predict
    y_pred = model.predict(df_sample)
    return y_pred
