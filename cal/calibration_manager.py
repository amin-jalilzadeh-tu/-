# calibration\calibration_manager.py

import os
import numpy as np
import pandas as pd
from typing import Dict, Any

from calibration.calibrator_random import random_calibration
from calibration.calibrator_ga import ga_calibration
from calibration.calibrator_bayes import bayes_calibration
from calibration.sensitivity import run_sensitivity_analysis
from calibration.ml_surrogate import SurrogateCalibrator

from generation.create_idfs import create_idf_files  # Example function
from validation.validate_results import validate_data

class CalibrationManager:
    def __init__(self, master_params_csv: str, measured_data_csv: str, sim_output_folder: str):
        """
        master_params_csv: path to CSV containing all parameters & ranges (e.g. master_parameters.csv).
        measured_data_csv: path to real measured data for validation.
        sim_output_folder: where simulation outputs (e.g., .csv from E+) are stored.
        """
        self.master_params_csv = master_params_csv
        self.measured_data_csv = measured_data_csv
        self.sim_output_folder = sim_output_folder
        self.df_params = pd.read_csv(master_params_csv)  # parameter info

    def run_calibration(self, method="random", max_iterations=10, threshold_cv_rmse=30.0):
        """
        High-level API to run calibration using different methods.
        """
        if method == "random":
            best_solution = random_calibration(self.df_params, max_iterations, threshold_cv_rmse)
        elif method == "ga":
            best_solution = ga_calibration(self.df_params, max_iterations, threshold_cv_rmse)
        elif method == "bayesian":
            best_solution = bayes_calibration(self.df_params, max_iterations, threshold_cv_rmse)
        else:
            raise ValueError(f"Unknown calibration method: {method}")

        return best_solution

    def run_sensitivity(self, method="sobol"):
        """
        Optionally run a sensitivity analysis to identify top parameters that influence energy usage.
        """
        top_parameters = run_sensitivity_analysis(self.df_params, method=method)
        return top_parameters
    
    def run_surrogate_calibration(self):
        """
        Example of using a Machine Learning Surrogate approach.
        """
        surrogate = SurrogateCalibrator(self.df_params, self.measured_data_csv)
        surrogate.build_surrogate()
        surrogate.optimize()
        # returns best parameter set
        best_params = surrogate.best_params
        return best_params

    # Potentially more manager functionalities...
