# main_calibration.py

import pandas as pd

# Import from your calibration_manager module:
from cali_1.calibration_manager import (
    create_param_specs_from_df,
    random_search,
    ga_optimization,
    bayes_optimization
)

# Suppose you have a function that runs a Surrogate or direct E+ sim:
def evaluate_param_dict(param_dict):
    """
    This is your 'calibration' objective function.
    In practice, you'd do:
      1) Create/modify IDF from param_dict
      2) Run EnergyPlus or call surrogate
      3) Compute difference vs. real data => e.g. CV(RMSE)
      4) Return that scalar (lower is better)
    For demonstration, let's do a dummy function like sphere_obj.
    """
    x = param_dict.get("x", 0)
    y = param_dict.get("y", 0)
    # Suppose we want to minimize (x^2 + y^2)
    return x**2 + y**2


def main():
    # 1) Load or define a DataFrame describing your calibration params
    #    e.g. from "calibration_params.csv" with columns:
    #      param_name, min_value, max_value, is_active, is_integer
    data = {
        "param_name": ["x", "y"],
        "min_value": [-5, -3],
        "max_value": [5, 3],
        "is_active": [True, True],
        "is_integer": [False, False]
    }
    df_params = pd.DataFrame(data)

    # 2) Create param specs
    param_specs = create_param_specs_from_df(df_params, active_only=True)

    # 3) Choose which calibration approach:
    #    (A) random_search
    #    (B) ga_optimization
    #    (C) bayes_optimization
    #    We'll do random_search as an example:
    best_pset, best_score = random_search(param_specs, evaluate_param_dict, n_iterations=50)

    print("[Calibration - Random] Best:", best_pset, "Score:", best_score)

    # 4) If you prefer GA:
    best_pset_ga, best_score_ga = ga_optimization(param_specs, evaluate_param_dict, pop_size=20, max_generations=10)
    print("[Calibration - GA] Best:", best_pset_ga, "Score:", best_score_ga)

    # 5) Or Bayesian:
    best_pset_bayes, best_score_bayes = bayes_optimization(param_specs, evaluate_param_dict, n_calls=30)
    print("[Calibration - Bayesian] Best:", best_pset_bayes, "Score:", best_score_bayes)

    # 6) Optionally, store the best parameter set in CSV or JSON
    # e.g. save "calibrated_params.csv"
    best_params_dict = best_pset_bayes.values
    df_calibrated = pd.DataFrame([best_params_dict])
    df_calibrated.to_csv("calibrated_params.csv", index=False)
    print("[INFO] Saved best Bayesian calibration to calibrated_params.csv")


if __name__ == "__main__":
    main()
