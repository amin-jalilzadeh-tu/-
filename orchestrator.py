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

"""
orchestrator.py - Updated with validation configuration support

Key changes:
1. Load validation-specific configuration
2. Pass ValidationConfig to validation functions
3. Better error handling for validation failures
"""

import os
import json
import logging
import threading
import time
from contextlib import contextmanager
import pandas as pd
from datetime import datetime

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
# New modification system imports
# New modification system imports
from idf_modification.modification_engine import ModificationEngine

from idf_modification.modification_config import ModificationConfig

from pathlib import Path

from datetime import datetime
# Validation - Updated imports
from validation.smart_validation_wrapper import run_smart_validation


# Sensitivity / Surrogate / Calibration
from c_sensitivity.sensitivity_data_manager import SensitivityDataManager
from c_sensitivity.unified_sensitivity import run_enhanced_sensitivity_analysis
from c_sensitivity.sensitivity_reporter import SensitivityReporter




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

# Parser imports
from parserr.energyplus_analyzer_main import EnergyPlusAnalyzer
from parserr.helpers import prepare_idf_sql_pairs_with_mapping, get_parsed_data_info


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
    Orchestrates the entire E+ workflow with enhanced validation configuration support.
    
    Changes:
    - Loads validation-specific configuration if present
    - Creates ValidationConfig object for validation steps
    - Better error handling and reporting for validation issues
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
    # 1) Identify the user_configs folder (where main_config.json resides)
    # -------------------------------------------------------------------------
    user_configs_folder = job_config.get("job_subfolder")
    if not user_configs_folder or not os.path.isdir(user_configs_folder):
        logger.error(f"[ERROR] job_subfolder not found or invalid => {user_configs_folder}")
        return

    # -------------------------------------------------------------------------
    # 2) Build an output directory for this job under OUTPUT_DIR
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
    # 4) Define helper function for path patching
    # -------------------------------------------------------------------------
    def patch_if_relative(csv_path: str):
        """
        1) If absolute, return as-is.
        2) If starts with 'data/', interpret as /usr/src/app/data/... (no job folder).
        3) Else, join with job_output_dir.
        """
        if not csv_path:
            return csv_path
        
        # Normalize path separators for cross-platform compatibility
        csv_path = csv_path.replace('\\', '/')
        
        if os.path.isabs(csv_path):
            return csv_path
        if csv_path.startswith("data/"):
            return os.path.join("/usr/src/app", csv_path)
        return os.path.join(job_output_dir, csv_path)

    # -------------------------------------------------------------------------
    # 5) Extract sub-sections from main_config
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

    # Extract parsing configuration
    parsing_cfg = main_config.get("parsing", {})
    perform_parsing = parsing_cfg.get("perform_parsing", False)
    parse_after_simulation = parsing_cfg.get("parse_after_simulation", True)
    categories_to_parse = parsing_cfg.get("categories", None)  # None means all categories

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
    if parsing_cfg.get("perform_parsing", False):
        steps_to_run.append("parsing to parquet")
    if modification_cfg.get("perform_modification", False):
        steps_to_run.append("modification")
    if validation_cfg.get("perform_validation", False):
        steps_to_run.append("validation")
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
    # 6) Possibly override idf_creation.idf_config from env, then force IDFs
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
    # 7) Setup default dictionaries
    # -------------------------------------------------------------------------
    base_res_data    = def_dicts.get("res_data", {})
    base_nonres_data = def_dicts.get("nonres_data", {})
    dhw_lookup       = def_dicts.get("dhw", {})
    epw_lookup       = def_dicts.get("epw", [])
    lighting_lookup  = def_dicts.get("lighting", {})
    hvac_lookup      = def_dicts.get("hvac", {})
    vent_lookup      = def_dicts.get("vent", {})

    # -------------------------------------------------------------------------
    # 8) Apply Excel overrides if flags are set
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
    # 9) JSON overrides from user_configs/<job_id> if user_flags are set
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
    # 10) IDF creation
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
    # 11) Perform structuring if requested
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

            # NEW:--- Shading ----------------------------------------------------
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

            # --- Equipment --------------------------------------------------
            from idf_objects.structuring.equipment_structuring import transform_equipment_log_to_structured
            equip_conf = structuring_cfg.get("equipment", {})
            user_equip_rules = safe_load_subjson("equipment.json", "equipment") or []
            
            if equip_conf:
                equip_in = patch_if_relative(equip_conf.get("csv_in"))
                equip_out = patch_if_relative(equip_conf.get("csv_out"))

                transform_equipment_log_to_structured(
                    csv_input=equip_in,
                    csv_output=equip_out,
                    user_equipment_rules=user_equip_rules
                )
            else:
                logger.warning("[STRUCTURING] 'equipment' configuration not found in structuring settings.")

            # --- Zone Sizing ------------------------------------------------
            from idf_objects.structuring.zone_sizing_structuring import transform_zone_sizing_log_to_structured
            sizing_conf = structuring_cfg.get("zone_sizing", {})
            user_sizing_rules = safe_load_subjson("zone_sizing.json", "zone_sizing") or []
            
            if sizing_conf:
                sizing_in = patch_if_relative(sizing_conf.get("csv_in"))
                sizing_out = patch_if_relative(sizing_conf.get("csv_out"))

                transform_zone_sizing_log_to_structured(
                    csv_input=sizing_in,
                    csv_output=sizing_out,
                    user_sizing_rules=user_sizing_rules
                )
            else:
                logger.warning("[STRUCTURING] 'zone_sizing' configuration not found.")

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
    # 12) Parse IDF/SQL files to Parquet format
    # -------------------------------------------------------------------------
    check_canceled()
    if perform_parsing:
        # Handle parsing based on configuration
        if parse_after_simulation and not perform_idf_creation:
            logger.warning("[WARN] Parse after simulation requested but no IDF creation performed")
        
        with step_timer(logger, "parsing to parquet"):
            logger.info("[INFO] Parsing IDF/SQL files to Parquet format...")
            
            # Create parser output directory
            parser_output_dir = os.path.join(job_output_dir, "parsed_data")
            os.makedirs(parser_output_dir, exist_ok=True)
            
            # Initialize the analyzer
            analyzer = EnergyPlusAnalyzer(parser_output_dir)
            
            # Get parsing configuration details
            parse_mode = parsing_cfg.get("parse_mode", "all")
            parse_types = parsing_cfg.get("parse_types", {"idf": True, "sql": True})
            building_selection = parsing_cfg.get("building_selection", {})
            idf_content_cfg = parsing_cfg.get("idf_content", {})
            sql_content_cfg = parsing_cfg.get("sql_content", {})
            use_profile = parsing_cfg.get("use_profile")
            
            # Apply profile if specified
            if use_profile:
                profiles = main_config.get("parsing_profiles", {})
                if use_profile in profiles:
                    profile_cfg = profiles[use_profile]
                    logger.info(f"[INFO] Using parsing profile: {use_profile}")
                    # Merge profile settings with existing config
                    if "parse_types" in profile_cfg:
                        parse_types.update(profile_cfg["parse_types"])
                    if "idf_content" in profile_cfg:
                        idf_content_cfg.update(profile_cfg["idf_content"])
                    if "sql_content" in profile_cfg:
                        sql_content_cfg.update(profile_cfg["sql_content"])
            
            # Use the same approach as in your successful test
            idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
            
            # Check if we have the mapping file
            if os.path.isfile(idf_map_csv):
                # Use the proven method from your test
                from parserr.helpers import prepare_idf_sql_pairs_with_mapping
                
                idf_sql_pairs, building_id_map = prepare_idf_sql_pairs_with_mapping(job_output_dir)
                
                if idf_sql_pairs:
                    logger.info(f"[INFO] Found {len(idf_sql_pairs)} file pairs to parse")
                    logger.info(f"[INFO] Parse mode: {parse_mode}")
                    
                    # Apply building selection if needed
                    if parse_mode == "selective" and building_selection:
                        mode = building_selection.get("mode", "all")
                        if mode == "specific":
                            building_ids = building_selection.get("building_ids", [])
                            if building_ids:
                                # Filter pairs based on building IDs
                                filtered_pairs = []
                                filtered_map = {}
                                for idf_path, sql_path in idf_sql_pairs:
                                    if idf_path in building_id_map:
                                        bid = int(building_id_map[idf_path])
                                        if bid in building_ids:
                                            filtered_pairs.append((idf_path, sql_path))
                                            filtered_map[idf_path] = building_id_map[idf_path]
                                idf_sql_pairs = filtered_pairs
                                building_id_map = filtered_map
                                logger.info(f"[INFO] Filtered to {len(idf_sql_pairs)} buildings")
                    
                    # Run the standard analysis (which works in your test)
                    analyzer.analyze_project(
                        idf_sql_pairs=idf_sql_pairs,
                        categories=categories_to_parse,  # Use the categories from config
                        validate_outputs=True,
                        building_id_map=building_id_map
                    )
                    
                    # Get parsing summary
                    parsed_info = get_parsed_data_info(parser_output_dir)
                    
                    # Save enhanced summary
                    parsing_summary = {
                        'job_id': job_id,
                        'parse_mode': parse_mode,
                        'parse_types': parse_types,
                        'files_parsed': len(idf_sql_pairs),
                        'parser_output_dir': parser_output_dir,
                        'timestamp': datetime.now().isoformat(),
                        'parsed_data_info': parsed_info,
                        'configuration': {
                            'parse_mode': parse_mode,
                            'categories': categories_to_parse
                        }
                    }
                    
                    summary_path = os.path.join(parser_output_dir, 'parsing_summary.json')
                    with open(summary_path, 'w') as f:
                        json.dump(parsing_summary, f, indent=2)
                    
                    logger.info(f"[INFO] Parsing complete. Data saved to: {parser_output_dir}")
                    logger.info(f"[INFO] Total categories: {len(parsed_info['categories'])}")
                    logger.info(f"[INFO] Total files: {parsed_info['total_files']}")
                    
                    # Close analyzer connections
                    analyzer.close()
                else:
                    logger.warning("[WARN] No valid file pairs found")
            else:
                logger.error(f"[ERROR] IDF mapping file not found: {idf_map_csv}")
                logger.error("[ERROR] Please run IDF creation first or provide mapping file")
    else:
        logger.info("[INFO] Skipping parsing.")










# -------------------------------------------------------------------------
    # 13) Scenario Modification (Using New Parquet-based System)
    # -------------------------------------------------------------------------
    check_canceled()
    if modification_cfg.get("perform_modification", False):
        with step_timer(logger, "modification"):
            logger.info("[INFO] Scenario modification is ENABLED.")
            
            # Check if parsing was performed
            parsed_data_path = os.path.join(job_output_dir, "parsed_data")
            if not os.path.exists(parsed_data_path):
                logger.error("[ERROR] Parsed data not found. Please enable parsing before modification.")
                logger.error("[ERROR] Set 'parsing.perform_parsing': true in configuration.")
                return
            
            # Initialize modification engine
            try:
                # Create the workflow config from loaded modification_cfg
                workflow_config = {
                    "modifications": modification_cfg,
                    "project_id": job_id,
                    "iddfile": idf_creation.idf_config.get("iddfile", "Energy+.idd")
                }
                
                # Initialize modification engine with correct directory
                mod_engine = ModificationEngine(
                    project_dir=job_output_dir,
                    config=workflow_config
                )
                
                # Generate session ID
                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                mod_engine.session_id = session_id
                
                # Get base IDF selection configuration
                base_idf_selection = modification_cfg.get("base_idf_selection", {})
                method = base_idf_selection.get("method", "specific")
                
                generated_files_all = []
                
                if method == "specific":
                    # Use specific building IDs
                    building_ids = base_idf_selection.get("building_ids", [])
                    
                    if not building_ids:
                        logger.error("[ERROR] No building_ids specified for 'specific' method")
                        return
                    
                    # Load IDF mapping
                    idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
                    if not os.path.isfile(idf_map_csv):
                        logger.error(f"[ERROR] IDF mapping file not found: {idf_map_csv}")
                        logger.error("[ERROR] Please run IDF creation first.")
                        return
                    
                    df_idf_map = pd.read_csv(idf_map_csv)
                    
                    for building_id in building_ids:
                        row_match = df_idf_map.loc[df_idf_map["ogc_fid"] == building_id]
                        
                        if not row_match.empty:
                            idf_filename = row_match.iloc[0]["idf_name"]
                            base_idf_path = os.path.join(job_output_dir, "output_IDFs", idf_filename)
                            
                            if os.path.exists(base_idf_path):
                                logger.info(f"[INFO] Processing building {building_id} with IDF: {idf_filename}")
                                
                                # Generate modifications
                                generated_files = mod_engine.generate_modifications(
                                    base_idf_path=base_idf_path,
                                    building_id=str(building_id)
                                )
                                
                                generated_files_all.extend(generated_files)
                                logger.info(f"[INFO] Generated {len(generated_files)} variants for building {building_id}")
                            else:
                                logger.warning(f"[WARN] IDF file not found: {base_idf_path}")
                        else:
                            logger.warning(f"[WARN] Building ID {building_id} not found in IDF mapping")
                            
                elif method == "representative":
                    # Select representative buildings based on some criteria
                    # This would need implementation based on your criteria
                    logger.warning("[WARN] 'representative' method not yet implemented")
                    
                elif method == "all":
                    # Process all available IDFs
                    idf_dir = os.path.join(job_output_dir, "output_IDFs")
                    if not os.path.exists(idf_dir):
                        logger.error(f"[ERROR] IDF directory not found: {idf_dir}")
                        return
                    
                    idf_files = list(Path(idf_dir).glob("*.idf"))
                    logger.info(f"[INFO] Found {len(idf_files)} IDF files to modify")
                    
                    for idf_path in idf_files:
                        # Extract building ID from filename (e.g., "building_123.idf" -> "123")
                        building_id = idf_path.stem.split('_')[1] if '_' in idf_path.stem else 'unknown'
                        
                        logger.info(f"[INFO] Processing {idf_path.name}")
                        
                        generated_files = mod_engine.generate_modifications(
                            base_idf_path=str(idf_path),
                            building_id=building_id
                        )
                        
                        generated_files_all.extend(generated_files)
                        logger.info(f"[INFO] Generated {len(generated_files)} variants for {idf_path.name}")
                
                else:
                    logger.error(f"[ERROR] Unknown base_idf_selection method: {method}")
                    return
                
                # Generate modification report
                if generated_files_all:
                    report_path = mod_engine.generate_modification_report()
                    logger.info(f"[INFO] Modification report saved to: {report_path}")
                    logger.info(f"[INFO] Total variants generated: {len(generated_files_all)}")
                    
                    # Optionally run simulations on modified IDFs
                    if modification_cfg.get("post_modification", {}).get("run_simulations", False):
                        logger.info("[INFO] Running simulations on modified IDFs...")
                        
                        # Import required modules
                        from epw.run_epw_sims import simulate_all
                        
                        # Get simulation configuration
                        sim_config = modification_cfg.get("post_modification", {}).get("simulation_config", {})
                        num_workers = sim_config.get("num_workers", simulate_config.get("num_workers", 4))
                        
                        # Prepare modified IDF data for simulation
                        modified_idfs_dir = os.path.join(job_output_dir, mod_engine.config['output_options']['output_dir'])
                        logger.info(f"[INFO] Looking for modified IDFs in: {modified_idfs_dir}")
                        
                        # Load the IDF mapping data
                        idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
                        if not os.path.isfile(idf_map_csv):
                            logger.error(f"[ERROR] IDF mapping file not found: {idf_map_csv}")
                            logger.error("[ERROR] Cannot run simulations without building data.")
                        else:
                            df_map = pd.read_csv(idf_map_csv)
                            
                            # CRITICAL FIX: Ensure consistent data types for comparison
                            # Convert ogc_fid to string to match the building_id extracted from filename
                            df_map['ogc_fid'] = df_map['ogc_fid'].astype(str)
                            logger.debug(f"[DEBUG] Loaded {len(df_map)} buildings from mapping file")
                            logger.debug(f"[DEBUG] Building IDs in mapping: {df_map['ogc_fid'].tolist()}")
                            
                            # Create a dataframe for modified IDFs
                            modified_buildings = []
                            
                            # Walk through all subdirectories to find IDF files
                            for root, dirs, files in os.walk(modified_idfs_dir):
                                for file in files:
                                    if file.endswith('.idf'):
                                        # Get full path
                                        full_path = os.path.join(root, file)
                                        
                                        # Extract building info from filename
                                        # Expected format: building_<id>_<variant>.idf
                                        base_name = os.path.basename(file)
                                        parts = base_name.replace('.idf', '').split('_')
                                        
                                        if len(parts) >= 3 and parts[0] == 'building':
                                            building_id = parts[1]  # This is a string
                                            variant_id = '_'.join(parts[2:])
                                            
                                            logger.debug(f"[DEBUG] Processing file: {file}, building_id: {building_id}, variant: {variant_id}")
                                            
                                            # Find original building data
                                            orig_building = df_map[df_map['ogc_fid'] == building_id]
                                            
                                            if not orig_building.empty:
                                                building_data = orig_building.iloc[0].to_dict()
                                                
                                                # Store the full filename with relative path from modified_idfs_dir
                                                # This is important for simulate_all to find the files
                                                rel_path = os.path.relpath(full_path, modified_idfs_dir)
                                                building_data['idf_name'] = rel_path
                                                building_data['variant_id'] = variant_id
                                                building_data['original_ogc_fid'] = building_id  # Keep original ID
                                                
                                                modified_buildings.append(building_data)
                                                logger.debug(f"[DEBUG] Added modified building: {building_id}, variant: {variant_id}, path: {rel_path}")
                                            else:
                                                logger.warning(f"[WARN] No building data found for ID '{building_id}'")
                                                logger.warning(f"[WARN] Available IDs: {df_map['ogc_fid'].unique()[:5]}...")  # Show first 5 for debugging
                            
                            if modified_buildings:
                                df_modified = pd.DataFrame(modified_buildings)
                                logger.info(f"[INFO] Found {len(df_modified)} modified IDF files to simulate")
                                logger.info(f"[INFO] Buildings to simulate: {df_modified.groupby('original_ogc_fid').size().to_dict()}")
                                
                                # Set output directory for modified simulation results
                                modified_sim_output = os.path.join(job_output_dir, "Modified_Sim_Results")
                                os.makedirs(modified_sim_output, exist_ok=True)
                                
                                # Get EPW configuration
                                # Check if job_config_dir is defined (should be from earlier in orchestrator)
                                if 'job_config_dir' not in locals():
                                    job_config_dir = os.path.join("user_configs", job_id)
                                
                                # Re-load the EPW configuration if needed
                                user_config_epw = None
                                if 'user_flags' in locals() and user_flags.get("override_epw_json", False):
                                    epw_json_path = os.path.join(job_config_dir, "user_config_epw.json")
                                    if os.path.isfile(epw_json_path):
                                        with open(epw_json_path, 'r') as f:
                                            epw_data = json.load(f)
                                            user_config_epw = epw_data.get("epw")
                                            logger.debug("[DEBUG] Loaded user EPW configuration")
                                
                                # Use the EPW assignment from simulation config if specified
                                epw_assignment = sim_config.get("epw_assignment", "use_original")
                                if epw_assignment != "use_original":
                                    logger.info(f"[INFO] Using EPW assignment strategy: {epw_assignment}")
                                    # You can implement custom EPW assignment logic here
                                
                                assigned_epw_log = {}  # Initialize empty log for EPW assignments
                                
                                # Log simulation setup
                                logger.info(f"[INFO] Simulation setup:")
                                logger.info(f"  - IDF directory: {modified_idfs_dir}")
                                logger.info(f"  - Output directory: {modified_sim_output}")
                                logger.info(f"  - Number of workers: {num_workers}")
                                logger.info(f"  - IDD file: {idf_creation.idf_config['iddfile']}")
                                
                                # Run simulations
                                try:
                                    simulate_all(
                                        df_buildings=df_modified,
                                        idf_directory=modified_idfs_dir,
                                        iddfile=idf_creation.idf_config["iddfile"],
                                        base_output_dir=modified_sim_output,
                                        user_config_epw=user_config_epw,
                                        assigned_epw_log=assigned_epw_log,
                                        num_workers=num_workers
                                    )
                                    
                                    logger.info(f"[INFO] Completed simulations for {len(df_modified)} modified IDFs")
                                    
                                    # Optionally parse results
                                    if modification_cfg.get("post_modification", {}).get("parse_results", {}).get("enabled", False):
                                        logger.info("[INFO] Parsing modified simulation results...")
                                        # Add parsing logic here if needed
                                        # You could use the same parsing approach as in section 12
                                        # but pointing to the Modified_Sim_Results directory
                                        
                                except Exception as e:
                                    logger.error(f"[ERROR] Simulation failed: {str(e)}")
                                    import traceback
                                    traceback.print_exc()
                                    
                            else:
                                logger.warning("[WARN] No modified IDF files found to simulate")
                                logger.warning(f"[WARN] Check directory: {modified_idfs_dir}")
                else:
                    logger.warning("[WARN] No IDF variants were generated")
                    
            except Exception as e:
                logger.error(f"[ERROR] Modification failed: {str(e)}")
                import traceback
                traceback.print_exc()
                
    else:
        logger.info("[INFO] Skipping scenario modification.")

    # -------------------------------------------------------------------------
    # 14) Enhanced Validation with Parquet Support
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # 14) Smart Validation (Replaces Enhanced Validation)
    # -------------------------------------------------------------------------
    check_canceled()
    validation_cfg = main_config.get("validation", {})

    if validation_cfg.get("perform_validation", False):
        with step_timer(logger, "validation"):
            logger.info("[INFO] Running smart validation...")
            
            # Get configuration
            val_config = validation_cfg.get("config", {})
            
            # Get real data path
            real_data_path = val_config.get("real_data_path", "measured_data.csv")
            if not os.path.isabs(real_data_path):
                real_data_path = patch_if_relative(real_data_path)
            
            # Check if real data exists
            if not os.path.isfile(real_data_path):
                logger.error(f"[ERROR] Real data file not found: {real_data_path}")
            else:
                # Import smart validation
                try:
                    from validation.smart_validation_wrapper import run_smart_validation
                    
                    # Run validation
                    results = run_smart_validation(
                        parsed_data_path=os.path.join(job_output_dir, "parsed_data"),
                        real_data_path=real_data_path,
                        config=val_config,
                        output_path=os.path.join(job_output_dir, "validation_results")
                    )
                    
                    # Log results
                    if results and 'summary' in results:
                        summary = results['summary']
                        if 'status' in summary:
                            logger.warning(f"[WARN] Validation status: {summary['status']}")
                        else:
                            logger.info(f"[INFO] Validation complete:")
                            logger.info(f"  - Pass rate: {summary.get('pass_rate', 0):.1f}%")
                            logger.info(f"  - Buildings validated: {summary.get('buildings_validated', 0)}")
                            logger.info(f"  - Variables validated: {summary.get('variables_validated', 0)}")
                            
                            if summary.get('unit_conversions', 0) > 0:
                                logger.info(f"  - Unit conversions: {summary['unit_conversions']}")
                            if summary.get('zone_aggregations', 0) > 0:
                                logger.info(f"  - Zone aggregations: {summary['zone_aggregations']}")
                            
                            # Save summary for other steps (calibration, etc.)
                            if results.get('validation_results'):
                                val_df = pd.DataFrame(results['validation_results'])
                                summary_path = os.path.join(job_output_dir, "validation_summary.parquet")
                                val_df.to_parquet(summary_path, index=False)
                                logger.info(f"[INFO] Saved validation summary to: {summary_path}")
                    
                except Exception as e:
                    logger.error(f"[ERROR] Smart validation failed: {str(e)}")
                    import traceback
                    traceback.print_exc()
    else:
        logger.info("[INFO] Skipping validation.")


    # -------------------------------------------------------------------------
    # 17) Enhanced Sensitivity Analysis
    # -------------------------------------------------------------------------
    check_canceled()
    if sens_cfg.get("perform_sensitivity", False):
        with step_timer(logger, "enhanced sensitivity analysis"):
            logger.info("[INFO] Enhanced Sensitivity Analysis is ENABLED.")
            
            # Check configuration flags
            building_specific = sens_cfg.get("building_specific_analysis", False)
            multi_objective = sens_cfg.get("multi_objective_analysis", False)
            hierarchical = sens_cfg.get("hierarchical_analysis", False)
            validation_weighted = sens_cfg.get("validation_weighted_analysis", False)
            export_for_surrogate = sens_cfg.get("export_for_surrogate", False)
            export_for_calibration = sens_cfg.get("export_for_calibration", False)
            generate_visualizations = sens_cfg.get("generate_visualizations", False)
            
            logger.info("[INFO] Running enhanced sensitivity analysis with:")
            logger.info(f"  - Building-specific analysis: {building_specific}")
            logger.info(f"  - Multi-objective analysis: {multi_objective}")
            logger.info(f"  - Hierarchical analysis: {hierarchical}")
            logger.info(f"  - Validation-weighted analysis: {validation_weighted}")
            
            # Patch paths
            validation_csv = sens_cfg.get("validation_csv", "")
            sens_cfg["validation_csv"] = patch_if_relative(validation_csv)
            
            if validation_weighted and validation_csv:
                logger.info(f"  - Validation CSV: {os.path.basename(validation_csv)}")
            
            logger.info(f"  - Export for surrogate: {export_for_surrogate}")
            logger.info(f"  - Export for calibration: {export_for_calibration}")
            logger.info(f"  - Generate visualizations: {generate_visualizations}")
            
            try:
                # Initialize the data manager
                manager = SensitivityDataManager(
                    project_root=job_output_dir  # FIXED: Changed from output_dir to job_output_dir
                    
                )
                
                # Check if we have the required data
                if not manager.has_parsed_data():
                    logger.error("[ERROR] No parsed data found. Please run parsing first.")
                elif not manager.has_time_series_data():
                    logger.error("[ERROR] No time series data found. Check parsing results.")
                else:
                    # Run the enhanced sensitivity analysis
                    report_path = run_enhanced_sensitivity_analysis(
                        manager=manager,
                        config=sens_cfg,
                        logger=logger
                    )
                    
                    if report_path and os.path.exists(report_path):
                        logger.info(f"[INFO] Sensitivity analysis complete. Report saved to: {report_path}")
                        
                        # Generate visualizations if requested
                        if generate_visualizations:
                            reporter = SensitivityReporter(manager)
                            viz_dir = os.path.join(job_output_dir, "sensitivity_visualizations")
                            os.makedirs(viz_dir, exist_ok=True)
                            
                            # Generate various plots
                            figs_created = 0
                            
                            # Parameter importance plot
                            fig = reporter.plot_parameter_importance()
                            if fig:
                                fig.savefig(os.path.join(viz_dir, "parameter_importance.png"))
                                plt.close(fig)
                                figs_created += 1
                            
                            # Building-specific plots
                            if building_specific:
                                fig = reporter.plot_building_specific_sensitivity()
                                if fig:
                                    fig.savefig(os.path.join(viz_dir, "building_sensitivity.png"))
                                    plt.close(fig)
                                    figs_created += 1
                            
                            # Category hierarchy plot
                            if hierarchical:
                                fig = reporter.plot_category_hierarchy()
                                if fig:
                                    fig.savefig(os.path.join(viz_dir, "category_hierarchy.png"))
                                    plt.close(fig)
                                    figs_created += 1
                            
                            logger.info(f"[INFO] Generated {figs_created} visualization(s) in: {viz_dir}")
                    else:
                        logger.warning("[WARN] Sensitivity analysis completed but no report generated.")
                        
            except Exception as e:
                logger.error(f"[ERROR] Enhanced sensitivity analysis failed: {e}")
                import traceback
                traceback.print_exc()
    else:
        logger.info("[INFO] Skipping enhanced sensitivity analysis.")

    # -------------------------------------------------------------------------
    # 18) Surrogate Modeling - ENHANCED VERSION with AutoML
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

            # Get configuration parameters
            target_var = sur_cfg["target_variable"]
            test_size = sur_cfg.get("test_size", 0.3)
            
            # NEW: Enhanced parameters
            file_patterns = sur_cfg.get("file_patterns")
            param_filters = sur_cfg.get("param_filters")
            time_aggregation = sur_cfg.get("time_aggregation", "sum")
            time_features = sur_cfg.get("extract_time_features", False)
            automated_ml = sur_cfg.get("automated_ml", False)
            model_types = sur_cfg.get("model_types")
            cv_strategy = sur_cfg.get("cv_strategy", "kfold")
            scale_features = sur_cfg.get("scale_features", True)
            create_interactions = sur_cfg.get("create_interactions", False)
            sensitivity_path = sur_cfg.get("sensitivity_results_path")
            feature_selection = sur_cfg.get("feature_selection")
            
            # NEW: AutoML parameters
            use_automl = sur_cfg.get("use_automl", False)
            automl_framework = sur_cfg.get("automl_framework")
            automl_time_limit = sur_cfg.get("automl_time_limit", 300)
            automl_config = sur_cfg.get("automl_config", {})
            
            # Patch sensitivity path if relative
            if sensitivity_path:
                sensitivity_path = patch_if_relative(sensitivity_path)

            # Load scenario data with filtering
            df_scen = sur_load_scenario_params(
                sur_cfg["scenario_folder"],
                file_patterns=file_patterns,
                param_filters=param_filters
            )
            pivot_df = pivot_scenario_params(df_scen)

            # Load and aggregate results
            df_sim = load_sim_results(
                sur_cfg["results_csv"],
                target_variables=target_var if isinstance(target_var, list) else [target_var]
            )
            df_agg = aggregate_results(
                df_sim, 
                time_aggregation=time_aggregation,
                time_features=time_features
            )
            
            # Merge with optional interaction features
            merged_df = merge_params_with_results(
                pivot_df, 
                df_agg, 
                target_var,
                create_interactions=create_interactions,
                interaction_features=sur_cfg.get("interaction_features", 10)
            )

            # Build surrogate with enhanced options
            rf_model, trained_cols = build_and_save_surrogate(
                df_data=merged_df,
                target_col=target_var,
                model_out_path=sur_cfg["model_out"],
                columns_out_path=sur_cfg["cols_out"],
                test_size=test_size,
                random_state=42,
                # Enhanced parameters
                model_types=model_types,
                automated_ml=automated_ml,
                scale_features=scale_features,
                scaler_type=sur_cfg.get("scaler_type", "standard"),
                cv_strategy=cv_strategy,
                sensitivity_results_path=sensitivity_path,
                feature_selection=feature_selection,
                save_metadata=sur_cfg.get("save_metadata", True),
                # AutoML parameters
                use_automl=use_automl,
                automl_framework=automl_framework,
                automl_time_limit=automl_time_limit,
                automl_config=automl_config
            )
            
            if rf_model:
                logger.info("[INFO] Surrogate model built & saved.")
                if use_automl:
                    logger.info(f"[INFO] Used AutoML framework: {automl_framework or 'auto-selected'}")
            else:
                logger.warning("[WARN] Surrogate modeling failed or insufficient data.")
    else:
        logger.info("[INFO] Skipping surrogate modeling.")

    # -------------------------------------------------------------------------
    # 19) Calibration - ENHANCED VERSION
    # -------------------------------------------------------------------------
    check_canceled()
    if cal_cfg.get("perform_calibration", False):
        with step_timer(logger, "calibration"):
            logger.info("[INFO] Calibration is ENABLED.")
            
            # Check if using enhanced features
            has_multi_config = bool(cal_cfg.get("calibration_configs"))
            has_multi_objective = bool(cal_cfg.get("objectives"))
            uses_advanced_method = cal_cfg.get("method") in ["pso", "de", "nsga2", "cmaes", "hybrid"]
            
            if has_multi_config:
                logger.info("[INFO] Using enhanced multi-configuration calibration")
            if has_multi_objective:
                logger.info("[INFO] Using multi-objective optimization")
            if uses_advanced_method:
                logger.info(f"[INFO] Using advanced optimization method: {cal_cfg.get('method')}")

            # Standard path patching
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
            
            # NEW: Enhanced calibration path patching
            # Handle sensitivity results path
            sens_path = cal_cfg.get("sensitivity_results_path", "")
            if sens_path:
                cal_cfg["sensitivity_results_path"] = patch_if_relative(sens_path)
            
            # Handle subset sensitivity CSV
            subset_sens = cal_cfg.get("subset_sensitivity_csv", "")
            if subset_sens:
                cal_cfg["subset_sensitivity_csv"] = patch_if_relative(subset_sens)
            
            # Handle history folder if different from best_params_folder
            hist_folder = cal_cfg.get("history_folder", "")
            if hist_folder:
                cal_cfg["history_folder"] = patch_if_relative(hist_folder)
            
            # Handle multiple calibration configurations
            if has_multi_config:
                for i, config in enumerate(cal_cfg["calibration_configs"]):
                    # Each config might have its own paths
                    if "real_data_csv" in config:
                        config["real_data_csv"] = patch_if_relative(config["real_data_csv"])
                    if "output_csv" in config:
                        config["output_csv"] = patch_if_relative(config["output_csv"])
                    if "surrogate_model_path" in config:
                        config["surrogate_model_path"] = patch_if_relative(config["surrogate_model_path"])
                    if "surrogate_columns_path" in config:
                        config["surrogate_columns_path"] = patch_if_relative(config["surrogate_columns_path"])
            
            # Handle file patterns - these might have full paths
            file_patterns = cal_cfg.get("file_patterns", [])
            if file_patterns:
                patched_patterns = []
                for pattern in file_patterns:
                    # Only patch if it looks like a path (contains /)
                    if "/" in pattern:
                        patched_patterns.append(patch_if_relative(pattern))
                    else:
                        # It's just a pattern like "*.csv", leave as is
                        patched_patterns.append(pattern)
                cal_cfg["file_patterns"] = patched_patterns

            # Run the enhanced unified calibration
            run_unified_calibration(cal_cfg)
            
            # Log completion with enhanced info
            if os.path.exists(os.path.join(best_params_folder, "calibration_metadata.json")):
                logger.info("[INFO] Enhanced calibration completed with metadata saved")
            if os.path.exists(os.path.join(best_params_folder, "convergence_data.json")):
                logger.info("[INFO] Convergence data saved for analysis")
            if has_multi_config:
                summary_path = os.path.join(best_params_folder, "calibration_summary.json")
                if os.path.exists(summary_path):
                    logger.info("[INFO] Multi-configuration summary saved")
    else:
        logger.info("[INFO] Skipping calibration.")

    # -------------------------------------------------------------------------
    # 20) Zip & Email final results, if mail_user.json present
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