#!/usr/bin/env python3
# train_surrogate.py

"""
Example script to build and save a surrogate model 
based on scenario parameters and a numeric target (e.g., mismatch or total energy).

Requirements:
  pip install pandas numpy scikit-learn joblib
"""

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import joblib

###############################################################################
# 1) Load scenario parameters
###############################################################################

def load_scenario_parameter_csvs(scenario_dir: str) -> pd.DataFrame:
    """
    Same logic as before: read scenario_params_* CSVs, combine.
    Expect columns: [scenario_index, ogc_fid, param_name, assigned_value].
    """
    dfs = []
    for fname in os.listdir(scenario_dir):
        if fname.startswith("scenario_params_") and fname.endswith(".csv"):
            fpath = os.path.join(scenario_dir, fname)
            df_temp = pd.read_csv(fpath)
            # Minimal check
            req_cols = {"scenario_index", "param_name", "assigned_value"}
            if not req_cols.issubset(df_temp.columns):
                continue
            dfs.append(df_temp)
    if not dfs:
        raise FileNotFoundError("No scenario_params_*.csv found.")
    df_merged = pd.concat(dfs, ignore_index=True)
    return df_merged


def pivot_scenario_params(df_params: pd.DataFrame) -> pd.DataFrame:
    """
    pivot => one row per scenario_index, columns=param_name, values=assigned_value
    """
    df_pivot = df_params.pivot_table(
        index="scenario_index",
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()
    df_pivot.columns.name = None
    return df_pivot


###############################################################################
# 2) Load or define the target (mismatch or consumption)
###############################################################################

def load_scenario_targets(target_csv: str) -> pd.DataFrame:
    """
    Suppose we have a CSV that has at least:
       scenario_index, mismatch_value
    If you have a different column name, adjust accordingly.
    """
    df = pd.read_csv(target_csv)
    # E.g. columns = ["scenario_index", "mismatch_value"]
    if "scenario_index" not in df.columns:
        raise ValueError("target_csv must have 'scenario_index' column.")
    if "mismatch_value" not in df.columns:
        raise ValueError("target_csv must have 'mismatch_value' column.")
    return df


###############################################################################
# 3) Merge parameters + target
###############################################################################

def merge_params_and_target(df_params: pd.DataFrame, df_target: pd.DataFrame) -> pd.DataFrame:
    """
    Join on 'scenario_index' so each scenario row has param columns + target column.
    """
    df_merged = pd.merge(df_params, df_target, on="scenario_index", how="inner")
    return df_merged


###############################################################################
# 4) Choose which columns to keep (all or top sensitive)
###############################################################################

def select_parameter_columns(df: pd.DataFrame,
                            top_sensitive: list = None) -> pd.DataFrame:
    """
    If top_sensitive is None => use all param columns except scenario_index + mismatch_value.
    Otherwise, only keep the columns in top_sensitive.
    Return the sub-DataFrame.
    """
    # We'll exclude scenario_index, mismatch_value from the input features
    exclude = {"scenario_index", "mismatch_value"}

    # Figure out param cols
    all_cols = set(df.columns)
    param_cols = [c for c in all_cols if c not in exclude]

    # If a top-sensitive param list is given, keep only those intersection
    if top_sensitive is not None:
        param_cols = [p for p in param_cols if p in top_sensitive]

    # We want a stable column order, so let's sort
    param_cols = sorted(param_cols)

    return df[list(param_cols)]  # reindex

###############################################################################
# 5) Train a surrogate model
###############################################################################

def train_surrogate_model(X: pd.DataFrame, y: pd.Series) -> RandomForestRegressor:
    """
    Example: a random forest regressor. 
    You can replace with other models (XGBRegressor, MLPRegressor, etc.).
    """
    # Some default hyperparams
    rf = RandomForestRegressor(
        n_estimators=50,
        max_depth=10,
        random_state=42
    )
    rf.fit(X, y)
    return rf

###############################################################################
# 6) Evaluate & Save the model
###############################################################################

def evaluate_model(model, X_test, y_test):
    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)
    mse = mean_squared_error(y_test, preds)
    rmse = np.sqrt(mse)
    return r2, rmse


def save_model(model, output_path: str):
    joblib.dump(model, output_path)
    print(f"[INFO] Saved model to {output_path}")


###############################################################################
# 7) MAIN
###############################################################################

def main():
    scenario_dir = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    target_csv = r"D:\Documents\E_Plus_2030_py\output\results\scenario_mismatch_values.csv"
    model_output_path = "surrogate_rf_model.joblib"

    # 1) Load param data
    df_params_long = load_scenario_parameter_csvs(scenario_dir)
    df_params_pivot = pivot_scenario_params(df_params_long)
    print("[INFO] scenario param pivot shape:", df_params_pivot.shape)
    print(df_params_pivot.head(3))

    # 2) Load target (mismatch or total consumption)
    df_target = load_scenario_targets(target_csv)
    print("[INFO] target shape:", df_target.shape)
    print(df_target.head(3))

    # 3) Merge
    df_merged = merge_params_and_target(df_params_pivot, df_target)
    print("[INFO] merged shape:", df_merged.shape)
    print(df_merged.head(3))

    # 4) Choose param columns
    # Option A: Use all
    # Option B: Use top few from sensitivity, e.g. ["infiltration_base", "occupant_density", "u_value_wall"]
    top_sensitive = None  # or ["infiltration_base", "occupant_density_m2_per_person"]
    X = select_parameter_columns(df_merged, top_sensitive=top_sensitive)

    # 5) The target is mismatch_value
    y = df_merged["mismatch_value"]

    # 6) Train/test split for evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    # 7) Train
    model = train_surrogate_model(X_train, y_train)

    # 8) Evaluate
    r2, rmse = evaluate_model(model, X_test, y_test)
    print(f"[DEBUG] Surrogate performance on test: R^2={r2:.3f}, RMSE={rmse:.3f}")

    # 9) Save the model
    save_model(model, model_output_path)


if __name__ == "__main__":
    main()
