"""
main_modifi.py

Handles the generation of scenario-based IDFs for sensitivity, surrogate,
calibration, or any parametric runs, then optionally runs E+ simulation,
post-processing, and validation in a job-specific folder if provided.

Usage:
  - Typically invoked from your orchestrator (or command line) with a config dict:
    {
      "base_idf_path": "output_IDFs/building_0.idf",
      "idd_path": "EnergyPlus/Energy+.idd",
      "assigned_csv": {
        "hvac_building": "output/assigned/assigned_hvac_building.csv",
        "hvac_zones": "output/assigned/assigned_hvac_zones.csv",
        "dhw": "output/assigned/assigned_dhw_params.csv",
        "vent_build": "output/assigned/assigned_vent_building.csv",
        "vent_zones": "output/assigned/assigned_vent_zones.csv",
        "elec": "output/assigned/assigned_lighting.csv",
        "fenez": "output/assigned/structured_fenez_params.csv"
      },
      "scenario_csv": {
        "hvac": "output/scenarios/scenario_params_hvac.csv",
        "dhw": "output/scenarios/scenario_params_dhw.csv",
        "vent": "output/scenarios/scenario_params_vent.csv",
        "elec": "output/scenarios/scenario_params_elec.csv",
        "fenez": "output/scenarios/scenario_params_fenez.csv"
      },
      "output_idf_dir": "output/scenario_idfs",
      "building_id": 4136730,
      "num_scenarios": 5,
      "picking_method": "random_uniform",
      "picking_scale_factor": 0.5,

      "run_simulations": true,
      "simulation_config": {
        "num_workers": 4,
        "output_dir": "output/Sim_Results/Scenarios"
      },
      "perform_post_process": true,
      "post_process_config": {
        "output_csv_as_is": "output/results_scenarioes/merged_as_is_scenarios.csv",
        "output_csv_daily_mean": "output/results_scenarioes/merged_daily_mean_scenarios.csv"
      },
      "perform_validation": true,
      "validation_config": {
        "real_data_csv": "data/mock_merged_daily_mean.csv",
        "sim_data_csv": "output/results_scenarioes/merged_daily_mean_scenarios.csv",
        "bldg_ranges": { "0": [0,1,2] },
        "variables_to_compare": [...],
        "threshold_cv_rmse": 30.0,
        "skip_plots": true,
        "output_csv": "scenario_validation_report.csv"
      },

      "job_output_dir": "/usr/src/app/output/xxxx-uuid"   # (Optional)
    }
"""

import os
import logging
import pandas as pd

# ---------------------------------------------------------------------------
# A) Common Utilities
# ---------------------------------------------------------------------------
from modification.common_utils import (
    load_assigned_csv,
    load_scenario_csv,
    load_idf,
    save_idf,
    generate_multiple_param_sets,
    save_param_scenarios_to_csv
)

# ---------------------------------------------------------------------------
# B) Modules for scenario creation & application
# ---------------------------------------------------------------------------
from modification.hvac_functions import (
    create_hvac_scenarios,
    apply_building_level_hvac,
    apply_zone_level_hvac
)
from modification.dhw_functions import (
    create_dhw_scenarios,
    apply_dhw_params_to_idf
)
from modification.vent_functions import (
    create_vent_scenarios,
    apply_building_level_vent,
    apply_zone_level_vent
)
from modification.elec_functions import (
    create_elec_scenarios,
    apply_building_level_elec,
    apply_object_level_elec
)
from modification.fenez_functions2 import (
    create_fenez_scenarios,
    apply_object_level_fenez
)


# NEW: Import the shading functions
from modification.shading_functions import create_shading_scenarios, apply_shading_params_to_idf

from modification.equipment_functions import create_equipment_scenarios, apply_equipment_params_to_idf

from modification.zone_sizing_functions import create_zone_sizing_scenarios, apply_zone_sizing_params_to_idf




# ---------------------------------------------------------------------------
# C) Simulation + Post-processing + Validation
# ---------------------------------------------------------------------------
from epw.run_epw_sims import simulate_all
from postproc.merge_results import merge_all_results
#from validation.main_validation import run_validation_process


def run_all_idfs_in_folder(
    folder_path: str,
    iddfile: str,
    base_output_dir: str,
    default_lat: float = 52.15,
    default_lon: float = 4.40,
    default_year: int = 2020,
    num_workers: int = 4
):
    """
    Utility function to find .idf files in folder_path and run them with simulate_all(...).
    Adjust lat/lon/year or load them from a side CSV if needed.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"[run_all_idfs_in_folder] Searching .idf files in {folder_path}")

    if not os.path.isdir(folder_path):
        logger.warning(f"[run_all_idfs_in_folder] Folder not found => {folder_path}")
        return

    idf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".idf")]
    if not idf_files:
        logger.warning(f"[run_all_idfs_in_folder] No .idf files in {folder_path} to run.")
        return

    data_rows = []
    for idx, idf_name in enumerate(idf_files):
        data_rows.append({
            "idf_name": idf_name,
            "lat": default_lat,
            "lon": default_lon,
            "desired_climate_year": default_year,
            "ogc_fid": idx  # or parse from filename
        })

    df_scenarios = pd.DataFrame(data_rows)
    logger.info(f"[run_all_idfs_in_folder] Running {len(df_scenarios)} scenario IDFs with simulate_all...")

    simulate_all(
        df_buildings=df_scenarios,
        idf_directory=folder_path,
        iddfile=iddfile,
        base_output_dir=base_output_dir,
        user_config_epw=None,
        assigned_epw_log=None,
        num_workers=num_workers
    )
    logger.info("[run_all_idfs_in_folder] Simulations triggered.")


def run_modification_workflow(config):
    """
    Main function for scenario-based IDF creation + optional E+ simulation,
    post-processing, and validation.

    Steps:
      1) Resolve folder paths (scenario IDFs, results) based on config + optional job_output_dir.
      2) Load assigned CSV data (HVAC, DHW, Vent, Elec, Fenez).
      3) Filter for the chosen building.
      4) Generate scenario param picks (random or otherwise).
      5) For each scenario, load a fresh base IDF, apply picks, save scenario IDF.
      6) (Optional) run E+ sims for these scenario IDFs, then post-process, then validate.

    :param config: dict
    :return: None
    """
    logger = logging.getLogger(__name__)
    logger.info("[MODIFICATION] Starting scenario-based workflow...")

    # -----------------------------------------------------------------------
    # 1) Extract config parts & resolve paths
    # -----------------------------------------------------------------------
    base_idf_path   = config["base_idf_path"]
    idd_path        = config["idd_path"]
    assigned_csvs   = config["assigned_csv"]
    scenario_csvs   = config["scenario_csv"]
    building_id     = config["building_id"]
    num_scenarios   = config["num_scenarios"]
    picking_method  = config["picking_method"]
    scale_factor    = config.get("picking_scale_factor", 1.0)

    # The user might specify something like "output/scenario_idfs" or just "scenario_idfs".
    scenario_idf_dir = config.get("output_idf_dir", "output/scenario_idfs")

    # Also we have simulation, post-processing, and validation flags:
    run_sims        = config.get("run_simulations", False)
    sim_cfg         = config.get("simulation_config", {})
    do_postproc     = config.get("perform_post_process", False)
    postproc_cfg    = config.get("post_process_config", {})
    do_validation   = config.get("perform_validation", False)
    validation_cfg  = config.get("validation_config", {})

    # If "job_output_dir" is provided, make scenario_idf_dir relative to it (if it's not absolute).
    job_output_dir = config.get("job_output_dir")  # optional
    if job_output_dir and not os.path.isabs(scenario_idf_dir):
        scenario_idf_dir = os.path.join(job_output_dir, scenario_idf_dir)
    os.makedirs(scenario_idf_dir, exist_ok=True)

    logger.info(f"[MODIFICATION] Scenario IDFs will be placed in: {scenario_idf_dir}")

    # -----------------------------------------------------------------------
    # 2) Load assigned CSV data
    # -----------------------------------------------------------------------
    # HVAC
    df_hvac_bld = None
    df_hvac_zn  = None
    if "hvac_building" in assigned_csvs and "hvac_zones" in assigned_csvs:
        df_hvac_bld = load_assigned_csv(assigned_csvs["hvac_building"])
        df_hvac_zn  = load_assigned_csv(assigned_csvs["hvac_zones"])
    elif "hvac" in assigned_csvs:
        df_hvac_bld = load_assigned_csv(assigned_csvs["hvac"])

    # DHW
    df_dhw = load_assigned_csv(assigned_csvs["dhw"]) if "dhw" in assigned_csvs else None

    # Vent
    df_vent_bld = None
    df_vent_zn  = None
    if "vent_build" in assigned_csvs and "vent_zones" in assigned_csvs:
        df_vent_bld = load_assigned_csv(assigned_csvs["vent_build"])
        df_vent_zn  = load_assigned_csv(assigned_csvs["vent_zones"])
    elif "vent" in assigned_csvs:
        df_vent_bld = load_assigned_csv(assigned_csvs["vent"])

    # Elec
    df_elec  = load_assigned_csv(assigned_csvs["elec"])  if "elec"  in assigned_csvs else None

    # Fenestration
    df_fenez = load_assigned_csv(assigned_csvs["fenez"]) if "fenez" in assigned_csvs else None

    # NEW: Load assigned shading data
    df_shading = load_assigned_csv(assigned_csvs["shading"]) if "shading" in assigned_csvs else None

    #  Load assigned CSV data
    df_equip = load_assigned_csv(assigned_csvs["equip"]) if "equip" in assigned_csvs else None
    # Zone sizing
    df_zone_sizing = load_assigned_csv(assigned_csvs["zone_sizing"]) if "zone_sizing" in assigned_csvs else None
    



    # -----------------------------------------------------------------------
    # 3) Filter data for this building
    # -----------------------------------------------------------------------
    def filter_for_building(df):
        if df is not None and not df.empty:
            return df[df["ogc_fid"] == building_id].copy()
        return pd.DataFrame()

    df_hvac_bld_sub = filter_for_building(df_hvac_bld)
    df_hvac_zn_sub  = filter_for_building(df_hvac_zn)
    df_dhw_sub      = filter_for_building(df_dhw)
    df_vent_bld_sub = filter_for_building(df_vent_bld)
    df_vent_zn_sub  = filter_for_building(df_vent_zn)
    df_elec_sub     = filter_for_building(df_elec)
    df_fenez_sub    = filter_for_building(df_fenez)



    # NEW: Filter shading data. It uses 'window_id', not 'ogc_fid'.
    # We assume for now that all windows in the base IDF belong to the target building.
    df_shading_sub = df_shading.copy() if df_shading is not None else pd.DataFrame()

    df_equip_sub = filter_for_building(df_equip)
    df_zone_sizing_sub = filter_for_building(df_zone_sizing)



    # -----------------------------------------------------------------------
    # 4) Generate scenario picks (random or otherwise)
    # -----------------------------------------------------------------------
    # HVAC
    if not df_hvac_bld_sub.empty:
        if not df_hvac_zn_sub.empty:
            # multi-step scenario creation for building & zone
            create_hvac_scenarios(
                df_building=df_hvac_bld_sub,
                df_zones=df_hvac_zn_sub,
                building_id=building_id,
                num_scenarios=num_scenarios,
                picking_method=picking_method,
                random_seed=42,
                scenario_csv_out=scenario_csvs["hvac"]
            )
        else:
            hvac_scen = generate_multiple_param_sets(
                df_main_sub=df_hvac_bld_sub,
                num_sets=num_scenarios,
                picking_method=picking_method,
                scale_factor=scale_factor
            )
            save_param_scenarios_to_csv(hvac_scen, building_id, scenario_csvs["hvac"])

    # DHW
    if not df_dhw_sub.empty:
        create_dhw_scenarios(
            df_dhw_input=df_dhw_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["dhw"]
        )

    # Vent
    if not df_vent_bld_sub.empty or not df_vent_zn_sub.empty:
        create_vent_scenarios(
            df_building=df_vent_bld_sub,
            df_zones=df_vent_zn_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["vent"]
        )

    # Elec
    if not df_elec_sub.empty:
        create_elec_scenarios(
            df_lighting=df_elec_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["elec"]
        )

    # Fenestration
    if not df_fenez_sub.empty:
        create_fenez_scenarios(
            df_struct_fenez=df_fenez_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["fenez"]
        )

    # NEW: Generate shading scenarios
    if not df_shading_sub.empty:
        create_shading_scenarios(
            df_shading_input=df_shading_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["shading"]
        )


    # eequip
    if not df_equip_sub.empty:
        create_equipment_scenarios(
            df_equipment_input=df_equip_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["equip"]
        )

    # Sizingg
    if not df_zone_sizing_sub.empty:
        create_zone_sizing_scenarios(
            df_sizing_input=df_zone_sizing_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method='random_uniform', # This function handles its own logic
            random_seed=42,
            scenario_csv_out=scenario_csvs["zone_sizing"]
        )




    # -----------------------------------------------------------------------
    # 5) Load scenario CSV => group by scenario_index
    # -----------------------------------------------------------------------
    def safe_load_scenario(csv_path):
        if os.path.isfile(csv_path):
            return load_scenario_csv(csv_path)
        return pd.DataFrame()

    df_hvac_scen  = safe_load_scenario(scenario_csvs["hvac"])
    df_dhw_scen   = safe_load_scenario(scenario_csvs["dhw"])
    df_vent_scen  = safe_load_scenario(scenario_csvs["vent"])
    df_elec_scen  = safe_load_scenario(scenario_csvs["elec"])
    df_fenez_scen = safe_load_scenario(scenario_csvs["fenez"])
    # NEW: Load shading scenarios
    df_shading_scen = safe_load_scenario(scenario_csvs["shading"])
    df_equip_scen = safe_load_scenario(scenario_csvs["equip"])
    df_sizing_scen = safe_load_scenario(scenario_csvs["zone_sizing"])


    hvac_groups  = df_hvac_scen.groupby("scenario_index")  if not df_hvac_scen.empty  else None
    dhw_groups   = df_dhw_scen.groupby("scenario_index")   if not df_dhw_scen.empty   else None
    vent_groups  = df_vent_scen.groupby("scenario_index")  if not df_vent_scen.empty  else None
    elec_groups  = df_elec_scen.groupby("scenario_index")  if not df_elec_scen.empty  else None
    fenez_groups = df_fenez_scen.groupby("scenario_index") if not df_fenez_scen.empty else None

    # NEW: Group shading scenarios
    shading_groups = df_shading_scen.groupby("scenario_index") if not df_shading_scen.empty else None
    equip_groups = df_equip_scen.groupby("scenario_index") if not df_equip_scen.empty else None
    sizing_groups = df_sizing_scen.groupby("scenario_index") if not df_sizing_scen.empty else None


    # -----------------------------------------------------------------------
    # 6) For each scenario, load base IDF, apply parameters, save new IDF
    # -----------------------------------------------------------------------
    for i in range(num_scenarios):
        logger.info(f"[MODIFICATION] => Creating scenario #{i} for building {building_id}")

        hvac_df   = hvac_groups.get_group(i) if hvac_groups and i in hvac_groups.groups else pd.DataFrame()
        dhw_df    = dhw_groups.get_group(i)  if dhw_groups  and i in dhw_groups.groups  else pd.DataFrame()
        vent_df   = vent_groups.get_group(i) if vent_groups and i in vent_groups.groups else pd.DataFrame()
        elec_df   = elec_groups.get_group(i) if elec_groups and i in elec_groups.groups else pd.DataFrame()
        fenez_df  = fenez_groups.get_group(i)if fenez_groups and i in fenez_groups.groups else pd.DataFrame()
        # NEW: Get the shading data for this specific scenario
        shading_df = shading_groups.get_group(i) if shading_groups and i in shading_groups.groups else pd.DataFrame()
        equip_df = equip_groups.get_group(i) if equip_groups and i in equip_groups.groups else pd.DataFrame()
        sizing_df = sizing_groups.get_group(i) if sizing_groups and i in sizing_groups.groups else pd.DataFrame()


        hvac_bld_df   = hvac_df[hvac_df["zone_name"].isna()]
        hvac_zone_df  = hvac_df[hvac_df["zone_name"].notna()]
        hvac_params   = _make_param_dict(hvac_bld_df)

        dhw_params    = _make_param_dict(dhw_df)

        vent_bld_df   = vent_df[vent_df["zone_name"].isnull()]
        vent_zone_df  = vent_df[vent_df["zone_name"].notnull()]
        vent_params   = _make_param_dict(vent_bld_df)

        elec_params   = _make_param_dict(elec_df)

        # Load base IDF
        idf = load_idf(base_idf_path, idd_path)

        # Apply HVAC
        apply_building_level_hvac(idf, hvac_params)
        apply_zone_level_hvac(idf, hvac_zone_df)

        # Apply DHW
        apply_dhw_params_to_idf(idf, dhw_params, suffix=f"Scenario_{i}")

        # Apply Vent
        if not vent_bld_df.empty or not vent_zone_df.empty:
            apply_building_level_vent(idf, vent_params)
            apply_zone_level_vent(idf, vent_zone_df)

        # Apply Elec => building-level or object-level
        if not elec_df.empty:
            apply_building_level_elec(idf, elec_params, zonelist_name="ALL_ZONES")
            # or use apply_object_level_elec(idf, elec_df) if you prefer

        # Apply Fenestration => object-level
        apply_object_level_fenez(idf, fenez_df)

        # NEW: Apply shading parameters
        apply_shading_params_to_idf(idf, shading_df)
        apply_equipment_params_to_idf(idf, equip_df)
        apply_zone_sizing_params_to_idf(idf, sizing_df)

        # Save scenario IDF
        scenario_idf_name = f"building_{building_id}_scenario_{i}.idf"
        scenario_idf_path = os.path.join(scenario_idf_dir, scenario_idf_name)
        save_idf(idf, scenario_idf_path)
        logger.info(f"[MODIFICATION] Saved scenario IDF => {scenario_idf_path}")

    logger.info("[MODIFICATION] All scenario IDFs generated successfully.")

    # -----------------------------------------------------------------------
    # 7) (Optional) Simulations
    # -----------------------------------------------------------------------
    if run_sims:
        logger.info("[MODIFICATION] Running E+ simulations for all scenario IDFs.")
        base_sim_dir = sim_cfg.get("output_dir", "output/Sim_Results/Scenarios")

        # if job_output_dir is given, we can make the sim results go inside it, too:
        if job_output_dir and not os.path.isabs(base_sim_dir):
            base_sim_dir = os.path.join(job_output_dir, base_sim_dir)
        os.makedirs(base_sim_dir, exist_ok=True)

        num_workers  = sim_cfg.get("num_workers", 4)

        run_all_idfs_in_folder(
            folder_path=scenario_idf_dir,
            iddfile=idd_path,
            base_output_dir=base_sim_dir,
            default_lat=52.15,
            default_lon=4.40,
            default_year=2020,
            num_workers=num_workers
        )

    # -----------------------------------------------------------------------
    # 8) (Optional) Post-processing
    # -----------------------------------------------------------------------
    if do_postproc:
        logger.info("[MODIFICATION] Performing post-processing merges.")

        base_sim_dir = sim_cfg.get("output_dir", "output/Sim_Results/Scenarios")
        if job_output_dir and not os.path.isabs(base_sim_dir):
            base_sim_dir = os.path.join(job_output_dir, base_sim_dir)

        output_csv_as_is = postproc_cfg.get("output_csv_as_is", "")
        output_csv_daily_mean = postproc_cfg.get("output_csv_daily_mean", "")

        # Build full paths inside job_output_dir if they are relative
        if output_csv_as_is:
            if job_output_dir and not os.path.isabs(output_csv_as_is):
                output_csv_as_is = os.path.join(job_output_dir, output_csv_as_is)
            os.makedirs(os.path.dirname(output_csv_as_is), exist_ok=True)

            merge_all_results(
                base_output_dir=base_sim_dir,
                output_csv=output_csv_as_is,
                convert_to_daily=False,
                convert_to_monthly=False
            )

        if output_csv_daily_mean:
            if job_output_dir and not os.path.isabs(output_csv_daily_mean):
                output_csv_daily_mean = os.path.join(job_output_dir, output_csv_daily_mean)
            os.makedirs(os.path.dirname(output_csv_daily_mean), exist_ok=True)

            merge_all_results(
                base_output_dir=base_sim_dir,
                output_csv=output_csv_daily_mean,
                convert_to_daily=True,
                daily_aggregator="mean",
                convert_to_monthly=False
            )

        logger.info("[MODIFICATION] Post-processing step complete.")

    # -----------------------------------------------------------------------
    # 9) (Optional) Validation
    # -----------------------------------------------------------------------
    if do_validation:
        logger.info("[MODIFICATION] Performing scenario validation with config => %s", validation_cfg)

        # If the validation config references CSV paths that might be relative,
        # you could also adjust them to be inside job_output_dir here if desired.
        # e.g.:
        # real_csv = validation_cfg.get("real_data_csv", "")
        # if job_output_dir and not os.path.isabs(real_csv):
        #     real_csv = os.path.join(job_output_dir, real_csv)
        # validation_cfg["real_data_csv"] = real_csv

        run_validation_process(validation_cfg)
        logger.info("[MODIFICATION] Validation step complete.")


def _make_param_dict(df_scenario):
    """
    Builds a dict {param_name: value} from the scenario DataFrame columns,
    checking 'assigned_value' or 'param_value'.
    """
    if df_scenario.empty:
        return {}

    cols = df_scenario.columns.tolist()
    if "assigned_value" in cols:
        val_col = "assigned_value"
    elif "param_value" in cols:
        val_col = "param_value"
    else:
        raise AttributeError(
            "No 'assigned_value' or 'param_value' column found in scenario dataframe! "
            f"Columns are: {cols}"
        )

    result = {}
    for row in df_scenario.itertuples():
        p_name = row.param_name
        raw_val = getattr(row, val_col)
        try:
            result[p_name] = float(raw_val)
        except (ValueError, TypeError):
            result[p_name] = raw_val
    return result
