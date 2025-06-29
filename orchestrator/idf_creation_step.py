"""
orchestrator/idf_creation_step.py

IDF creation logic (includes simulation as it's part of create_idfs_for_all_buildings).
"""

import os
import pandas as pd
import logging
from typing import Dict, Any, Optional

from database_handler import load_buildings_from_db
from idf_creation import create_idfs_for_all_buildings


def run_idf_creation(
    main_config: dict,
    idf_cfg: dict,
    job_output_dir: str,
    paths_dict: dict,
    updated_res_data: dict,
    updated_nonres_data: dict,
    user_config_geom: list,
    user_config_lighting: dict,
    user_config_dhw: dict,
    user_config_hvac: dict,
    user_config_vent: list,
    user_config_epw: list,
    logger: logging.Logger
) -> Optional[pd.DataFrame]:
    """
    Run IDF creation and optionally simulations.
    
    Returns:
        DataFrame of buildings with IDF information or None if skipped
    """
    if not idf_cfg.get("perform_idf_creation", False):
        logger.info("[INFO] Skipping IDF creation.")
        return None
        
    logger.info("[INFO] IDF creation is ENABLED.")
    
    # Extract IDF creation parameters
    scenario = idf_cfg.get("scenario", "scenario1")
    calibration_stage = idf_cfg.get("calibration_stage", "pre_calibration")
    strategy = idf_cfg.get("strategy", "B")
    random_seed = idf_cfg.get("random_seed", 42)
    run_simulations = idf_cfg.get("run_simulations", True)
    simulate_config = idf_cfg.get("simulate_config", {})
    post_process = idf_cfg.get("post_process", True)
    post_process_config = idf_cfg.get("post_process_config", {})
    output_definitions = idf_cfg.get("output_definitions", {})
    
    # Database settings
    use_database = main_config.get("use_database", False)
    db_filter = main_config.get("db_filter", {})
    filter_by = main_config.get("filter_by")

    # Load building data
    if use_database:
        logger.info("[INFO] Loading building data from DB.")
        if not filter_by:
            raise ValueError("[ERROR] 'filter_by' must be specified when 'use_database' is True.")
        df_buildings = load_buildings_from_db(db_filter, filter_by)

        # Save the raw DB buildings
        extracted_csv_path = os.path.join(job_output_dir, "extracted_buildings.csv")
        df_buildings.to_csv(extracted_csv_path, index=False)
        logger.info(f"[INFO] Saved extracted buildings to {extracted_csv_path}")

    else:
        bldg_data_path = paths_dict.get("building_data", "")
        if os.path.isfile(bldg_data_path):
            df_buildings = pd.read_csv(bldg_data_path)
        else:
            logger.warning(f"[WARN] building_data CSV not found => {bldg_data_path}")
            df_buildings = pd.DataFrame()

    logger.info(f"[INFO] Number of buildings to simulate: {len(df_buildings)}")

    # Create IDFs & run simulations
    df_buildings = create_idfs_for_all_buildings(
        df_buildings=df_buildings,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_geom=user_config_geom,
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

    # Store the mapping (ogc_fid -> idf_name)
    idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
    df_buildings.to_csv(idf_map_csv, index=False)
    logger.info(f"[INFO] Wrote building -> IDF map to {idf_map_csv}")
    
    return df_buildings