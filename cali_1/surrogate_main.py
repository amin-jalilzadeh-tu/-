# surrogate_main.py

import os
import re
import joblib
import numpy as np
import pandas as pd
from typing import Optional

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor

# -----------------------------------------------------------------------------
# A) AggregateSurrogate CLASS
#    - Stores the training columns in self.feature_columns
#    - Reorders new X in predict() to match training order
# -----------------------------------------------------------------------------
class AggregateSurrogate:
    """
    Surrogate for predicting a single scalar (e.g. total annual consumption).
    Uses RandomForestRegressor by default.
    """

    def __init__(self, model=None):
        if model is None:
            self.model = RandomForestRegressor(
                n_estimators=50,
                random_state=42
            )
        else:
            self.model = model

        self.is_fitted = False
        self.feature_columns = None  # will store the list of columns used for training

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """
        Train the surrogate on X,y. Also stores X columns for consistent prediction.
        """
        # Make sure X is a DataFrame so we can get column names
        if not isinstance(X, pd.DataFrame):
            raise ValueError("X must be a pandas DataFrame so we can store column names.")

        self.feature_columns = X.columns.tolist()  # store the training columns
        self.model.fit(X, y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict using the trained model. Automatically reorders X columns
        to match the training order.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted yet.")

        if not isinstance(X, pd.DataFrame):
            raise ValueError("X must be a pandas DataFrame.")

        # Check that all training columns exist in new X
        missing_cols = [col for col in self.feature_columns if col not in X.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in new data: {missing_cols}")

        # Also check if X has extra columns that were not in training
        extra_cols = [col for col in X.columns if col not in self.feature_columns]
        if extra_cols:
            print(f"[WARNING] New data has extra columns not seen in training: {extra_cols}")

        # Reorder X to match the training columns exactly
        X_reordered = X[self.feature_columns]

        return self.model.predict(X_reordered)


# (Optional) If you need a multi-output/time-series version
class TimeSeriesSurrogate:
    """
    Surrogate for predicting multiple outputs (e.g. 24-hour, 8760-hour).
    Wraps a RandomForestRegressor in MultiOutputRegressor by default,
    and also tracks feature columns for consistent prediction.
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
            raise ValueError("X must be a pandas DataFrame.")
        self.feature_columns = X.columns.tolist()

        self.model.fit(X, Y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame):
        if not self.is_fitted:
            raise RuntimeError("Model not fitted yet.")
        if not isinstance(X, pd.DataFrame):
            raise ValueError("X must be a pandas DataFrame.")

        missing_cols = [c for c in self.feature_columns if c not in X.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in new data: {missing_cols}")

        extra_cols = [c for c in X.columns if c not in self.feature_columns]
        if extra_cols:
            print(f"[WARNING] Extra columns in new data: {extra_cols}")

        X_reordered = X[self.feature_columns]
        return self.model.predict(X_reordered)


# -----------------------------------------------------------------------------
# B) Loading Scenario CSVs
# -----------------------------------------------------------------------------
def load_scenario_params(scenario_folder: str) -> pd.DataFrame:
    """
    Reads scenario CSV files (dhw, elec, fenez, hvac, vent)
    from `scenario_folder`. Merges them into a single DataFrame.
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
            df["source_file"] = fname
            dfs.append(df)
        else:
            print(f"[WARNING] Not found: {fpath}")

    if not dfs:
        raise FileNotFoundError(f"No scenario CSVs found in {scenario_folder}.")
    merged = pd.concat(dfs, ignore_index=True)
    return merged


# -----------------------------------------------------------------------------
# C) Optionally Filter by Sensitivity
# -----------------------------------------------------------------------------
def filter_top_parameters(all_params_df: pd.DataFrame,
                          sensitivity_csv: str,
                          top_n: int = 5) -> pd.DataFrame:
    """
    Reads a sensitivity CSV, picks the top N parameters, returns filtered scenario data.
    Must have a param column (e.g. 'param_name') and a numeric metric to sort by (like 'mu_star').
    """
    if not os.path.isfile(sensitivity_csv):
        print(f"[INFO] No sensitivity file found: {sensitivity_csv}, skipping filter.")
        return all_params_df

    sens_df = pd.read_csv(sensitivity_csv)

    possible_param_cols = ["param", "param_name", "ParameterName"]
    param_col = None
    for c in possible_param_cols:
        if c in sens_df.columns:
            param_col = c
            break
    if param_col is None:
        raise ValueError(f"No param column found in {sensitivity_csv}. "
                         f"Columns: {sens_df.columns.tolist()}")

    # Decide which metric
    if "mu_star" in sens_df.columns:
        sort_col = "mu_star"
        print("[INFO] Sorting by mu_star (Morris).")
    elif "ST" in sens_df.columns:
        sort_col = "ST"
        print("[INFO] Sorting by ST (Sobol).")
    elif "S1" in sens_df.columns:
        sort_col = "S1"
        print("[INFO] Sorting by S1 (Sobol).")
    else:
        cand = [col for col in sens_df.columns if col != param_col]
        if not cand:
            raise ValueError("No numeric column to sort by in sensitivity CSV.")
        sort_col = cand[0]
        print(f"[WARNING] Fallback sorting by {sort_col}.")

    # Sort, pick top
    sens_df_sorted = sens_df.sort_values(by=sort_col, ascending=False)
    top_params = sens_df_sorted.head(top_n)[param_col].tolist()
    print(f"[INFO] Top {top_n} parameters by {sort_col}: {top_params}")

    # Filter
    filtered = all_params_df[all_params_df["param_name"].isin(top_params)].copy()
    return filtered


# -----------------------------------------------------------------------------
# D) Build (X, y) Summing Daily Columns => 'AnnualTotal'
# -----------------------------------------------------------------------------
def build_training_data(
    all_params_df: pd.DataFrame,
    results_csv: str,
    scenario_index_col: str = "scenario_index",
    date_col_pattern: str = r"^\d{2}/\d{2}$",
    new_target_col: str = "AnnualTotal"
):
    """
    1) pivot scenario => wide form
    2) read results, sum columns matching date_col_pattern => new_target_col
    3) merge => (X,y)
    """
    # pivot
    pivot_df = all_params_df.pivot_table(
        index=scenario_index_col,
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()

    # read results
    if not os.path.isfile(results_csv):
        raise FileNotFoundError(f"Results CSV not found: {results_csv}")
    res_df = pd.read_csv(results_csv)

    # rename if needed
    if "BuildingID" in res_df.columns and scenario_index_col != "BuildingID":
        res_df.rename(columns={"BuildingID": scenario_index_col}, inplace=True)

    # sum daily columns
    pattern = re.compile(date_col_pattern)
    daily_cols = [c for c in res_df.columns if pattern.match(c)]
    if not daily_cols:
        print(f"[WARNING] No daily columns found via pattern={date_col_pattern}")
        # If we don’t have daily cols, we expect new_target_col to already exist
        if new_target_col not in res_df.columns:
            raise ValueError(f"{new_target_col} not found, no daily columns to sum.")
    else:
        # sum them
        res_df[new_target_col] = res_df[daily_cols].sum(axis=1)

    if new_target_col not in res_df.columns:
        raise ValueError(f"{new_target_col} not found in results. "
                         f"Columns: {res_df.columns.tolist()}")

    # merge
    merged = pd.merge(pivot_df, res_df, on=scenario_index_col, how="inner")

    y = merged[new_target_col].values
    param_cols = pivot_df.columns.drop(scenario_index_col).tolist()
    X = merged[[scenario_index_col] + param_cols].copy()

    if scenario_index_col in X.columns:
        X.drop(columns=[scenario_index_col], inplace=True)

    return X, y


# -----------------------------------------------------------------------------
# E) Orchestrator: Train & Save
# -----------------------------------------------------------------------------
def train_aggregate_surrogate(
    scenario_folder: str,
    results_csv: str,
    sensitivity_csv: Optional[str] = None,
    top_n: Optional[int] = None,
    output_model_path: str = "aggregate_surrogate.pkl"
):
    """
    Steps:
      1) load scenario CSV
      2) filter top N if needed
      3) build (X,y) => sum daily columns => AnnualTotal
      4) train AggregateSurrogate
      5) save model
    """
    # 1) load scenario data
    all_params_df = load_scenario_params(scenario_folder)

    # 2) optionally filter
    if sensitivity_csv and top_n is not None:
        all_params_df = filter_top_parameters(all_params_df, sensitivity_csv, top_n)

    # 3) build training data
    X, y = build_training_data(all_params_df, results_csv)
    print(f"[INFO] Training data shape => X: {X.shape}, y: {y.shape}")

    # 4) train
    model = AggregateSurrogate()
    model.fit(X, y)
    print("[INFO] Surrogate training complete.")

    # 5) save
    joblib.dump(model, output_model_path)
    print(f"[INFO] Model saved => {output_model_path}")


# -----------------------------------------------------------------------------
# F) Load Surrogate
# -----------------------------------------------------------------------------
def load_aggregate_surrogate(model_path: str) -> AggregateSurrogate:
    """
    Loads an AggregateSurrogate from the same environment.
    """
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"File not found: {model_path}")

    loaded_obj = joblib.load(model_path)

    # We'll do a gentler check that it has 'predict' and 'fit'
    if not hasattr(loaded_obj, "predict") or not hasattr(loaded_obj, "fit"):
        raise TypeError("Loaded object does not look like a surrogate model (missing predict/fit).")

    # If you want to confirm it's the EXACT class, uncomment:
    # if not isinstance(loaded_obj, AggregateSurrogate):
    #     raise TypeError("Loaded object is not an AggregateSurrogate.")

    return loaded_obj


# -----------------------------------------------------------------------------
# G) Example Main (Optional)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    scenario_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    results_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"

    sensitivity_csv = "morris_sensitivity_results.csv"
    top_n = 5
    output_model_path = "my_aggregate_surrogate.pkl"

    # 1) Train & save
    train_aggregate_surrogate(
        scenario_folder=scenario_folder,
        results_csv=results_csv,
        sensitivity_csv=sensitivity_csv,
        top_n=top_n,
        output_model_path=output_model_path
    )

    # 2) Load the model
    loaded_model = load_aggregate_surrogate(output_model_path)

    # 3) Example new param set in a DataFrame with EXACT same columns as training
    new_params = pd.DataFrame({
        # Must have the same columns as X in the same or any order:
        "exterior_wall_U_value": [0.38],
        "infiltration_base": [1.2],
        "occupant_density_m2_per_person": [28.0],
        "default_heater_capacity_w": [4000.0],
        "ground_floor_window_construction_name": [0]
    })

    # .predict() will reorder columns internally to match training
    pred = loaded_model.predict(new_params)
    print("[INFO] Surrogate prediction =>", pred)
