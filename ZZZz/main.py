"""
main.py as an API server that:
  - Provides a single endpoint (/run-workflow) which:
    * Receives a combined JSON payload
    * Splits it into sub-JSON files in user_configs/ folder
    * (Optionally) deep merges main_config with existing main_config.json
    * Spawns the entire E+ workflow in a background thread
    * Streams logs to the client in real time
"""

import os
import json
import logging
import threading
import queue
import time
from flask import Flask, request, Response, jsonify

import pandas as pd

# ------------------------------------------------------------------------
# (1) Import from your own modules
# ------------------------------------------------------------------------
from splitter import split_combined_json, deep_merge_dicts  # <--- from splitter.py
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

###############################################################################
# Custom Logging: We'll create a special handler that sends logs into a queue
###############################################################################
class QueueLoggerHandler(logging.Handler):
    """Custom logging handler that pushes logs into a queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


###############################################################################
# 1) Logging Setup
###############################################################################
def setup_logging_for_queue(log_queue, log_level=logging.INFO):
    """
    Configure the root logger to also send logs to an in-memory queue
    so we can stream them out to the HTTP client.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Optional: remove old handlers if you want a fresh start
    for h in logger.handlers[:]:
        logger.removeHandler(h)

    # 1) Console/logfile handlers as you wish
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # 2) Our queue handler
    queue_handler = QueueLoggerHandler(log_queue)
    queue_handler.setLevel(log_level)
    queue_handler.setFormatter(console_fmt)
    logger.addHandler(queue_handler)

    return logger


###############################################################################
# 2) Utility: load JSON from file
###############################################################################
def load_json(filepath):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    with open(filepath, "r") as f:
        return json.load(f)


###############################################################################
# 3) The Main Orchestration Workflow
###############################################################################
def orchestrate_workflow(override_json=None):
    """
    The entire logic that was previously in main().
    `override_json` can be any final overrides you want to merge with main_config.
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Starting orchestrate_workflow ===")

    # --------------------------------------------------------------------------
    # A) Load the existing main_config.json from user_configs
    # --------------------------------------------------------------------------
    current_dir = os.getcwd()
    user_configs_folder = os.path.join(current_dir, "user_configs")
    main_config_path = os.path.join(user_configs_folder, "main_config.json")

    if not os.path.isfile(main_config_path):
        logger.error(f"[ERROR] Cannot find main_config.json at {main_config_path}")
        return  # or raise an exception

    main_config_file = load_json(main_config_path)
    # main_config_file should look like {"main_config": {...}} if we splitted it using split_combined_json
    main_config = main_config_file.get("main_config", {})

    # --------------------------------------------------------------------------
    # B) Deep Merge override_json["main_config"] if provided
    # --------------------------------------------------------------------------
    if override_json and "main_config" in override_json:
        # override_json itself might contain other top-level keys, but let's specifically
        # deep-merge the "main_config" portion
        logger.info("[INFO] Deep merging override_json['main_config'] into existing main_config ...")
        from splitter import deep_merge_dicts  # or use the one already imported
        deep_merge_dicts(main_config, override_json["main_config"])
        # Re-save the updated main_config to disk
        with open(main_config_path, "w") as f:
            json.dump({"main_config": main_config}, f, indent=2)

    # Now we have our final main_config in memory
    logger.info("[INFO] Final main_config loaded & possibly merged.")

    # --------------------------------------------------------------------------
    # C) Possibly override idf_creation config with environment variables
    # --------------------------------------------------------------------------
    # NOTE: 'idf_creation.idf_config' is a module-level global in 'idf_creation.py'.
    # This approach can be fragile if used by multiple threads or multiple calls.
    # But we'll keep it for now.
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

    # Merge the local config from main_config["idf_creation"]
    idf_cfg = main_config.get("idf_creation", {})
    if "iddfile" in idf_cfg:
        idf_creation.idf_config["iddfile"] = idf_cfg["iddfile"]
    if "idf_file_path" in idf_cfg:
        idf_creation.idf_config["idf_file_path"] = idf_cfg["idf_file_path"]
    if "output_idf_dir" in idf_cfg:
        idf_creation.idf_config["output_dir"] = idf_cfg["output_idf_dir"]

    # --------------------------------------------------------------------------
    # D) Extract top-level fields from main_config
    # --------------------------------------------------------------------------
    paths_dict     = main_config.get("paths", {})
    excel_flags    = main_config.get("excel_overrides", {})
    user_flags     = main_config.get("user_config_overrides", {})
    def_dicts      = main_config.get("default_dicts", {})
    structuring_cfg  = main_config.get("structuring", {})
    modification_cfg = main_config.get("modification", {})
    validation_cfg   = main_config.get("validation", {})
    sens_cfg         = main_config.get("sensitivity", {})
    sur_cfg          = main_config.get("surrogate", {})
    cal_cfg          = main_config.get("calibration", {})

    # From idf_creation
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

    # Setup default dicts
    base_res_data    = def_dicts.get("res_data", {})
    base_nonres_data = def_dicts.get("nonres_data", {})
    dhw_lookup       = def_dicts.get("dhw", {})
    epw_lookup       = def_dicts.get("epw", [])
    lighting_lookup  = def_dicts.get("lighting", {})
    hvac_lookup      = def_dicts.get("hvac", {})
    vent_lookup      = def_dicts.get("vent", {})

    # --------------------------------------------------------------------------
    # E) Potentially override fenestration, DHW, EPW, etc. from Excel
    # (if excel_overrides flags are set)
    # --------------------------------------------------------------------------
    from idf_objects.fenez.fenez_config_manager import build_fenez_config
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=base_res_data,
        base_nonres_data=base_nonres_data,
        excel_path=paths_dict.get("fenez_excel", ""),
        do_excel_override=excel_flags.get("override_fenez_excel", False),
        user_fenez_overrides=[]
    )

    if excel_flags.get("override_dhw_excel", False):
        from excel_overrides import override_dhw_lookup_from_excel_file
        dhw_lookup = override_dhw_lookup_from_excel_file(
            dhw_excel_path=paths_dict.get("dhw_excel", ""),
            default_dhw_lookup=dhw_lookup,
            override_dhw_flag=True
        )

    if excel_flags.get("override_epw_excel", False):
        from excel_overrides import override_epw_lookup_from_excel_file
        epw_lookup = override_epw_lookup_from_excel_file(
            epw_excel_path=paths_dict.get("epw_excel", ""),
            epw_lookup=epw_lookup,
            override_epw_flag=True
        )

    if excel_flags.get("override_lighting_excel", False):
        from excel_overrides import override_lighting_lookup_from_excel_file
        lighting_lookup = override_lighting_lookup_from_excel_file(
            lighting_excel_path=paths_dict.get("lighting_excel", ""),
            lighting_lookup=lighting_lookup,
            override_lighting_flag=True
        )

    if excel_flags.get("override_hvac_excel", False):
        from excel_overrides import override_hvac_lookup_from_excel_file
        hvac_lookup = override_hvac_lookup_from_excel_file(
            hvac_excel_path=paths_dict.get("hvac_excel", ""),
            hvac_lookup=hvac_lookup,
            override_hvac_flag=True
        )

    if excel_flags.get("override_vent_excel", False):
        from excel_overrides import override_vent_lookup_from_excel_file
        vent_lookup = override_vent_lookup_from_excel_file(
            vent_excel_path=paths_dict.get("vent_excel", ""),
            vent_lookup=vent_lookup,
            override_vent_flag=True
        )

    # --------------------------------------------------------------------------
    # F) JSON overrides from user_configs/* if user_flags are set
    #    e.g. fenestration.json, dhw.json, epw.json, lighting.json, hvac.json, vent.json, ...
    # --------------------------------------------------------------------------
    def safe_load_subjson(fname, key):
        """
        Loads user_configs/fname if it exists, returns data.get(key, None).
        """
        full_path = os.path.join(user_configs_folder, fname)
        if os.path.isfile(full_path):
            try:
                data = load_json(full_path)
                return data.get(key, None)
            except Exception as e:
                logger.error(f"[ERROR] loading {fname} => {e}")
        return None

    # Fenestration
    user_fenez_data = []
    if user_flags.get("override_fenez_json", False):
        fenez_data = safe_load_subjson("fenestration.json", "fenestration")
        if fenez_data:
            user_fenez_data = fenez_data
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=updated_res_data,
        base_nonres_data=updated_nonres_data,
        excel_path="",  # no further Excel overrides
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
        epw_data = safe_load_subjson("epw.json", "epw")
        if epw_data:
            user_config_epw = epw_data

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
        vent_data = safe_load_subjson("vent.json", "vent")
        if vent_data:
            user_config_vent = vent_data

    # Geometry
    geom_data = {}
    if user_flags.get("override_geometry_json", False):
        geometry_loaded = safe_load_subjson("geometry.json", "geometry")
        if geometry_loaded:
            geom_data["geometry"] = geometry_loaded

    # Shading
    shading_data = {}
    if user_flags.get("override_shading_json", False):
        shading_loaded = safe_load_subjson("shading.json", "shading")
        if shading_loaded:
            shading_data["shading"] = shading_loaded

    # --------------------------------------------------------------------------
    # G) IDF Creation Step
    # --------------------------------------------------------------------------
    if perform_idf_creation:
        logger.info("[INFO] IDF creation is ENABLED.")

        # (1) Get building DataFrame
        df_buildings = pd.DataFrame()
        if use_database:
            logger.info("[INFO] Loading building data from DB.")
            df_buildings = load_buildings_from_db(db_filter)
            if df_buildings.empty:
                logger.warning("[WARN] No buildings returned from DB filters.")
        else:
            bldg_data_path = paths_dict.get("building_data", "")
            if os.path.isfile(bldg_data_path):
                df_buildings = pd.read_csv(bldg_data_path)
            else:
                logger.warning(f"[WARN] Building data CSV not found => {bldg_data_path}")

        # (2) Create IDFs
        from idf_creation import create_idfs_for_all_buildings
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

    # --------------------------------------------------------------------------
    # H) Structuring Step
    # --------------------------------------------------------------------------
    if structuring_cfg.get("perform_structuring", False):
        logger.info("[INFO] Performing structuring ...")

        # Example fenestration struct
        from idf_objects.structuring.fenestration_structuring import (
            transform_fenez_log_to_structured_with_ranges
        )
        fenez_conf = structuring_cfg.get("fenestration", {})
        fenez_in   = fenez_conf.get("csv_in",  "output/assigned/assigned_fenez_params.csv")
        fenez_out  = fenez_conf.get("csv_out", "output/assigned/structured_fenez_params.csv")
        transform_fenez_log_to_structured_with_ranges(csv_input=fenez_in, csv_output=fenez_out)

        # Similarly for DHW, HVAC, Vent ...
        from idf_objects.structuring.dhw_structuring import transform_dhw_log_to_structured
        dhw_conf = structuring_cfg.get("dhw", {})
        dhw_in   = dhw_conf.get("csv_in",  "output/assigned/assigned_dhw_params.csv")
        dhw_out  = dhw_conf.get("csv_out", "output/assigned/structured_dhw_params.csv")
        transform_dhw_log_to_structured(csv_input=dhw_in, csv_output=dhw_out)

        from idf_objects.structuring.flatten_hvac import flatten_hvac_data, parse_assigned_value as parse_hvac
        hvac_conf = structuring_cfg.get("hvac", {})
        hvac_in   = hvac_conf.get("csv_in", "output/assigned/assigned_hvac_params.csv")
        hvac_bld  = hvac_conf.get("build_out", "output/assigned/assigned_hvac_building.csv")
        hvac_zone = hvac_conf.get("zone_out",  "output/assigned/assigned_hvac_zones.csv")
        if os.path.isfile(hvac_in):
            df_hvac = pd.read_csv(hvac_in)
            df_hvac["assigned_value"] = df_hvac["assigned_value"].apply(parse_hvac)
            flatten_hvac_data(df_input=df_hvac, out_build_csv=hvac_bld, out_zone_csv=hvac_zone)

        from idf_objects.structuring.flatten_assigned_vent import (
            flatten_ventilation_data,
            parse_assigned_value as parse_vent
        )
        vent_conf = structuring_cfg.get("vent", {})
        vent_in   = vent_conf.get("csv_in", "output/assigned/assigned_ventilation.csv")
        vent_bld  = vent_conf.get("build_out", "output/assigned/assigned_vent_building.csv")
        vent_zone = vent_conf.get("zone_out", "output/assigned/assigned_vent_zones.csv")
        if os.path.isfile(vent_in):
            df_vent = pd.read_csv(vent_in)
            df_vent["assigned_value"] = df_vent["assigned_value"].apply(parse_vent)
            flatten_ventilation_data(df_input=df_vent, out_build_csv=vent_bld, out_zone_csv=vent_zone)
    else:
        logger.info("[INFO] Skipping structuring.")

    # --------------------------------------------------------------------------
    # I) Scenario Modification
    # --------------------------------------------------------------------------
    if modification_cfg.get("perform_modification", False):
        logger.info("[INFO] Scenario modification is ENABLED.")
        run_modification_workflow(modification_cfg["modify_config"])
    else:
        logger.info("[INFO] Skipping scenario modification.")

    # --------------------------------------------------------------------------
    # J) Global Validation
    # --------------------------------------------------------------------------
    if validation_cfg.get("perform_validation", False):
        logger.info("[INFO] Global Validation is ENABLED.")
        run_validation_process(validation_cfg["config"])
    else:
        logger.info("[INFO] Skipping global validation.")

    # --------------------------------------------------------------------------
    # K) Sensitivity Analysis
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
    # L) Surrogate Modeling
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # M) Calibration
    # --------------------------------------------------------------------------
    if cal_cfg.get("perform_calibration", False):
        logger.info("[INFO] Calibration is ENABLED.")
        run_unified_calibration(cal_cfg)
    else:
        logger.info("[INFO] Skipping calibration.")

    logger.info("=== End of orchestrate_workflow ===")


###############################################################################
# 4) Flask App for Real-Time Streaming
###############################################################################
app = Flask(__name__)

@app.route("/run-workflow", methods=["POST"])
def run_workflow_api():
    """
    This single endpoint:
      1) Receives a combined JSON in the request body.
      2) Splits it into sub-JSON files in user_configs/ (via split_combined_json).
      3) Deep merges 'main_config' from the request (if present) with existing user_configs/main_config.json
      4) Spawns the orchestrate_workflow in a background thread
      5) Streams logs back to the client in real time.
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON payload"}), 400

    posted_data = request.get_json()
    user_configs_folder = os.path.join(os.getcwd(), "user_configs")

    # 1) Split the posted data into separate JSON files (dhw.json, epw.json, etc.)
    split_combined_json(posted_data, user_configs_folder)

    # 2) We'll pass the entire posted_data as override_json to orchestrate_workflow.
    #    The orchestrate_workflow function itself will do the deep merge of "main_config".
    override_json = posted_data

    # 3) Create a thread-safe queue for logs
    log_queue = queue.Queue()
    setup_logging_for_queue(log_queue, log_level=logging.INFO)

    # 4) Background function to run the workflow
    def background_workflow():
        try:
            orchestrate_workflow(override_json=override_json)
        except Exception as e:
            logging.getLogger(__name__).exception(f"Workflow crashed: {e}")
        finally:
            # Put a sentinel (None) to signal that logs are done
            log_queue.put(None)

    # 5) Start the background thread
    t = threading.Thread(target=background_workflow, daemon=True)
    t.start()

    # 6) Define a generator that yields log lines
    def log_stream():
        while True:
            msg = log_queue.get()
            if msg is None:
                break
            yield msg + "\n"

    # 7) Return a streaming response
    return Response(log_stream(), mimetype='text/plain')


if __name__ == "__main__":
    # Run the Flask app on port 8000
    app.run(host="0.0.0.0", port=8000, debug=True)
