# validate_results_custom.py

import pandas as pd
from validation.compare_sims_with_measured import load_csv_as_df, align_data_for_variable
from validation.metrics import mean_bias_error, cv_rmse, nmbe
from validation.visualize import (
    plot_time_series_comparison,
    scatter_plot_comparison,
)

def validate_with_ranges(
    real_data_path, 
    sim_data_path, 
    bldg_ranges, 
    threshold_cv_rmse=30.0,
    skip_plots=False
):
    """
    Compare each real building with each sim building in the given range one-by-one,
    computing metrics (MBE, CV(RMSE), NMBE) for each pairing.

    :param skip_plots: If True, do NOT generate any figures (time-series or scatter).
    """
    df_real = pd.read_csv(real_data_path)
    df_sim  = pd.read_csv(sim_data_path)

    # Strip whitespace, if needed, to avoid trailing-space issues
    df_real["VariableName"] = df_real["VariableName"].astype(str).str.strip()
    df_sim["VariableName"]  = df_sim["VariableName"].astype(str).str.strip()

    results = {}

    for real_bldg, sim_bldg_range in bldg_ranges.items():
        # Filter real data for just the real_bldg
        df_real_sub = df_real[df_real["BuildingID"] == real_bldg]
        if df_real_sub.empty:
            print(f"[WARN] No real data for building {real_bldg}")
            continue

        # For each sim building in that range
        for sim_bldg in sim_bldg_range:
            df_sim_sub = df_sim[df_sim["BuildingID"] == sim_bldg]
            if df_sim_sub.empty:
                print(f"[WARN] No sim data for building {sim_bldg}")
                continue

            # For each variable in real data
            for var_name in df_real_sub["VariableName"].unique():
                # Align by passing both real and sim building IDs
                sim_vals, obs_vals, merged_df = align_data_for_variable(
                    df_real_sub, 
                    df_sim_sub,
                    real_bldg,  # real building
                    sim_bldg,   # sim building
                    var_name
                )

                if len(sim_vals) == 0 or len(obs_vals) == 0:
                    continue

                # Compute metrics
                this_mbe = mean_bias_error(sim_vals, obs_vals)
                this_cv  = cv_rmse(sim_vals, obs_vals)
                this_nmbe = nmbe(sim_vals, obs_vals)

                pass_fail = False
                if this_cv is not None and not (this_cv is float('nan')):
                    pass_fail = (this_cv < threshold_cv_rmse)

                # Store metrics in the results dictionary
                results[(real_bldg, sim_bldg, var_name)] = {
                    'MBE': this_mbe,
                    'CVRMSE': this_cv,
                    'NMBE': this_nmbe,
                    'Pass': pass_fail
                }

                # (NEW) Skip plots if requested
                if not skip_plots:
                    label_for_plot = f"{real_bldg}_VS_{sim_bldg}"
                    plot_time_series_comparison(merged_df, label_for_plot, var_name)
                    scatter_plot_comparison(merged_df, label_for_plot, var_name)

    return results
