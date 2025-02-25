"""
main.py as an API server that:
  - Provides an endpoint /run-workflow (POST)
  - Reads/merges optional user config JSON from request
  - Runs your existing orchestration logic in a background thread
  - Streams partial logs/updates back to the client
"""

import os
import json
import logging
import threading
import queue
import time
from flask import Flask, request, Response

import pandas as pd

# ------------------------------------------------------------------------
# (1) Import all your submodules exactly as before
# ------------------------------------------------------------------------
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

# If these come from user_config_overrides, ensure correct import:
# from user_config_overrides import apply_geometry_user_config, apply_shading_user_config


###############################################################################
# Custom Logging: We'll create a special handler that sends logs to a queue
###############################################################################
class QueueLoggerHandler(logging.Handler):
    """Custom logging handler to push logs into a queue."""
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
    Configure root logger to also send logs to an in-memory queue so we can
    stream them out to the HTTP client.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Optional: remove old handlers if you want a fresh start
    for h in logger.handlers[:]:
        logger.removeHandler(h)

    # Console/logfile handlers as you wish
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # Our queue handler
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
# 3) Orchestration Logic (previously main() ). Renamed to a function so we can
#    call it from the Flask endpoint in a background thread.
###############################################################################
def orchestrate_workflow(override_json=None):
    """
    The entire logic that was previously in main().
    `override_json` can be a dict to merge with main_config if provided by the user
    via POST request (optional).
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Starting orchestrate_workflow ===")

    # --------------------------------------------------------------------------
    # A) Load main_config.json
    # --------------------------------------------------------------------------
    current_dir = os.getcwd()
    user_configs_folder = os.path.join(current_dir, "user_configs")
    main_config_path = os.path.join(user_configs_folder, "main_config.json")

    if not os.path.isfile(main_config_path):
        logger.error(f"[ERROR] Cannot find main_config.json at {main_config_path}")
        return

    main_config = load_json(main_config_path)

    # If you want to merge any user POSTed config into main_config:
    if override_json is not None:
        # Shallow example: main_config.update(override_json)
        # Or do a deeper merge, depending on your structure
        logger.info("[INFO] Merging override_json into main_config ...")
        main_config = {**main_config, **override_json}
        # More advanced merges can be done if you have nested dicts, etc.

    # --------------------------------------------------------------------------
    # B) Possibly override idf_creation config with environment variables
    # --------------------------------------------------------------------------
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

    # Also read user overrides from main_config["idf_creation"]
    idf_cfg = main_config.get("idf_creation", {})
    custom_idd = idf_cfg.get("iddfile")
    if custom_idd:
        idf_creation.idf_config["iddfile"] = custom_idd
    custom_base_idf = idf_cfg.get("idf_file_path")
    if custom_base_idf:
        idf_creation.idf_config["idf_file_path"] = custom_base_idf
    custom_out_dir = idf_cfg.get("output_idf_dir")
    if custom_out_dir:
        idf_creation.idf_config["output_dir"] = custom_out_dir

    # Extract top-level fields from main_config
    paths_dict = main_config.get("paths", {})
    excel_flags = main_config.get("excel_overrides", {})
    user_flags  = main_config.get("user_config_overrides", {})
    def_dicts   = main_config.get("default_dicts", {})

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

    # Excel overrides
    override_fenez_excel = excel_flags.get("override_fenez_excel", False)
    fenez_excel_path     = paths_dict.get("fenez_excel", "")
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=base_res_data,
        base_nonres_data=base_nonres_data,
        excel_path=fenez_excel_path,
        do_excel_override=override_fenez_excel,
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

    # JSON overrides
    user_fenez_overrides = []
    if user_flags.get("override_fenez_json", False):
        fenestration_json_path = os.path.join(user_configs_folder, "fenestration.json")
        if os.path.isfile(fenestration_json_path):
            try:
                fen_data = load_json(fenestration_json_path)
                user_fenez_overrides = fen_data.get("fenestration", [])
            except Exception as e:
                logger.error(f"[ERROR] loading fenestration.json => {e}")

    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=updated_res_data,
        base_nonres_data=updated_nonres_data,
        excel_path="",
        do_excel_override=False,
        user_fenez_overrides=user_fenez_overrides
    )

    user_config_dhw = None
    if user_flags.get("override_dhw_json", False):
        dhw_json_path = os.path.join(user_configs_folder, "dhw.json")
        if os.path.isfile(dhw_json_path):
            try:
                dhw_data = load_json(dhw_json_path)
                user_config_dhw = dhw_data.get("dhw", [])
            except Exception as e:
                logger.error(f"[ERROR] loading dhw.json => {e}")

    user_config_epw = []
    if user_flags.get("override_epw_json", False):
        epw_json_path = os.path.join(user_configs_folder, "epw.json")
        if os.path.isfile(epw_json_path):
            epw_data = load_json(epw_json_path)
            user_config_epw = epw_data.get("epw", [])

    user_config_lighting = None
    if user_flags.get("override_lighting_json", False):
        lighting_json_path = os.path.join(user_configs_folder, "lighting.json")
        if os.path.isfile(lighting_json_path):
            try:
                lighting_data = load_json(lighting_json_path)
                user_config_lighting = lighting_data.get("lighting", [])
            except Exception as e:
                logger.error(f"[ERROR] loading lighting.json => {e}")

    user_config_hvac = None
    if user_flags.get("override_hvac_json", False):
        hvac_json_path = os.path.join(user_configs_folder, "hvac.json")
        if os.path.isfile(hvac_json_path):
            hvac_data = load_json(hvac_json_path)
            user_config_hvac = hvac_data.get("hvac", [])

    user_config_vent = []
    if user_flags.get("override_vent_json", False):
        vent_json_path = os.path.join(user_configs_folder, "vent.json")
        if os.path.isfile(vent_json_path):
            vent_data = load_json(vent_json_path)
            user_config_vent = vent_data.get("vent", [])

    geometry_dict = {}
    geom_data = {}
    if user_flags.get("override_geometry_json", False):
        geometry_json_path = os.path.join(user_configs_folder, "geometry.json")
        if os.path.isfile(geometry_json_path):
            try:
                geom_data = load_json(geometry_json_path)
                # from user_config_overrides import apply_geometry_user_config
                # geometry_dict = apply_geometry_user_config({}, geom_data.get("geometry", []))
            except Exception as e:
                logger.error(f"[ERROR] loading geometry.json => {e}")

    shading_dict = {}
    if user_flags.get("override_shading_json", False):
        shading_json_path = os.path.join(user_configs_folder, "shading.json")
        if os.path.isfile(shading_json_path):
            try:
                shading_data = load_json(shading_json_path)
                # from user_config_overrides import apply_shading_user_config
                # shading_dict = apply_shading_user_config({}, shading_data.get("shading", []))
            except Exception as e:
                logger.error(f"[ERROR] loading shading.json => {e}")

    # --------------------------------------------------------------------------
    # F) IDF Creation
    # --------------------------------------------------------------------------
    if perform_idf_creation:
        logger.info("[INFO] IDF creation is ENABLED.")

        # 1) Get building DataFrame
        if use_database:
            logger.info("[INFO] Loading building data from PostgreSQL using filters.")
            df_buildings = load_buildings_from_db(db_filter)
            if df_buildings.empty:
                logger.warning("[WARN] No buildings returned from DB filters.")
        else:
            bldg_data_path = paths_dict.get("building_data", "")
            if os.path.isfile(bldg_data_path):
                df_buildings = pd.read_csv(bldg_data_path)
            else:
                logger.warning(f"[WARN] Building data CSV not found at {bldg_data_path}.")
                df_buildings = pd.DataFrame()

        # 2) Create IDFs
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
    # G) Structuring Step
    # --------------------------------------------------------------------------
    if structuring_cfg.get("perform_structuring", False):
        logger.info("[INFO] Performing log structuring ...")
        # Example fenestration structuring
        from idf_objects.structuring.fenestration_structuring import transform_fenez_log_to_structured_with_ranges
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

    # --------------------------------------------------------------------------
    # H) Scenario Modification
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
    # L) Calibration
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
    Endpoint to start the entire workflow.  
    - Accepts optional JSON in the request body to override or augment main_config.  
    - Returns a streaming (chunked) HTTP response of log lines as they occur.
    """
    # (A) Parse JSON from request (optional)
    override_json = None
    if request.is_json:
        override_json = request.get_json()

    # (B) Create a thread-safe queue for logs
    log_queue = queue.Queue()

    # (C) Setup logging to push all log messages into the queue
    setup_logging_for_queue(log_queue, log_level=logging.INFO)

    # (D) Define a background function that runs the workflow
    def background_workflow():
        try:
            orchestrate_workflow(override_json=override_json)
        except Exception as e:
            logging.getLogger(__name__).exception(f"Workflow crashed: {e}")
        finally:
            # Put a sentinel in the queue to signal we're done
            log_queue.put(None)

    # (E) Start the background thread
    t = threading.Thread(target=background_workflow, daemon=True)
    t.start()

    # (F) Define a generator that yields log lines from the queue in real time
    def log_stream():
        """
        Continuously read from log_queue and yield lines to the client.
        If we encounter `None`, it means the workflow is done.
        """
        while True:
            msg = log_queue.get()
            if msg is None:
                break
            # Yield this log line + a newline so client sees separate lines
            yield msg + "\n"
            # Optional: slow down the stream a little if desired
            # time.sleep(0.5)

    # (G) Return the response as a chunked stream
    return Response(log_stream(), mimetype='text/plain')


if __name__ == "__main__":
    # Run the Flask app on port 8000 (or whichever you exposed in Docker)
    app.run(host="0.0.0.0", port=8000, debug=True)
