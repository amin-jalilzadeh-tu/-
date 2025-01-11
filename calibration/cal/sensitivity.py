# calibration\sensitivity.py

def run_sensitivity_analysis(df_params, method="sobol"):
    """
    Could do something like:
      1. Sample param sets (Morris or Sobol).
      2. Run sims, measure output variance.
      3. Return top parameters affecting CV(RMSE) or energy usage.
    """
    if method == "sobol":
        print("[INFO] Running Sobol sensitivity (placeholder).")
    elif method == "morris":
        print("[INFO] Running Morris method (placeholder).")
    else:
        print(f"[WARN] Unknown sensitivity method: {method}")

    # Return a list of param_names ranked by importance
    return ["some_top_param","next_param"]
