# main.py

from validation.validate_results_custom import validate_with_ranges
import matplotlib.pyplot as plt
import csv

def main():
    real_data_csv = r"D:\Documents\E_Plus_2030_py\output\results\mock_merged_daily_mean.csv"
    sim_data_csv  = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"

    # Example: Compare real building 0 vs. sim buildings [0..4] individually
    bldg_ranges = {
        0: range(0, 5)
        # If you also want real bldg=1 to compare vs. sim bldgs [0..4], do:
        # 1: range(0, 5)
        # etc.
    }

    print("=== Starting Validation with bldg_ranges ===")
    metric_results = validate_with_ranges(
        real_data_path=real_data_csv,
        sim_data_path=sim_data_csv,
        bldg_ranges=bldg_ranges,
        threshold_cv_rmse=30.0
    )

    # ---------------------------------------------------
    # Print summary for each (RealBldg, SimBldg, Variable)
    # ---------------------------------------------------
    print("\n=== Validation Summary ===")
    for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
        print(f"Real={real_bldg}, Sim={sim_bldg}, Var={var_name} => "
              f"MBE={mvals['MBE']:.2f}, CV(RMSE)={mvals['CVRMSE']:.2f}, "
              f"NMBE={mvals['NMBE']:.2f}, Pass={mvals['Pass']}")

    # ---------------------------------------------------
    # Save metrics to CSV
    #   with columns: RealBldg, SimBldg, VariableName, ...
    # ---------------------------------------------------
    output_csv = "validation_report.csv"
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

    # ---------------------------------------------------
    # Check for calibration
    #   We trigger calibration if Pass=False
    # ---------------------------------------------------
    print("\n=== Checking for Calibration Needs ===")
    for (real_bldg, sim_bldg, var_name), mvals in metric_results.items():
        if not mvals['Pass']:
            print(f"[CALIBRATION] RealBldg={real_bldg}, SimBldg={sim_bldg}, Var={var_name}: "
                  f"CV(RMSE)={mvals['CVRMSE']:.2f}% > threshold => Trigger calibration steps...")

    # ---------------------------------------------------
    # Bar chart of CV(RMSE) for each (Real, Sim, Var)
    # ---------------------------------------------------
    bar_chart_metrics_for_triple(metric_results, title="CV(RMSE) Validation (Per Real vs. Sim)")

def bar_chart_metrics_for_triple(metric_dict, title="Validation Metrics"):
    """
    Create a bar chart of CV(RMSE) where each bar is (RealBldg vs. SimBldg, VarName).
    """
    if not metric_dict:
        print("[DEBUG] No metrics to plot - metric_dict is empty.")
        return

    labels = []
    cvrmse_values = []
    pass_status = []

    for (real_bldg, sim_bldg, var_name), mvals in metric_dict.items():
        # Example label: "R0-S3-Heating"
        label = f"R{real_bldg}-S{sim_bldg}-{var_name}"
        labels.append(label)
        cvrmse_values.append(mvals['CVRMSE'])
        pass_status.append(mvals['Pass'])

    x = range(len(labels))

    plt.figure(figsize=(12, 6))
    bars = plt.bar(x, cvrmse_values, alpha=0.7)

    # Color-code pass/fail
    for i, bar in enumerate(bars):
        bar.set_color('green' if pass_status[i] else 'red')

    plt.xticks(list(x), labels, rotation=45, ha='right')
    plt.ylabel("CV(RMSE) (%)")
    plt.title(title)
    if cvrmse_values:
        plt.ylim(0, max(cvrmse_values) * 1.1)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
