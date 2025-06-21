"""
main cal.py - UPDATED

Example script that demonstrates how to call enhanced sensitivity analysis
functions with time slicing and parameter filtering.
"""

from c_sensitivity.unified_sensitivity import run_sensitivity_analysis


def main():
    scenario_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    
    # Example 1: Basic correlation analysis (unchanged)
    print("\n=== Example 1: Basic Correlation Analysis ===")
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="correlation",
        results_csv=r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv",
        target_variable="Heating:EnergyTransfer [J](Hourly)",
        output_csv="correlation_sensitivity_basic.csv"
    )
    
    # Example 2: Correlation with time slice - Peak cooling months
    print("\n=== Example 2: Peak Cooling Months Analysis ===")
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="correlation",
        results_csv=r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv",
        target_variable="Cooling:EnergyTransfer [J](Hourly)",
        output_csv="correlation_peak_cooling.csv",
        time_slice_config={
            "method": "predefined",
            "predefined_slice": "peak_cooling_months"
        }
    )
    
    # Example 3: Custom time slice - Weekday afternoons
    print("\n=== Example 3: Weekday Afternoon Analysis ===")
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="correlation",
        results_csv=r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv",
        target_variable=["Cooling:EnergyTransfer [J](Hourly)", "Electricity:Facility [J](Hourly)"],
        output_csv="correlation_weekday_afternoons.csv",
        time_slice_config={
            "method": "custom",
            "custom_config": {
                "hours": [14, 15, 16, 17],
                "weekdays_only": True
            }
        }
    )
    
    # Example 4: Parameter filtering - Only HVAC parameters
    print("\n=== Example 4: HVAC Parameters Only ===")
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="morris",
        output_csv="morris_hvac_only.csv",
        n_morris_trajectories=15,
        num_levels=4,
        file_patterns=["*hvac*.csv"],
        param_filters={
            "param_name_contains": ["setpoint", "temperature"]
        }
    )
    
    # Example 5: Multiple analysis configurations
    print("\n=== Example 5: Multiple Analysis Configurations ===")
    analysis_configs = [
        {
            "name": "Summer Peak Cooling",
            "method": "correlation",
            "results_csv": r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv",
            "target_variable": "Cooling:EnergyTransfer [J](Hourly)",
            "output_csv": "sensitivity_summer_peak.csv",
            "time_slice_config": {
                "method": "custom",
                "custom_config": {
                    "months": [7, 8],
                    "hours": [14, 15, 16, 17, 18]
                }
            },
            "file_patterns": ["*hvac*.csv", "*vent*.csv"]
        },
        {
            "name": "Winter Morning Heating",
            "method": "correlation",
            "results_csv": r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv",
            "target_variable": "Heating:EnergyTransfer [J](Hourly)",
            "output_csv": "sensitivity_winter_morning.csv",
            "time_slice_config": {
                "method": "predefined",
                "predefined_slice": "winter_mornings"
            },
            "param_filters": {
                "param_name_contains": ["heating", "insulation"]
            }
        }
    ]
    
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        analysis_configs=analysis_configs
    )
    
    # Example 6: Exclude certain parameters
    print("\n=== Example 6: Exclude Roughness Parameters ===")
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="sobol",
        output_csv="sobol_no_roughness.csv",
        n_sobol_samples=256,
        param_filters={
            "exclude_params": ["roughness"],
            "source_files": ["scenario_params_hvac.csv", "scenario_params_dhw.csv", "scenario_params_vent.csv"]
        }
    )
    
    print("\n=== All analyses complete! ===")


if __name__ == "__main__":
    main()






"""
main.py

Example usage of the functions/classes from unified_surrogate.py:
1) Load scenario CSVs from a folder
2) Pivot into a wide DataFrame
3) (Optionally) filter top parameters
4) Load & aggregate simulation results
5) Merge to get X,y
6) Train & save surrogate
7) Reload & predict
"""

import os
import pandas as pd
from cal.unified_surrogate import (
    load_scenario_params,
    pivot_scenario_params,
    filter_top_parameters,
    load_sim_results,
    aggregate_results,
    merge_params_with_results,
    build_and_save_surrogate,
    load_surrogate_and_predict
)

def main():
    # A) scenario CSVs
    scenario_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    if not os.path.isdir(scenario_folder):
        print(f"[ERROR] Scenario folder not found: {scenario_folder}")
        return

    df_scen = load_scenario_params(scenario_folder)
    pivot_df = pivot_scenario_params(df_scen)
    print("[INFO] pivot shape:", pivot_df.shape)

    # Optional: Filter top parameters from a sensitivity file
    # pivot_df = filter_top_parameters(pivot_df, "morris_sensitivity.csv", top_n=5)

    # B) Load & aggregate sim results
    results_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"
    if not os.path.isfile(results_csv):
        print(f"[ERROR] Results CSV not found: {results_csv}")
        return

    df_sim = load_sim_results(results_csv)
    df_agg = aggregate_results(df_sim)

    # C) Merge param pivot with aggregated results for a chosen target var
    target_variable = "Heating:EnergyTransfer [J](Hourly)"
    merged_df = merge_params_with_results(pivot_df, df_agg, target_variable)

    # We'll rename "TotalEnergy_J" -> "target"
    merged_df.rename(columns={"TotalEnergy_J": "target"}, inplace=True)

    # D) Build & Save Surrogate
    model_out = "heating_surrogate_model.joblib"
    col_out   = "heating_surrogate_columns.joblib"
    rf_model, trained_cols = build_and_save_surrogate(
        df_data=merged_df,
        target_col="target",
        model_out_path=model_out,
        columns_out_path=col_out,
        test_size=0.3,
        random_state=42
    )

    if rf_model is None:
        print("[ERROR] Surrogate training unsuccessful or insufficient data.")
        return

    # E) Reload & Predict (using the first row as a sample)
    sample_row = merged_df.iloc[0].drop(["BuildingID","ogc_fid","VariableName","target"])
    sample_dict = sample_row.to_dict()
    y_pred = load_surrogate_and_predict(model_out, col_out, sample_dict)

    print(f"\n[SAMPLE PREDICTION] => {y_pred[0]:.2f} J (approx) for {sample_dict}")

if __name__ == "__main__":
    main()







"""
main.py

Example script that demonstrates how to call the calibration methods
from unified_calibration.py to run random search, GA, or Bayesian optimization.
"""

import os
from unified_calibration import (
    load_scenario_params,
    build_param_specs_from_scenario,
    simulate_or_surrogate,
    CalibrationManager,
    save_history_to_csv
)

def main():
    """
    1) Load scenario param CSVs => get param_min, param_max
    2) Build param_specs
    3) Define a calibration objective => simulate_or_surrogate
    4) Choose method (random, ga, bayes)
    5) Save best params + error, optional CSV log
    """
    scenario_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    if not os.path.isdir(scenario_folder):
        print(f"[ERROR] Scenario folder not found: {scenario_folder}")
        return

    print("[INFO] Loading scenario data")
    df_scen = load_scenario_params(scenario_folder)

    # Build param specs
    param_specs = build_param_specs_from_scenario(df_scen)
    print(f"[INFO] Found {len(param_specs)} unique parameters from scenario data.")
    for spec in param_specs[:5]:
        print(f"   - {spec.name}: {spec.min_value} .. {spec.max_value}, int={spec.is_integer}")

    # Create a manager with our placeholder evaluation function
    manager = CalibrationManager(param_specs, simulate_or_surrogate)

    # EXAMPLE: run GA
    print("\n=== Running GA Calibration ===")
    best_params_ga, best_err_ga, hist_ga = manager.run_calibration(
        method="ga",
        pop_size=10,
        generations=5,
        crossover_prob=0.7,
        mutation_prob=0.2
    )
    print(f"[GA] Best error={best_err_ga:.3f}, best params={best_params_ga}")
    save_history_to_csv(hist_ga, "calibration_history_ga.csv")

    # EXAMPLE: run Bayesian
    print("\n=== Running Bayesian Calibration ===")
    best_params_bayes, best_err_bayes, hist_bayes = manager.run_calibration(
        method="bayes",
        n_calls=15
    )
    print(f"[BAYES] Best error={best_err_bayes:.3f}, best params={best_params_bayes}")
    save_history_to_csv(hist_bayes, "calibration_history_bayes.csv")

    # EXAMPLE: run Random
    print("\n=== Running Random Search Calibration ===")
    best_params_rand, best_err_rand, hist_rand = manager.run_calibration(
        method="random",
        n_iterations=20
    )
    print(f"[RANDOM] Best error={best_err_rand:.3f}, best params={best_params_rand}")
    save_history_to_csv(hist_rand, "calibration_history_random.csv")

    # Compare final best
    results = [
        ("GA", best_params_ga, best_err_ga),
        ("Bayes", best_params_bayes, best_err_bayes),
        ("Random", best_params_rand, best_err_rand)
    ]
    results.sort(key=lambda x: x[2])  # sort by error ascending
    print("\n=== Overall Best Among the 3 ===")
    print(f"Method={results[0][0]}, error={results[0][2]:.3f}, params={results[0][1]}")

if __name__ == "__main__":
    main()
