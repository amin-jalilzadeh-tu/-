# validation/validate_results_custom.py - Updated with ValidationConfig support

import pandas as pd
import numpy as np
import logging

from validation.compare_sims_with_measured import align_data_for_variable
from validation.metrics import mean_bias_error, cv_rmse, nmbe, analyze_peaks, analyze_ramp_rates
from validation.visualize import (
    plot_time_series_comparison,
    scatter_plot_comparison,
    plot_diurnal_profile,
    plot_ramp_rate_distribution,
)
from validation.validation_config import ValidationConfig
from validation.data_alignment import DataAligner

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def get_season(dt):
    """
    Determines the meteorological season for a given datetime object.
    Assumes Northern Hemisphere seasons.
    """
    month = dt.month
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else: # 9, 10, 11
        return "Autumn"


def validate_with_ranges(
    real_data_path,
    sim_data_path,
    bldg_ranges,
    variables_to_compare=None,
    threshold_cv_rmse=30.0,
    skip_plots=False,
    analysis_options=None,
    validation_config=None  # NEW parameter
):
    """
    Compare real vs sim data with advanced, configurable time-based analysis.
    Now includes support for unit conversion and variable mapping via ValidationConfig.
    """
    if variables_to_compare is None:
        variables_to_compare = []
    if analysis_options is None:
        analysis_options = {}
    
    # Create validation config if not provided
    if validation_config is None:
        validation_config = ValidationConfig()
    
    # Create data aligner for unit conversions
    aligner = DataAligner(validation_config)
    
    # 1) Load the main CSVs
    logging.info("Loading real and simulated data CSVs.")
    try:
        df_real = pd.read_csv(real_data_path, encoding=validation_config.config['real_data']['encoding'])
        df_sim = pd.read_csv(sim_data_path, encoding=validation_config.config['real_data']['encoding'])
        logging.info("Data loaded successfully.")
    except FileNotFoundError as e:
        logging.error(f"Could not load data files: {e}")
        return {}
    
    # 2) Clean up column names and apply variable mappings
    df_real["VariableName"] = df_real["VariableName"].astype(str).str.strip()
    df_sim["VariableName"] = df_sim["VariableName"].astype(str).str.strip()
    
    # Apply variable name mappings from config
    df_real = aligner.standardize_variable_names(df_real)
    df_sim = aligner.standardize_variable_names(df_sim)
    
    results = {}
    missing_in_real, missing_in_sim = [], []
    
    # 3) Iterate over building mappings and variables
    for real_bldg_str, sim_bldg_list in bldg_ranges.items():
        try:
            real_bldg = int(real_bldg_str)
        except ValueError:
            logging.warning(f"Could not convert real building '{real_bldg_str}' to int; skipping.")
            continue
        
        logging.info(f"Processing Real Building ID: {real_bldg}")
        df_real_bldg = df_real[df_real["BuildingID"] == real_bldg]
        if df_real_bldg.empty:
            logging.warning(f"No real data found for building {real_bldg}. Skipping.")
            continue
        
        for sb in sim_bldg_list:
            try:
                sim_bldg = int(sb)
            except ValueError:
                logging.warning(f"Could not convert sim building '{sb}' to int; skipping.")
                continue
            
            logging.info(f"  -> Comparing with Sim Building ID: {sim_bldg}")
            df_sim_bldg = df_sim[df_sim["BuildingID"] == sim_bldg]
            if df_sim_bldg.empty:
                logging.warning(f"No sim data found for building {sim_bldg}. Skipping.")
                continue
            
            for var_name in variables_to_compare:
                logging.info(f"    -> Processing Variable: {var_name}")
                
                # Apply unit conversion if needed
                real_unit = aligner.extract_units(var_name) or validation_config.config['units'].get(
                    aligner.detect_variable_type(var_name), 'J'
                )
                sim_unit = 'J' if 'energy' in var_name.lower() else 'W'
                
                # Check if conversion needed
                if real_unit != sim_unit:
                    logging.info(f"      Unit conversion needed: {real_unit} -> {sim_unit}")
                    df_real_bldg_copy = df_real_bldg.copy()
                    df_real_bldg_copy = aligner.apply_unit_conversion(
                        df_real_bldg_copy, var_name, real_unit, sim_unit
                    )
                else:
                    df_real_bldg_copy = df_real_bldg
                
                # 4) Align the primary variable data
                sim_vals, obs_vals, merged_df = align_data_for_variable(
                    df_real_bldg_copy, df_sim_bldg, real_bldg, sim_bldg, var_name
                )
                if merged_df.empty:
                    logging.warning(f"      No overlapping dates found for this combination. Skipping variable.")
                    continue
                
                logging.info(f"      Found {len(merged_df)} overlapping data points.")
                
                # Check for extreme value ratios that suggest unit issues
                if len(sim_vals) > 0 and len(obs_vals) > 0:
                    value_ratio = np.mean(sim_vals) / np.mean(obs_vals) if np.mean(obs_vals) != 0 else 0
                    if value_ratio > 100 or value_ratio < 0.01:
                        logging.warning(
                            f"      UNIT WARNING: Sim/Real ratio = {value_ratio:.2f}. "
                            f"Real mean = {np.mean(obs_vals):.2f}, Sim mean = {np.mean(sim_vals):.2f}"
                        )
                
                # 5) CRITICAL: Convert 'Date' column to datetime objects
                date_formats = validation_config.get_date_formats()
                
                parsed_successfully = False
                # Try parsing with specified formats
                for fmt in date_formats:
                    try:
                        merged_df['Timestamp'] = pd.to_datetime(merged_df['Date'], format=fmt)
                        parsed_successfully = True
                        logging.info(f"      Successfully parsed dates using format: {fmt}")
                        break 
                    except (ValueError, TypeError):
                        continue
                
                # If no specified format worked, try pandas' automatic inference
                if not parsed_successfully:
                    try:
                        merged_df['Timestamp'] = pd.to_datetime(merged_df['Date'])
                        parsed_successfully = True
                        logging.info("      Successfully parsed dates using pandas' automatic date inference.")
                    except Exception as e:
                        logging.error(
                            f"      Could not parse dates for '{var_name}'. "
                            f"Skipping time-based analysis. Error: {e}"
                        )
                        continue
                
                # --- 6) Time-based Analysis Starts Here ---
                data_slices = {"annual": merged_df}
                logging.info("      Generating analysis time slices...")
                
                # 6a) Granularity Analysis (Monthly/Seasonal)
                if "monthly" in analysis_options.get("granularity", []):
                    for month_name, group in merged_df.groupby(merged_df['Timestamp'].dt.strftime('%B')):
                        data_slices[month_name] = group
                if "seasonal" in analysis_options.get("granularity", []):
                    merged_df['Season'] = merged_df['Timestamp'].apply(get_season)
                    for season_name, group in merged_df.groupby('Season'):
                        data_slices[season_name] = group
                
                # 6b) Weekday/Weekend Analysis
                if analysis_options.get("weekday_weekend"):
                    merged_df['DayType'] = np.where(
                        merged_df['Timestamp'].dt.dayofweek < 5, 'Weekday', 'Weekend'
                    )
                    for day_type, group in merged_df.groupby('DayType'):
                        data_slices[day_type] = group
                
                # 6c) Extreme Day Analysis
                extreme_day_opts = analysis_options.get("extreme_day_analysis", {})
                if extreme_day_opts.get("perform"):
                    logging.info("        Performing extreme day analysis...")
                    weather_var = extreme_day_opts.get("weather_variable")
                    n_days = extreme_day_opts.get("n_days", 5)
                    # Align weather data (from the real dataset)
                    _, weather_vals, weather_df = align_data_for_variable(
                        df_real_bldg_copy, df_real_bldg_copy, real_bldg, real_bldg, weather_var
                    )
                    if not weather_df.empty:
                        weather_parsed_successfully = False
                        for fmt in date_formats:
                            try:
                                weather_df['Timestamp'] = pd.to_datetime(weather_df['Date'], format=fmt)
                                weather_parsed_successfully = True
                                break
                            except (ValueError, TypeError):
                                continue
                        
                        if not weather_parsed_successfully:
                            try:
                                weather_df['Timestamp'] = pd.to_datetime(weather_df['Date'])
                                weather_parsed_successfully = True
                            except (ValueError, TypeError):
                                pass
                        
                        if weather_parsed_successfully:
                            daily_weather = weather_df.set_index('Timestamp').resample('D')['Value_obs'].mean()
                            
                            hottest_days = daily_weather.nlargest(n_days).index
                            coldest_days = daily_weather.nsmallest(n_days).index
                            
                            data_slices['Hottest_Days'] = merged_df[
                                merged_df['Timestamp'].dt.date.isin(hottest_days.date)
                            ]
                            data_slices['Coldest_Days'] = merged_df[
                                merged_df['Timestamp'].dt.date.isin(coldest_days.date)
                            ]
                            logging.info(f"          Found {len(data_slices['Hottest_Days'])} data points for hottest days.")
                            logging.info(f"          Found {len(data_slices['Coldest_Days'])} data points for coldest days.")
                        else:
                            logging.warning(f"        Could not parse weather data dates. Skipping extreme day analysis.")
                    else:
                        logging.warning(f"        Could not find weather variable '{weather_var}' for extreme day analysis.")
                
                # --- 7) Calculate Standard Metrics for Each Slice ---
                logging.info(f"      Calculating standard metrics for {len(data_slices)} slices...")
                for slice_name, df_slice in data_slices.items():
                    if df_slice.empty or len(df_slice) < 2: 
                        logging.debug(f"        Skipping slice '{slice_name}' due to insufficient data ({len(df_slice)} points).")
                        continue
                    
                    logging.debug(f"        Calculating metrics for slice: '{slice_name}'")
                    sim_slice = df_slice['Value_sim'].values
                    obs_slice = df_slice['Value_obs'].values
                    
                    # Get threshold from config
                    var_threshold = validation_config.get_threshold('cvrmse', var_name)
                    
                    # Store standard metrics
                    key = (real_bldg, sim_bldg, var_name, slice_name)
                    cv_rmse_val = cv_rmse(sim_slice, obs_slice)
                    results[key] = {
                        "MBE": mean_bias_error(sim_slice, obs_slice),
                        "CVRMSE": cv_rmse_val,
                        "NMBE": nmbe(sim_slice, obs_slice),
                        "Pass": (cv_rmse_val if cv_rmse_val is not None else 1e6) < var_threshold
                    }
                
                # --- 8) Perform Specialized Analyses on the Annual Data ---
                annual_key = (real_bldg, sim_bldg, var_name, 'annual')
                logging.info("      Performing specialized analyses on annual data...")
                
                # 8a) Peak Analysis
                peak_opts = analysis_options.get("peak_analysis", {})
                if peak_opts.get("perform"):
                    logging.info("        Performing peak analysis...")
                    results[annual_key]['peak_metrics'] = analyze_peaks(
                        merged_df['Value_obs'].values,
                        merged_df['Value_sim'].values,
                        n_peaks=peak_opts.get("n_peaks", 5)
                    )
                
                # 8b) Ramp Rate Analysis
                if analysis_options.get("ramp_rate_analysis"):
                    logging.info("        Performing ramp rate analysis...")
                    obs_ramps = np.diff(merged_df['Value_obs'].values)
                    sim_ramps = np.diff(merged_df['Value_sim'].values)
                    results[annual_key]['ramp_rate_metrics'] = analyze_ramp_rates(
                        merged_df['Value_obs'].values, merged_df['Value_sim'].values
                    )
                    if not skip_plots:
                        plot_ramp_rate_distribution(obs_ramps, sim_ramps, f"R{real_bldg}-S{sim_bldg}", var_name)
                
                # --- 9) Plotting ---
                if not skip_plots:
                    logging.info("      Generating plots...")
                    label = f"R{real_bldg}-S{sim_bldg}"
                    plot_time_series_comparison(merged_df, label, var_name)
                    scatter_plot_comparison(merged_df, label, var_name)
                    
                    # 9a) Diurnal Profile Plot
                    if analysis_options.get("diurnal_profiles"):
                        logging.info("        Generating diurnal profile plot...")
                        diurnal_df = merged_df.groupby(merged_df['Timestamp'].dt.hour)[['Value_obs', 'Value_sim']].mean()
                        if not diurnal_df.empty:
                            plot_diurnal_profile(diurnal_df.reset_index(), label, var_name)
    
    logging.info("Finished iterating through all building/variable combinations.")
    return results