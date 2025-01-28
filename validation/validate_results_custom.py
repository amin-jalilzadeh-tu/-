# validation/validate_results_custom.py

import pandas as pd

from validation.compare_sims_with_measured import align_data_for_variable
from validation.metrics import mean_bias_error, cv_rmse, nmbe
from validation.visualize import (
    plot_time_series_comparison,
    scatter_plot_comparison,
)

def validate_with_ranges(
    real_data_path,
    sim_data_path,
    bldg_ranges,
    variables_to_compare=None,
    threshold_cv_rmse=30.0,
    skip_plots=False
):
    """
    Compare real vs sim data for specified building mappings and variable names.

    :param real_data_path: Path to the CSV file with real data
    :param sim_data_path: Path to the CSV file with sim data
    :param bldg_ranges: dict mapping real_bldg (string) -> list of sim_bldgs. 
                       e.g. {"0": [0, 1, 2]}, or {"4136730": ["4136730"]}
    :param variables_to_compare: list of variable names (strings) to be validated.
    :param threshold_cv_rmse: pass/fail threshold for CV(RMSE) in percent
    :param skip_plots: if True, disable time-series and scatter plots
    :return: a dict of metrics keyed by (real_bldg, sim_bldg, variable_name)
    """

    if variables_to_compare is None:
        # If none provided, default to empty => no variables will be compared
        variables_to_compare = []

    # 1) Load the CSVs
    df_real = pd.read_csv(real_data_path)
    df_sim  = pd.read_csv(sim_data_path)

    # 2) Clean up any trailing whitespace in VariableName
    df_real["VariableName"] = df_real["VariableName"].astype(str).str.strip()
    df_sim["VariableName"]  = df_sim["VariableName"].astype(str).str.strip()

    # 3) Initialize a results dictionary
    results = {}

    # 4) Keep track of missing variables for debug
    missing_in_real = []
    missing_in_sim  = []

    # 5) Iterate over building mappings
    for real_bldg_str, sim_bldg_list in bldg_ranges.items():
        # Convert the real building ID from string to int
        # (If your CSV has building IDs as int64, this ensures a match)
        try:
            real_bldg = int(real_bldg_str)
        except ValueError:
            print(f"[WARN] Could not convert real building '{real_bldg_str}' to int; skipping.")
            continue

        # Subset real data for this real_bldg
        df_real_sub = df_real[df_real["BuildingID"] == real_bldg]
        if df_real_sub.empty:
            print(f"[WARN] No real data for building {real_bldg}")
            continue

        for sb in sim_bldg_list:
            # If the sim building is a string, also convert it to int
            try:
                sim_bldg = int(sb)
            except ValueError:
                print(f"[WARN] Could not convert sim building '{sb}' to int; skipping.")
                continue

            # Subset sim data for this sim_bldg
            df_sim_sub = df_sim[df_sim["BuildingID"] == sim_bldg]
            if df_sim_sub.empty:
                print(f"[WARN] No sim data for building {sim_bldg}")
                continue

            # 6) Loop over user-specified variables
            for var_name in variables_to_compare:
                # Check presence in real data
                if var_name not in df_real_sub["VariableName"].unique():
                    missing_in_real.append((real_bldg, var_name))
                    continue

                # Check presence in sim data
                if var_name not in df_sim_sub["VariableName"].unique():
                    missing_in_sim.append((sim_bldg, var_name))
                    continue

                # 7) Align data
                sim_vals, obs_vals, merged_df = align_data_for_variable(
                    df_real_sub,
                    df_sim_sub,
                    real_bldg,
                    sim_bldg,
                    var_name
                )

                # If no overlap or empty arrays, skip
                if len(sim_vals) == 0 or len(obs_vals) == 0:
                    print(f"[WARN] No overlap in dates for RealBldg={real_bldg}, SimBldg={sim_bldg}, Var={var_name}")
                    continue

                # 8) Compute metrics
                this_mbe   = mean_bias_error(sim_vals, obs_vals)
                this_cvrmse = cv_rmse(sim_vals, obs_vals)
                this_nmbe  = nmbe(sim_vals, obs_vals)

                pass_fail = False
                if this_cvrmse is not None and not (this_cvrmse is float('nan')):
                    pass_fail = (this_cvrmse < threshold_cv_rmse)

                # 9) Store results
                results[(real_bldg, sim_bldg, var_name)] = {
                    "MBE":    this_mbe,
                    "CVRMSE": this_cvrmse,
                    "NMBE":   this_nmbe,
                    "Pass":   pass_fail
                }

                # 10) Optionally plot
                if not skip_plots:
                    label_for_plot = f"{real_bldg}_VS_{sim_bldg}"
                    plot_time_series_comparison(merged_df, label_for_plot, var_name)
                    scatter_plot_comparison(merged_df, label_for_plot, var_name)

    # 11) Print missing variable info
    if missing_in_real:
        print("\n[INFO] Variables missing in REAL data for these (Building, Var):")
        unique_missing_real = set(missing_in_real)
        for (bldg, var) in unique_missing_real:
            print(f"   - RealBldg={bldg}, Var={var}")

    if missing_in_sim:
        print("\n[INFO] Variables missing in SIM data for these (Building, Var):")
        unique_missing_sim = set(missing_in_sim)
        for (bldg, var) in unique_missing_sim:
            print(f"   - SimBldg={bldg}, Var={var}")

    # Return the final dictionary of metrics
    return results
