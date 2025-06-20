"""
main_validation.py - Updated with configuration support
Provides a reusable function `run_validation_process` that uses the new configuration system
"""

import csv
import matplotlib.pyplot as plt
import logging
from collections import defaultdict
import time
from pathlib import Path

# Local imports
from validation.validate_results_custom import validate_with_ranges
from validation.validation_config import ValidationConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def run_validation_process(config):
    """
    Runs a detailed validation process based on a user config dict.
    Now uses the ValidationConfig class for better configuration handling.
    
    Args:
        config: Dictionary with validation configuration or path to config file
    """
    start_time = time.time()
    logger.info("=====================================================")
    logger.info("========== Starting Validation Process ==========")
    logger.info("=====================================================")
    
    # Create ValidationConfig instance
    if isinstance(config, str):
        # Config is a file path
        validation_config = ValidationConfig(config_path=config)
        config_dict = validation_config.to_dict()
    elif isinstance(config, dict):
        # Config is a dictionary
        validation_config = ValidationConfig(config_dict=config)
        config_dict = config
    else:
        raise ValueError("Config must be a dictionary or path to JSON file")
    
    # Extract config values
    real_data_csv = config_dict.get("real_data_csv", "")
    sim_data_csv = config_dict.get("sim_data_csv", "")
    bldg_ranges = config_dict.get("bldg_ranges", {})
    threshold_cv_rmse = config_dict.get("threshold_cv_rmse", 30.0)
    skip_plots = config_dict.get("skip_plots", False)
    output_csv = config_dict.get("output_csv", "validation_report.csv")
    
    # Get thresholds from new config system
    thresholds = validation_config.config.get("thresholds", {})
    threshold_cv_rmse = thresholds.get("cvrmse", threshold_cv_rmse)
    
    # Extract analysis options
    analysis_options = config_dict.get("analysis_options", {})
    
    logger.info("Configuration loaded:")
    logger.info(f"  Real data CSV      = {real_data_csv}")
    logger.info(f"  Sim data CSV       = {sim_data_csv}")
    logger.info(f"  Building Ranges    = {bldg_ranges}")
    logger.info(f"  Variables to Compare = {config_dict.get('variables_to_compare')}")
    logger.info(f"  Threshold CV(RMSE) = {threshold_cv_rmse}%")
    logger.info(f"  Analysis Options   = {analysis_options}")
    
    # Check for unit specifications
    units_config = validation_config.config.get("units", {})
    if units_config:
        logger.info(f"  Unit Configuration = {units_config}")
    
    # Check for variable mappings
    var_mappings = validation_config.config.get("variable_mappings", {})
    if var_mappings:
        logger.info(f"  Variable Mappings  = {var_mappings}")
    
    # Call the core validation function
    logger.info("Starting core validation logic...")
    metric_results = validate_with_ranges(
        real_data_path=real_data_csv,
        sim_data_path=sim_data_csv,
        bldg_ranges=bldg_ranges,
        variables_to_compare=config_dict.get("variables_to_compare", []),
        threshold_cv_rmse=threshold_cv_rmse,
        skip_plots=skip_plots,
        analysis_options=analysis_options,
        validation_config=validation_config  # Pass the config object
    )
    logger.info("Core validation logic finished.")
    
    if not metric_results:
        logger.warning("Validation process returned no results. Ending.")
        return
    
    # Print detailed summary to console
    print("\n\n=== Detailed Validation Summary ===")
    
    # Check for unit conversion warnings
    unit_warnings = []
    
    for (real_bldg, sim_bldg, var_name, slice_name), mvals in sorted(metric_results.items()):
        pass_status = mvals.get('Pass', 'N/A')
        cvrmse = mvals.get('CVRMSE')
        nmbe = mvals.get('NMBE')
        
        # Format metrics for printing
        cvrmse_str = f"{cvrmse:.2f}" if cvrmse is not None else "N/A"
        nmbe_str = f"{nmbe:.2f}" if nmbe is not None else "N/A"
        
        # Check for potential unit issues
        if cvrmse is not None and cvrmse > 1000:
            unit_warnings.append((real_bldg, sim_bldg, var_name, cvrmse))
        
        print(
            f"  - ID: R{real_bldg}-S{sim_bldg} | Var: {var_name:<35} | Slice: {slice_name:<15} => "
            f"CV(RMSE)={cvrmse_str:<7}, NMBE={nmbe_str:<7}, Pass={pass_status}"
        )
    
    # Report unit warnings
    if unit_warnings:
        print("\n\n=== UNIT CONVERSION WARNINGS ===")
        print("The following validations show extremely high CV(RMSE) values, suggesting unit mismatches:")
        for real_bldg, sim_bldg, var_name, cvrmse in unit_warnings:
            print(f"  - R{real_bldg}-S{sim_bldg}, {var_name}: CV(RMSE)={cvrmse:.0f}%")
        print("\nCheck your unit configuration in the validation config file.")
    
    # Save all metrics to CSV
    logger.info("Saving detailed metrics report...")
    save_detailed_metrics_to_csv(metric_results, output_csv, validation_config)
    logger.info(f"Metrics report saved to '{output_csv}'")
    
    # Check for calibration triggers
    print("\n\n=== Checking for Calibration Needs (based on Annual metrics) ===")
    calibration_needed = False
    
    for (real_bldg, sim_bldg, var_name, slice_name), mvals in metric_results.items():
        if slice_name == 'annual' and not mvals.get('Pass', True):
            calibration_needed = True
            cvrmse = mvals.get('CVRMSE')
            cvrmse_str = f"{cvrmse:.2f}%" if cvrmse is not None else "N/A"
            
            # Get variable-specific threshold
            var_threshold = validation_config.get_threshold('cvrmse', var_name)
            
            logger.warning(
                f"[CALIBRATION] R{real_bldg}-S{sim_bldg}, Var='{var_name}': "
                f"Annual CV(RMSE)={cvrmse_str} > threshold ({var_threshold}%) => Trigger calibration steps."
            )
    
    if not calibration_needed:
        logger.info("No calibration triggers found based on annual CV(RMSE) metrics.")
    
    # Generate summary bar chart
    if not skip_plots:
        logger.info("Generating summary bar chart for annual metrics...")
        annual_metrics = {k: v for k, v in metric_results.items() if k[3] == 'annual'}
        bar_chart_metrics_for_triple(
            annual_metrics,
            title="CV(RMSE) Validation Summary (Annual Metrics)",
            threshold=threshold_cv_rmse
        )
        logger.info("Bar chart generated.")
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info("===================================================")
    logger.info(f"========== Validation Process Finished ==========")
    logger.info(f"Total Execution Time: {duration:.2f} seconds")
    logger.info("===================================================")


def save_detailed_metrics_to_csv(metric_results, output_csv, validation_config):
    """Saves the hierarchical metric results to a flattened CSV file with config info."""
    
    base_headers = ["RealBldg", "SimBldg", "VariableName", "AnalysisSlice"]
    stat_headers = ["MBE", "CVRMSE", "NMBE", "Pass", "Threshold_CVRMSE", "Threshold_NMBE"]
    peak_headers = ["peak_avg_obs_val", "peak_avg_sim_val", "peak_avg_magnitude_diff_pct"]
    ramp_headers = ["ramp_rate_obs_mean_abs", "ramp_rate_sim_mean_abs", 
                   "ramp_rate_obs_max_abs", "ramp_rate_sim_max_abs"]
    
    # Add unit info headers
    unit_headers = ["Real_Units", "Sim_Units", "Unit_Conversion_Applied"]
    
    full_header = base_headers + stat_headers + peak_headers + ramp_headers + unit_headers
    
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
            for header in ["MBE", "CVRMSE", "NMBE", "Pass"]:
                row[header] = mvals.get(header)
            
            # Add thresholds
            row["Threshold_CVRMSE"] = validation_config.get_threshold('cvrmse', var_name)
            row["Threshold_NMBE"] = validation_config.get_threshold('nmbe', var_name)
            
            # Add specialized metrics if they exist
            peak_metrics = mvals.get('peak_metrics', {})
            for header in peak_headers:
                row[header] = peak_metrics.get(header)
            
            ramp_metrics = mvals.get('ramp_rate_metrics', {})
            for header in ramp_headers:
                row[header] = ramp_metrics.get(header)
            
            # Add unit information
            units_config = validation_config.config.get("units", {})
            var_type = validation_config.aligner.detect_variable_type(var_name)
            row["Real_Units"] = units_config.get(var_type, "Unknown")
            row["Sim_Units"] = "J" if var_type == "energy" else "W" if var_type == "power" else "C"
            row["Unit_Conversion_Applied"] = row["Real_Units"] != row["Sim_Units"]
            
            # Write the ordered row
            writer.writerow([
                f"{row.get(h, ''):.4f}" if isinstance(row.get(h), (int, float)) 
                else row.get(h, '') 
                for h in full_header
            ])


def bar_chart_metrics_for_triple(metric_dict, title="Validation Metrics", threshold=30.0):
    """
    Create a bar chart of CV(RMSE) for each (RealBldg, SimBldg, Var) tuple.
    Bars are green if pass, red if fail. Includes a threshold line.
    """
    if not metric_dict:
        logger.info("No 'annual' metrics to plot in summary bar chart.")
        return
    
    labels = []
    cvrmse_values = []
    pass_status = []
    
    for (r, s, v, _), m in metric_dict.items():
        # Create shorter labels
        var_short = v.split(' ')[0].split(':')[-1]  # Get last part of variable name
        labels.append(f"R{r}-S{s}\n{var_short}")
        cvrmse_values.append(m.get('CVRMSE', 0))
        pass_status.append(m.get('Pass', False))
    
    x = range(len(labels))
    
    plt.figure(figsize=(max(12, len(labels) * 0.8), 7))
    bars = plt.bar(x, cvrmse_values, alpha=0.8, width=0.6)
    
    for i, bar in enumerate(bars):
        bar.set_color('mediumseagreen' if pass_status[i] else 'salmon')
        yval = bar.get_height()
        
        # Add value labels on bars
        if yval > 1000:  # Likely unit issue
            label_text = f'{yval:.0f}\n(Unit?)'
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, 
                    label_text, ha='center', va='bottom', color='red', fontweight='bold')
        else:
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, 
                    f'{yval:.1f}', ha='center', va='bottom')
    
    # Add threshold line
    plt.axhline(y=threshold, color='crimson', linestyle='--', linewidth=2, 
                label=f'Threshold ({threshold}%)')
    
    plt.xticks(list(x), labels, rotation=45, ha='right')
    plt.ylabel("CV(RMSE) (%)")
    plt.title(title)
    
    # Set y-axis limit
    if cvrmse_values:
        max_val = max(cvrmse_values)
        if max_val > 1000:
            plt.ylim(0, min(max_val * 1.1, 5000))  # Cap at 5000% for readability
            plt.text(0.02, 0.98, "Note: Very high values may indicate unit mismatches", 
                    transform=plt.gca().transAxes, verticalalignment='top', 
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
        else:
            plt.ylim(0, max(max_val * 1.2, threshold * 1.2))
    
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.show()