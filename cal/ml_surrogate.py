# calibration\ml_surrogate.py
import pandas as pd
import random

class SurrogateCalibrator:
    def __init__(self, df_params: pd.DataFrame, measured_data_csv: str):
        self.df_params = df_params
        self.measured_data_csv = measured_data_csv
        self.model = None
        self.best_params = None

    def build_surrogate(self):
        """
        1. Possibly sample N param sets, run sims => store X, y
        2. Train an ML model => self.model
        """
        # pseudo-code:
        # X, y = gather_training_data()
        # self.model = RandomForestRegressor(...)
        # self.model.fit(X, y)
        pass

    def optimize(self):
        """
        Use model predictions to guide a search for best param set.
        """
        # e.g. random approach:
        best_cv = float("inf")
        best_params = None
        for i in range(50):
            param_set = sample_param_set(self.df_params)
            cv_est = self.model.predict([list(param_set.values())])[0]
            if cv_est < best_cv:
                best_cv = cv_est
                best_params = param_set

        self.best_params = best_params


def sample_param_set(df_params: pd.DataFrame):
    out = {}
    for _, row in df_params.iterrows():
        pname = row["param_name"]
        mn = row["min_value"]
        mx = row["max_value"]
        val= row["assigned_value"]
        if pd.notnull(mn) and pd.notnull(mx):
            out[pname] = random.uniform(mn, mx)
        else:
            out[pname] = val
    return out
