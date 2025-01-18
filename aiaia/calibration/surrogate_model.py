"""
surrogate_model.py

Provides two example surrogate modeling classes:

1. AggregateSurrogate: For predicting a single scalar target (e.g. total energy, error metric).
2. TimeSeriesSurrogate: For predicting multi-output/time-series data (e.g. 24-hour or 8760-hour profile).

Dependencies:
    pip install numpy pandas scikit-learn
"""

import numpy as np
import pandas as pd
from typing import Optional, Union

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split


# ------------------------------------------------------------------------------
#  A) Surrogate for Single Scalar (e.g. aggregated energy or an error metric)
# ------------------------------------------------------------------------------
class AggregateSurrogate:
    """
    A simple class that:
      1. Accepts training data in X (param sets) and y (scalar target).
      2. Trains a single-output regression model (RandomForest by default).
      3. Predicts the scalar output for new param sets.
    """

    def __init__(self, model=None):
        """
        :param model: An optional sklearn regressor. Defaults to RandomForestRegressor.
        """
        if model is None:
            # default model
            self.model = RandomForestRegressor(
                n_estimators=50,
                random_state=42
            )
        else:
            self.model = model

        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: Union[pd.Series, np.ndarray]):
        """
        Train the surrogate on existing data.

        :param X: DataFrame (or array) of shape (n_samples, n_params),
                  representing your parameter sets.
        :param y: Array-like of shape (n_samples,),
                  representing the scalar target (e.g. total energy or CV(RMSE)).
        """
        self.model.fit(X, y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict the scalar target for new param sets.

        :param X: DataFrame (or array) of shape (m_samples, n_params)
        :return: numpy array of shape (m_samples,)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        return self.model.predict(X)


# ------------------------------------------------------------------------------
#  B) Surrogate for Multi-Output / Time-Series
# ------------------------------------------------------------------------------
class TimeSeriesSurrogate:
    """
    A class that predicts multiple outputs for each param set.
    For example, predicting a 24-hour load profile or 8760-hour annual load.

    By default, uses a RandomForestRegressor wrapped in sklearn's MultiOutputRegressor.
    That ensures the model can handle multi-output arrays (Y shape: (n_samples, n_times)).
    """

    def __init__(self, model=None):
        """
        :param model: An optional sklearn regressor. Defaults to RandomForestRegressor,
                      but wrapped in MultiOutputRegressor for multi-output predictions.
        """
        if model is None:
            # default underlying model
            base_model = RandomForestRegressor(
                n_estimators=50,
                random_state=42
            )
            self.model = MultiOutputRegressor(base_model)
        else:
            # If user passes an already multi-output capable model (e.g. RFRegressor that handles multi-output),
            # you might not need MultiOutputRegressor. 
            self.model = model

        self.is_fitted = False

    def fit(self, X: pd.DataFrame, Y: pd.DataFrame):
        """
        Train the surrogate on existing multi-output data.

        :param X: DataFrame/array of shape (n_samples, n_params)
        :param Y: DataFrame/array of shape (n_samples, n_outputs)
                  e.g. for a 24-hour profile, n_outputs = 24
        """
        self.model.fit(X, Y)
        self.is_fitted = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict the multi-output/time-series data for new param sets.

        :param X: DataFrame/array of shape (m_samples, n_params)
        :return: numpy array of shape (m_samples, n_outputs)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        return self.model.predict(X)


# ------------------------------------------------------------------------------
#  C) Example Usage / Testing
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # -------------------
    # 1) Example: Single Scalar Surrogate
    # -------------------
    print("=== Testing AggregateSurrogate with synthetic data ===")
    # Let's say we have 2 parameters (like infiltration, occupant_density),
    # and one target scalar (e.g., total annual energy).
    rng = np.random.RandomState(42)
    n_samples = 50
    X_data = rng.rand(n_samples, 2)  # param1 in col0, param2 in col1
    y_data = 1000 + 300 * X_data[:, 0] + 500 * X_data[:, 1] + rng.randn(n_samples) * 5

    X_train, X_test, y_train, y_test = train_test_split(
        X_data, y_data, test_size=0.2, random_state=42
    )

    agg_model = AggregateSurrogate()
    agg_model.fit(X_train, y_train)

    preds = agg_model.predict(X_test)
    mse = np.mean((preds - y_test) ** 2)
    print(f"[Aggregate] Test MSE: {mse:.2f}")

    # -------------------
    # 2) Example: Time-Series Surrogate
    # -------------------
    print("\n=== Testing TimeSeriesSurrogate with synthetic 24-hour data ===")
    # Suppose each sample has 2 parameters, and we want to predict
    # a 24-hour load profile => Y shape is (n_samples, 24).

    n_samples = 50
    n_hours = 24
    X_data_2 = rng.rand(n_samples, 2)  # e.g. infiltration, occupant_density
    # synthetic time-series: e.g. daily load profile depends linearly on these 2 params
    Y_data_2 = []
    for i in range(n_samples):
        # create a "profile" of length 24
        # param 0 influences amplitude, param 1 influences offset
        amplitude = 10 + 5 * X_data_2[i, 0]
        offset = 20 + 10 * X_data_2[i, 1]
        # for hour in 0..23, let's do load = offset + amplitude*sin(hour * pi/12)
        profile = [
            offset + amplitude * np.sin((h * np.pi) / 12) for h in range(n_hours)
        ]
        Y_data_2.append(profile)

    Y_data_2 = np.array(Y_data_2)  # shape (50, 24)

    X_train2, X_test2, Y_train2, Y_test2 = train_test_split(
        X_data_2, Y_data_2, test_size=0.2, random_state=42
    )

    ts_model = TimeSeriesSurrogate()
    ts_model.fit(X_train2, Y_train2)

    preds2 = ts_model.predict(X_test2)  # shape (10, 24)
    mse2 = np.mean((preds2 - Y_test2) ** 2)
    print(f"[TimeSeries] Test MSE (24-hour profile): {mse2:.2f}")
