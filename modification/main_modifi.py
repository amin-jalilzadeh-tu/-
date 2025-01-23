"""
main_modifi.py

Handles the generation of scenario-based IDFs for sensitivity, surrogate, 
calibration, or any parametric runs. It:
  1) Loads previously "assigned" CSVs or base parameter data for HVAC, DHW, Vent, Elec, Fenestration
  2) Generates multiple scenario parameter sets (e.g., random or LHS picks)
  3) Applies these parameters to a base IDF to produce new scenario IDFs
  4) Optionally runs simulations, post-processes, and performs validation

This module is typically invoked by main.py with a config dictionary:
  from main_modifi import run_modification_workflow
  run_modification_workflow(config)
"""

"""
main_modifi.py

Handles the generation of scenario-based IDFs for sensitivity, calibration, 
or parametric runs.
"""

import os
import pandas as pd

from modification.common_utils import (
    load_assigned_csv,
    load_scenario_csv,
    load_idf,
    save_idf,
    generate_multiple_param_sets,
    save_param_scenarios_to_csv
)

from modification.hvac_functions import (
    apply_building_level_hvac, 
    apply_zone_level_hvac  # if needed
)
from modification.dhw_functions import apply_dhw_params_to_idf
from modification.vent_functions import (
    apply_building_level_vent, 
    apply_zone_level_vent  # if needed
)
# from elec_functions import apply_elec_params_to_idf  # if you have it

# Fenes modules:
from modification.fenez_functions2 import (
    apply_building_level_fenez,
    apply_object_level_fenez
)


def _make_param_dict(df_scenario):
    """
    Converts a scenario sub-DataFrame (with columns param_name, assigned_value)
    into a dictionary {param_name: assigned_value}.
    """
    param_dict = {}
    for row in df_scenario.itertuples():
        p_name = row.param_name
        val = row.assigned_value
        # Attempt float conversion
        try:
            param_dict[p_name] = float(val)
        except (ValueError, TypeError):
            param_dict[p_name] = val
    return param_dict


def run_modification_workflow(config):
    """
    Main function that orchestrates scenario generation, IDF creation,
    optional simulation, post-processing, and validation.
    """
    # 1) Extract top-level config
    base_idf_path   = config["base_idf_path"]
    idd_path        = config["idd_path"]
    assigned_csvs   = config["assigned_csv"]
    scenario_csvs   = config["scenario_csv"]
    building_id     = config["building_id"]
    num_scenarios   = config["num_scenarios"]
    picking_method  = config["picking_method"]
    scale_factor    = config.get("picking_scale_factor", 1.0)
    output_idf_dir  = config["output_idf_dir"]

    os.makedirs(output_idf_dir, exist_ok=True)

    # 2) Load "assigned" CSVs for the building
    df_hvac  = load_assigned_csv(assigned_csvs["hvac"])
    df_dhw   = load_assigned_csv(assigned_csvs["dhw"])
    df_vent  = load_assigned_csv(assigned_csvs["vent"])
    df_elec  = load_assigned_csv(assigned_csvs["elec"])
    df_fenez = load_assigned_csv(assigned_csvs["fenez"])

    df_hvac_sub  = df_hvac[df_hvac["ogc_fid"] == building_id].copy()
    df_dhw_sub   = df_dhw[df_dhw["ogc_fid"] == building_id].copy()
    df_vent_sub  = df_vent[df_vent["ogc_fid"] == building_id].copy()
    df_elec_sub  = df_elec[df_elec["ogc_fid"] == building_id].copy()
    df_fenez_sub = df_fenez[df_fenez["ogc_fid"] == building_id].copy()

    # 3) Generate multiple scenario picks (random scaling, etc.) & save to CSV
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

    fenez_scenarios = generate_multiple_param_sets(
        df_main_sub=df_fenez_sub,
        num_sets=num_scenarios,
        picking_method=picking_method,
        scale_factor=scale_factor
    )
    save_param_scenarios_to_csv(
        all_scenarios=fenez_scenarios,
        building_id=building_id,
        out_csv=scenario_csvs["fenez"]
    )

    # 4) Load scenario CSVs back, group by scenario_index
    df_hvac_scen  = load_scenario_csv(scenario_csvs["hvac"])
    df_dhw_scen   = load_scenario_csv(scenario_csvs["dhw"])
    df_vent_scen  = load_scenario_csv(scenario_csvs["vent"])
    df_elec_scen  = load_scenario_csv(scenario_csvs["elec"])
    df_fenez_scen = load_scenario_csv(scenario_csvs["fenez"])

    hvac_groups  = df_hvac_scen.groupby("scenario_index")
    dhw_groups   = df_dhw_scen.groupby("scenario_index")
    vent_groups  = df_vent_scen.groupby("scenario_index")
    elec_groups  = df_elec_scen.groupby("scenario_index")
    fenez_groups = df_fenez_scen.groupby("scenario_index")

    # 5) For each scenario, load base IDF, apply parameters, save new IDF
    for i in range(num_scenarios):
        print(f"\n--- Creating scenario #{i} for building {building_id} ---")

        hvac_df   = hvac_groups.get_group(i)
        dhw_df    = dhw_groups.get_group(i)
        vent_df   = vent_groups.get_group(i)
        elec_df   = elec_groups.get_group(i)
        fenez_df  = fenez_groups.get_group(i)

        hvac_params  = _make_param_dict(hvac_df)
        dhw_params   = _make_param_dict(dhw_df)
        vent_params  = _make_param_dict(vent_df)
        elec_params  = _make_param_dict(elec_df)
        fenez_params = _make_param_dict(fenez_df)

        # Load base IDF
        idf = load_idf(base_idf_path, idd_path)

        # Apply HVAC
        apply_building_level_hvac(idf, hvac_params)
        # apply_zone_level_hvac(idf, hvac_params)  # if zone-level needed

        # Apply DHW
        apply_dhw_params_to_idf(idf, dhw_params, suffix=f"Scenario_{i}")

        # Apply Vent
        apply_building_level_vent(idf, vent_params)
        # apply_zone_level_vent(idf, vent_params)  # if zone-level needed

        # Apply Elec (if you have a function for that)
        # apply_elec_params_to_idf(idf, elec_params)

        # 5f) **FIX**: Apply Fenestration. 
        # Instead of passing a CSV path, pass a dict describing the building and param picks:
        building_row = {"ogc_fid": building_id}  # minimal example
        apply_building_level_fenez(
            idf=idf,
            building_row=building_row,     # must be a dict, not a string
            user_config_fenez=fenez_params # pass the scenario's fenestration picks
        )

        # If you wanted the object-level approach:
        # apply_object_level_fenez(idf, fenez_df)

        # 6) Save scenario IDF
        scenario_idf_name = f"building_{building_id}_scenario_{i}.idf"
        scenario_idf_path = os.path.join(output_idf_dir, scenario_idf_name)
        save_idf(idf, scenario_idf_path)
        print(f"[INFO] Saved scenario IDF: {scenario_idf_path}")

    print("[INFO] All scenario IDFs generated successfully.")

    # 6) (Optional) Run Simulations
    if config.get("run_simulations", False):
        print("\n[INFO] Running simulations for scenario IDFs...")
        sim_cfg = config.get("simulation_config", {})
        # simulate_all(...) or similar code
        # ...
        print("[INFO] Simulations complete (placeholder).")

    # 7) (Optional) Post-processing
    if config.get("perform_post_process", False):
        print("[INFO] Performing post-processing merges (placeholder).")
        ppcfg = config.get("post_process_config", {})
        # merge_all_results(...) etc.
        # ...
        print("[INFO] Post-processing step complete (placeholder).")

    # 8) (Optional) Validation
    if config.get("perform_validation", False):
        print("[INFO] Performing validation on scenario results (placeholder).")
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
