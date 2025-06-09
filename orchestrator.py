"""
orchestrator.py

Orchestrates the entire EnergyPlus workflow using a job-specific subfolder
for config files and a job-specific folder in /output for results.

Steps:
  1. Retrieve 'job_id' from job_config (set by job_manager or app).
  2. Form an output directory: <OUTPUT_DIR>/<job_id>.
  3. Load main_config.json from user_configs/<job_id>.
  4. Merge with posted_data["main_config"] if present.
  5. Apply Excel overrides, JSON overrides, create IDFs, run sims, etc.
  6. If scenario modification is enabled, override paths so scenario IDFs/results
     stay in the same job folder, then run scenario-based modifications.
  7. Perform structuring (e.g., flatten assigned CSVs) if requested.
  8. Perform global validation, sensitivity, surrogate, calibration if requested;
     patch any relative CSV paths to be inside the job folder (unless "data/").
  9. Zip & email final results if mail_user.json is present.
  10. Respect any cancel_event from job_manager.
"""

import os
import json
import logging
import threading
import time
from contextlib import contextmanager
import pandas as pd

# Splitting / deep-merge
from splitter import deep_merge_dicts

# DB loading if needed
from database_handler import load_buildings_from_db

# Excel overrides
from excel_overrides import (
    override_dhw_lookup_from_excel_file,
    override_epw_lookup_from_excel_file,
    override_lighting_lookup_from_excel_file,
    override_hvac_lookup_from_excel_file,
    override_vent_lookup_from_excel_file
)

# Fenestration config
from idf_objects.fenez.fenez_config_manager import build_fenez_config


# IDF creation
import idf_creation
from idf_creation import create_idfs_for_all_buildings

# Scenario modification
from main_modifi import run_modification_workflow

# Validation
from validation.main_validation import run_validation_process

# Sensitivity / Surrogate / Calibration
from cal.unified_sensitivity import run_sensitivity_analysis
from cal.unified_surrogate import (
    load_scenario_params as sur_load_scenario_params,
    pivot_scenario_params,
    load_sim_results,
    aggregate_results,
    merge_params_with_results,
    build_and_save_surrogate
)
from cal.unified_calibration import run_unified_calibration

# Zip & email
from zip_and_mail import zip_user_output, send_results_email

from cleanup_old_jobs import cleanup_old_results


class WorkflowCanceled(Exception):
    """Custom exception used to stop the workflow if a cancel_event is set."""
    pass


@contextmanager
def step_timer(logger, name: str):
    """Context manager to log step durations."""
    logger.info(f"[STEP] Starting {name} ...")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"[STEP] Finished {name} in {elapsed:.2f} seconds.")


def orchestrate_workflow(job_config: dict, cancel_event: threading.Event = None):
    """
    Orchestrates the entire E+ workflow using a job-specific subfolder for config JSON,
    plus a job-specific output folder for results.

    Args:
        job_config (dict): includes:
            {
              "job_id": "<unique_id_for_this_job>",
              "job_subfolder": "user_configs/<job_id>",
              "posted_data": {...} (optional),
              ...
            }
        cancel_event (threading.Event): If set, we gracefully exit early.

    Raises:
        WorkflowCanceled if cancel_event is set mid-way.

    Returns:
        None (logs extensively, optionally zips/emails final results).
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Starting orchestrate_workflow ===")
    overall_start = time.perf_counter()

    # -------------------------------------------------------------------------
    # 0) Identify job_id, define check_canceled
    # -------------------------------------------------------------------------
    job_id = job_config.get("job_id", "unknown_job_id")
    logger.info(f"[INFO] Orchestrator for job_id={job_id}")

    def check_canceled():
        """Raise WorkflowCanceled if cancel_event is set."""
        if cancel_event and cancel_event.is_set():
            logger.warning("=== CANCEL event detected. Stopping workflow. ===")
            raise WorkflowCanceled("Workflow was canceled by user request.")


    # -------------------------------------------------------------------------
    # 12) Helper to handle patching CSVs that are "relative" but not "data/".
    # -------------------------------------------------------------------------
    def patch_if_relative(csv_path: str):
        """
        1) If absolute, return as-is.
        2) If starts with 'data/', interpret as /usr/src/app/data/... (no job folder).
        3) Else, join with job_output_dir.
        """
        if not csv_path:
            return csv_path
        if os.path.isabs(csv_path):
            return csv_path
        if csv_path.startswith("data/"):
            return os.path.join("/usr/src/app", csv_path)
        return os.path.join(job_output_dir, csv_path)





    # -------------------------------------------------------------------------
    # 1) Identify the user_configs folder (where main_config.json resides)
    # -------------------------------------------------------------------------
    user_configs_folder = job_config.get("job_subfolder")
    if not user_configs_folder or not os.path.isdir(user_configs_folder):
        logger.error(f"[ERROR] job_subfolder not found or invalid => {user_configs_folder}")
        return

    # -------------------------------------------------------------------------
    # 2) Build an output directory for this job under OUTPUT_DIR
    #    e.g. /usr/src/app/output/<job_id>
    # -------------------------------------------------------------------------
    env_out_dir = os.environ.get("OUTPUT_DIR", "/usr/src/app/output")
    job_output_dir = os.path.join(env_out_dir, job_id)
    os.makedirs(job_output_dir, exist_ok=True)
    logger.info(f"[INFO] Using job-specific output folder: {job_output_dir}")

    # -------------------------------------------------------------------------
    # 3) Load main_config.json from user_configs/<job_id>
    # -------------------------------------------------------------------------
    main_config_path = os.path.join(user_configs_folder, "main_config.json")
    if not os.path.isfile(main_config_path):
        logger.error(f"[ERROR] Cannot find main_config.json at {main_config_path}")
        return

    with open(main_config_path, "r") as f:
        existing_config_raw = json.load(f)
    main_config = existing_config_raw.get("main_config", {})
    logger.info(f"[INFO] Loaded existing main_config from {main_config_path}.")

    # Merge posted_data["main_config"] if present
    posted_data = job_config.get("posted_data", {})
    if "main_config" in posted_data:
        logger.info("[INFO] Deep merging posted_data['main_config'] into main_config.")
        deep_merge_dicts(main_config, posted_data["main_config"])
        # optionally re-save
        with open(main_config_path, "w") as f:
            json.dump({"main_config": main_config}, f, indent=2)

    # -------------------------------------------------------------------------
    # 4) Extract sub-sections from main_config
    # -------------------------------------------------------------------------
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

    # IDF creation block
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
    filter_by            = main_config.get("filter_by")  # if using DB

    # Summarize which major steps will run
    steps_to_run = []
    if perform_idf_creation:
        steps_to_run.append("IDF creation")
        if run_simulations:
            steps_to_run.append("simulations")
    if structuring_cfg.get("perform_structuring", False):
        steps_to_run.append("structuring")
    if modification_cfg.get("perform_modification", False):
        steps_to_run.append("modification")
    if main_config.get("validation_base", {}).get("perform_validation", False):
        steps_to_run.append("base validation")
    if main_config.get("validation_scenarios", {}).get("perform_validation", False):
        steps_to_run.append("scenario validation")
    if sens_cfg.get("perform_sensitivity", False):
        steps_to_run.append("sensitivity analysis")
    if sur_cfg.get("perform_surrogate", False):
        steps_to_run.append("surrogate modeling")
    if cal_cfg.get("perform_calibration", False):
        steps_to_run.append("calibration")

    if steps_to_run:
        logger.info("[INFO] Steps to execute: " + ", ".join(steps_to_run))
    else:
        logger.info("[INFO] No major steps are enabled in configuration.")

    # -------------------------------------------------------------------------
    # 5) Possibly override idf_creation.idf_config from env, then force IDFs
    #    to go in <job_output_dir>/output_IDFs
    # -------------------------------------------------------------------------
    check_canceled()

    env_idd_path = os.environ.get("IDD_PATH")
    if env_idd_path:
        idf_creation.idf_config["iddfile"] = env_idd_path
    env_base_idf = os.environ.get("BASE_IDF_PATH")
    if env_base_idf:
        idf_creation.idf_config["idf_file_path"] = env_base_idf

    job_idf_dir = os.path.join(job_output_dir, "output_IDFs")
    os.makedirs(job_idf_dir, exist_ok=True)
    idf_creation.idf_config["output_dir"] = job_idf_dir

    # If user explicitly set these in main_config, override again
    if "iddfile" in idf_cfg:
        idf_creation.idf_config["iddfile"] = idf_cfg["iddfile"]
    if "idf_file_path" in idf_cfg:
        idf_creation.idf_config["idf_file_path"] = idf_cfg["idf_file_path"]

    if "output_idf_dir" in idf_cfg:
        subfolder = idf_cfg["output_idf_dir"]  # e.g. "output_IDFs"
        full_dir = os.path.join(job_output_dir, subfolder)
        idf_creation.idf_config["output_dir"] = full_dir
    else:
        idf_creation.idf_config["output_dir"] = os.path.join(job_output_dir, "output_IDFs")

    # -------------------------------------------------------------------------
    # 6) Setup default dictionaries
    # -------------------------------------------------------------------------
    base_res_data    = def_dicts.get("res_data", {})
    base_nonres_data = def_dicts.get("nonres_data", {})
    dhw_lookup       = def_dicts.get("dhw", {})
    epw_lookup       = def_dicts.get("epw", [])
    lighting_lookup  = def_dicts.get("lighting", {})
    hvac_lookup      = def_dicts.get("hvac", {})
    vent_lookup      = def_dicts.get("vent", {})

    # -------------------------------------------------------------------------
    # 7) Apply Excel overrides if flags are set
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 8) JSON overrides from user_configs/<job_id> if user_flags are set
    # -------------------------------------------------------------------------
    check_canceled()

    def safe_load_subjson(fname, key):
        """
        Loads user_configs/<job_id>/fname if it exists, returns data.get(key).
        """
        full_path = os.path.join(user_configs_folder, fname)
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r") as ff:
                    data = json.load(ff)
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
        excel_path="",
        do_excel_override=False,
        user_fenez_overrides=user_fenez_data
    )

    # DHW
    user_config_dhw = None
    if user_flags.get("override_dhw_json", False):
        user_config_dhw = safe_load_subjson("dhw.json", "dhw")

    # EPW
    user_config_epw = []
    if user_flags.get("override_epw_json", False):
        e = safe_load_subjson("epw.json", "epw")
        if e:
            user_config_epw = e

    # Lighting
    user_config_lighting = None
    if user_flags.get("override_lighting_json", False):
        user_config_lighting = safe_load_subjson("lighting.json", "lighting")

    # HVAC
    user_config_hvac = None
    if user_flags.get("override_hvac_json", False):
        user_config_hvac = safe_load_subjson("hvac.json", "hvac")

    # Vent
    user_config_vent = []
    if user_flags.get("override_vent_json", False):
        v = safe_load_subjson("vent.json", "vent")
        if v:
            user_config_vent = v

    # Geometry
    geom_data = {}
    if user_flags.get("override_geometry_json", False):
        g = safe_load_subjson("geometry.json", "geometry")
        if g:
            geom_data["geometry"] = g

    # Shading
    shading_data = {}
    if user_flags.get("override_shading_json", False):
        s = safe_load_subjson("shading.json", "shading")
        if s:
            shading_data["shading"] = s

    # -------------------------------------------------------------------------
    # 9) IDF creation
    # -------------------------------------------------------------------------
    check_canceled()
    df_buildings = pd.DataFrame()

    if perform_idf_creation:
        logger.info("[INFO] IDF creation is ENABLED.")
        with step_timer(logger, "IDF creation and simulations"):
            # a) Load building data
            if use_database:
                logger.info("[INFO] Loading building data from DB.")
                if not filter_by:
                    raise ValueError("[ERROR] 'filter_by' must be specified when 'use_database' is True.")
                df_buildings = load_buildings_from_db(db_filter, filter_by)

                # Optionally save the raw DB buildings
                extracted_csv_path = os.path.join(job_output_dir, "extracted_buildings.csv")
                df_buildings.to_csv(extracted_csv_path, index=False)
                logger.info(f"[INFO] Saved extracted buildings to {extracted_csv_path}")

            else:
                bldg_data_path = paths_dict.get("building_data", "")
                if os.path.isfile(bldg_data_path):
                    df_buildings = pd.read_csv(bldg_data_path)
                else:
                    logger.warning(f"[WARN] building_data CSV not found => {bldg_data_path}")

            logger.info(f"[INFO] Number of buildings to simulate: {len(df_buildings)}")

            # b) Create IDFs & (optionally) run sims in job folder
            df_buildings = create_idfs_for_all_buildings(
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
                post_process_config=post_process_config,
                logs_base_dir=job_output_dir
            )

            # === Store the mapping (ogc_fid -> idf_name) so we can look it up later ===
            idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
            df_buildings.to_csv(idf_map_csv, index=False)
            logger.info(f"[INFO] Wrote building -> IDF map to {idf_map_csv}")

    else:
        logger.info("[INFO] Skipping IDF creation.")

    # -------------------------------------------------------------------------
    # 10) Perform structuring if requested
    # -------------------------------------------------------------------------
    check_canceled()
    if structuring_cfg.get("perform_structuring", False):
        with step_timer(logger, "structuring"):
            logger.info("[INFO] Performing structuring ...")

            # --- Fenestration -------------------------------------------------
            from idf_objects.structuring.fenestration_structuring import transform_fenez_log_to_structured_with_ranges
            fenez_conf = structuring_cfg.get("fenestration", {})
            fenez_in = fenez_conf.get("csv_in", "assigned/assigned_fenez_params.csv")
            fenez_out = fenez_conf.get("csv_out", "assigned/structured_fenez_params.csv")
            if not os.path.isabs(fenez_in):
                fenez_in = os.path.join(job_output_dir, fenez_in)
            if not os.path.isabs(fenez_out):
                fenez_out = os.path.join(job_output_dir, fenez_out)
            if os.path.isfile(fenez_in):
                transform_fenez_log_to_structured_with_ranges(csv_input=fenez_in, csv_output=fenez_out)
            else:
                logger.warning(f"[STRUCTURING] Fenestration input CSV not found => {fenez_in}")

            # --- DHW ---------------------------------------------------------
            from idf_objects.structuring.dhw_structuring import transform_dhw_log_to_structured
            dhw_conf = structuring_cfg.get("dhw", {})
            dhw_in = dhw_conf.get("csv_in", "assigned/assigned_dhw_params.csv")
            dhw_out = dhw_conf.get("csv_out", "assigned/structured_dhw_params.csv")
            if not os.path.isabs(dhw_in):
                dhw_in = os.path.join(job_output_dir, dhw_in)
            if not os.path.isabs(dhw_out):
                dhw_out = os.path.join(job_output_dir, dhw_out)
            if os.path.isfile(dhw_in):
                transform_dhw_log_to_structured(dhw_in, dhw_out)
            else:
                logger.warning(f"[STRUCTURING] DHW input CSV not found => {dhw_in}")


            # --- Shading ----------------------------------------------------
            from idf_objects.structuring.shading_structuring import transform_shading_log_to_structured
            shading_conf = structuring_cfg.get("shading", {})
            user_shading_rules = safe_load_subjson("shading.json", "shading") or []
            
            if shading_conf:
                shading_in = patch_if_relative(shading_conf.get("csv_in"))
                shading_out = patch_if_relative(shading_conf.get("csv_out"))

                transform_shading_log_to_structured(
                    csv_input=shading_in,
                    csv_output=shading_out,
                    user_shading_rules=user_shading_rules
                )
            else:
                logger.warning("[STRUCTURING] 'shading' configuration not found in structuring settings.")









            # --- HVAC flatten -----------------------------------------------
            from idf_objects.structuring.flatten_hvac import flatten_hvac_data, parse_assigned_value as parse_hvac
            hvac_conf = structuring_cfg.get("hvac", {})
            hvac_in = hvac_conf.get("csv_in", "assigned/assigned_hvac_params.csv")
            hvac_bld = hvac_conf.get("build_out", "assigned/assigned_hvac_building.csv")
            hvac_zone = hvac_conf.get("zone_out", "assigned/assigned_hvac_zones.csv")
            if not os.path.isabs(hvac_in):
                hvac_in = os.path.join(job_output_dir, hvac_in)
            if not os.path.isabs(hvac_bld):
                hvac_bld = os.path.join(job_output_dir, hvac_bld)
            if not os.path.isabs(hvac_zone):
                hvac_zone = os.path.join(job_output_dir, hvac_zone)
            if os.path.isfile(hvac_in):
                df_hvac = pd.read_csv(hvac_in)
                if "assigned_value" in df_hvac.columns:
                    df_hvac["assigned_value"] = df_hvac["assigned_value"].apply(parse_hvac)
                    flatten_hvac_data(
                        df_input=df_hvac,
                        out_build_csv=hvac_bld,
                        out_zone_csv=hvac_zone,
                    )
                else:
                    logger.warning(
                        f"[STRUCTURING] 'assigned_value' column missing in {hvac_in}. Skipping HVAC flatten."
                    )
            else:
                logger.warning(f"[STRUCTURING] HVAC input CSV not found => {hvac_in}")

            # --- Vent flatten -----------------------------------------------
            from idf_objects.structuring.flatten_assigned_vent import flatten_ventilation_data, parse_assigned_value as parse_vent
            vent_conf = structuring_cfg.get("vent", {})
            vent_in = vent_conf.get("csv_in", "assigned/assigned_ventilation.csv")
            vent_bld = vent_conf.get("build_out", "assigned/assigned_vent_building.csv")
            vent_zone = vent_conf.get("zone_out", "assigned/assigned_vent_zones.csv")
            if not os.path.isabs(vent_in):
                vent_in = os.path.join(job_output_dir, vent_in)
            if not os.path.isabs(vent_bld):
                vent_bld = os.path.join(job_output_dir, vent_bld)
            if not os.path.isabs(vent_zone):
                vent_zone = os.path.join(job_output_dir, vent_zone)
            if os.path.isfile(vent_in):
                df_vent = pd.read_csv(vent_in)
                if "assigned_value" in df_vent.columns:
                    df_vent["assigned_value"] = df_vent["assigned_value"].apply(parse_vent)
                    flatten_ventilation_data(
                        df_input=df_vent,
                        out_build_csv=vent_bld,
                        out_zone_csv=vent_zone,
                    )
                else:
                    logger.warning(
                        f"[STRUCTURING] 'assigned_value' column missing in {vent_in}. Skipping ventilation flatten."
                    )
            else:
                logger.warning(f"[STRUCTURING] Vent input CSV not found => {vent_in}")
    else:
        logger.info("[INFO] Skipping structuring.")

    # -------------------------------------------------------------------------
    # 11) Scenario Modification
    # -------------------------------------------------------------------------
    check_canceled()
    if modification_cfg.get("perform_modification", False):
        with step_timer(logger, "modification"):
            logger.info("[INFO] Scenario modification is ENABLED.")

            mod_cfg = modification_cfg["modify_config"]

            # 1) Ensure scenario IDFs go to <job_output_dir>/scenario_idfs
            scenario_idf_dir = os.path.join(job_output_dir, "scenario_idfs")
            os.makedirs(scenario_idf_dir, exist_ok=True)
            mod_cfg["output_idf_dir"] = scenario_idf_dir

            # 2) Ensure scenario sims => <job_output_dir>/Sim_Results/Scenarios
            if "simulation_config" in mod_cfg:
                sim_out = os.path.join(job_output_dir, "Sim_Results", "Scenarios")
                os.makedirs(sim_out, exist_ok=True)
                mod_cfg["simulation_config"]["output_dir"] = sim_out

            # 3) Post-process => <job_output_dir>/results_scenarioes
            if "post_process_config" in mod_cfg:
                ppcfg = mod_cfg["post_process_config"]
                as_is_csv = os.path.join(job_output_dir, "results_scenarioes", "merged_as_is_scenarios.csv")
                daily_csv = os.path.join(job_output_dir, "results_scenarioes", "merged_daily_mean_scenarios.csv")
                os.makedirs(os.path.dirname(as_is_csv), exist_ok=True)
                os.makedirs(os.path.dirname(daily_csv), exist_ok=True)
                ppcfg["output_csv_as_is"] = as_is_csv
                ppcfg["output_csv_daily_mean"] = daily_csv

            # 4) Fix assigned_csv paths
            assigned_csv_dict = mod_cfg.get("assigned_csv", {})
            for key, rel_path in assigned_csv_dict.items():
                assigned_csv_dict[key] = os.path.join(job_output_dir, rel_path)

            # 5) Fix scenario_csv paths
            scenario_csv_dict = mod_cfg.get("scenario_csv", {})
            for key, rel_path in scenario_csv_dict.items():
                scenario_csv_dict[key] = os.path.join(job_output_dir, rel_path)

            # ----------------------------------------------------------------------
            # NEW LOGIC: pick the base_idf_path from building_id automatically
            # ----------------------------------------------------------------------
            # The user sets "building_id" in the config, e.g. 20233330
            building_id = mod_cfg["building_id"]

            # We need the CSV that was saved right after create_idfs_for_all_buildings(...)
            idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
            if not os.path.isfile(idf_map_csv):
                raise FileNotFoundError(
                    f"Cannot find building->IDF map CSV at {idf_map_csv}. "
                    f"Did you skip 'perform_idf_creation'?"
                )

        # Read the mapping: each row has "ogc_fid" and "idf_name"
            df_idf_map = pd.read_csv(idf_map_csv)
            row_match = df_idf_map.loc[df_idf_map["ogc_fid"] == building_id]

            if row_match.empty:
                raise ValueError(
                    f"No building found for building_id={building_id} in {idf_map_csv}"
                )

        # e.g. "building_0.idf", "building_16.idf", "building_16_ba62d0.idf", etc.
            idf_filename = row_match.iloc[0]["idf_name"]

        # Build the full path to that IDF in output_IDFs
            base_idf_path = os.path.join(job_output_dir, "output_IDFs", idf_filename)
            mod_cfg["base_idf_path"] = base_idf_path
            logger.info(f"[INFO] Auto-selected base IDF => {base_idf_path}")
        # ----------------------------------------------------------------------

            # Finally, run the scenario workflow
            run_modification_workflow(mod_cfg)
    else:
        logger.info("[INFO] Skipping scenario modification.")


    # -------------------------------------------------------------------------
    # 12) Helper to handle patching CSVs that are "relative" but not "data/".
    # -------------------------------------------------------------------------
    def patch_if_relative(csv_path: str):
        """
        1) If absolute, return as-is.
        2) If starts with 'data/', interpret as /usr/src/app/data/... (no job folder).
        3) Else, join with job_output_dir.
        """
        if not csv_path:
            return csv_path
        if os.path.isabs(csv_path):
            return csv_path
        if csv_path.startswith("data/"):
            return os.path.join("/usr/src/app", csv_path)
        return os.path.join(job_output_dir, csv_path)

    # -------------------------------------------------------------------------
    # 13) Global Validation
    # -------------------------------------------------------------------------
        # (A) Validation - BASE
    # -------------------------------------------------------------------------
    check_canceled()
    base_validation_cfg = main_config.get("validation_base", {})
    if base_validation_cfg.get("perform_validation", False):
        with step_timer(logger, "base validation"):
            logger.info("[INFO] BASE Validation is ENABLED.")
            val_conf = base_validation_cfg["config"]

            # Patch relative paths
            sim_csv = val_conf.get("sim_data_csv")
            if sim_csv:
                val_conf["sim_data_csv"] = patch_if_relative(sim_csv)

            real_csv = val_conf.get("real_data_csv")
            if real_csv:
                val_conf["real_data_csv"] = patch_if_relative(real_csv)

            out_csv = val_conf.get("output_csv")
            if out_csv:
                val_conf["output_csv"] = patch_if_relative(out_csv)

            # Now run the validation
            run_validation_process(val_conf)
    else:
        logger.info("[INFO] Skipping BASE validation or not requested.")

    # (B) Validation - SCENARIOS
    # -------------------------------------------------------------------------
    check_canceled()
    scenario_validation_cfg = main_config.get("validation_scenarios", {})
    if scenario_validation_cfg.get("perform_validation", False):
        with step_timer(logger, "scenario validation"):
            logger.info("[INFO] SCENARIO Validation is ENABLED.")
            val_conf = scenario_validation_cfg["config"]

            # Patch relative paths
            sim_csv = val_conf.get("sim_data_csv")
            if sim_csv:
                val_conf["sim_data_csv"] = patch_if_relative(sim_csv)

            real_csv = val_conf.get("real_data_csv")
            if real_csv:
                val_conf["real_data_csv"] = patch_if_relative(real_csv)

            out_csv = val_conf.get("output_csv")
            if out_csv:
                val_conf["output_csv"] = patch_if_relative(out_csv)

            # Now run the validation
            run_validation_process(val_conf)
    else:
        logger.info("[INFO] Skipping SCENARIO validation or not requested.")


    # -------------------------------------------------------------------------
    # 14) Sensitivity Analysis
    # -------------------------------------------------------------------------
    check_canceled()
    if sens_cfg.get("perform_sensitivity", False):
        with step_timer(logger, "sensitivity analysis"):
            logger.info("[INFO] Sensitivity Analysis is ENABLED.")

            scenario_folder = sens_cfg.get("scenario_folder", "")
            sens_cfg["scenario_folder"] = patch_if_relative(scenario_folder)

            results_csv = sens_cfg.get("results_csv", "")
            sens_cfg["results_csv"] = patch_if_relative(results_csv)

            out_csv = sens_cfg.get("output_csv", "sensitivity_output.csv")
            sens_cfg["output_csv"] = patch_if_relative(out_csv)

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

    # -------------------------------------------------------------------------
    # 15) Surrogate Modeling
    # -------------------------------------------------------------------------
    check_canceled()
    if sur_cfg.get("perform_surrogate", False):
        with step_timer(logger, "surrogate modeling"):
            logger.info("[INFO] Surrogate Modeling is ENABLED.")

            scenario_folder = sur_cfg.get("scenario_folder", "")
            sur_cfg["scenario_folder"] = patch_if_relative(scenario_folder)

            results_csv = sur_cfg.get("results_csv", "")
            sur_cfg["results_csv"] = patch_if_relative(results_csv)

            model_out = sur_cfg.get("model_out", "")
            sur_cfg["model_out"] = patch_if_relative(model_out)

            cols_out = sur_cfg.get("cols_out", "")
            sur_cfg["cols_out"] = patch_if_relative(cols_out)

            target_var = sur_cfg["target_variable"]
            test_size  = sur_cfg["test_size"]

            df_scen = sur_load_scenario_params(sur_cfg["scenario_folder"])
            pivot_df = pivot_scenario_params(df_scen)

            df_sim = load_sim_results(sur_cfg["results_csv"])
            df_agg = aggregate_results(df_sim)
            merged_df = merge_params_with_results(pivot_df, df_agg, target_var)

            rf_model, trained_cols = build_and_save_surrogate(
                df_data=merged_df,
                target_col=target_var,
                model_out_path=sur_cfg["model_out"],
                columns_out_path=sur_cfg["cols_out"],
                test_size=test_size,
                random_state=42
            )
            if rf_model:
                logger.info("[INFO] Surrogate model built & saved.")
            else:
                logger.warning("[WARN] Surrogate modeling failed or insufficient data.")
    else:
        logger.info("[INFO] Skipping surrogate modeling.")

    # -------------------------------------------------------------------------
    # 16) Calibration
    # -------------------------------------------------------------------------
    check_canceled()
    if cal_cfg.get("perform_calibration", False):
        with step_timer(logger, "calibration"):
            logger.info("[INFO] Calibration is ENABLED.")

            scen_folder = cal_cfg.get("scenario_folder", "")
            cal_cfg["scenario_folder"] = patch_if_relative(scen_folder)

            real_csv = cal_cfg.get("real_data_csv", "")
            cal_cfg["real_data_csv"] = patch_if_relative(real_csv)

            sur_model_path = cal_cfg.get("surrogate_model_path", "")
            cal_cfg["surrogate_model_path"] = patch_if_relative(sur_model_path)

            sur_cols_path = cal_cfg.get("surrogate_columns_path", "")
            cal_cfg["surrogate_columns_path"] = patch_if_relative(sur_cols_path)

            hist_csv = cal_cfg.get("output_history_csv", "")
            cal_cfg["output_history_csv"] = patch_if_relative(hist_csv)

            best_params_folder = cal_cfg.get("best_params_folder", "")
            cal_cfg["best_params_folder"] = patch_if_relative(best_params_folder)

            run_unified_calibration(cal_cfg)
    else:
        logger.info("[INFO] Skipping calibration.")

    # -------------------------------------------------------------------------
    # 17) Zip & Email final results, if mail_user.json present
    # -------------------------------------------------------------------------
    try:
        with step_timer(logger, "zipping and email"):
            mail_user_path = os.path.join(user_configs_folder, "mail_user.json")
            mail_info = {}
            if os.path.isfile(mail_user_path):
                with open(mail_user_path, "r") as f:
                    mail_info = json.load(f)

                mail_user_list = mail_info.get("mail_user", [])
                if len(mail_user_list) > 0:
                    first_user = mail_user_list[0]
                    recipient_email = first_user.get("email", "")
                    if recipient_email:
                        zip_path = zip_user_output(job_output_dir)
                        send_results_email(zip_path, recipient_email)
                        logger.info(f"[INFO] Emailed zip {zip_path} to {recipient_email}")
                    else:
                        logger.warning("[WARN] mail_user.json => missing 'email'")
                else:
                    logger.warning("[WARN] mail_user.json => 'mail_user' list is empty.")
            else:
                logger.info("[INFO] No mail_user.json found, skipping email.")
    except Exception as e:
        logger.error(f"[ERROR] Zipping/Emailing results failed => {e}")

    # -------------------------------------------------------------------------
    # LAST STEP: (Optional) Call the cleanup function
    # -------------------------------------------------------------------------
    try:
        cleanup_old_results()  # This will remove any job folder older than MAX_AGE_HOURS
    except Exception as e:
        logger.error(f"[CLEANUP ERROR] => {e}")

    total_time = time.perf_counter() - overall_start
    logger.info(f"=== End of orchestrate_workflow (took {total_time:.2f} seconds) ===")
