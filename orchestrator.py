"""
orchestrator.py

Orchestrates the entire EnergyPlus workflow using a job-specific subfolder
for config files. This supports concurrency and avoids overwriting each other's
`main_config.json`.

Steps:
  1. Get the subfolder from job_config["job_subfolder"] (e.g., user_configs/<job_id>)
  2. Load main_config.json from that folder
  3. Optionally deep-merge posted_data["main_config"] if needed
  4. Apply Excel overrides, JSON overrides, etc.
  5. Perform IDF creation, structuring, scenario modifications, validation, etc.
  6. Respect cancellation if cancel_event.is_set().

Usage:
  Called from job_manager.py, inside _job_thread_runner, for each job.

CAVEATS:
  - If your code references 'excel_overrides', 'user_config_overrides', etc.,
    ensure those are found inside the newly loaded main_config. 
  - Each job writes output CSV in /output or /output/<job_id> as you prefer.
"""

import os
import json
import logging
import pandas as pd
import threading

# Imports for your modules
from splitter import deep_merge_dicts
from database_handler import load_buildings_from_db
from excel_overrides import (
    override_dhw_lookup_from_excel_file,
    override_epw_lookup_from_excel_file,
    override_lighting_lookup_from_excel_file,
    override_hvac_lookup_from_excel_file,
    override_vent_lookup_from_excel_file
)
from idf_objects.fenez.fenez_config_manager import build_fenez_config
import idf_creation
from idf_creation import create_idfs_for_all_buildings
from main_modifi import run_modification_workflow
from validation.main_validation import run_validation_process
from cal.unified_sensitivity import run_sensitivity_analysis
from cal.unified_surrogate import (
    load_scenario_params as sur_load_scenario_params,
    pivot_scenario_params,
    filter_top_parameters,
    load_sim_results,
    aggregate_results,
    merge_params_with_results,
    build_and_save_surrogate
)
from cal.unified_calibration import run_unified_calibration

# A custom exception to handle user-requested cancellation
class WorkflowCanceled(Exception):
    pass

def orchestrate_workflow(job_config: dict, cancel_event: threading.Event = None):
    """
    Orchestrates the entire E+ workflow using a job-specific subfolder for config JSON.

    job_config typically has:
      {
        "job_subfolder": "/usr/src/app/user_configs/<job_id>",
        "posted_data": {...},  # optional
      }

    1) Load user_configs/<job_id>/main_config.json
       => 'main_config' inside it might contain your high-level settings.
    2) (Optional) if posted_data["main_config"] is present, you can deep-merge it again.
    3) Apply Excel overrides, JSON overrides, create IDFs, run sims, etc.
    4) Check cancel_event between major steps to allow graceful stop.

    Args:
        job_config (dict): A dictionary stored in job_manager, includes "job_subfolder".
        cancel_event (threading.Event): If set, we gracefully exit early.

    Returns:
        None (but logs extensively).
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Starting orchestrate_workflow ===")

    def check_canceled():
        """
        If cancel_event is set, raise WorkflowCanceled so the job_manager can mark status=CANCELED.
        """
        if cancel_event and cancel_event.is_set():
            logger.warning("=== CANCEL event detected. Stopping workflow. ===")
            raise WorkflowCanceled("Workflow was canceled by user request.")

    # 1) Identify the job-specific subfolder (e.g. user_configs/<job_id>)
    user_configs_folder = job_config.get("job_subfolder")
    if not user_configs_folder or not os.path.isdir(user_configs_folder):
        logger.error(f"[ERROR] job_subfolder not found or invalid => {user_configs_folder}")
        return  # or raise an exception

    # 2) Load main_config.json from that subfolder
    main_config_path = os.path.join(user_configs_folder, "main_config.json")
    if not os.path.isfile(main_config_path):
        logger.error(f"[ERROR] Cannot find main_config.json at {main_config_path}")
        return

    with open(main_config_path, "r") as f:
        existing_config_raw = json.load(f)

    # Some folks structure main_config.json as {"main_config": { ... }}.
    # If so, adjust accordingly:
    main_config = existing_config_raw.get("main_config", {})
    logger.info(f"[INFO] Loaded existing main_config from {main_config_path}.")

    # 2.5) Optionally deep-merge posted_data["main_config"] if you want to re-override:
    posted_data = job_config.get("posted_data", {})
    if "main_config" in posted_data:
        logger.info("[INFO] Deep merging job_config['posted_data']['main_config'] into main_config.")
        deep_merge_dicts(main_config, posted_data["main_config"])
        # Optionally re-save if you want:
        with open(main_config_path, "w") as f:
            json.dump({"main_config": main_config}, f, indent=2)

    # 3) Extract sub-sections from main_config
    check_canceled()
    paths_dict       = main_config.get("paths", {})
    excel_flags      = main_config.get("excel_overrides", {})
    user_flags       = main_config.get("user_config_overrides", {})
    def_dicts        = main_config.get("default_dicts", {})
    structuring_cfg  = main_config.get("structuring", {})
    modification_cfg = main_config.get("modification", {})
    validation_cfg   = main_config.get("validation", {})
    sens_cfg         = main_config.get("sensitivity", {})
    sur_cfg          = main_config.get("surrogate", {})
    cal_cfg          = main_config.get("calibration", {})

    # From idf_creation block
    idf_cfg = main_config.get("idf_creation", {})
    perform_idf_creation = idf_cfg.get("perform_idf_creation", False)
    scenario             = idf_cfg.get("scenario", "scenario1")
    calibration_stage    = idf_cfg.get("calibration_stage", "pre_calibration")
    strategy             = idf_cfg.get("strategy", "B")
    random_seed          = idf_cfg.get("random_seed", 42)
    run_simulations      = idf_cfg.get("run_simulations", True)
    simulate_config      = idf_cfg.get("simulate_config", {})
    post_process         = idf_cfg.get("post_process", True)
    post_process_config  = idf_cfg.get("post_process_config", {})
    output_definitions   = idf_cfg.get("output_definitions", {})
    use_database         = main_config.get("use_database", False)
    db_filter            = main_config.get("db_filter", {})

    # 4) Possibly override idf_creation.idf_config with environment variables
    check_canceled()
    env_idd_path = os.environ.get("IDD_PATH")
    if env_idd_path:
        idf_creation.idf_config["iddfile"] = env_idd_path

    env_base_idf = os.environ.get("BASE_IDF_PATH")
    if env_base_idf:
        idf_creation.idf_config["idf_file_path"] = env_base_idf

    env_out_dir = os.environ.get("OUTPUT_DIR")
    if env_out_dir:
        out_idf_dir = os.path.join(env_out_dir, "output_IDFs")
        idf_creation.idf_config["output_dir"] = out_idf_dir

    # Merge local config from idf_cfg
    if "iddfile" in idf_cfg:
        idf_creation.idf_config["iddfile"] = idf_cfg["iddfile"]
    if "idf_file_path" in idf_cfg:
        idf_creation.idf_config["idf_file_path"] = idf_cfg["idf_file_path"]
    if "output_idf_dir" in idf_cfg:
        idf_creation.idf_config["output_dir"] = idf_cfg["output_idf_dir"]

    # 5) Setup default dictionaries from def_dicts
    base_res_data    = def_dicts.get("res_data", {})
    base_nonres_data = def_dicts.get("nonres_data", {})
    dhw_lookup       = def_dicts.get("dhw", {})
    epw_lookup       = def_dicts.get("epw", [])
    lighting_lookup  = def_dicts.get("lighting", {})
    hvac_lookup      = def_dicts.get("hvac", {})
    vent_lookup      = def_dicts.get("vent", {})

    # 6) Apply Excel overrides if flags are set
    check_canceled()
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=base_res_data,
        base_nonres_data=base_nonres_data,
        excel_path=paths_dict.get("fenez_excel", ""),
        do_excel_override=excel_flags.get("override_fenez_excel", False),
        user_fenez_overrides=[]
    )

    if excel_flags.get("override_dhw_excel", False):
        dhw_lookup = override_dhw_lookup_from_excel_file(
            dhw_excel_path=paths_dict.get("dhw_excel", ""),
            default_dhw_lookup=dhw_lookup,
            override_dhw_flag=True
        )

    if excel_flags.get("override_epw_excel", False):
        epw_lookup = override_epw_lookup_from_excel_file(
            epw_excel_path=paths_dict.get("epw_excel", ""),
            epw_lookup=epw_lookup,
            override_epw_flag=True
        )

    if excel_flags.get("override_lighting_excel", False):
        lighting_lookup = override_lighting_lookup_from_excel_file(
            lighting_excel_path=paths_dict.get("lighting_excel", ""),
            lighting_lookup=lighting_lookup,
            override_lighting_flag=True
        )

    if excel_flags.get("override_hvac_excel", False):
        hvac_lookup = override_hvac_lookup_from_excel_file(
            hvac_excel_path=paths_dict.get("hvac_excel", ""),
            hvac_lookup=hvac_lookup,
            override_hvac_flag=True
        )

    if excel_flags.get("override_vent_excel", False):
        vent_lookup = override_vent_lookup_from_excel_file(
            vent_excel_path=paths_dict.get("vent_excel", ""),
            vent_lookup=vent_lookup,
            override_vent_flag=True
        )

    # 7) JSON overrides from the same job_subfolder if user_flags are set
    check_canceled()

    def safe_load_subjson(fname, key):
        """
        Loads user_configs/<job_id>/fname if it exists, returns data.get(key).
        Example usage: safe_load_subjson('fenestration.json', 'fenestration')
        """
        full_path = os.path.join(user_configs_folder, fname)
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r") as f:
                    data = json.load(f)
                return data.get(key)
            except Exception as e:
                logger.error(f"[ERROR] loading {fname} => {e}")
        return None

    # Fenestration
    user_fenez_data = []
    if user_flags.get("override_fenez_json", False):
        loaded = safe_load_subjson("fenestration.json", "fenestration")
        if loaded:
            user_fenez_data = loaded

    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=updated_res_data,
        base_nonres_data=updated_nonres_data,
        excel_path="",  # no further excel
        do_excel_override=False,
        user_fenez_overrides=user_fenez_data
    )

    user_config_dhw = None
    if user_flags.get("override_dhw_json", False):
        user_config_dhw = safe_load_subjson("dhw.json", "dhw")

    user_config_epw = []
    if user_flags.get("override_epw_json", False):
        e = safe_load_subjson("epw.json", "epw")
        if e:
            user_config_epw = e

    user_config_lighting = None
    if user_flags.get("override_lighting_json", False):
        user_config_lighting = safe_load_subjson("lighting.json", "lighting")

    user_config_hvac = None
    if user_flags.get("override_hvac_json", False):
        user_config_hvac = safe_load_subjson("hvac.json", "hvac")

    user_config_vent = []
    if user_flags.get("override_vent_json", False):
        v = safe_load_subjson("vent.json", "vent")
        if v:
            user_config_vent = v

    geom_data = {}
    if user_flags.get("override_geometry_json", False):
        g = safe_load_subjson("geometry.json", "geometry")
        if g:
            geom_data["geometry"] = g

    shading_data = {}
    if user_flags.get("override_shading_json", False):
        s = safe_load_subjson("shading.json", "shading")
        if s:
            shading_data["shading"] = s

    # 8) IDF Creation
    check_canceled()
    if perform_idf_creation:
        logger.info("[INFO] IDF creation is ENABLED.")

        # a) Load building data from DB or CSV
        df_buildings = pd.DataFrame()
        if use_database:
            logger.info("[INFO] Loading building data from DB.")
            df_buildings = load_buildings_from_db(db_filter)
        else:
            bldg_data_path = paths_dict.get("building_data", "")
            if os.path.isfile(bldg_data_path):
                df_buildings = pd.read_csv(bldg_data_path)
            else:
                logger.warning(f"[WARN] building_data CSV not found => {bldg_data_path}")

        # b) Actually create IDFs
        create_idfs_for_all_buildings(
            df_buildings=df_buildings,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=random_seed,
            user_config_geom=geom_data.get("geometry", []),
            user_config_lighting=user_config_lighting,
            user_config_dhw=user_config_dhw,
            res_data=updated_res_data,
            nonres_data=updated_nonres_data,
            user_config_hvac=user_config_hvac,
            user_config_vent=user_config_vent,
            user_config_epw=user_config_epw,
            output_definitions=output_definitions,
            run_simulations=run_simulations,
            simulate_config=simulate_config,
            post_process=post_process,
            post_process_config=post_process_config
        )
    else:
        logger.info("[INFO] Skipping IDF creation.")

    # 9) Structuring
    check_canceled()
    if structuring_cfg.get("perform_structuring", False):
        logger.info("[INFO] Performing structuring ...")

        # For example, fenestration
        from idf_objects.structuring.fenestration_structuring import transform_fenez_log_to_structured_with_ranges
        fenez_conf = structuring_cfg.get("fenestration", {})
        fenez_in   = fenez_conf.get("csv_in",  "output/assigned/assigned_fenez_params.csv")
        fenez_out  = fenez_conf.get("csv_out", "output/assigned/structured_fenez_params.csv")
        transform_fenez_log_to_structured_with_ranges(csv_input=fenez_in, csv_output=fenez_out)

        # Similarly for DHW
        from idf_objects.structuring.dhw_structuring import transform_dhw_log_to_structured
        dhw_conf = structuring_cfg.get("dhw", {})
        dhw_in   = dhw_conf.get("csv_in",  "output/assigned/assigned_dhw_params.csv")
        dhw_out  = dhw_conf.get("csv_out", "output/assigned/structured_dhw_params.csv")
        transform_dhw_log_to_structured(dhw_in, dhw_out)

        # HVAC
        from idf_objects.structuring.flatten_hvac import flatten_hvac_data, parse_assigned_value as parse_hvac
        hvac_conf = structuring_cfg.get("hvac", {})
        hvac_in   = hvac_conf.get("csv_in", "output/assigned/assigned_hvac_params.csv")
        hvac_bld  = hvac_conf.get("build_out", "output/assigned/assigned_hvac_building.csv")
        hvac_zone = hvac_conf.get("zone_out",  "output/assigned/assigned_hvac_zones.csv")
        if os.path.isfile(hvac_in):
            df_hvac = pd.read_csv(hvac_in)
            df_hvac["assigned_value"] = df_hvac["assigned_value"].apply(parse_hvac)
            flatten_hvac_data(df_input=df_hvac, out_build_csv=hvac_bld, out_zone_csv=hvac_zone)

        # Vent
        from idf_objects.structuring.flatten_assigned_vent import flatten_ventilation_data, parse_assigned_value as parse_vent
        vent_conf = structuring_cfg.get("vent", {})
        vent_in   = vent_conf.get("csv_in", "output/assigned/assigned_ventilation.csv")
        vent_bld  = vent_conf.get("build_out", "output/assigned/assigned_vent_building.csv")
        vent_zone = vent_conf.get("zone_out",  "output/assigned/assigned_vent_zones.csv")
        if os.path.isfile(vent_in):
            df_vent = pd.read_csv(vent_in)
            df_vent["assigned_value"] = df_vent["assigned_value"].apply(parse_vent)
            flatten_ventilation_data(df_input=df_vent, out_build_csv=vent_bld, out_zone_csv=vent_zone)
    else:
        logger.info("[INFO] Skipping structuring.")

    # 10) Scenario Modification
    check_canceled()
    if modification_cfg.get("perform_modification", False):
        logger.info("[INFO] Scenario modification is ENABLED.")
        run_modification_workflow(modification_cfg["modify_config"])
    else:
        logger.info("[INFO] Skipping scenario modification.")

    # 11) Global Validation
    check_canceled()
    if validation_cfg.get("perform_validation", False):
        logger.info("[INFO] Global Validation is ENABLED.")
        run_validation_process(validation_cfg["config"])
    else:
        logger.info("[INFO] Skipping global validation.")

    # 12) Sensitivity Analysis
    check_canceled()
    if sens_cfg.get("perform_sensitivity", False):
        logger.info("[INFO] Sensitivity Analysis is ENABLED.")
        run_sensitivity_analysis(
            scenario_folder=sens_cfg["scenario_folder"],
            method=sens_cfg["method"],
            results_csv=sens_cfg.get("results_csv", ""),
            target_variable=sens_cfg.get("target_variable", []),
            output_csv=sens_cfg.get("output_csv", "sensitivity_output.csv"),
            n_morris_trajectories=sens_cfg.get("n_morris_trajectories", 10),
            num_levels=sens_cfg.get("num_levels", 4),
            n_sobol_samples=sens_cfg.get("n_sobol_samples", 128)
        )
    else:
        logger.info("[INFO] Skipping sensitivity analysis.")

    # 13) Surrogate Modeling
    check_canceled()
    if sur_cfg.get("perform_surrogate", False):
        logger.info("[INFO] Surrogate Modeling is ENABLED.")
        scenario_folder = sur_cfg["scenario_folder"]
        results_csv     = sur_cfg["results_csv"]
        target_var      = sur_cfg["target_variable"]
        model_out       = sur_cfg["model_out"]
        cols_out        = sur_cfg["cols_out"]
        test_size       = sur_cfg["test_size"]

        df_scen = sur_load_scenario_params(scenario_folder)
        pivot_df = pivot_scenario_params(df_scen)
        # pivot_df = filter_top_parameters(...) # if needed

        df_sim = load_sim_results(results_csv)
        df_agg = aggregate_results(df_sim)
        merged_df = merge_params_with_results(pivot_df, df_agg, target_var)

        rf_model, trained_cols = build_and_save_surrogate(
            df_data=merged_df,
            target_col=target_var,
            model_out_path=model_out,
            columns_out_path=cols_out,
            test_size=test_size,
            random_state=42
        )
        if rf_model:
            logger.info("[INFO] Surrogate model built & saved.")
        else:
            logger.warning("[WARN] Surrogate modeling failed or insufficient data.")
    else:
        logger.info("[INFO] Skipping surrogate modeling.")

    # 14) Calibration
    check_canceled()
    if cal_cfg.get("perform_calibration", False):
        logger.info("[INFO] Calibration is ENABLED.")
        run_unified_calibration(cal_cfg)
    else:
        logger.info("[INFO] Skipping calibration.")

    logger.info("=== End of orchestrate_workflow ===")
