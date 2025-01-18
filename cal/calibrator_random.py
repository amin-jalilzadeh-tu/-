# calibration/calibrator_random.py

import random
import pandas as pd

def random_calibration(df_params: pd.DataFrame,
                       max_iterations=10,
                       threshold_cv_rmse=30.0):
    """
    1. Randomly sample param sets from their min/max.
    2. Run simulation + validation, track best CV(RMSE).
    3. Return best solution.
    """
    best_cv = float('inf')
    best_solution = None

    for i in range(max_iterations):
        # 1) Generate a random param set
        param_set = {}
        for _, row in df_params.iterrows():
            param_name = row["param_name"]
            mn = row["min_value"]
            mx = row["max_value"]
            val = row["assigned_value"]

            # If min/max exist, sample between them; else use assigned_value
            if pd.notnull(mn) and pd.notnull(mx):
                param_set[param_name] = random.uniform(mn, mx)
            else:
                param_set[param_name] = val

        # 2) Create IDF, run sim, do validation -> get CV(RMSE)
        cvrmse = run_sim_and_validate(param_set)  # A function you define

        # 3) Check if better
        if cvrmse < best_cv:
            best_cv = cvrmse
            best_solution = param_set

        # 4) Early stopping if we pass threshold
        if best_cv < threshold_cv_rmse:
            print(f"[INFO] Early stopping: Found CV(RMSE)={best_cv:.2f} < {threshold_cv_rmse}")
            break

    print("[INFO] Best CV(RMSE) found:", best_cv)
    return best_solution


def run_sim_and_validate(param_set):
    """
    This function should:
      1. Write param_set to a new IDF (via generation scripts).
      2. Run E+ simulation.
      3. Run validate_data(...) => returns a metric, e.g. CV(RMSE).
    For brevity, we just return a random float.
    """
    # Pseudocode:
    # create_idfs(param_set)
    # run_simulation(...)
    # metrics = validate_data(real_data_csv, sim_data_csv)
    # cvrmse = ...
    return random.uniform(10,50)  # mock
