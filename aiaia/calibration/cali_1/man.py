import os
from cali_1.sensitivity_main import run_sensitivity_analysis

def main():
    """
    This script shows how to call the `run_sensitivity_analysis` function
    from sensitivity_main.py. Update the scenario folder and methods as needed.
    """
    scenario_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"

    # Make sure the folder exists or adjust the path
    if not os.path.isdir(scenario_folder):
        print(f"[ERROR] Scenario folder does not exist: {scenario_folder}")
        return

    # Example: Running Morris analysis
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="morris",
        output_csv="morris_sensitivity_results.csv"
    )

    # Example: Running Sobol analysis
    run_sensitivity_analysis(
        scenario_folder=scenario_folder,
        method="sobol",
        output_csv="sobol_sensitivity_results.csv"
    )

if __name__ == "__main__":
    main()



# man.py

import pandas as pd
from cali_1.surrogate_main import (
    train_aggregate_surrogate,
    load_aggregate_surrogate
)

if __name__ == "__main__":
    # Example usage

    # 1) Define paths
    scenario_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    results_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"
    sensitivity_csv = "morris_sensitivity_results.csv"  # or None
    top_n = 5
    output_model_path = "my_aggregate_surrogate.pkl"

    # 2) Train & save
    train_aggregate_surrogate(
        scenario_folder=scenario_folder,
        results_csv=results_csv,
        sensitivity_csv=sensitivity_csv,
        top_n=top_n,
        output_model_path=output_model_path
    )

    # 3) Load the trained model
    model = load_aggregate_surrogate(output_model_path)

    # 4) Predict on new data (columns must match training columns!)
    new_params = pd.DataFrame({
        "exterior_wall_U_value": [0.38],
        "infiltration_base": [1.2],
        "occupant_density_m2_per_person": [28.0],
        "default_heater_capacity_w": [4000.0],
        "ground_floor_window_construction_name": [0]
    })

    predictions = model.predict(new_params)
    print("Predictions:", predictions)
