"""
surrogate_model_main.py

Demonstration of:
  1) Loading parameter data and target data (single scalar or time-series).
  2) Optionally filtering to top N most sensitive parameters (based on prior SALib results).
  3) Training either an AggregateSurrogate (single-output) or TimeSeriesSurrogate (multi-output).
  4) Saving and re-loading the trained model for future usage.

Dependencies:
    pip install numpy pandas scikit-learn joblib
"""

import os
import numpy as np
import pandas as pd
from typing import List

# For saving/loading the model
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor

class AggregateSurrogate:
    """
    A simple class that:
      1. Accepts training data in X (param sets) and y (scalar target).
      2. Trains a single-output regression model (RandomForest by default).
      3. Predicts the scalar output for new param sets.
    """
    def __init__(self, model=None):
        if model is None:
            # default model
            self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        else:
            self.model = model
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        self.model.fit(X, y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        return self.model.predict(X)


class TimeSeriesSurrogate:
    """
    A class that predicts multiple outputs for each param set.
    For example, predicting a 24-hour load profile or 8760-hour annual load.

    By default, uses a RandomForestRegressor wrapped in sklearn's MultiOutputRegressor.
    That ensures the model can handle multi-output arrays (Y shape: (n_samples, n_times)).
    """
    def __init__(self, model=None):
        if model is None:
            base_model = RandomForestRegressor(n_estimators=50, random_state=42)
            self.model = MultiOutputRegressor(base_model)
        else:
            self.model = model
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, Y: pd.DataFrame):
        self.model.fit(X, Y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        return self.model.predict(X)


def load_data_for_surrogate(
    param_csv: str,
    target_csv: str,
    top_params_csv: str = None,
    top_n: int = None,
    multi_output: bool = False
) -> (pd.DataFrame, pd.DataFrame):
    """
    Reads 'param_csv' which should contain columns for parameter features
    (one column per parameter). Also reads 'target_csv' for the outputs.

    If 'top_params_csv' is provided, we read it to get a list of the top
    N parameter names (e.g. from a SALib sensitivity analysis).
    Then we filter param_csv to those columns only.

    :param param_csv: Path to CSV with shape (n_samples, n_params).
                     Each row is one sample's parameter values.
    :param target_csv: Path to CSV with shape (n_samples, ?).
                     If multi_output=False => single column with scalar target.
                     If multi_output=True  => multiple columns for time-series or multi-target.
    :param top_params_csv: Optional path to a CSV with columns: [param_name, some_sensitivity_metric]
    :param top_n: If provided, we keep only the top N param_names based on that metric.
    :param multi_output: If True, we assume target_csv has multiple columns => multi-output.
    :return: (df_X, df_Y)
    """
    # 1) Read parameter data
    df_X = pd.read_csv(param_csv)
    # e.g. columns: "infiltration_base", "occupant_density", "wall_u_value", etc.

    # 2) If we have a CSV of top parameters, filter
    if top_params_csv and top_n:
        df_top = pd.read_csv(top_params_csv)
        # Suppose df_top has columns: param_name, mu_star (or S1), etc.
        # We'll sort by the sensitivity metric descending
        # and keep the top N param_names
        df_top_sorted = df_top.sort_values(by="mu_star", ascending=False)
        top_params = df_top_sorted["param_name"].head(top_n).tolist()

        # Now keep only those columns in df_X that are in top_params
        existing_cols = [c for c in df_X.columns if c in top_params]
        df_X = df_X[existing_cols]
        print(f"[INFO] Filtered parameter columns to top {len(existing_cols)} from {top_params_csv}.")
    else:
        print("[INFO] Using all parameter columns from param_csv; no top-parameter filter applied.")

    # 3) Read target data
    df_Y = pd.read_csv(target_csv)

    # Ensure shapes align: same number of rows, etc.
    if len(df_X) != len(df_Y):
        raise ValueError(f"Mismatch in row counts: df_X={len(df_X)}, df_Y={len(df_Y)}")

    return df_X, df_Y


def save_model(model, filename: str):
    """
    Saves the fitted surrogate model to a .pkl file using joblib.
    :param model: An instance of AggregateSurrogate or TimeSeriesSurrogate
    :param filename: output path
    """
    joblib.dump(model, filename)
    print(f"[INFO] Model saved to {filename}")


def load_model(filename: str):
    """
    Loads a previously saved surrogate model.
    """
    print(f"[INFO] Loading model from {filename}")
    model = joblib.load(filename)
    return model


def run_demo():
    """
    Runs two demonstration examples:
      - Example 1: Single scalar target
      - Example 2: Multi-output (time-series) target
    """
    print("=== Example 1: Single Scalar Surrogate ===")
    np.random.seed(42)
    n_samples = 40
    param_names = ["paramA", "paramB", "paramC", "paramD"]
    df_param_demo = pd.DataFrame(np.random.rand(n_samples, 4), columns=param_names)
    # Let's define a random scalar target => "energy"
    target_vals = (1000
                   + 300 * df_param_demo["paramA"]
                   + 200 * df_param_demo["paramB"]
                   + 50  * df_param_demo["paramC"]
                   + 10  * df_param_demo["paramD"]
                   + np.random.randn(n_samples) * 10)
    df_target_demo = pd.DataFrame({"energy": target_vals})

    # Save them to CSV (mock)
    df_param_demo.to_csv("demo_params_single.csv", index=False)
    df_target_demo.to_csv("demo_target_single.csv", index=False)

    # Load them with the load_data_for_surrogate function
    df_X_single, df_Y_single = load_data_for_surrogate(
        param_csv="demo_params_single.csv",
        target_csv="demo_target_single.csv"
    )

    # Now we train a single-output surrogate
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        df_X_single, df_Y_single, test_size=0.2, random_state=42
    )

    y_train_np = y_train.values.ravel()
    y_test_np  = y_test.values.ravel()

    agg_model = AggregateSurrogate()
    agg_model.fit(X_train, y_train_np)

    preds = agg_model.predict(X_test)
    mse = np.mean((preds - y_test_np)**2)
    print(f"[SingleOutput] Test MSE: {mse:.2f}")

    # Save the model
    save_model(agg_model, "my_single_output_model.pkl")

    print("\n=== Example 2: Multi-Output Time-Series Surrogate ===")
    param_names_2 = ["param1", "param2", "param3"]
    n_hours = 24
    n_samples_2 = 30

    df_param2 = pd.DataFrame(np.random.rand(n_samples_2, 3), columns=param_names_2)

    # Create a synthetic time-series: shape (n_samples, 24)
    Y_data_2 = []
    for i in range(n_samples_2):
        p1 = df_param2.loc[i, "param1"]
        p2 = df_param2.loc[i, "param2"]
        p3 = df_param2.loc[i, "param3"]
        amplitude = 5 + 10 * p1
        offset    = 20 + 5 * p2
        freqShift = 0.5 + p3
        profile_i = [
            offset + amplitude * np.sin((h * np.pi) / (12 * freqShift))
            for h in range(n_hours)
        ]
        Y_data_2.append(profile_i)

    df_target2 = pd.DataFrame(Y_data_2, columns=[f"H{i}" for i in range(n_hours)])

    df_param2.to_csv("demo_params_multi.csv", index=False)
    df_target2.to_csv("demo_target_multi.csv", index=False)

    # Load them
    df_X_multi, df_Y_multi = load_data_for_surrogate(
        param_csv="demo_params_multi.csv",
        target_csv="demo_target_multi.csv",
        multi_output=True
    )

    X_train2, X_test2, Y_train2, Y_test2 = train_test_split(
        df_X_multi, df_Y_multi, test_size=0.2, random_state=42
    )

    ts_model = TimeSeriesSurrogate()
    ts_model.fit(X_train2, Y_train2)

    preds2 = ts_model.predict(X_test2)
    mse2 = np.mean((preds2 - Y_test2.values)**2)
    print(f"[MultiOutput] Test MSE over 24-hour profile: {mse2:.2f}")

    # Save the multi-output model
    save_model(ts_model, "my_multi_output_model.pkl")

    # Example of re-loading the single-output model and predicting
    loaded_agg = load_model("my_single_output_model.pkl")
    new_preds = loaded_agg.predict(X_test.iloc[:2])
    print("[Loaded single-output model] Predictions for first 2 rows:", new_preds)


if __name__ == "__main__":
    # If you run this file directly, it calls run_demo().
    run_demo()
