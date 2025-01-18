"""
surrogate_model.py

FULL CODE EXAMPLE: Surrogate Model Building with 
 - scenario-based parameters (from multiple CSVs),
 - EnergyPlus results (merged_daily_mean_mocked.csv),
 - Hyperparameter tuning (RandomizedSearchCV),
 - Feature list saving & re-loading,
 - Handling of fillna + infer_objects to avoid FutureWarning,
 - Potential improvement in test R^2 by tuning parameters or collecting more data.
"""

import os
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import r2_score, mean_absolute_error


# ---------------------------------------------------------------------
# 1) LOADING AND AGGREGATION UTILITIES
# ---------------------------------------------------------------------

def load_scenario_file(filepath):
    """
    Loads a single scenario CSV with columns like:
      [scenario_index, ogc_fid, param_name, assigned_value].
    """
    return pd.read_csv(filepath)


def combine_scenarios(scenarios_dict):
    """
    Merges scenario DataFrames from multiple subsystems (dhw, hvac, fenez, etc.)
    into one combined DataFrame, then pivots param_name -> columns.

    Returns a pivot_df with columns like:
    [scenario_index, ogc_fid, param1, param2, ...].
    """
    all_scenarios = []
    for scenario_name, df_scenario in scenarios_dict.items():
        df_temp = df_scenario.copy()
        df_temp["scenario_type"] = scenario_name  # optional
        all_scenarios.append(df_temp)

    combined = pd.concat(all_scenarios, ignore_index=True)

    # Pivot param_name -> columns
    pivot_df = combined.pivot_table(
        index=["scenario_index", "ogc_fid"],
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()

    return pivot_df


def filter_top_parameters(full_param_df, top_params_list):
    """
    OPTIONAL: If you only want to keep the top parameters from sensitivity,
    plus scenario_index and ogc_fid. Otherwise, skip this step.
    """
    keep_cols = ["scenario_index", "ogc_fid"] + top_params_list
    exist_cols = [c for c in keep_cols if c in full_param_df.columns]
    return full_param_df[exist_cols].copy()


def load_sim_results(results_csv):
    """
    Load the merged E+ results file, e.g. 'merged_daily_mean_mocked.csv'.
    Columns typically: [BuildingID, VariableName, 01-Jan, 02-Jan, 03-Jan, ...].
    """
    return pd.read_csv(results_csv)


def aggregate_results(df_sim):
    """
    Convert wide daily columns to a single numeric measure (sum across days),
    returning a DataFrame with [BuildingID, VariableName, TotalEnergy_J].
    """
    melted = df_sim.melt(
        id_vars=["BuildingID", "VariableName"],
        var_name="Day",
        value_name="Value"
    )
    # sum across days
    agg_df = (
        melted.groupby(["BuildingID", "VariableName"])["Value"]
        .sum()
        .reset_index()
        .rename(columns={"Value": "TotalEnergy_J"})
    )
    return agg_df


def merge_params_with_results(pivot_df, df_agg, target_variable=None):
    """
    - rename pivot_df's 'scenario_index' to 'BuildingID' for merging
    - merge with df_agg on BuildingID
    - (optionally) filter rows to target_variable
    """
    merged = pivot_df.copy()
    merged.rename(columns={"scenario_index": "BuildingID"}, inplace=True)

    # Join param data with aggregated simulation results
    merged = pd.merge(
        merged,
        df_agg,
        on="BuildingID",
        how="inner"  # or 'left' if you want all param rows
    )

    if target_variable is not None:
        merged = merged[merged["VariableName"] == target_variable].copy()

    return merged


# ---------------------------------------------------------------------
# 2) MODEL BUILDING & PREDICTION
# ---------------------------------------------------------------------

def build_and_save_surrogate(
    df_data,
    target_col="TotalEnergy_J",
    model_out_path="surrogate_model.joblib",
    columns_out_path="surrogate_model_columns.joblib",
    test_size=0.3,
    random_state=42
):
    """
    Train a RandomForest with hyperparameter search. Then save:
      - The model (model_out_path)
      - The list of columns used for training (columns_out_path)
    """
    # Step A: Exclude rows missing target
    df_data = df_data.dropna(subset=[target_col])

    # Step B: Exclude ID columns or any that are definitely not features
    excluded_cols = ["BuildingID", "ogc_fid", "VariableName", "scenario_type", target_col]

    # potential feature set
    candidate_cols = [c for c in df_data.columns if c not in excluded_cols]

    # Keep only numeric columns
    numeric_cols = []
    for c in candidate_cols:
        if pd.api.types.is_numeric_dtype(df_data[c]):
            numeric_cols.append(c)

    # Prepare X, y
    X = df_data[numeric_cols].copy()
    y = df_data[target_col].copy()

    # Drop rows that have NaNs in X
    mask = ~X.isna().any(axis=1)
    X = X[mask]
    y = y[mask]

    if len(X) < 5:
        print("[ERROR] Not enough data to train a surrogate (fewer than 5 rows).")
        return None, None

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Step C: Hyperparameter Tuning with RandomizedSearchCV
    param_distributions = {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20, 40],
        'max_features': ['auto', 'sqrt', 0.5],
    }
    base_rf = RandomForestRegressor(random_state=random_state)

    search = RandomizedSearchCV(
        base_rf,
        param_distributions,
        n_iter=10,
        cv=3,
        random_state=random_state,
        n_jobs=-1  # use all cores
    )
    search.fit(X_train, y_train)
    rf = search.best_estimator_

    # Evaluate performance
    y_pred_train = rf.predict(X_train)
    y_pred_test = rf.predict(X_test)

    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)

    print("\n=== Surrogate Model Performance ===")
    print(f"Best Hyperparams: {search.best_params_}")
    print(f"Train R^2: {r2_train:.3f}")
    print(f"Test  R^2: {r2_test:.3f}")
    print(f"Test  MAE: {mae_test:.3f}")

    # Save the model
    joblib.dump(rf, model_out_path)
    print(f"[INFO] Surrogate model saved to: {model_out_path}")

    # Save the list of numeric columns used at training
    joblib.dump(numeric_cols, columns_out_path)
    print(f"[INFO] Model columns saved to: {columns_out_path}")

    return rf, numeric_cols


def load_and_predict_sample(
    model_path,
    columns_path,
    sample_series
):
    """
    Re-load the RandomForest + the feature column list. 
    Build a 1-row DataFrame from sample_series, ensuring we have the same columns in the same order.
    Fill missing columns with 0.0, then .infer_objects() to avoid the future warning.
    Predict and return result.
    """
    # Load model
    rf = joblib.load(model_path)
    # Load columns
    trained_columns = joblib.load(columns_path)

    # Convert sample_series -> DataFrame(1 row)
    sample_df = sample_series.to_frame().T

    # Guarantee that all 'trained_columns' are present
    for col in trained_columns:
        if col not in sample_df.columns:
            sample_df[col] = np.nan

    # Drop columns not in trained_columns
    sample_df = sample_df[trained_columns]

    # Fill missing numeric fields
    sample_df = sample_df.fillna(0.0)

    # Convert object dtypes to numeric if possible, to avoid future warnings
    sample_df = sample_df.infer_objects(copy=False)

    # Predict
    y_pred = rf.predict(sample_df)
    return y_pred


# ---------------------------------------------------------------------
# 3) MAIN SCRIPT: GATHER, TRAIN, SAVE, DEMO
# ---------------------------------------------------------------------

def main():
    """
    Full pipeline demonstration:
    1) Load scenario CSVs (dhw, hvac, etc.)
    2) Combine -> param pivot
    3) Load sim results & sum daily -> df_agg
    4) Merge param pivot w/ results for a chosen variable => merged_df
    5) build_and_save_surrogate => random forest
    6) load_and_predict_sample => single-sample prediction
    """
    # A) Load scenario CSVs
    scenarios_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    scenario_files = {
        "dhw":   "scenario_params_dhw.csv",
        "elec":  "scenario_params_elec.csv",
        "fenez": "scenario_params_fenez.csv",
        "hvac":  "scenario_params_hvac.csv",
        "vent":  "scenario_params_vent.csv",
    }

    scenarios_dict = {}
    for name, fname in scenario_files.items():
        fpath = os.path.join(scenarios_folder, fname)
        if os.path.exists(fpath):
            df_scenario = load_scenario_file(fpath)
            scenarios_dict[name] = df_scenario
        else:
            print(f"[WARN] Missing scenario file: {fpath}")

    # Combine into pivot
    pivot_df = combine_scenarios(scenarios_dict)

    # (OPTIONAL) If you want only top parameters from sensitivity:
    # top_params_list = ["infiltration_base", "occupant_density_m2_per_person", "heating_day_setpoint"]
    # pivot_df = filter_top_parameters(pivot_df, top_params_list)

    # B) Load & aggregate sim results
    results_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"
    df_sim = load_sim_results(results_csv)
    df_agg = aggregate_results(df_sim)

    # C) Merge param pivot with results for a chosen variable (Heating, e.g.)
    target_variable = "Heating:EnergyTransfer [J](Hourly)"
    merged_df = merge_params_with_results(pivot_df, df_agg, target_variable=target_variable)

    # We'll rename 'TotalEnergy_J' -> 'target' for clarity
    merged_df.rename(columns={"TotalEnergy_J": "target"}, inplace=True)

    # D) Build & Save Surrogate 
    model_path = "heating_surrogate_model.joblib"
    columns_path = "heating_surrogate_columns.joblib"
    rf_model, col_list = build_and_save_surrogate(
        df_data=merged_df,
        target_col="target",
        model_out_path=model_path,
        columns_out_path=columns_path,
        test_size=0.3,  # 30% test
        random_state=42
    )
    if rf_model is None:
        print("[ERROR] Surrogate model training unsuccessful.")
        return

    # E) Demo: Re-load & predict a single row
    if not merged_df.empty:
        sample_row = merged_df.iloc[0].copy()  # pick 1 row from the DF
        y_pred_sample = load_and_predict_sample(
            model_path,
            columns_path,
            sample_row
        )
        print(f"\n[SAMPLE PREDICTION] Heating Energy = {y_pred_sample[0]:.2f} J (approx)")
    else:
        print("[WARN] Merged DataFrame is empty - no row to sample for prediction.")


# Keep the following if you want to run this directly:
if __name__ == "__main__":
    main()
