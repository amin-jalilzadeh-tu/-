# main_validation.py
"""
validation/main_validation.py

This module provides a reusable function `run_validation_process` that:
- Reads a user config for validation, including advanced analysis options.
- Calls the core validation logic in `validate_results_custom.py`.
- Prints a detailed summary of metrics for various time slices.
- Saves all standard and specialized metrics to a single, comprehensive CSV report.
- Generates a summary bar chart for the primary 'annual' metrics.
"""

import csv
import matplotlib.pyplot as plt
import logging
from collections import defaultdict
import time  # Added for time tracking

# Local imports
from validation.validate_results_custom import validate_with_ranges

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def run_validation_process(config):
    """
    Runs a detailed validation process based on a user config dict.

    The function now processes a much richer result set, including metrics for
    different time granularities (monthly, seasonal) and specialized analyses
    (peaks, ramp rates).
    """
    start_time = time.time()
    logging.info("=====================================================")
    logging.info("========== Starting Validation Process ==========")
    logging.info("=====================================================")

    # 1) Extract config values
    real_data_csv = config.get("real_data_csv", "")
    sim_data_csv = config.get("sim_data_csv", "")
    bldg_ranges = config.get("bldg_ranges", {})
    threshold_cv_rmse = config.get("threshold_cv_rmse", 30.0)
    skip_plots = config.get("skip_plots", False)
    output_csv = config.get("output_csv", "validation_report.csv")
    
    # NEW: Extract the advanced analysis options
    analysis_options = config.get("analysis_options", {})

    logging.info("Configuration loaded:")
    logging.info(f"  Real data CSV      = {real_data_csv}")
    logging.info(f"  Sim data CSV       = {sim_data_csv}")
    logging.info(f"  Building Ranges    = {bldg_ranges}")
    logging.info(f"  Variables to Compare = {config.get('variables_to_compare')}")
    logging.info(f"  Threshold CV(RMSE) = {threshold_cv_rmse}%")
    logging.info(f"  Analysis Options   = {analysis_options}")

    # 2) Call the core validation function
    logging.info("Starting core validation logic...")
    metric_results = validate_with_ranges(
        real_data_path=real_data_csv,
        sim_data_path=sim_data_csv,
        bldg_ranges=bldg_ranges,
        variables_to_compare=config.get("variables_to_compare", []),
        threshold_cv_rmse=threshold_cv_rmse,
        skip_plots=skip_plots,
        analysis_options=analysis_options  # Pass in the new argument
    )
    logging.info("Core validation logic finished.")

    if not metric_results:
        logging.warning("Validation process returned no results. Ending.")
        return

    # 3) Print detailed summary to console
    print("\n\n=== Detailed Validation Summary ===")
    for (real_bldg, sim_bldg, var_name, slice_name), mvals in sorted(metric_results.items()):
        pass_status = mvals.get('Pass', 'N/A')
        cvrmse = mvals.get('CVRMSE')
        nmbe = mvals.get('NMBE')
        
        # Format metrics for printing, handling potential None values
        cvrmse_str = f"{cvrmse:.2f}" if cvrmse is not None else "N/A"
        nmbe_str = f"{nmbe:.2f}" if nmbe is not None else "N/A"

        print(
            f"  - ID: R{real_bldg}-S{sim_bldg} | Var: {var_name:<35} | Slice: {slice_name:<15} => "
            f"CV(RMSE)={cvrmse_str:<7}, NMBE={nmbe_str:<7}, Pass={pass_status}"
        )

    # 4) Save all metrics to a single, comprehensive CSV
    logging.info("Saving detailed metrics report...")
    save_detailed_metrics_to_csv(metric_results, output_csv)
    logging.info(f"Metrics report saved to '{output_csv}'")

    # 5) Check for calibration triggers based on ANNUAL results
    print("\n\n=== Checking for Calibration Needs (based on Annual metrics) ===")
    calibration_needed = False
    for (real_bldg, sim_bldg, var_name, slice_name), mvals in metric_results.items():
        if slice_name == 'annual' and not mvals.get('Pass', True):
            calibration_needed = True
            cvrmse = mvals.get('CVRMSE')
            cvrmse_str = f"{cvrmse:.2f}%" if cvrmse is not None else "N/A"
            logging.warning(
                f"[CALIBRATION] R{real_bldg}-S{sim_bldg}, Var='{var_name}': "
                f"Annual CV(RMSE)={cvrmse_str} > threshold ({threshold_cv_rmse}%) => Trigger calibration steps."
            )
    if not calibration_needed:
        logging.info("No calibration triggers found based on annual CV(RMSE) metrics.")

    # 6) Generate a summary bar chart for ANNUAL CV(RMSE) results
    if not skip_plots:
        logging.info("Generating summary bar chart for annual metrics...")
        annual_metrics = {k: v for k, v in metric_results.items() if k[3] == 'annual'}
        bar_chart_metrics_for_triple(
            annual_metrics,
            title="CV(RMSE) Validation Summary (Annual Metrics)",
            threshold=threshold_cv_rmse
        )
        logging.info("Bar chart generated.")

    end_time = time.time()
    duration = end_time - start_time
    logging.info("===================================================")
    logging.info(f"========== Validation Process Finished ==========")
    logging.info(f"Total Execution Time: {duration:.2f} seconds")
    logging.info("===================================================")


def save_detailed_metrics_to_csv(metric_results, output_csv):
    """Saves the hierarchical metric results to a flattened CSV file."""
    # This function remains the same but will be called with more logging context.
    
    base_headers = ["RealBldg", "SimBldg", "VariableName", "AnalysisSlice"]
    stat_headers = ["MBE", "CVRMSE", "NMBE", "Pass"]
    peak_headers = ["peak_avg_obs_val", "peak_avg_sim_val", "peak_avg_magnitude_diff_pct"]
    ramp_headers = ["ramp_rate_obs_mean_abs", "ramp_rate_sim_mean_abs", "ramp_rate_obs_max_abs", "ramp_rate_sim_max_abs"]
    
    full_header = base_headers + stat_headers + peak_headers + ramp_headers

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(full_header)

        for (real_bldg, sim_bldg, var_name, slice_name), mvals in sorted(metric_results.items()):
            row = {
                "RealBldg": real_bldg,
                "SimBldg": sim_bldg,
                "VariableName": var_name,
                "AnalysisSlice": slice_name
            }
            # Add standard metrics
            for header in stat_headers:
                row[header] = mvals.get(header)
            
            # Add specialized metrics if they exist for this entry
            peak_metrics = mvals.get('peak_metrics', {})
            for header in peak_headers:
                row[header] = peak_metrics.get(header)

            ramp_metrics = mvals.get('ramp_rate_metrics', {})
            for header in ramp_headers:
                row[header] = ramp_metrics.get(header)

            # Write the ordered row
            writer.writerow([f"{row.get(h, ''):.4f}" if isinstance(row.get(h), (int, float)) else row.get(h, '') for h in full_header])


def bar_chart_metrics_for_triple(metric_dict, title="Validation Metrics", threshold=30.0):
    """
    Create a bar chart of CV(RMSE) for each (RealBldg, SimBldg, Var) tuple.
    Bars are green if pass, red if fail. Includes a threshold line.
    """
    if not metric_dict:
        logging.info("No 'annual' metrics to plot in summary bar chart.")
        return

    labels = [f"R{r}-S{s}\n{v.split(' ')[0]}" for (r, s, v, _), m in metric_dict.items()]
    cvrmse_values = [m.get('CVRMSE', 0) for m in metric_dict.values()]
    pass_status = [m.get('Pass', False) for m in metric_dict.values()]

    x = range(len(labels))

    plt.figure(figsize=(max(12, len(labels) * 0.8), 7))
    bars = plt.bar(x, cvrmse_values, alpha=0.8, width=0.6)

    for i, bar in enumerate(bars):
        bar.set_color('mediumseagreen' if pass_status[i] else 'salmon')
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f'{yval:.1f}', ha='center', va='bottom')

    # Add threshold line
    plt.axhline(y=threshold, color='crimson', linestyle='--', linewidth=2, label=f'Threshold ({threshold}%)')

    plt.xticks(list(x), labels, rotation=45, ha='right')
    plt.ylabel("CV(RMSE) (%)")
    plt.title(title)
    if cvrmse_values:
        plt.ylim(0, max(max(cvrmse_values) * 1.2, threshold * 1.2))
        
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.show()