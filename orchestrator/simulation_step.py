"""
orchestrator/simulation_step.py

Simulation logic that can be reused for both regular and modified IDFs.
"""

import os
import pandas as pd
import logging
from typing import Dict, Any, Optional
import idf_creation


def run_simulations_on_modified_idfs(
    modified_results: dict,
    post_mod_cfg: dict,
    job_output_dir: str,
    idf_cfg: dict,
    user_config_epw: list,
    logger: logging.Logger
) -> bool:
    """
    Run simulations on modified IDF files.
    
    Args:
        modified_results: Results from modification step
        post_mod_cfg: Post-modification configuration
        job_output_dir: Job output directory
        idf_cfg: IDF configuration
        user_config_epw: EPW configuration
        logger: Logger instance
        
    Returns:
        True if simulations were successful, False otherwise
    """
    logger.info("[INFO] Running simulations on modified IDFs...")
    
    # Import simulation module
    from epw.run_epw_sims import simulate_all
    
    # Get simulation configuration
    sim_config = post_mod_cfg.get("simulation_config", {})
    num_workers = sim_config.get("num_workers", idf_cfg.get("simulate_config", {}).get("num_workers", 4))
    
    # Create output directory for modified simulations
    modified_sim_output = os.path.join(job_output_dir, "Modified_Sim_Results")
    os.makedirs(modified_sim_output, exist_ok=True)
    
    # Load original building data to get all necessary fields
    idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
    if not os.path.isfile(idf_map_csv):
        logger.error(f"[ERROR] Original IDF mapping not found: {idf_map_csv}")
        return False
        
    df_original = pd.read_csv(idf_map_csv)
    modified_building_data = modified_results.get("modified_building_data", [])
    modified_idfs_dir = modified_results.get("modified_idfs_dir")
    
    # Create DataFrame for modified buildings with all necessary fields
    modified_rows = []
    for mod_data in modified_building_data:
        # Find original building data
        orig_building = df_original[
            df_original['ogc_fid'].astype(str) == mod_data['original_building_id']
        ]
        
        if not orig_building.empty:
            # Copy original building data
            new_row = orig_building.iloc[0].to_dict()
            
            # Update with modified IDF info
            new_row['idf_name'] = os.path.relpath(
                mod_data['idf_path'], 
                modified_idfs_dir
            )
            new_row['variant_id'] = mod_data['variant_id']
            new_row['original_ogc_fid'] = mod_data['original_building_id']
            
            modified_rows.append(new_row)
        else:
            logger.warning(f"No original data found for building {mod_data['original_building_id']}")
    
    if not modified_rows:
        logger.error("[ERROR] No valid modified building data for simulation")
        return False
        
    df_modified = pd.DataFrame(modified_rows)
    
    # Run simulations
    try:
        simulate_all(
            df_buildings=df_modified,
            idf_directory=str(modified_idfs_dir),
            iddfile=idf_creation.idf_config["iddfile"],
            base_output_dir=modified_sim_output,
            user_config_epw=user_config_epw,
            assigned_epw_log={},  # Empty log for modified runs
            num_workers=num_workers
        )
        
        logger.info(f"[INFO] Completed simulations for {len(df_modified)} modified IDFs")
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Modified simulations failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False