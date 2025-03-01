"""
main.py

Orchestrates the entire workflow:
  1) Loads main_config.json (which has two sets of override flags:
     excel_overrides, user_config_overrides) plus a "structuring" section
     for post-processing logs into structured CSVs.
  2) Applies Excel overrides if "override_*_excel" is True.
  3) Applies JSON overrides if "override_*_json" is True,
     loading fenestration.json, dhw.json, etc.
  4) Creates base IDFs (optional), runs simulations & merges results (optional).
  5) If "perform_structuring" is true, restructures the assigned_* CSV logs
     into more refined CSVs for scenario usage.
  6) If "perform_modification" is true, calls `run_modification_workflow`
     to create scenario-based IDFs & run them.
  7) If "perform_validation" is true, calls global validation.
  8) If "perform_sensitivity" is true, runs a sensitivity analysis.
  9) If "perform_surrogate" is true, builds a surrogate model.
 10) If "perform_calibration" is true, does calibration steps.
"""

import os
import json
import logging
import pandas as pd

# Database loader (if "use_database": true)
from database_handler import load_buildings_from_db

# --------------------------------------------------------------------------
# A) Overriding modules (Excel + JSON partial overrides)
# --------------------------------------------------------------------------
from excel_overrides import (
    override_dhw_lookup_from_excel_file,
    override_epw_lookup_from_excel_file,
    override_lighting_lookup_from_excel_file,
    override_hvac_lookup_from_excel_file,
    override_vent_lookup_from_excel_file
)
from idf_objects.fenez.fenez_config_manager import build_fenez_config

# --------------------------------------------------------------------------
# B) IDF creation & scenario modules
# --------------------------------------------------------------------------
import idf_creation  # We'll override idf_creation.idf_config with env vars below
from idf_creation import create_idfs_for_all_buildings
from main_modifi import run_modification_workflow

# --------------------------------------------------------------------------
# C) Validation
# --------------------------------------------------------------------------
from validation.main_validation import run_validation_process

# --------------------------------------------------------------------------
# D) Calibration, Sensitivity, Surrogate modules
# --------------------------------------------------------------------------
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


###############################################################################
# 1) Logging Setup
###############################################################################
def setup_logging(log_level=logging.INFO):
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


###############################################################################
# 2) Utility: load JSON from file
###############################################################################
def load_json(filepath):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    with open(filepath, "r") as f:
        return json.load(f)


###############################################################################
# 3) Main Orchestration
###############################################################################
def main():
    logger = setup_logging()
    logger.info("=== Starting main.py ===")

    # --------------------------------------------------------------------------
    # A) Load main_config.json from user_configs folder
    #    (Adjust path to match your Docker or local directory structure)
    # --------------------------------------------------------------------------
    # For Docker, you might keep user configs in "/app/user_configs"
    # or somewhere else. Example:
    user_configs_folder = os.path.join(os.path.dirname(__file__), "user_configs")
    main_config_path = os.path.join(user_configs_folder, "main_config.json")

    if not os.path.isfile(main_config_path):
        logger.error(f"[ERROR] Cannot find main_config.json at {main_config_path}")
        return

    main_config = load_json(main_config_path)

    # --------------------------------------------------------------------------
    # B) Override idf_creation config with environment variables (if present)
    #    This ensures Docker .env or docker-compose environment can override them
    # --------------------------------------------------------------------------
    env_idd_path = os.environ.get("IDD_PATH")
    if env_idd_path:
        idf_creation.idf_config["iddfile"] = env_idd_path
    env_base_idf = os.environ.get("BASE_IDF_PATH")
    if env_base_idf:
        idf_creation.idf_config["idf_file_path"] = env_base_idf
    env_out_dir = os.environ.get("OUTPUT_DIR")
    if env_out_dir:
        # We'll store IDFs in a subfolder, e.g. "/app/output/output_IDFs"
        out_idf_dir = os.path.join(env_out_dir, "output_IDFs")
        idf_creation.idf_config["output_dir"] = out_idf_dir

    # --------------------------------------------------------------------------
    # Extract top-level sections from main_config
    # --------------------------------------------------------------------------
    paths_dict       = main_config.get("paths", {})
    excel_flags      = main_config.get("excel_overrides", {})
    user_flags       = main_config.get("user_config_overrides", {})
    def_dicts        = main_config.get("default_dicts", {})
    idf_cfg          = main_config.get("idf_creation", {})
    structuring_cfg  = main_config.get("structuring", {})
    modification_cfg = main_config.get("modification", {})
    validation_cfg   = main_config.get("validation", {})
    sens_cfg         = main_config.get("sensitivity", {})
    sur_cfg          = main_config.get("surrogate", {})
    cal_cfg          = main_config.get("calibration", {})

    # --------------------------------------------------------------------------
    # C) Setup default dictionaries (fenestration + others)
    # --------------------------------------------------------------------------
    base_res_data    = def_dicts.get("res_data", {})
    base_nonres_data = def_dicts.get("nonres_data", {})
    dhw_lookup       = def_dicts.get("dhw", {})
    epw_lookup       = def_dicts.get("epw", [])
    lighting_lookup  = def_dicts.get("lighting", {})
    hvac_lookup      = def_dicts.get("hvac", {})
    vent_lookup      = def_dicts.get("vent", {})

    # --------------------------------------------------------------------------
    # D) Excel-based overrides if flagged
    # --------------------------------------------------------------------------
    override_fenez_excel = excel_flags.get("override_fenez_excel", False)
    fenez_excel_path     = paths_dict.get("fenez_excel", "")

    # Build fenestration config from Excel (if enabled)
    from idf_objects.fenez.fenez_config_manager import build_fenez_config
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=base_res_data,
        base_nonres_data=base_nonres_data,
        excel_path=fenez_excel_path,
        do_excel_override=override_fenez_excel,
        user_fenez_overrides=[]
    )

    # Other Excel overrides
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

    # --------------------------------------------------------------------------
    # E) User JSON overrides if flagged
    # --------------------------------------------------------------------------
    #  - Fenestration
    override_fenez_json = user_flags.get("override_fenez_json", False)
    if override_fenez_json:
        fenestration_json_path = os.path.join(user_configs_folder, "fenestration.json")
        if os.path.isfile(fenestration_json_path):
            try:
                fen_data = load_json(fenestration_json_path)
                user_fenez_overrides = fen_data.get("fenestration", [])
            except Exception as e:
                logger.error(f"[ERROR] loading fenestration.json => {e}")
                user_fenez_overrides = []
        else:
            logger.warning(f"[WARN] fenestration.json not found at {fenestration_json_path}")
            user_fenez_overrides = []
    else:
        user_fenez_overrides = []

    # Re-apply fenestration config with user_fenez_overrides
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=updated_res_data,
        base_nonres_data=updated_nonres_data,
        excel_path="",
        do_excel_override=False,
        user_fenez_overrides=user_fenez_overrides
    )

    #  - DHW JSON
    override_dhw_json = user_flags.get("override_dhw_json", False)
    user_config_dhw = None
    if override_dhw_json:
        dhw_json_path = os.path.join(user_configs_folder, "dhw.json")
        if os.path.isfile(dhw_json_path):
            try:
                dhw_data = load_json(dhw_json_path)
                user_config_dhw = dhw_data.get("dhw", [])
            except Exception as e:
                logger.error(f"[ERROR] loading dhw.json => {e}")
                user_config_dhw = None

    #  - EPW JSON
    override_epw_json = user_flags.get("override_epw_json", False)
    user_config_epw = []
    if override_epw_json:
        epw_json_path = os.path.join(user_configs_folder, "epw.json")
        if os.path.isfile(epw_json_path):
            epw_data = load_json(epw_json_path)
            user_config_epw = epw_data.get("epw", [])

    #  - Lighting JSON
    override_lighting_json = user_flags.get("override_lighting_json", False)
    user_config_lighting = None
    if override_lighting_json:
        lighting_json_path = os.path.join(user_configs_folder, "lighting.json")
        if os.path.isfile(lighting_json_path):
            try:
                lighting_data = load_json(lighting_json_path)
                user_config_lighting = lighting_data.get("lighting", [])
            except Exception as e:
                logger.error(f"[ERROR] loading lighting.json => {e}")
                user_config_lighting = None

    #  - HVAC JSON
    override_hvac_json = user_flags.get("override_hvac_json", False)
    user_config_hvac = None
    if override_hvac_json:
        hvac_json_path = os.path.join(user_configs_folder, "hvac.json")
        if os.path.isfile(hvac_json_path):
            hvac_data = load_json(hvac_json_path)
            user_config_hvac = hvac_data.get("hvac", [])
        else:
            logger.warning("[WARN] hvac.json not found.")

    #  - Vent JSON
    override_vent_json = user_flags.get("override_vent_json", False)
    user_config_vent = []
    if override_vent_json:
        vent_json_path = os.path.join(user_configs_folder, "vent.json")
        if os.path.isfile(vent_json_path):
            vent_data = load_json(vent_json_path)
            user_config_vent = vent_data.get("vent", [])
        else:
            user_config_vent = []

    #  - Geometry JSON
    override_geometry_json = user_flags.get("override_geometry_json", False)
    geometry_dict = {}
    geom_data = {}
    if override_geometry_json:
        geometry_json_path = os.path.join(user_configs_folder, "geometry.json")
        if os.path.isfile(geometry_json_path):
            try:
                geom_data = load_json(geometry_json_path)
                from user_config_overrides import apply_geometry_user_config
                geometry_dict = apply_geometry_user_config({}, geom_data.get("geometry", []))
            except Exception as e:
                logger.error(f"[ERROR] loading geometry.json => {e}")

    #  - Shading JSON
    override_shading_json = user_flags.get("override_shading_json", False)
    shading_dict = {}
    if override_shading_json:
        shading_json_path = os.path.join(user_configs_folder, "shading.json")
        if os.path.isfile(shading_json_path):
            try:
                shading_data = load_json(shading_json_path)
                from user_config_overrides import apply_shading_user_config
                shading_dict = apply_shading_user_config({}, shading_data.get("shading", []))
            except Exception as e:
                logger.error(f"[ERROR] loading shading.json => {e}")

    # --------------------------------------------------------------------------
    # F) IDF Creation (if enabled)
    #    -> Here is where we load building data from either DB or CSV
    # --------------------------------------------------------------------------
    if idf_cfg.get("perform_idf_creation", False):
        logger.info("[INFO] IDF creation is ENABLED.")

        use_database = main_config.get("use_database", False)
        db_filter = main_config.get("db_filter", {})  # e.g. { "postcodes": [...], "bbox_xy": [...], etc. }

        # Option 1: Load from DB if "use_database" is True
        if use_database:
            logger.info("[INFO] Loading building data from PostgreSQL using filter criteria.")
            df_buildings = load_buildings_from_db(db_filter)

            if df_buildings.empty:
                logger.warning("[WARN] No buildings returned from the DB based on filters; using empty DataFrame.")
        else:
            # Option 2: Fallback to CSV
            bldg_data_path = paths_dict.get("building_data", "")
            if os.path.isfile(bldg_data_path):
                df_buildings = pd.read_csv(bldg_data_path)
            else:
                logger.warning(f"[WARN] Building data CSV not found at {bldg_data_path}. Using empty DF.")
                df_buildings = pd.DataFrame()

        # Now create IDFs
        create_idfs_for_all_buildings(
            df_buildings=df_buildings,
            scenario=idf_cfg.get("scenario", "scenario1"),
            calibration_stage=idf_cfg.get("calibration_stage", "pre_calibration"),
            strategy=idf_cfg.get("strategy", "B"),
            random_seed=idf_cfg.get("random_seed", 42),
            user_config_geom=geom_data.get("geometry", []) if override_geometry_json else None,
            user_config_lighting=user_config_lighting,
            user_config_dhw=user_config_dhw,
            res_data=updated_res_data,
            nonres_data=updated_nonres_data,
            user_config_hvac=user_config_hvac,
            user_config_vent=user_config_vent,
            user_config_epw=user_config_epw,  # if your create_idfs_for_all_buildings uses it
            run_simulations=idf_cfg.get("run_simulations", True),
            simulate_config={"num_workers": idf_cfg.get("num_workers", 4)},
            post_process=idf_cfg.get("post_process", True)
        )
    else:
        logger.info("[INFO] Skipping IDF creation per user config.")

    # --------------------------------------------------------------------------
    # G) Structuring Step
    # --------------------------------------------------------------------------
    if structuring_cfg.get("perform_structuring", False):
        logger.info("[INFO] Performing log structuring (fenestration, dhw, hvac, vent).")

        # 1) Fenestration
        from idf_objects.structuring.fenestration_structuring import transform_fenez_log_to_structured_with_ranges
        fenez_conf = structuring_cfg.get("fenestration", {})
        fenez_in   = fenez_conf.get("csv_in",  "output/assigned/assigned_fenez_params.csv")
        fenez_out  = fenez_conf.get("csv_out", "output/assigned/structured_fenez_params.csv")
        transform_fenez_log_to_structured_with_ranges(csv_input=fenez_in, csv_output=fenez_out)

        # 2) DHW
        from idf_objects.structuring.dhw_structuring import transform_dhw_log_to_structured
        dhw_conf = structuring_cfg.get("dhw", {})
        dhw_in   = dhw_conf.get("csv_in",  "output/assigned/assigned_dhw_params.csv")
        dhw_out  = dhw_conf.get("csv_out", "output/assigned/structured_dhw_params.csv")
        transform_dhw_log_to_structured(csv_input=dhw_in, csv_output=dhw_out)

        # 3) HVAC
        from idf_objects.structuring.flatten_hvac import flatten_hvac_data, parse_assigned_value
        hvac_conf = structuring_cfg.get("hvac", {})
        hvac_in   = hvac_conf.get("csv_in",    "output/assigned/assigned_hvac_params.csv")
        hvac_bld  = hvac_conf.get("build_out", "output/assigned/assigned_hvac_building.csv")
        hvac_zone = hvac_conf.get("zone_out",  "output/assigned/assigned_hvac_zones.csv")

        if os.path.isfile(hvac_in):
            df_hvac = pd.read_csv(hvac_in)
            df_hvac["assigned_value"] = df_hvac["assigned_value"].apply(parse_assigned_value)
            flatten_hvac_data(df_input=df_hvac, out_build_csv=hvac_bld, out_zone_csv=hvac_zone)
        else:
            logger.warning(f"[WARN] HVAC input CSV not found at {hvac_in}; skipping.")

        # 4) Vent
        from idf_objects.structuring.flatten_assigned_vent import flatten_ventilation_data, parse_assigned_value
        vent_conf = structuring_cfg.get("vent", {})
        vent_in   = vent_conf.get("csv_in",    "output/assigned/assigned_ventilation.csv")
        vent_bld  = vent_conf.get("build_out", "output/assigned/assigned_vent_building.csv")
        vent_zone = vent_conf.get("zone_out",  "output/assigned/assigned_vent_zones.csv")

        if os.path.isfile(vent_in):
            df_vent = pd.read_csv(vent_in)
            df_vent["assigned_value"] = df_vent["assigned_value"].apply(parse_assigned_value)
            flatten_ventilation_data(df_input=df_vent, out_build_csv=vent_bld, out_zone_csv=vent_zone)
        else:
            logger.warning(f"[WARN] Vent input CSV not found at {vent_in}; skipping.")
    else:
        logger.info("[INFO] Skipping structuring step (perform_structuring=false).")

    # --------------------------------------------------------------------------
    # H) Scenario Modification / Generation
    # --------------------------------------------------------------------------
    if modification_cfg.get("perform_modification", False):
        logger.info("[INFO] Scenario modification is ENABLED.")
        run_modification_workflow(modification_cfg["modify_config"])
    else:
        logger.info("[INFO] Skipping scenario modification.")

    # --------------------------------------------------------------------------
    # I) Global Validation
    # --------------------------------------------------------------------------
    if validation_cfg.get("perform_validation", False):
        logger.info("[INFO] Global Validation is ENABLED.")
        run_validation_process(validation_cfg["config"])
    else:
        logger.info("[INFO] Skipping global validation.")

    # --------------------------------------------------------------------------
    # J) Sensitivity Analysis
    # --------------------------------------------------------------------------
    if sens_cfg.get("perform_sensitivity", False):
        logger.info("[INFO] Sensitivity Analysis is ENABLED.")
        run_sensitivity_analysis(
            scenario_folder=sens_cfg["scenario_folder"],
            method=sens_cfg["method"],
            results_csv=sens_cfg.get("results_csv", ""),
            target_variable=sens_cfg.get("target_variable", ""),
            output_csv=sens_cfg.get("output_csv", "sensitivity_output.csv"),
            n_morris_trajectories=sens_cfg.get("n_morris_trajectories", 10),
            num_levels=sens_cfg.get("num_levels", 4),
            n_sobol_samples=sens_cfg.get("n_sobol_samples", 128)
        )
    else:
        logger.info("[INFO] Skipping sensitivity analysis.")

    # --------------------------------------------------------------------------
    # K) Surrogate Modeling
    # --------------------------------------------------------------------------
    if sur_cfg.get("perform_surrogate", False):
        logger.info("[INFO] Surrogate Modeling is ENABLED.")

        scenario_folder = sur_cfg["scenario_folder"]
        results_csv     = sur_cfg["results_csv"]
        target_var      = sur_cfg["target_variable"]
        model_out       = sur_cfg["model_out"]
        cols_out        = sur_cfg["cols_out"]
        test_size       = sur_cfg["test_size"]

        # 1) Load & pivot scenario params
        df_scen = sur_load_scenario_params(scenario_folder)
        pivot_df = pivot_scenario_params(df_scen)

        # 2) (Optional) filter top parameters - if you want
        # pivot_df = filter_top_parameters(pivot_df, "morris_sensitivity.csv", top_n=5)

        # 3) Load & aggregate sim results
        df_sim = load_sim_results(results_csv)
        df_agg = aggregate_results(df_sim)

        # 4) Merge
        merged_df = merge_params_with_results(pivot_df, df_agg, target_var)

        # 5) Build & save surrogate
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

    # --------------------------------------------------------------------------
    # L) Calibration
    # --------------------------------------------------------------------------
    if cal_cfg.get("perform_calibration", False):
        logger.info("[INFO] Calibration steps are ENABLED.")
        run_unified_calibration(cal_cfg)
    else:
        logger.info("[INFO] Skipping calibration steps.")

    logger.info("=== End of main.py ===")


###############################################################################
# 4) Script Entry
###############################################################################
if __name__ == "__main__":
    main()
