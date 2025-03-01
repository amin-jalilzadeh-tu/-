"""
validation/main_validation.py

This module provides a reusable function `run_validation_process` that
- Reads user config for validation
- Calls validate_with_ranges(...) from validate_results_custom.py
- Prints and saves a CSV of metrics
- Optionally generates a bar chart (or time-series/scatter) if skip_plots is False

Dependencies (unchanged):
- validation.compare_sims_with_measured
- validation.metrics
- validation.validate_results_custom
- validation.visualize
"""

import csv
import matplotlib.pyplot as plt

from validation.validate_results_custom import validate_with_ranges

def run_validation_process(config):
    """
    Runs a validation process based on a user config dict.

    Example config keys:
    {
        "real_data_csv": "...",
        "sim_data_csv": "...",
        "bldg_ranges": {0: range(0, 5)},
        "threshold_cv_rmse": 30.0,
        "skip_plots": True,          # or False
        "output_csv": "validation_report.csv"
    }
    """

    real_data_csv   = config.get("real_data_csv", "")
    sim_data_csv    = config.get("sim_data_csv", "")
    bldg_ranges     = config.get("bldg_ranges", {})
    threshold_cv_rmse = config.get("threshold_cv_rmse", 30.0)
    skip_plots      = config.get("skip_plots", False)
    output_csv      = config.get("output_csv", "validation_report.csv")

    print(f"[INFO] Starting validation with real_data_csv={real_data_csv}, sim_data_csv={sim_data_csv}")
    print(f"[INFO] Building Ranges: {bldg_ranges}, Threshold CV(RMSE)={threshold_cv_rmse}, skip_plots={skip_plots}")

    # 1) Call validate_with_ranges
    metric_results = validate_with_ranges(
        real_data_path=real_data_csv,
        sim_data_path=sim_data_csv,
        bldg_ranges=bldg_ranges,
        threshold_cv_rmse=threshold_cv_rmse,
        skip_plots=skip_plots
    )

    # 2) Print summary
    print("\n=== Validation Summary ===")
    for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
        print(f"Real={real_bldg}, Sim={sim_bldg}, Var={var_name} => "
              f"MBE={mvals['MBE']:.2f}, CV(RMSE)={mvals['CVRMSE']:.2f}, "
              f"NMBE={mvals['NMBE']:.2f}, Pass={mvals['Pass']}")

    # 3) Save metrics to CSV
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

    # 4) Check for calibration triggers
    print("\n=== Checking for Calibration Needs ===")
    for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
        if not mvals['Pass']:
            print(f"[CALIBRATION] RealBldg={real_bldg}, SimBldg={sim_bldg}, Var={var_name}: "
                  f"CV(RMSE)={mvals['CVRMSE']:.2f}% > threshold => Trigger calibration steps...")

    # 5) Optional bar chart (requires a helper function)
    #    We'll define an inline function here, or you could import from visualize.py
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
