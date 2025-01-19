"""
main_modifi.py

Handles the generation of scenario-based IDFs for sensitivity, surrogate, 
calibration, or any parametric runs. It:
  1) Loads previously "assigned" CSVs or base parameter data for HVAC, DHW, Vent, Elec
  2) (Optionally) generates multiple scenario parameter sets for these subsystems
     (HVAC, DHW, Vent, Elec)
  3) Leaves fenestration (fenez) as a CSV-based approach (Option A) so we
     directly pass the CSV path to `apply_object_level_fenez(...)`.
  4) Applies these parameters to a base IDF to produce new scenario IDFs
  5) Optionally runs simulations, post-processes, and performs validation
"""

import os
import pandas as pd

# 1) Common utility imports
from modification.common_utils import (
    load_assigned_csv,
    load_scenario_csv,
    load_idf,
    save_idf,
    generate_multiple_param_sets,
    save_param_scenarios_to_csv
)

# 2) Subsystem functions (placeholders; replace with your actual names)
from modification.hvac_functions import apply_building_level_hvac, apply_zone_level_hvac
from modification.dhw_functions import apply_dhw_params_to_idf
from modification.vent_functions import apply_building_level_vent, apply_zone_level_vent
# from elec_functions import apply_elec_params_to_idf   # if you have such a module
from modification.fenez_functions import apply_object_level_fenez

# 3) Simulation, post-processing, and validation imports (placeholders)
# from epw.run_epw_sims import simulate_all
# from postproc.merge_results import merge_all_results
# from validation.main_validation import run_validation_process


def run_modification_workflow(config):
    """
    Main function that orchestrates scenario generation, IDF creation,
    optional simulation, post-processing, and validation.

    We do scenario-based picks for HVAC, DHW, Vent, Elec, but for fenestration
    we keep the original CSV approach. That means `apply_object_level_fenez`
    expects a CSV path. We'll pass the 'fenez' assigned path directly,
    skipping scenario generation for fenestration.

    Expected config structure (example):
    {
      "base_idf_path": "D:/Documents/E_Plus_2030_py/output/output_IDFs/building_0.idf",
      "idd_path":      "D:/EnergyPlus/Energy+.idd",

      "assigned_csv": {
        "hvac":  "D:/Documents/E_Plus_2030_py/output/assigned/assigned_hvac_building.csv",
        "dhw":   "D:/Documents/E_Plus_2030_py/output/assigned/assigned_dhw_params.csv",
        "vent":  "D:/Documents/E_Plus_2030_py/output/assigned/assigned_vent_building.csv",
        "elec":  "D:/Documents/E_Plus_2030_py/output/assigned/assigned_lighting.csv",
        "fenez": "D:/Documents/E_Plus_2030_py/output/assigned/structured_fenez_params.csv"
      },

      "scenario_csv": {
        "hvac":  "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_hvac.csv",
        "dhw":   "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_dhw.csv",
        "vent":  "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_vent.csv",
        "elec":  "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_elec.csv"
        // "fenez": not needed now
      },

      "output_idf_dir": "D:/Documents/E_Plus_2030_py/output/scenario_idfs",
      "building_id": 4136730,
      "num_scenarios": 5,
      "picking_method": "random_uniform",
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
         "real_data_csv": "D:/Documents/E_Plus_2030_py/output/results/mock_merged_daily_mean.csv",
         "sim_data_csv":  "D:/Documents/E_Plus_2030_py/output/results/merged_daily_mean_mocked.csv",
         "bldg_ranges": {0: range(0,5)},
         "threshold_cv_rmse": 30.0,
         "skip_plots": False,
         "output_csv": "scenario_validation_report.csv"
      }
    }
    """
    # 1) Extract top-level config
    base_idf_path   = config["base_idf_path"]
    idd_path        = config["idd_path"]
    assigned_csvs   = config["assigned_csv"]      # dictionary of assigned CSV paths
    scenario_csvs   = config["scenario_csv"]      # dictionary of scenario CSV output paths
    building_id     = config["building_id"]
    num_scenarios   = config["num_scenarios"]
    picking_method  = config["picking_method"]
    scale_factor    = config.get("picking_scale_factor", 1.0)
    output_idf_dir  = config["output_idf_dir"]

    os.makedirs(output_idf_dir, exist_ok=True)

    # 2) Load "assigned" CSVs for HVAC, DHW, Vent, Elec
    #    (We skip scenario-based fenestration, so we won't load df_fenez_sub for scenarios)
    df_hvac  = load_assigned_csv(assigned_csvs["hvac"])
    df_dhw   = load_assigned_csv(assigned_csvs["dhw"])
    df_vent  = load_assigned_csv(assigned_csvs["vent"])
    df_elec  = load_assigned_csv(assigned_csvs["elec"])

    # Filter for the building of interest
    df_hvac_sub = df_hvac[df_hvac["ogc_fid"] == building_id].copy()
    df_dhw_sub  = df_dhw[df_dhw["ogc_fid"] == building_id].copy()
    df_vent_sub = df_vent[df_vent["ogc_fid"] == building_id].copy()
    df_elec_sub = df_elec[df_elec["ogc_fid"] == building_id].copy()

    # 3) Generate multiple scenario picks (HVAC, DHW, Vent, Elec)
    hvac_scenarios = generate_multiple_param_sets(
        df_main_sub=df_hvac_sub,
        num_sets=num_scenarios,
        picking_method=picking_method,
        scale_factor=scale_factor
    )
    save_param_scenarios_to_csv(
        all_scenarios=hvac_scenarios,
        building_id=building_id,
        out_csv=scenario_csvs["hvac"]
    )

    dhw_scenarios = generate_multiple_param_sets(
        df_main_sub=df_dhw_sub,
        num_sets=num_scenarios,
        picking_method=picking_method,
        scale_factor=scale_factor
    )
    save_param_scenarios_to_csv(
        all_scenarios=dhw_scenarios,
        building_id=building_id,
        out_csv=scenario_csvs["dhw"]
    )

    vent_scenarios = generate_multiple_param_sets(
        df_main_sub=df_vent_sub,
        num_sets=num_scenarios,
        picking_method=picking_method,
        scale_factor=scale_factor
    )
    save_param_scenarios_to_csv(
        all_scenarios=vent_scenarios,
        building_id=building_id,
        out_csv=scenario_csvs["vent"]
    )

    elec_scenarios = generate_multiple_param_sets(
        df_main_sub=df_elec_sub,
        num_sets=num_scenarios,
        picking_method=picking_method,
        scale_factor=scale_factor
    )
    save_param_scenarios_to_csv(
        all_scenarios=elec_scenarios,
        building_id=building_id,
        out_csv=scenario_csvs["elec"]
    )

    # For fenestration, we do NOT do scenario generation; we pass the assigned CSV path directly.

    # 4) Load scenario CSVs for HVAC, DHW, Vent, Elec
    df_hvac_scen = load_scenario_csv(scenario_csvs["hvac"])
    df_dhw_scen  = load_scenario_csv(scenario_csvs["dhw"])
    df_vent_scen = load_scenario_csv(scenario_csvs["vent"])
    df_elec_scen = load_scenario_csv(scenario_csvs["elec"])

    hvac_groups = df_hvac_scen.groupby("scenario_index")
    dhw_groups  = df_dhw_scen.groupby("scenario_index")
    vent_groups = df_vent_scen.groupby("scenario_index")
    elec_groups = df_elec_scen.groupby("scenario_index")

    # Because fenestration isn't scenario-based, we just store the CSV path:
    fenez_csv_path = assigned_csvs["fenez"]  # e.g. "D:/Documents/E_Plus_2030_py/output/assigned/structured_fenez_params.csv"

    # 5) For each scenario, load base IDF, apply params, apply fenestration from CSV, then save
    for i in range(num_scenarios):
        print(f"\n--- Creating scenario #{i} IDF for building {building_id} ---")

        hvac_df   = hvac_groups.get_group(i)
        dhw_df    = dhw_groups.get_group(i)
        vent_df   = vent_groups.get_group(i)
        elec_df   = elec_groups.get_group(i)

        # Build param dicts
        hvac_params = _make_param_dict(hvac_df)
        dhw_params  = _make_param_dict(dhw_df)
        vent_params = _make_param_dict(vent_df)
        elec_params = _make_param_dict(elec_df)
        # fenestration => no param dict, we have a CSV approach

        # 5a) Load base IDF
        idf = load_idf(base_idf_path, idd_path)

        # 5b) Apply HVAC
        apply_building_level_hvac(idf, hvac_params)

        # 5c) Apply DHW
        apply_dhw_params_to_idf(idf, dhw_params, suffix=f"Scenario_{i}")

        # 5d) Apply Vent
        apply_building_level_vent(idf, vent_params)

        # 5e) Apply Elec
        # apply_elec_params_to_idf(idf, elec_params)   # if you have an elec function

        # 5f) Apply Fenestration from the assigned CSV path (Option A)
        apply_object_level_fenez(idf, "D:/Documents/E_Plus_2030_py/output/scenarios/scenario_params_fenez.csv")
        # ^ `apply_object_level_fenez(...)` reads from CSV. 
        #   It does not expect a dict; pass the actual file path.

        # 6) Save scenario IDF
        scenario_idf_name = f"building_{building_id}_scenario_{i}.idf"
        scenario_idf_path = os.path.join(output_idf_dir, scenario_idf_name)
        save_idf(idf, scenario_idf_path)
        print(f"[INFO] Saved scenario IDF: {scenario_idf_path}")

    print("[INFO] All scenario IDFs generated successfully.")

    # -------------------------------------------------------------------------
    # 6) (Optional) Run Simulations
    # -------------------------------------------------------------------------
    if config.get("run_simulations", False):
        print("\n[INFO] Running simulations for scenario IDFs...")
        sim_cfg = config.get("simulation_config", {})
        # from epw.run_epw_sims import simulate_all
        # simulate_all(
        #    idf_folder=output_idf_dir,
        #    output_folder=sim_cfg.get("output_dir", "Sim_Results/Scenarios"),
        #    num_workers=sim_cfg.get("num_workers", 4)
        # )
        print("[INFO] Simulations complete (placeholder).")

    # -------------------------------------------------------------------------
    # 7) (Optional) Post-processing
    # -------------------------------------------------------------------------
    if config.get("perform_post_process", False):
        print("[INFO] Performing post-processing merges (placeholder).")
        # from postproc.merge_results import merge_all_results
        ppcfg = config.get("post_process_config", {})
        # merged_as_is   = ppcfg.get("output_csv_as_is", "merged_as_is_scenarios.csv")
        # merged_daily   = ppcfg.get("output_csv_daily_mean", "merged_daily_mean_scenarios.csv")

        # e.g.:
        # merge_all_results(
        #    base_output_dir=sim_cfg.get("output_dir", "Sim_Results/Scenarios"),
        #    output_csv=merged_as_is,
        #    convert_to_daily=False
        # )
        # merge_all_results(
        #    base_output_dir=sim_cfg.get("output_dir", "Sim_Results/Scenarios"),
        #    output_csv=merged_daily,
        #    convert_to_daily=True,
        #    daily_aggregator="mean"
        # )
        print("[INFO] Post-processing step complete (placeholder).")

    # -------------------------------------------------------------------------
    # 8) (Optional) Validation
    # -------------------------------------------------------------------------
    if config.get("perform_validation", False):
        print("[INFO] Performing validation on scenario results (placeholder).")
        # from validation.main_validation import run_validation_process
        val_cfg = config["validation_config"]
        # run_validation_process(val_cfg)
        print("[INFO] Validation step complete (placeholder).")


def _make_param_dict(df_scenario):
    """
    Helper function to build a param dict from scenario DataFrame.
    e.g., each row has (param_name, assigned_value).
    """
    param_dict = {}
    for row in df_scenario.itertuples():
        p_name = row.param_name
        val = row.assigned_value
        # Attempt float conversion if possible
        try:
            param_dict[p_name] = float(val)
        except:
            param_dict[p_name] = val
    return param_dict
