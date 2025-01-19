"""
unified_surrogate.py

A single module that handles:
  1) Reading scenario parameters (dhw, elec, fenez, hvac, vent).
  2) Pivoting them into a wide form DataFrame of param columns.
  3) Optionally filtering top parameters (from a sensitivity CSV).
  4) Loading E+ results, aggregating daily columns => a numeric target.
  5) Training a Surrogate (RandomForest) for single-output or multi-output.
  6) Saving and re-loading for inference.

Author: Example
"""

import os
import pandas as pd
import numpy as np
import joblib
from typing import Optional, List
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor


# --------------------------------------------------------------------
# 1) Surrogate Classes
# --------------------------------------------------------------------
class AggregateSurrogate:
    """
    Single-output surrogate model. 
    By default, uses RandomForestRegressor. 
    Stores training columns for consistent column order at predict time.
    """

    def __init__(self, model=None):
        if model is None:
            # default model
            self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        else:
            self.model = model
        self.is_fitted = False
        self.feature_columns = None

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """
        Train the surrogate on X,y. We also store X.columns for consistent ordering.
        """
        if not isinstance(X, pd.DataFrame):
            raise ValueError("X must be a DataFrame so we can track column names.")
        self.feature_columns = X.columns.tolist()
        self.model.fit(X, y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict using the trained model. 
        Automatically reorders X's columns to match training order.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted yet.")
        if not isinstance(X, pd.DataFrame):
            raise ValueError("X must be a DataFrame.")

        # Check all training columns exist
        missing_cols = [c for c in self.feature_columns if c not in X.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in new data: {missing_cols}")

        # Possibly extra columns
        extra_cols = [c for c in X.columns if c not in self.feature_columns]
        if extra_cols:
            print(f"[WARNING] Extra columns in new data: {extra_cols}")

        # reorder
        X_ordered = X[self.feature_columns]
        return self.model.predict(X_ordered)


class TimeSeriesSurrogate:
    """
    Multi-output surrogate model, e.g. for 24-hour or 8760-hour profiles.
    Wraps a RandomForestRegressor with MultiOutputRegressor by default.
    Also tracks feature_columns to reorder at predict time.
    """

    def __init__(self, model=None):
        if model is None:
            base = RandomForestRegressor(n_estimators=50, random_state=42)
            self.model = MultiOutputRegressor(base)
        else:
            self.model = model
        self.is_fitted = False
        self.feature_columns = None

    def fit(self, X: pd.DataFrame, Y: pd.DataFrame):
        if not isinstance(X, pd.DataFrame):
            raise ValueError("X must be a DataFrame.")
        if not isinstance(Y, pd.DataFrame):
            raise ValueError("Y must be a DataFrame.")

        self.feature_columns = X.columns.tolist()
        self.model.fit(X, Y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first.")
        missing_cols = [c for c in self.feature_columns if c not in X.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in new data: {missing_cols}")

        extra_cols = [c for c in X.columns if c not in self.feature_columns]
        if extra_cols:
            print(f"[WARNING] Extra columns in new data: {extra_cols}")

        X_ordered = X[self.feature_columns]
        return self.model.predict(X_ordered)


# --------------------------------------------------------------------
# 2) Loading Scenario CSVs
# --------------------------------------------------------------------
def load_scenario_file(filepath: str) -> pd.DataFrame:
    """
    Read one scenario CSV with columns like [scenario_index, ogc_fid, param_name, assigned_value].
    """
    return pd.read_csv(filepath)


def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Reads scenario CSVs from folder: scenario_params_dhw.csv, elec, fenez, hvac, vent
    merges them into one DataFrame with columns [scenario_index, param_name, assigned_value, etc.].
    """
    scenario_files = {
        "dhw":   "scenario_params_dhw.csv",
        "elec":  "scenario_params_elec.csv",
        "fenez": "scenario_params_fenez.csv",
        "hvac":  "scenario_params_hvac.csv",
        "vent":  "scenario_params_vent.csv",
    }
    dfs = []
    for name, fname in scenario_files.items():
        fpath = os.path.join(scenario_folder, fname)
        if os.path.isfile(fpath):
            df_scenario = load_scenario_file(fpath)
            df_scenario["scenario_type"] = name
            dfs.append(df_scenario)
        else:
            print(f"[WARN] Missing scenario file: {fpath}")

    if not dfs:
        raise FileNotFoundError(f"No scenario CSV found in {scenario_folder}.")
    merged = pd.concat(dfs, ignore_index=True)
    return merged


def pivot_scenario_params(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot so each scenario_index => one row, columns=param_name => assigned_value
    Returns a pivoted DataFrame with columns [scenario_index, ogc_fid, param1, param2, ...].
    """
    pivot_df = df.pivot_table(
        index=["scenario_index", "ogc_fid"],
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()
    pivot_df.columns.name = None
    return pivot_df


# --------------------------------------------------------------------
# 3) Optional Filtering by Sensitivity
# --------------------------------------------------------------------
def filter_top_parameters(df_pivot: pd.DataFrame,
                          sensitivity_csv: str,
                          top_n: int,
                          param_col: str = "param",
                          metric_col: str = "mu_star") -> pd.DataFrame:
    """
    Reads a sensitivity CSV with columns like [param, mu_star, sigma, ...].
    Sorts by `metric_col` descending, picks top_n param names,
    and filters df_pivot to those columns + [scenario_index, ogc_fid].
    """
    if not os.path.isfile(sensitivity_csv):
        print(f"[INFO] sensitivity_csv not found: {sensitivity_csv}, skipping filter.")
        return df_pivot

    sens_df = pd.read_csv(sensitivity_csv)
    if param_col not in sens_df.columns:
        raise ValueError(f"Param column '{param_col}' not in sensitivity CSV.")
    if metric_col not in sens_df.columns:
        raise ValueError(f"Metric column '{metric_col}' not in sensitivity CSV.")

    # sort & pick top
    sens_df_sorted = sens_df.sort_values(metric_col, ascending=False)
    top_params = sens_df_sorted[param_col].head(top_n).tolist()

    keep_cols = ["scenario_index", "ogc_fid"] + top_params
    exist_cols = [c for c in keep_cols if c in df_pivot.columns]
    filtered = df_pivot[exist_cols].copy()
    print(f"[INFO] Filtered pivot from {df_pivot.shape} to {filtered.shape} using top {top_n} params.")
    return filtered


# --------------------------------------------------------------------
# 4) Load & Aggregate E+ Results
# --------------------------------------------------------------------
def load_sim_results(results_csv: str) -> pd.DataFrame:
    """
    e.g. 'merged_daily_mean_mocked.csv' with columns:
       [BuildingID, VariableName, 01-Jan, 02-Jan, ...]
    """
    return pd.read_csv(results_csv)


def aggregate_results(df_sim: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wide daily columns to a single numeric measure (sum across days),
    returning a DataFrame with [BuildingID, VariableName, TotalEnergy_J].
    """
    # Melt + group
    id_vars = ["BuildingID", "VariableName"]
    melted = df_sim.melt(id_vars=id_vars, var_name="Day", value_name="Value")
    daily_sum = melted.groupby(["BuildingID", "VariableName"])["Value"].sum().reset_index()
    daily_sum.rename(columns={"Value": "TotalEnergy_J"}, inplace=True)
    return daily_sum


def merge_params_with_results(pivot_df: pd.DataFrame,
                              df_agg: pd.DataFrame,
                              target_variable: Optional[str] = None) -> pd.DataFrame:
    """
    - rename pivot_df's 'scenario_index' -> 'BuildingID' for merging
    - merges with df_agg on 'BuildingID'
    - if target_variable is provided, filter that variable
    - returns a DataFrame with param columns + [BuildingID, VariableName, TotalEnergy_J]
    """
    merged = pivot_df.copy()
    merged.rename(columns={"scenario_index": "BuildingID"}, inplace=True)

    merged = pd.merge(merged, df_agg, on="BuildingID", how="inner")
    if target_variable is not None:
        merged = merged[merged["VariableName"] == target_variable]
    return merged


# --------------------------------------------------------------------
# 5) Surrogate Training & Saving
# --------------------------------------------------------------------
def build_and_save_surrogate(
    df_data: pd.DataFrame,
    target_col: str = "TotalEnergy_J",
    model_out_path: str = "surrogate_model.joblib",
    columns_out_path: str = "surrogate_columns.joblib",
    test_size: float = 0.3,
    random_state: int = 42
):
    """
    Train a RandomForest with hyperparameter search (RandomizedSearchCV).
    Then save:
      - The model
      - The list of columns used
    We exclude 'BuildingID', 'ogc_fid', 'VariableName', 'scenario_type', and target_col from features.
    """
    from sklearn.model_selection import train_test_split, RandomizedSearchCV
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import r2_score, mean_absolute_error

    # A) Exclude any row missing target
    df_data = df_data.dropna(subset=[target_col])

    # B) Identify candidate features
    excluded = ["BuildingID", "ogc_fid", "VariableName", "scenario_type", target_col]
    candidate_cols = [c for c in df_data.columns if c not in excluded]
    # numeric only
    numeric_cols = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df_data[c])]

    X = df_data[numeric_cols].copy()
    y = df_data[target_col].copy()

    # Drop rows with NaN in X
    mask = ~X.isna().any(axis=1)
    X = X[mask]
    y = y[mask]

    if len(X) < 2:
        print("[ERROR] Not enough data to train a surrogate (<10 rows).")
        return None, None

    # Train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # param distributions
    param_distributions = {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20, 40],
        'max_features': ['auto', 'sqrt', 0.5],
    }
    rf = RandomForestRegressor(random_state=random_state)
    search = RandomizedSearchCV(
        rf,
        param_distributions,
        n_iter=10,
        cv=3,
        random_state=random_state,
        n_jobs=-1
    )
    search.fit(X_train, y_train)
    best_rf = search.best_estimator_

    # Evaluate
    y_pred_train = best_rf.predict(X_train)
    y_pred_test = best_rf.predict(X_test)

    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)

    print("\n[Surrogate Training Summary]")
    print(f"Best Params: {search.best_params_}")
    print(f"Train R^2: {r2_train:.3f}")
    print(f"Test  R^2: {r2_test:.3f}")
    print(f"Test  MAE: {mae_test:.3f}")

    # Save model
    joblib.dump(best_rf, model_out_path)
    print(f"[INFO] Surrogate model saved => {model_out_path}")

    # Save the column list
    joblib.dump(numeric_cols, columns_out_path)
    print(f"[INFO] Column list saved => {columns_out_path}")

    return best_rf, numeric_cols


def load_surrogate_and_predict(
    model_path: str,
    columns_path: str,
    sample_dict: dict
):
    """
    Reload a random forest + feature columns. 
    Convert sample_dict -> 1-row DataFrame, reorder columns, fill missing with 0, predict.
    """
    rf = joblib.load(model_path)
    trained_columns = joblib.load(columns_path)

    # Convert sample_dict -> DataFrame(1 row)
    df_sample = pd.DataFrame([sample_dict])

    # Ensure all trained columns exist
    for col in trained_columns:
        if col not in df_sample.columns:
            df_sample[col] = np.nan

    # Drop columns not in trained_columns
    df_sample = df_sample[trained_columns]

    # fillna
    df_sample = df_sample.fillna(0.0)
    df_sample = df_sample.infer_objects()

    y_pred = rf.predict(df_sample)
    return y_pred

