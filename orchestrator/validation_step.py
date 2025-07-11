"""
orchestrator/validation_step.py

Smart validation logic with multi-stage support.
"""

import os
import pandas as pd
import logging
from typing import Dict, Any, Optional

from validation.smart_validation_wrapper import run_smart_validation
from .utils import patch_if_relative
from .iteration.validation_support import extract_building_summary, save_iteration_validation_results


def run_validation(
    validation_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger,
    stage_name: str = "default",
    parsed_data_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Run smart validation process with stage support.
    
    Args:
        validation_cfg: Validation configuration
        job_output_dir: Job output directory
        logger: Logger instance
        stage_name: Name of validation stage (e.g., "baseline", "modified")
        parsed_data_path: Override path to parsed data (defaults to job_output_dir/parsed_data)
    
    Returns:
        Validation results dictionary or None if failed
    """
    logger.info(f"[INFO] Running smart validation - stage: {stage_name}")
    
    # Handle new staged configuration format
    if "stages" in validation_cfg and stage_name != "default":
        # Check if this stage exists and is enabled
        if stage_name not in validation_cfg["stages"]:
            logger.warning(f"[WARN] Validation stage '{stage_name}' not found in configuration")
            return None
            
        stage_config = validation_cfg["stages"][stage_name]
        if not stage_config.get("enabled", False):
            logger.info(f"[INFO] Validation stage '{stage_name}' is disabled")
            return None
            
        val_config = stage_config.get("config", {})
    else:
        # Use old format or default config
        val_config = validation_cfg.get("config", {})
    
    # Get real data path
    real_data_path = val_config.get("real_data_path", "measured_data.csv")
    if not os.path.isabs(real_data_path):
        real_data_path = patch_if_relative(real_data_path, job_output_dir)
    
    # Check if real data exists
    if not os.path.isfile(real_data_path):
        logger.error(f"[ERROR] Real data file not found: {real_data_path}")
        return None
    
    # Determine parsed data path
    if parsed_data_path is None:
        parsed_data_path = os.path.join(job_output_dir, "parsed_data")
    
    # Create stage-specific output directory
    output_path = os.path.join(job_output_dir, "validation_results", stage_name)
    
    # Import smart validation
    try:
        # Check if we should validate variants (for modified stage)
        validate_variants = stage_config.get('validate_variants', False) or stage_name == 'modified'
        
        # Run validation
        results = run_smart_validation(
            parsed_data_path=parsed_data_path,
            real_data_path=real_data_path,
            config=val_config,
            output_path=output_path,
            validate_variants=validate_variants
        )
        
        # Add stage information to results
        if results:
            results['stage'] = stage_name
        
        # Log results
        if results and 'summary' in results:
            summary = results['summary']
            if 'status' in summary:
                logger.warning(f"[WARN] Validation status: {summary['status']}")
            else:
                logger.info(f"[INFO] Validation complete for stage '{stage_name}':")
                
                # Check if this is variant validation
                if validate_variants and 'configurations_validated' in summary:
                    logger.info(f"  - Configurations validated: {summary.get('configurations_validated', 0)}")
                    logger.info(f"  - Best configuration: {summary.get('best_configuration', 'Unknown')}")
                    logger.info(f"  - Best pass rate: {summary.get('best_pass_rate', 0):.1f}%")
                    logger.info(f"  - Best CVRMSE: {summary.get('best_cvrmse', 0):.1f}%")
                    
                    if summary.get('improvements_found'):
                        logger.info(f"  - Found {len(summary['improvements_found'])} improved variants")
                else:
                    # Standard validation logging
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
                    summary_path = os.path.join(job_output_dir, f"validation_summary_{stage_name}.parquet")
                    val_df.to_parquet(summary_path, index=False)
                    logger.info(f"[INFO] Saved validation summary to: {summary_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"[ERROR] Smart validation failed for stage '{stage_name}': {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_validation_stages(
    validation_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger,
    current_stage: str
) -> Optional[Dict[str, Any]]:
    """
    Run validation stages based on current workflow position.
    
    Args:
        validation_cfg: Validation configuration
        job_output_dir: Job output directory
        logger: Logger instance
        current_stage: Current workflow stage (e.g., "parsing", "modification_parsing")
        
    Returns:
        Validation results or None
    """
    if not validation_cfg.get("perform_validation", False):
        return None
        
    # Check if using staged configuration
    if "stages" not in validation_cfg:
        # Old format - only run if current_stage is "default"
        if current_stage == "default":
            return run_validation(validation_cfg, job_output_dir, logger)
        return None
    
    # Find stages that should run after current_stage
    results = {}
    for stage_name, stage_config in validation_cfg["stages"].items():
        if stage_config.get("run_after") == current_stage and stage_config.get("enabled", False):
            logger.info(f"[INFO] Running validation stage '{stage_name}' after '{current_stage}'")
            
            # Determine parsed data path based on stage
            if current_stage == "modification_parsing":
                parsed_data_path = os.path.join(job_output_dir, "parsed_modified_results")
            else:
                parsed_data_path = os.path.join(job_output_dir, "parsed_data")
            
            stage_results = run_validation(
                validation_cfg, 
                job_output_dir, 
                logger,
                stage_name=stage_name,
                parsed_data_path=parsed_data_path
            )
            
            if stage_results:
                results[stage_name] = stage_results
    
    return results if results else None


def run_validation_for_iteration(
    validation_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger,
    iteration: int,
    parsed_data_path: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Run validation for iteration workflow and return building summary.
    
    Args:
        validation_cfg: Validation configuration
        job_output_dir: Job output directory
        logger: Logger instance
        iteration: Current iteration number
        parsed_data_path: Override path to parsed data
        
    Returns:
        DataFrame with building-level validation summary or None
    """
    from pathlib import Path
    
    logger.info(f"[INFO] Running validation for iteration {iteration}")
    
    # Determine parsed data path
    if parsed_data_path is None:
        if iteration == 0:
            parsed_data_path = os.path.join(job_output_dir, "parsed_data")
        else:
            parsed_data_path = os.path.join(job_output_dir, "iterations", f"iteration_{iteration}", "parsed_data")
    
    # Run validation
    stage_name = f"iteration_{iteration}"
    results = run_validation(
        validation_cfg=validation_cfg,
        job_output_dir=job_output_dir,
        logger=logger,
        stage_name=stage_name,
        parsed_data_path=parsed_data_path
    )
    
    if not results:
        logger.error(f"[ERROR] Validation failed for iteration {iteration}")
        return None
    
    # Extract building summary
    building_summary = extract_building_summary(results)
    
    if building_summary.empty:
        logger.error(f"[ERROR] No building summary extracted for iteration {iteration}")
        return None
    
    # Save iteration results
    iteration_dir = Path(job_output_dir) / "iterations" / f"iteration_{iteration}"
    iteration_dir.mkdir(parents=True, exist_ok=True)
    
    save_iteration_validation_results(
        validation_results=results,
        building_summary=building_summary,
        iteration_dir=iteration_dir,
        iteration=iteration
    )
    
    # Log summary statistics
    logger.info(f"[INFO] Validation summary for iteration {iteration}:")
    logger.info(f"  - Buildings validated: {len(building_summary)}")
    logger.info(f"  - Buildings passed: {len(building_summary[building_summary['validation_passed']])}")
    logger.info(f"  - Average CVRMSE: {building_summary['cvrmse'].mean():.2f}%")
    logger.info(f"  - Average NMBE: {building_summary['nmbe'].mean():.2f}%")
    
    return building_summary