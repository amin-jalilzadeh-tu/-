"""
Modification support for iteration workflow
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging


def run_modification_for_iteration(
    modification_cfg: dict,
    job_output_dir: str,
    selected_buildings: List[str],
    iteration: int,
    intensity: str,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Run modification for selected buildings in an iteration.
    
    Args:
        modification_cfg: Modification configuration
        job_output_dir: Job output directory
        selected_buildings: List of building IDs to modify
        iteration: Current iteration number
        intensity: Modification intensity level
        logger: Logger instance
        
    Returns:
        Dictionary with modification results
    """
    from ..modification_step import run_modification
    
    # Get iteration directory
    iter_dir = Path(job_output_dir) / "iterations" / f"iteration_{iteration}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup iteration-specific paths
    iter_idf_dir = iter_dir / "idfs"
    iter_mod_dir = iter_dir / "modifications"
    iter_idf_dir.mkdir(exist_ok=True)
    iter_mod_dir.mkdir(exist_ok=True)
    
    # Copy base IDFs for selected buildings
    base_idf_dir = Path(job_output_dir) / "output_IDFs"
    copied_count = 0
    
    for building_id in selected_buildings:
        # Find matching IDF file
        matching_files = list(base_idf_dir.glob(f"{building_id}_*.idf"))
        if matching_files:
            src_file = matching_files[0]
            dst_file = iter_idf_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            copied_count += 1
            logger.info(f"[MOD_ITER] Copied IDF for building {building_id}")
        else:
            logger.warning(f"[MOD_ITER] No IDF found for building {building_id}")
    
    if copied_count == 0:
        logger.error("[MOD_ITER] No IDFs copied for modification")
        return {"success": False, "error": "No IDFs found"}
    
    # Update modification config for iteration
    iter_mod_cfg = modification_cfg.copy()
    iter_mod_cfg["output_dir"] = str(iter_mod_dir)
    iter_mod_cfg["modification_intensity"] = intensity
    
    # Add iteration-specific parameters
    iter_mod_cfg["iteration"] = iteration
    iter_mod_cfg["selected_buildings"] = selected_buildings
    
    # Update strategy based on iteration
    if iteration == 1:
        iter_mod_cfg["strategy"] = "conservative"
    elif iteration == 2:
        iter_mod_cfg["strategy"] = "moderate"
    else:
        iter_mod_cfg["strategy"] = "aggressive"
    
    logger.info(f"[MOD_ITER] Running modification with intensity: {intensity}, strategy: {iter_mod_cfg['strategy']}")
    
    # Run modification
    mod_results = run_modification(
        modification_cfg=iter_mod_cfg,
        job_output_dir=str(iter_dir),
        job_idf_dir=str(iter_idf_dir),
        logger=logger
    )
    
    # Process results
    if mod_results and mod_results.get("modified_building_data"):
        # Copy modified IDFs back to iteration IDF directory
        mod_idf_dir = Path(mod_results["modified_idfs_dir"])
        for mod_idf in mod_idf_dir.glob("*.idf"):
            dst_file = iter_idf_dir / mod_idf.name
            shutil.copy2(mod_idf, dst_file)
        
        # Save iteration modification summary
        summary = {
            "iteration": iteration,
            "buildings_modified": len(mod_results["modified_building_data"]),
            "intensity": intensity,
            "strategy": iter_mod_cfg["strategy"],
            "modifications_applied": mod_results.get("total_modifications", 0)
        }
        
        summary_file = iter_mod_dir / f"iteration_{iteration}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"[MOD_ITER] Modified {summary['buildings_modified']} buildings with {summary['modifications_applied']} changes")
        
        return {
            "success": True,
            "summary": summary,
            "modified_idfs_dir": str(iter_idf_dir),
            "modified_building_data": mod_results["modified_building_data"]
        }
    else:
        logger.error("[MOD_ITER] Modification failed")
        return {"success": False, "error": "Modification failed"}