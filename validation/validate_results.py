# validation/validate_results.py
import os
import pandas as pd

from validation.compare_sims_with_measured import load_csv_as_df, align_data_for_variable
from validation.metrics import mean_bias_error, cv_rmse, nmbe
from validation.visualize import (
    plot_time_series_comparison,
    scatter_plot_comparison,
    bar_chart_metrics
)



def validate_data(
    real_data_path, 
    sim_data_path, 
    threshold_cv_rmse=30.0,
    real_bldg_ids=None,     # optional: which building IDs to include from real data
    sim_bldg_ids=None       # optional: which building IDs to include from sim data
):
    """
    Returns a dictionary with validation metrics for each Building/Variable.
    Also generates timeseries and scatter plots for quick visual checks.

    :param real_data_path: path to CSV with real (observed) data
    :param sim_data_path:  path to CSV with sim (model) data
    :param threshold_cv_rmse: float, threshold for pass/fail
    :param real_bldg_ids: list of building IDs to filter from real data
    :param sim_bldg_ids:  list of building IDs to filter from sim data
    """

    df_real, df_sim = load_csv_as_df(real_data_path, sim_data_path)

    # ------------------------------------------------------------
    # (1) Optionally filter by building IDs in real_data
    # ------------------------------------------------------------
    if real_bldg_ids is not None:
        df_real = df_real[df_real['BuildingID'].isin(real_bldg_ids)]
        print(f"[DEBUG] Filtered real data to these building IDs: {real_bldg_ids}")

    # ------------------------------------------------------------
    # (2) Optionally filter by building IDs in sim_data
    # ------------------------------------------------------------
    if sim_bldg_ids is not None:
        df_sim = df_sim[df_sim['BuildingID'].isin(sim_bldg_ids)]
        print(f"[DEBUG] Filtered sim data to these building IDs: {sim_bldg_ids}")

    # Now proceed with your existing approach:
    unique_buildings = df_real['BuildingID'].unique()
    unique_vars      = df_real['VariableName'].unique()

    results = {}
    for b_id in unique_buildings:
        for var_name in unique_vars:
            print(f"\n--- Checking building={b_id}, var={var_name} ---")

            sim_vals, obs_vals, merged_df = align_data_for_variable(
                df_real, df_sim, 
                building_id=b_id, 
                variable_name=var_name
            )
            if len(sim_vals) == 0 or len(obs_vals) == 0:
                print(f"  => No data to compare. Skipping metrics.")
                continue

            # --- Compute metrics ---
            this_mbe  = mean_bias_error(sim_vals, obs_vals)
            this_cv   = cv_rmse(sim_vals, obs_vals)
            this_nmbe = nmbe(sim_vals, obs_vals)

            pass_fail = False
            if this_cv is not None and not (this_cv is float('nan')):
                pass_fail = (this_cv < threshold_cv_rmse)

            results[(b_id, var_name)] = {
                'MBE': this_mbe,
                'CVRMSE': this_cv,
                'NMBE': this_nmbe,
                'Pass': pass_fail
            }

            # Plot
            plot_time_series_comparison(merged_df, b_id, var_name)
            scatter_plot_comparison(merged_df, b_id, var_name)

    return results


def save_metrics_to_csv(metric_results, output_csv="validation_report.csv"):
    """
    Saves the metric_results dictionary to a CSV file.
    metric_results is in the form:
      {
        (b_id, var_name): {
           'MBE':  float,
           'CVRMSE': float,
           'NMBE': float,
           'Pass': bool
        },
        ...
      }
    """
    rows = []
    for (bldg, var), vals in metric_results.items():
        row = {
            "BuildingID": bldg,
            "VariableName": var,
            "MBE": vals['MBE'],
            "CVRMSE": vals['CVRMSE'],
            "NMBE": vals['NMBE'],
            "Pass": vals['Pass']
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    print(f"[INFO] Validation metrics saved to {output_csv}")


def check_for_calibration(metric_results):
    """
    Examines the metric_results and identifies any BuildingID/Variable that fails the threshold.
    If 'Pass' == False, we could trigger a calibration pipeline.

    In a real scenario, we might feed these to a calibrate_model() function or similar.
    """
    for (bldg, var), vals in metric_results.items():
        if not vals['Pass']:
            # Here is where you'd call your calibration logic, e.g.:
            # calibrate_model(building_id=bldg, variable=var, reason="High CV(RMSE)")
            print(f"[CALIBRATION] Building={bldg}, Variable={var}: "
                  f"CV(RMSE)={vals['CVRMSE']:.2f}% > threshold => Trigger calibration steps...")
            # (Placeholder) possibly log or store in DB, then re-run pipeline, etc.
