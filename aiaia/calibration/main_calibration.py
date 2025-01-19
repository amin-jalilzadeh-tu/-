# calibration\main_calibration.py
import os
from calibration.calibration_manager import CalibrationManager

def main():
    folder = r"D:\Documents\E_Plus_2030_py\output"  
    master_params_csv = os.path.join(folder, "assigned", "master_parameters.csv")
    measured_data_csv = os.path.join(folder, "mock_data.csv")  # example
    sim_output_folder = os.path.join(folder, "results")

    manager = CalibrationManager(
        master_params_csv=master_params_csv,
        measured_data_csv=measured_data_csv,
        sim_output_folder=sim_output_folder
    )

    # (A) Maybe do sensitivity first
    # top_params = manager.run_sensitivity(method="sobol")
    # print("Top influential parameters:", top_params)

    # (B) Calibration step
    best_random = manager.run_calibration(method="random", max_iterations=10)
    print("Best random solution:", best_random)

    best_ga = manager.run_calibration(method="ga", max_iterations=20)
    print("Best GA solution:", best_ga)

    best_bayes = manager.run_calibration(method="bayesian", max_iterations=15)
    print("Best Bayesian solution:", best_bayes)

    # (C) Surrogate approach
    # best_surrogate = manager.run_surrogate_calibration()
    # print("Best Surrogate solution:", best_surrogate)

if __name__ == "__main__":
    main()
