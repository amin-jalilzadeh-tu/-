"""
orchestrator/calibration_step.py

Enhanced calibration logic with multi-objective optimization.
"""

import os
import logging
from typing import Dict, Any

from cal.unified_calibration import run_unified_calibration
from .utils import patch_if_relative


def run_calibration(
    cal_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger
) -> None:
    """
    Run calibration with enhanced features.
    """
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

    # Patch all paths in configuration
    patch_calibration_paths(cal_cfg, job_output_dir)

    try:
        # Run the enhanced unified calibration
        run_unified_calibration(cal_cfg)
        
        # Log completion with enhanced info
        best_params_folder = cal_cfg.get("best_params_folder", "")
        if os.path.exists(os.path.join(best_params_folder, "calibration_metadata.json")):
            logger.info("[INFO] Enhanced calibration completed with metadata saved")
        if os.path.exists(os.path.join(best_params_folder, "convergence_data.json")):
            logger.info("[INFO] Convergence data saved for analysis")
        if has_multi_config:
            summary_path = os.path.join(best_params_folder, "calibration_summary.json")
            if os.path.exists(summary_path):
                logger.info("[INFO] Multi-configuration summary saved")
                
    except Exception as e:
        logger.error(f"[ERROR] Calibration failed: {e}")
        import traceback
        traceback.print_exc()


def patch_calibration_paths(cal_cfg: dict, job_output_dir: str) -> None:
    """
    Patch all paths in calibration configuration.
    """
    # Standard paths
    path_keys = [
        "scenario_folder", "real_data_csv", "surrogate_model_path",
        "surrogate_columns_path", "output_history_csv", "best_params_folder",
        "sensitivity_results_path", "subset_sensitivity_csv", "history_folder"
    ]
    
    for key in path_keys:
        if key in cal_cfg and cal_cfg[key]:
            cal_cfg[key] = patch_if_relative(cal_cfg[key], job_output_dir)
    
    # Handle multiple calibration configurations
    if "calibration_configs" in cal_cfg:
        for config in cal_cfg["calibration_configs"]:
            # Each config might have its own paths
            config_path_keys = [
                "real_data_csv", "output_csv", "surrogate_model_path", 
                "surrogate_columns_path"
            ]
            for key in config_path_keys:
                if key in config and config[key]:
                    config[key] = patch_if_relative(config[key], job_output_dir)
    
    # Handle file patterns - these might have full paths
    if "file_patterns" in cal_cfg:
        file_patterns = cal_cfg["file_patterns"]
        if file_patterns:
            patched_patterns = []
            for pattern in file_patterns:
                # Only patch if it looks like a path (contains /)
                if "/" in pattern:
                    patched_patterns.append(patch_if_relative(pattern, job_output_dir))
                else:
                    # It's just a pattern like "*.csv", leave as is
                    patched_patterns.append(pattern)
            cal_cfg["file_patterns"] = patched_patterns