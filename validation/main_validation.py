# main_validation.py
"""
validation/main_validation.py

This module provides a reusable function `run_validation_process` that:
- Reads user config for validation
- Calls validate_with_ranges(...) from validate_results_custom.py
- Prints and saves a CSV of metrics
- Optionally generates a bar chart (or time-series/scatter) if skip_plots is False

Added Feature:
- Uses config["variables_to_compare"] to restrict which VariableNames to validate.

Dependencies (unchanged):
- validation.compare_sims_with_measured
- validation.metrics
- validation.validate_results_custom (must be updated to accept `variables_to_compare`)
- validation.visualize
"""

import csv
import matplotlib.pyplot as plt

from validation.validate_results_custom import validate_with_ranges

def run_validation_process(config):
    """
    Runs a validation process based on a user config dict.

    Example config structure:
    {
        "real_data_csv": "path/to/real_data.csv",
        "sim_data_csv":  "path/to/sim_data.csv",
        "bldg_ranges":   { "0": [0, 1, 2], "1": [1] },
        "variables_to_compare": [
            "Electricity:Facility [J](Hourly)",
            "Heating:EnergyTransfer [J](Hourly)"
        ],
        "threshold_cv_rmse": 30.0,
        "skip_plots": false,
        "output_csv": "validation_report.csv"
    }
    """

    # 1) Extract config values
    real_data_csv     = config.get("real_data_csv", "")
    sim_data_csv      = config.get("sim_data_csv", "")
    bldg_ranges       = config.get("bldg_ranges", {})
    threshold_cv_rmse = config.get("threshold_cv_rmse", 30.0)
    skip_plots        = config.get("skip_plots", False)
    output_csv        = config.get("output_csv", "validation_report.csv")

    # NEW: A list of variable names to compare
    variables_to_compare = config.get("variables_to_compare", [])

    print(f"[INFO] Starting validation with:")
    print(f"   Real data CSV = {real_data_csv}")
    print(f"   Sim  data CSV = {sim_data_csv}")
    print(f"   Building Ranges = {bldg_ranges}")
    print(f"   Variables to Compare = {variables_to_compare}")
    print(f"   Threshold CV(RMSE) = {threshold_cv_rmse}")
    print(f"   skip_plots = {skip_plots}")
    print(f"   output_csv = {output_csv}")

    # 2) Call validate_with_ranges
    metric_results = validate_with_ranges(
        real_data_path=real_data_csv,
        sim_data_path=sim_data_csv,
        bldg_ranges=bldg_ranges,
        variables_to_compare=variables_to_compare,   # pass in the new argument
        threshold_cv_rmse=threshold_cv_rmse,
        skip_plots=skip_plots
    )

    # 3) Print summary to console
    print("\n=== Validation Summary ===")
    for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
        print(
            f"Real={real_bldg}, Sim={sim_bldg}, Var={var_name} => "
            f"MBE={mvals['MBE']:.2f}, "
            f"CV(RMSE)={mvals['CVRMSE']:.2f}, "
            f"NMBE={mvals['NMBE']:.2f}, "
            f"Pass={mvals['Pass']}"
        )

    # 4) Save metrics to CSV
    print(f"\n[INFO] Saving metrics to {output_csv}")
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["RealBldg", "SimBldg", "VariableName", "MBE", "CVRMSE", "NMBE", "Pass"])
        for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
            writer.writerow([
                real_bldg,
                sim_bldg,
                var_name,
                f"{mvals['MBE']:.2f}",
                f"{mvals['CVRMSE']:.2f}",
                f"{mvals['NMBE']:.2f}",
                mvals['Pass']
            ])

    # 5) Check for calibration triggers if CV(RMSE) fails
    print("\n=== Checking for Calibration Needs ===")
    for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
        if not mvals['Pass']:
            print(
                f"[CALIBRATION] RealBldg={real_bldg}, SimBldg={sim_bldg}, Var={var_name}: "
                f"CV(RMSE)={mvals['CVRMSE']:.2f}% > threshold => Trigger calibration steps..."
            )

    # 6) Optional bar chart: CV(RMSE) for each (RealBldg, SimBldg, Var)
    #    We'll define an inline function here or import from visualize.
    bar_chart_metrics_for_triple(metric_results, title="CV(RMSE) Validation (Per Real vs. Sim)")

def bar_chart_metrics_for_triple(metric_dict, title="Validation Metrics"):
    """
    Create a bar chart of CV(RMSE) for each (RealBldg, SimBldg, Var).
    Bars are green if pass, red if fail.
    """
    if not metric_dict:
        print("[DEBUG] No metrics to plot - metric_dict is empty.")
        return

    labels = []
    cvrmse_values = []
    pass_status = []

    for (real_bldg, sim_bldg, var_name), mvals in metric_dict.items():
        label = f"R{real_bldg}-S{sim_bldg}-{var_name}"
        labels.append(label)
        cvrmse_values.append(mvals['CVRMSE'])
        pass_status.append(mvals['Pass'])

    x = range(len(labels))

    plt.figure(figsize=(12, 6))
    bars = plt.bar(x, cvrmse_values, alpha=0.7)

    for i, bar in enumerate(bars):
        bar.set_color('green' if pass_status[i] else 'red')

    plt.xticks(list(x), labels, rotation=45, ha='right')
    plt.ylabel("CV(RMSE) (%)")
    plt.title(title)
    if cvrmse_values:
        plt.ylim(0, max(cvrmse_values)*1.1)
    plt.tight_layout()
    plt.show()
