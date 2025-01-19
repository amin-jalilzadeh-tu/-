"""
main.py

Description:
  - High-level orchestrator for the EnergyPlus workflow.
  - Demonstrates:
      1) Loading user configs
      2) Applying Excel overrides + user config overrides
      3) Creating IDFs, running simulations, post-processing
      4) Placeholders for calibration, validation, advanced analyses

Usage:
  python main.py
"""

import logging
import os
import pandas as pd

# Import from your newly created modules:
from excel_overrides import (
    override_fenestration_dicts_from_excel,
    override_dhw_lookup_from_excel_file,
    override_epw_lookup_from_excel_file,
    override_lighting_lookup_from_excel_file,
    override_hvac_lookup_from_excel_file,
    override_vent_lookup_from_excel_file
)
from user_config_overrides import (
    apply_geometry_user_config,
    apply_fenestration_user_config,
    apply_dhw_user_config,
    apply_lighting_user_config,
    apply_hvac_user_config,
    apply_ventilation_user_config,
    apply_epw_user_config
)
from idf_creation import create_idfs_for_all_buildings

from validation.main_validation import run_validation_process


from modification.main_modifi import run_modification_workflow



###############################################################################
# 1. Logging Setup
###############################################################################
def setup_logging(log_level=logging.INFO):
    """Initialize logging with a standard format."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

###############################################################################
# 2. Main Orchestration
###############################################################################
def main():
    logger = setup_logging()
    logger.info("==== Starting main.py ====")

    # --------------------------------------------------------------------------
    # A) Load User Config (Mock Example)
    # --------------------------------------------------------------------------
    # In real use, you'd parse a JSON or YAML file, e.g.:
    # user_config = load_user_configs("user_configs/config.json")
    # For demonstration, let's define a dictionary in code:
    user_config = {
        "paths": {
            "building_data": "data/df_buildings.csv",
            "fenez_excel": "excel_data/envelop.xlsx",
            "dhw_excel": "excel_data/dhw_overrides.xlsx",
            "epw_excel": "excel_data/epw_overrides.xlsx",
            "lighting_excel": "excel_data/lighting_overrides.xlsx",
            "hvac_excel": "excel_data/hvac_overrides.xlsx",
            "vent_excel": "excel_data/vent_overrides.xlsx"
        },
        "excel_overrides": {
            "override_fenez": False,
            "override_dhw": False,
            "override_epw": False,
            "override_lighting": False,
            "override_hvac": False,
            "override_vent": False
        },
        "idf_creation": {
            "perform_idf_creation": True,
            "scenario": "scenario1",
            "calibration_stage": "pre_calibration",
            "strategy": "B",
            "random_seed": 42,
            "run_simulations": True,
            "num_workers": 4,
            "post_process": True
        },
        "user_config_geom": [
            {"building_id": 4136730, "param_name": "perimeter_depth", "fixed_value": 3.5}
        ],
        "user_config_fenez": {
            "wwr": 0.32,
            "elements": {
                "windows": {"U_value": 2.9}
            }
        },
        "user_config_dhw": [],
        "user_config_lighting": [],
        "user_config_hvac": {},
        "user_config_vent": [],
        "validation": {
            "perform_validation": True,
            "real_data_csv": r"D:\Documents\E_Plus_2030_py\output\results\mock_merged_daily_mean.csv",
            "sim_data_csv":  r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv",
            "bldg_ranges": {
                0: range(0, 5)
            },
            "threshold_cv_rmse": 30.0,
            "skip_plots": True,
            "output_csv": "validation_report.csv"
        },
        "calibration": {
            "perform_calibration": False
        }
        # placeholders for advanced analysis if needed
    }

    # ------------------------------------------------------------------------
    # B) Load Default Dictionaries (mock)
    # ------------------------------------------------------------------------
    default_res_data = {"R1": "some_res_data"}
    default_nonres_data = {"NR1": "some_nonres_data"}
    default_dhw_lookup = {"Office": {"setpoint_c": 55.0}}
    default_epw_lookup = [{"city": "DefaultCity", "file": "DefaultCity.epw"}]
    default_lighting_lookup = {"lights_wm2": 10.0}
    default_hvac_lookup = {"heating_day_setpoint": 20.0}
    default_vent_lookup = {"infiltration_base": 1.0}

    # ------------------------------------------------------------------------
    # C) Apply Excel Overrides (In-Memory)
    # ------------------------------------------------------------------------
    epaths = user_config["paths"]
    eover = user_config["excel_overrides"]

    # Fenez
    default_res_data, default_nonres_data = override_fenestration_dicts_from_excel(
        excel_path=epaths["fenez_excel"],
        default_res_data=default_res_data,
        default_nonres_data=default_nonres_data,
        override_from_excel_flag=eover["override_fenez"]
    )
    # DHW
    default_dhw_lookup = override_dhw_lookup_from_excel_file(
        dhw_excel_path=epaths["dhw_excel"],
        default_dhw_lookup=default_dhw_lookup,
        override_dhw_flag=eover["override_dhw"]
    )
    # EPW
    default_epw_lookup = override_epw_lookup_from_excel_file(
        epw_excel_path=epaths["epw_excel"],
        epw_lookup=default_epw_lookup,
        override_epw_flag=eover["override_epw"]
    )
    # Lighting
    default_lighting_lookup = override_lighting_lookup_from_excel_file(
        lighting_excel_path=epaths["lighting_excel"],
        lighting_lookup=default_lighting_lookup,
        override_lighting_flag=eover["override_lighting"]
    )
    # HVAC
    default_hvac_lookup = override_hvac_lookup_from_excel_file(
        hvac_excel_path=epaths["hvac_excel"],
        hvac_lookup=default_hvac_lookup,
        override_hvac_flag=eover["override_hvac"]
    )
    # Vent
    default_vent_lookup = override_vent_lookup_from_excel_file(
        vent_excel_path=epaths["vent_excel"],
        vent_lookup=default_vent_lookup,
        override_vent_flag=eover["override_vent"]
    )

    # ------------------------------------------------------------------------
    # D) Apply User Config Partial Overrides
    # ------------------------------------------------------------------------
    final_geometry_dict = apply_geometry_user_config({}, user_config["user_config_geom"])
    final_fenez_dict = apply_fenestration_user_config(
        fenez_dict={"res": default_res_data, "nonres": default_nonres_data},
        user_config_fenez=user_config["user_config_fenez"]
    )
    final_dhw_lookup = apply_dhw_user_config(default_dhw_lookup, user_config["user_config_dhw"])
    final_lighting_lookup = apply_lighting_user_config(default_lighting_lookup, user_config["user_config_lighting"])
    final_hvac_lookup = apply_hvac_user_config(default_hvac_lookup, user_config["user_config_hvac"])
    final_vent_lookup = apply_ventilation_user_config(default_vent_lookup, user_config["user_config_vent"])
    final_epw_lookup = apply_epw_user_config(default_epw_lookup, None)  # If no user EPW config

    # Possibly store them all in a single dict if you want
    final_lookups = {
        "geometry": final_geometry_dict,
        "fenez": final_fenez_dict,
        "dhw": final_dhw_lookup,
        "lighting": final_lighting_lookup,
        "hvac": final_hvac_lookup,
        "vent": final_vent_lookup,
        "epw": final_epw_lookup
    }

    # ------------------------------------------------------------------------
    # E) Load Building Data
    # ------------------------------------------------------------------------
    bldg_data_path = user_config["paths"]["building_data"]
    if os.path.isfile(bldg_data_path):
        df_buildings = pd.read_csv(bldg_data_path)
        logger.info(f"Loaded building data: {len(df_buildings)} rows from {bldg_data_path}.")
    else:
        logger.warning(f"Could not find building data at {bldg_data_path}; using empty DataFrame.")
        df_buildings = pd.DataFrame()

    # (If shading data needed)
    df_bldg_shading = None
    df_trees_shading = None

    # ------------------------------------------------------------------------
    # F) IDF Creation & Simulation
    # ------------------------------------------------------------------------
    idf_cfg = user_config["idf_creation"]
    if idf_cfg.get("perform_idf_creation", False):
        logger.info("[INFO] IDF creation is enabled. Creating IDFs & optionally simulating.")

        # Example call to create and (optionally) simulate
        create_idfs_for_all_buildings(
            df_buildings=df_buildings,
            scenario=idf_cfg.get("scenario", "scenario1"),
            calibration_stage=idf_cfg.get("calibration_stage", "pre_calibration"),
            strategy=idf_cfg.get("strategy", "B"),
            random_seed=idf_cfg.get("random_seed", 42),
            # Pass user config partial overrides:
            user_config_geom=user_config["user_config_geom"],
            user_config_lighting=user_config["user_config_lighting"],
            user_config_dhw=user_config["user_config_dhw"],
            user_config_fenez=user_config["user_config_fenez"],
            user_config_hvac=user_config["user_config_hvac"],
            user_config_vent=user_config["user_config_vent"],
            df_bldg_shading=df_bldg_shading,
            df_trees_shading=df_trees_shading,
            run_simulations=idf_cfg.get("run_simulations", True),
            simulate_config={"num_workers": idf_cfg.get("num_workers", 4)},
            post_process=idf_cfg.get("post_process", True)
        )
    else:
        logger.info("[INFO] Skipping IDF creation & simulation per user config.")

    # ------------------------------------------------------------------------
    # G) Validation
    # ------------------------------------------------------------------------
    val_cfg = user_config.get("validation", {})
    if val_cfg.get("perform_validation", False):
        logger.info("[INFO] Running validation process...")
        run_validation_process(val_cfg)
    else:
        logger.info("[INFO] Skipping validation per user config.")






    config = {
      "base_idf_path": "D:/Documents/E_Plus_2030_py/output/output_IDFs/building_0.idf",
      "idd_path":      "D:/EnergyPlus/Energy+.idd",
      "assigned_csv": {
          "hvac":  "D:/Documents/E_Plus_2030_py/output/assigned/assigned_hvac_building.csv",
          "dhw":   "D:/Documents/E_Plus_2030_py/output/assigned/assigned_dhw_params.csv",
          "vent":  "D:/Documents/E_Plus_2030_py/output/assigned/assigned_vent_building.csv",
          "elec":  "D:/Documents/E_Plus_2030_py/output/assigned/assigned_lighting.csv",
          "fenez": "D:/Documents/E_Plus_2030_py/output/assigned/structured_fenez_params.csv",
      },
      "scenario_csv": {
          "hvac":  "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_hvac.csv",
          "dhw":   "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_dhw.csv",
          "vent":  "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_vent.csv",
          "elec":  "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_elec.csv",
          "fenez": "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_fenez.csv"
      },
      "output_idf_dir":  "D:/Documents/E_Plus_2030_py/output/scenario_idfs",
      "building_id":     4136730,
      "num_scenarios":   5,
      "picking_method":  "random_uniform",
      "picking_scale_factor": 0.5,

      "run_simulations": True,
      "simulation_config": {
         "num_workers": 4,
         "output_dir": "D:/Documents/E_Plus_2030_py/output/Sim_Results/Scenarios"
      },

      "perform_post_process": True,
      "post_process_config": {
         "output_csv_as_is": "D:/Documents/E_Plus_2030_py/output/results/merged_as_is_scenarios.csv",
         "output_csv_daily_mean": "D:/Documents/E_Plus_2030_py/output/results/merged_daily_mean_scenarios.csv"
      },

      "perform_validation": True,
      "validation_config": {
         "real_data_csv":   "D:/Documents/E_Plus_2030_py/output/results/mock_merged_daily_mean.csv",
         "sim_data_csv":    "D:/Documents/E_Plus_2030_py/output/results/merged_daily_mean_mocked.csv",
         "bldg_ranges":     {0: range(0,5)},
         "threshold_cv_rmse": 30.0,
         "skip_plots": False,
         "output_csv": "scenario_validation_report.csv"
      }
    }

    run_modification_workflow(config)
























    # ------------------------------------------------------------------------
    # H) Calibration Placeholder
    # ------------------------------------------------------------------------
    if user_config["calibration"].get("perform_calibration", False):
        logger.info("[INFO] Running calibration steps... (placeholder)")
        # run_calibration_loop(...)  # your actual calibration function
    else:
        logger.info("[INFO] Skipping calibration per user config.")


    # ------------------------------------------------------------------------
    # I) (Optional) Advanced analyses: sensitivity, surrogate, optimization
    # ------------------------------------------------------------------------
    # if user_config.get("sensitivity", {}).get("perform_sensitivity", False):
    #     logger.info("[INFO] Running sensitivity analysis placeholder...")
    #     run_sensitivity_analysis(...)
    # if user_config.get("surrogate", {}).get("perform_surrogate", False):
    #     logger.info("[INFO] Running surrogate modeling placeholder...")
    #     run_surrogate_model(...)
    # if user_config.get("optimization", {}).get("perform_optimization", False):
    #     logger.info("[INFO] Running optimization workflow placeholder...")
    #     run_optimization_workflow(...)

    logger.info("=== End of main.py ===")























###############################################################################
# 3. Script Entry Point
###############################################################################
if __name__ == "__main__":
    main()
