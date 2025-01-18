"""
man.py

Simple driver script that uses functions from sensitivity_analysis_main.py.
"""

import sys
import os

# Adjust the import path if needed
# If `sensitivity_analysis_main.py` is in the same folder, this should work:
from cal_1.sensitivity_analysis_main import run_sensitivity_analyses

if __name__ == "__main__":
    # Adjust the paths below to point to your scenario CSV files
    dhw_csv   = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_dhw.csv"
    elec_csv  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_elec.csv"
    fenez_csv = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_fenez.csv"
    hvac_csv  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_hvac.csv"
    vent_csv  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_vent.csv"

    scenario_index = 0    # Example
    # You can customize these:
    n_morris_trajectories = 10
    n_sobol_samples = 128

    # Run the main sensitivity analyses
    run_sensitivity_analyses(
        dhw_csv,
        elec_csv,
        fenez_csv,
        hvac_csv,
        vent_csv,
        scenario_index=scenario_index,
        n_morris_trajectories=n_morris_trajectories,
        n_sobol_samples=n_sobol_samples
    )







    """
man.py

This file imports 'surrogate_model_main' and runs the demo.
Usage:
    python man.py
"""

import cal_1.surrogate_model

if __name__ == "__main__":
    cal_1.surrogate_model.run_demo()

