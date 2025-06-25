"""
orchestrator/main.py

Main orchestration logic that coordinates all workflow steps.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
# Add these imports at the top of main.py if not already present:

import math  # For power of 2 calculation in Sobol validation
from pathlib import Path  # For path operations

# The sensitivity analysis import should already be there:
from orchestrator.sensitivity_step import run_sensitivity_analysis
# Import all step modules
from .config_and_setup import (
    setup_job_environment,
    load_and_merge_config,
    apply_excel_overrides,
    apply_json_overrides,
    setup_idf_config
)
from .idf_creation_step import run_idf_creation
from .simulation_step import run_simulations_on_modified_idfs
from .parsing_step import run_parsing, run_parsing_modified_results
from .modification_step import run_modification
from .sensitivity_step import run_sensitivity_analysis
from .surrogate_step import run_surrogate_modeling
from .calibration_step import run_calibration
from .post_processing import run_post_processing, cleanup_old_results_safe
from .utils import WorkflowCanceled, check_canceled, step_timer
from .validation_step import run_validation, run_validation_stages  # Update this line

def orchestrate_workflow(job_config: dict, cancel_event: threading.Event = None):
    """
    Orchestrates the entire E+ workflow with enhanced validation configuration support.
    
    This is the main entry point called by job_manager.py
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Starting orchestrate_workflow ===")
    overall_start = time.perf_counter()

    # -------------------------------------------------------------------------
    # 0) Setup job environment and identify job_id
    # -------------------------------------------------------------------------
    job_id = job_config.get("job_id", "unknown_job_id")
    logger.info(f"[INFO] Orchestrator for job_id={job_id}")

    # Create check_canceled function for this job
    def check_canceled_func():
        check_canceled(cancel_event, logger)

    # -------------------------------------------------------------------------
    # 1) Setup job environment and folders
    # -------------------------------------------------------------------------
    job_output_dir, user_configs_folder = setup_job_environment(job_config, logger)
    if not job_output_dir:
        return

    # -------------------------------------------------------------------------
    # 2) Load and merge configuration
    # -------------------------------------------------------------------------
    main_config = load_and_merge_config(user_configs_folder, job_config, logger)
    if not main_config:
        return

    # -------------------------------------------------------------------------
    # 3) Extract sub-sections from main_config
    # -------------------------------------------------------------------------
    check_canceled_func()
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
    parsing_cfg      = main_config.get("parsing", {})
    idf_cfg          = main_config.get("idf_creation", {})

    # Log which steps will run
    steps_to_run = []
    if idf_cfg.get("perform_idf_creation", False):
        steps_to_run.append("IDF creation")
        if idf_cfg.get("run_simulations", True):
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
    # 4) Setup IDF configuration
    # -------------------------------------------------------------------------
    check_canceled_func()
    setup_idf_config(idf_cfg, job_output_dir, logger)

    # -------------------------------------------------------------------------
    # 5) Apply Excel overrides
    # -------------------------------------------------------------------------
    check_canceled_func()
    lookups = apply_excel_overrides(
        def_dicts, excel_flags, paths_dict, logger
    )
    dhw_lookup = lookups["dhw"]
    epw_lookup = lookups["epw"]
    lighting_lookup = lookups["lighting"]
    hvac_lookup = lookups["hvac"]
    vent_lookup = lookups["vent"]
    updated_res_data = lookups["res_data"]
    updated_nonres_data = lookups["nonres_data"]

    # -------------------------------------------------------------------------
    # 6) Apply JSON overrides
    # -------------------------------------------------------------------------
    check_canceled_func()
    json_overrides = apply_json_overrides(
        user_configs_folder, user_flags, 
        updated_res_data, updated_nonres_data, logger
    )
    
    # Update with JSON overrides
    updated_res_data = json_overrides["res_data"]
    updated_nonres_data = json_overrides["nonres_data"]
    user_config_dhw = json_overrides["dhw"]
    user_config_epw = json_overrides["epw"]
    user_config_lighting = json_overrides["lighting"]
    user_config_hvac = json_overrides["hvac"]
    user_config_vent = json_overrides["vent"]
    geom_data = json_overrides["geometry"]
    shading_data = json_overrides["shading"]

    # -------------------------------------------------------------------------
    # 7) IDF Creation
    # -------------------------------------------------------------------------
    check_canceled_func()
    df_buildings = None
    
    if idf_cfg.get("perform_idf_creation", False):
        with step_timer(logger, "IDF creation and simulations"):
            df_buildings = run_idf_creation(
                main_config=main_config,
                idf_cfg=idf_cfg,
                job_output_dir=job_output_dir,
                paths_dict=paths_dict,
                updated_res_data=updated_res_data,
                updated_nonres_data=updated_nonres_data,
                user_config_geom=geom_data.get("geometry", []),
                user_config_lighting=user_config_lighting,
                user_config_dhw=user_config_dhw,
                user_config_hvac=user_config_hvac,
                user_config_vent=user_config_vent,
                user_config_epw=user_config_epw,
                logger=logger
            )

    # -------------------------------------------------------------------------
    # 8) Parsing
    # -------------------------------------------------------------------------
    check_canceled_func()
    if parsing_cfg.get("perform_parsing", False):
        parse_after_simulation = parsing_cfg.get("parse_after_simulation", True)
        
        if parse_after_simulation and not idf_cfg.get("perform_idf_creation", False):
            logger.warning("[WARN] Parse after simulation requested but no IDF creation performed")
        
        with step_timer(logger, "parsing to parquet"):
            run_parsing(
                parsing_cfg=parsing_cfg,
                main_config=main_config,
                job_output_dir=job_output_dir,
                job_id=job_id,
                logger=logger
            )


    # -------------------------------------------------------------------------
    # 8a) Validation after initial parsing (if configured)
    # -------------------------------------------------------------------------
    check_canceled_func()
    if validation_cfg.get("perform_validation", False):
        # Check if we should run baseline validation after parsing
        validation_results_baseline = run_validation_stages(
            validation_cfg=validation_cfg,
            job_output_dir=job_output_dir,
            logger=logger,
            current_stage="parsing"
        )
        
        if validation_results_baseline:
            logger.info(f"[INFO] Completed {len(validation_results_baseline)} validation stage(s) after parsing")


    # -------------------------------------------------------------------------
    # 9) Modification
    # -------------------------------------------------------------------------
    check_canceled_func()
    if modification_cfg.get("perform_modification", False):
        with step_timer(logger, "IDF modification"):
            modified_results = run_modification(
                modification_cfg=modification_cfg,
                job_output_dir=job_output_dir,
                job_idf_dir=os.path.join(job_output_dir, "output_IDFs"),
                logger=logger
            )
            
            # Handle post-modification simulations and parsing
            if modified_results and modified_results.get("modified_building_data"):
                post_mod_cfg = modification_cfg.get("post_modification", {})
                
                # Run simulations on modified IDFs
                if post_mod_cfg.get("run_simulations", False):
                    with step_timer(logger, "post-modification simulations"):
                        sim_success = run_simulations_on_modified_idfs(
                            modified_results=modified_results,
                            post_mod_cfg=post_mod_cfg,
                            job_output_dir=job_output_dir,
                            idf_cfg=idf_cfg,
                            user_config_epw=user_config_epw,
                            logger=logger
                        )
                        
                        # Parse modified results if simulations were successful
                        if sim_success and post_mod_cfg.get("parse_results"):
                            with step_timer(logger, "parsing modified results"):
                                run_parsing_modified_results(
                                    parse_cfg=post_mod_cfg.get("parse_results", {}),
                                    job_output_dir=job_output_dir,
                                    modified_sim_output=os.path.join(job_output_dir, "Modified_Sim_Results"),
                                    modified_idfs_dir=modified_results["modified_idfs_dir"],
                                    idf_map_csv=os.path.join(job_output_dir, "extracted_idf_buildings.csv"),
                                    logger=logger
                                )
                            


                            # Validation after modification parsing
                            check_canceled_func()
                            validation_results_modified = run_validation_stages(
                                validation_cfg=validation_cfg,
                                job_output_dir=job_output_dir,
                                logger=logger,
                                current_stage="modification_parsing"
                            )
                            
                            if validation_results_modified:
                                logger.info(f"[INFO] Completed validation for modified results")
                        elif not sim_success:
                            logger.warning("[WARN] Skipping modified results parsing due to simulation failures")


    # -------------------------------------------------------------------------
    # 10) Validation
    # -------------------------------------------------------------------------
    check_canceled_func()
    if validation_cfg.get("perform_validation", False):
        with step_timer(logger, "validation"):
            # Check for old-style configuration (backward compatibility)
            if "config" in validation_cfg and "stages" not in validation_cfg:
                # Run default validation
                default_results = run_validation(
                    validation_cfg=validation_cfg,
                    job_output_dir=job_output_dir,
                    logger=logger,
                    stage_name="default"
                )
                
                if default_results:
                    logger.info("[INFO] Completed default validation")
            
            # Aggregate all validation results if multiple stages were run
            try:
                from .validation_aggregator import aggregate_validation_results
                
                combined_summary = aggregate_validation_results(
                    job_output_dir=job_output_dir,
                    logger=logger
                )
                
                if combined_summary:
                    logger.info("[INFO] Generated combined validation summary")
                    
                    # Log overall improvement metrics if available
                    if "improvement_metrics" in combined_summary:
                        metrics = combined_summary["improvement_metrics"]
                        logger.info("[INFO] Modification impact on validation:")
                        for var, improvement in metrics.items():
                            if improvement > 0:
                                logger.info(f"  - {var}: {improvement:.1f}% improvement")
                            else:
                                logger.info(f"  - {var}: {abs(improvement):.1f}% degradation")
                                
            except ImportError:
                logger.debug("Validation aggregator not available")
            except Exception as e:
                logger.error(f"[ERROR] Failed to aggregate validation results: {e}")


    # -------------------------------------------------------------------------
    # 11) Sensitivity Analysis (Updated with advanced features support)
    # -------------------------------------------------------------------------
    check_canceled_func()
    if sens_cfg.get("perform_sensitivity", False):
        with step_timer(logger, "enhanced sensitivity analysis"):
            # Log sensitivity configuration summary
            logger.info("[INFO] ========== SENSITIVITY ANALYSIS CONFIGURATION ==========")
            logger.info(f"[INFO] Analysis type: {sens_cfg.get('analysis_type', 'traditional')}")
            
            # Check for advanced analysis features
            advanced_cfg = sens_cfg.get("advanced_analysis", {})
            if advanced_cfg.get("enabled", False):
                logger.info("[INFO] Advanced analysis features ENABLED:")
                advanced_features = []
                if advanced_cfg.get("uncertainty_propagation", False):
                    advanced_features.append("Uncertainty Quantification")
                if advanced_cfg.get("threshold_analysis", False):
                    advanced_features.append("Threshold/Breakpoint Detection")
                if advanced_cfg.get("regional_sensitivity", False):
                    advanced_features.append("Regional Sensitivity Analysis")
                if advanced_cfg.get("sobol_analysis", False):
                    advanced_features.append("Sobol Variance Decomposition")
                if advanced_cfg.get("temporal_patterns", False):
                    advanced_features.append("Temporal Pattern Analysis")
                
                for feature in advanced_features:
                    logger.info(f"[INFO]   - {feature}")
                
                # Validate advanced configuration
                if advanced_cfg.get("sobol_analysis", False):
                    n_samples = advanced_cfg.get("sobol_samples", 0)
                    if n_samples > 0 and (n_samples & (n_samples - 1)) != 0:
                        logger.warning("[WARN] Sobol samples should be a power of 2 for optimal results")
                        # Suggest nearest power of 2
                        import math
                        suggested = 2 ** int(math.log2(n_samples) + 0.5)
                        logger.info(f"[INFO] Consider using sobol_samples = {suggested}")
                
                if advanced_cfg.get("uncertainty_propagation", False):
                    if advanced_cfg.get("uncertainty_samples", 0) < 100:
                        logger.warning("[WARN] Low uncertainty_samples may give unreliable confidence intervals")
            
            # Check if this is modification-based sensitivity
            if sens_cfg.get("analysis_type") == "modification_based":
                # Ensure we have modification results
                if not modification_cfg.get("perform_modification", False):
                    logger.warning("[WARN] Modification-based sensitivity requested but no modifications performed")
                    logger.info("[INFO] Switching to traditional sensitivity analysis")
                    sens_cfg["analysis_type"] = "traditional"
                else:
                    # Get categories_to_modify from modification config
                    categories_to_modify = modification_cfg.get("categories_to_modify", {})
                    
                    # Update sensitivity config with modification results info
                    if 'modified_results' in locals() and modified_results and modified_results.get("modified_idfs_dir"):
                        sens_cfg["modification_tracking_dir"] = modified_results["modified_idfs_dir"]
                    
                    # Check if we should use multi-level analysis
                    use_multi_level = sens_cfg.get("modification_analysis", {}).get("multi_level_analysis", True)
                    
                    if use_multi_level:
                        # Check for zone-level data
                        zone_data_path = Path(job_output_dir) / "parsed_data" / "sql_results" / "timeseries" / "aggregated" / "daily" / "zones_daily.parquet"
                        relationships_path = Path(job_output_dir) / "parsed_data" / "relationships"
                        
                        if not zone_data_path.exists():
                            logger.warning("[WARN] Zone-level data not found, falling back to building-level analysis")
                            sens_cfg["modification_analysis"]["multi_level_analysis"] = False
                        elif not relationships_path.exists():
                            logger.warning("[WARN] Zone/equipment relationships not found, falling back to building-level analysis")
                            sens_cfg["modification_analysis"]["multi_level_analysis"] = False
                        else:
                            logger.info("[INFO] Multi-level sensitivity analysis enabled with zone and equipment support")
                    
                    # Ensure we have parsed modified results
                    post_mod_cfg = modification_cfg.get("post_modification", {})
                    if not (post_mod_cfg.get("run_simulations", False) and 
                           post_mod_cfg.get("parse_results")):
                        logger.error("[ERROR] Modification-based sensitivity requires parsed modified results")
                        logger.info("[INFO] Please enable post_modification.run_simulations and parse_results")
                    else:
                        # Build parameter groups with new format
                        if "modification_analysis" not in sens_cfg:
                            sens_cfg["modification_analysis"] = {}
                        
                        # Create parameter patterns that match the new format
                        param_groups = {}
                        
                        # Map category names to object types
                        category_object_map = {
                            'hvac': ['ZONEHVAC:IDEALLOADSAIRSYSTEM', 'SIZING:ZONE'],
                            'lighting': ['LIGHTS'],
                            'materials': ['MATERIAL', 'MATERIAL:NOMASS', 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM'],
                            'infiltration': ['ZONEINFILTRATION:DESIGNFLOWRATE'],
                            'ventilation': ['DESIGNSPECIFICATION:OUTDOORAIR', 'ZONEVENTILATION:DESIGNFLOWRATE'],
                            'equipment': ['ELECTRICEQUIPMENT'],
                            'dhw': ['WATERHEATER:MIXED'],
                            'shading': ['WINDOWSHADINGCONTROL', 'WINDOWMATERIAL:BLIND'],
                            'geometry': ['ZONE', 'BUILDINGSURFACE:DETAILED'],
                            'schedules': ['SCHEDULE:CONSTANT', 'SCHEDULE:COMPACT'],
                            'simulation_control': ['TIMESTEP', 'SHADOWCALCULATION'],
                            'site_location': ['SITE:LOCATION', 'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE']
                        }
                        
                        for cat, cat_config in categories_to_modify.items():
                            if cat_config.get("enabled", False):
                                # Get the object types for this category
                                object_types = category_object_map.get(cat, [])
                                
                                if object_types:
                                    # Create parameter patterns for this category
                                    # Format: category*object_type*
                                    patterns = [f"{cat}*{obj_type}*" for obj_type in object_types]
                                    param_groups[cat] = patterns
                                    logger.debug(f"[DEBUG] Parameter patterns for {cat}: {patterns}")
                        
                        sens_cfg["modification_analysis"]["parameter_groups"] = param_groups
                        
                        # Add zone-level output variables if multi-level
                        if use_multi_level:
                            # Ensure we have zone-level outputs in the list
                            output_vars = sens_cfg.get("modification_analysis", {}).get("output_variables", [])
                            zone_vars = [
                                "Zone Air Temperature [C](Hourly)",
                                "Zone Air System Sensible Heating Energy [J](Hourly)",
                                "Zone Air System Sensible Cooling Energy [J](Hourly)"
                            ]
                            for var in zone_vars:
                                if var not in output_vars:
                                    output_vars.append(var)
                            sens_cfg["modification_analysis"]["output_variables"] = output_vars
                        
                        logger.info(f"[INFO] Using {len(param_groups)} parameter groups from modifications")
                        logger.info(f"[INFO] Total parameter patterns: {sum(len(patterns) for patterns in param_groups.values())}")
                        if use_multi_level:
                            logger.info("[INFO] Including zone-level analysis")
                        
                        # If advanced analysis is enabled with modification-based, add parameter info
                        if advanced_cfg.get("enabled", False):
                            # For uncertainty analysis, add parameter distribution info if not present
                            if advanced_cfg.get("uncertainty_propagation", False) and "parameter_distributions" not in advanced_cfg:
                                logger.info("[INFO] Auto-generating parameter distributions for uncertainty analysis")
                                param_dists = {}
                                
                                # Create distributions based on modification ranges
                                for cat, cat_config in categories_to_modify.items():
                                    if cat_config.get("enabled", False):
                                        # Get modification range
                                        mod_range = cat_config.get("modification_range", [-0.2, 0.2])
                                        mean_mod = sum(mod_range) / 2
                                        std_mod = abs(mod_range[1] - mod_range[0]) / 4  # ~95% within range
                                        
                                        # Apply to all parameters in this category
                                        for pattern in param_groups.get(cat, []):
                                            param_dists[pattern] = {
                                                "type": "normal",
                                                "mean": 1.0 + mean_mod,  # Relative to baseline
                                                "std": std_mod
                                            }
                                
                                advanced_cfg["parameter_distributions"] = param_dists
                                logger.info(f"[INFO] Generated distributions for {len(param_dists)} parameter patterns")
            
            # Check for time slicing configuration
            time_slicing_cfg = sens_cfg.get("time_slicing", {})
            if time_slicing_cfg.get("enabled", False):
                logger.info(f"[INFO] Time slicing enabled: {time_slicing_cfg.get('slice_type', 'custom')}")
                if time_slicing_cfg.get("compare_time_slices", False):
                    logger.info("[INFO] Comparative time slice analysis will be performed")
                
                # If temporal patterns analysis is enabled, ensure time column is set
                if advanced_cfg.get("temporal_patterns", False) and "time_column" not in advanced_cfg:
                    advanced_cfg["time_column"] = "DateTime"
                    logger.info("[INFO] Set time_column = 'DateTime' for temporal pattern analysis")
            
            # Log output configuration
            output_cfg = sens_cfg.get("output_options", {})
            logger.info("[INFO] Output options:")
            logger.info(f"[INFO]   - Save raw results: {output_cfg.get('save_raw_results', True)}")
            logger.info(f"[INFO]   - Generate report: {output_cfg.get('generate_report', True)}")
            logger.info(f"[INFO]   - Create visualizations: {output_cfg.get('create_visualizations', True)}")
            logger.info(f"[INFO]   - Export format: {output_cfg.get('export_format', 'parquet')}")
            
            # Check data availability for advanced features
            if advanced_cfg.get("enabled", False):
                parsed_data_path = Path(job_output_dir) / "parsed_data"
                
                # Check for sufficient data
                if advanced_cfg.get("sobol_analysis", False):
                    # Sobol needs many samples
                    logger.info("[INFO] Sobol analysis requires sufficient parameter variations")
                    logger.info("[INFO] Ensure you have run enough simulations for reliable results")
                
                if advanced_cfg.get("temporal_patterns", False):
                    # Temporal needs time series data
                    hourly_path = parsed_data_path / "sql_results" / "timeseries" / "aggregated" / "hourly"
                    if not hourly_path.exists():
                        logger.warning("[WARN] Hourly data not found - temporal patterns may be limited")
                        logger.info("[INFO] Consider using daily aggregation for temporal analysis")
            
            # Run sensitivity analysis (will route to appropriate method)
            logger.info("[INFO] Starting sensitivity analysis...")
            sensitivity_report = None
            
            try:
                sensitivity_report = run_sensitivity_analysis(
                    sens_cfg=sens_cfg,
                    job_output_dir=job_output_dir,
                    logger=logger
                )
                
                if sensitivity_report:
                    logger.info(f"[SUCCESS] Sensitivity analysis complete: {sensitivity_report}")
                    
                    # Log summary of results if available
                    sens_results_path = Path(sensitivity_report).parent
                    
                    # Check for advanced results
                    if advanced_cfg.get("enabled", False):
                        advanced_results_files = {
                            "uncertainty": "uncertainty_analysis_results.parquet",
                            "threshold": "threshold_analysis_results.parquet",
                            "regional": "regional_sensitivity_results.parquet",
                            "sobol": "sobol_analysis_results.parquet",
                            "temporal": "temporal_pattern_results.parquet"
                        }
                        
                        logger.info("[INFO] Advanced analysis results:")
                        for method, filename in advanced_results_files.items():
                            result_file = sens_results_path / filename
                            if result_file.exists():
                                file_size_mb = result_file.stat().st_size / (1024 * 1024)
                                logger.info(f"[INFO]   - {method}: {filename} ({file_size_mb:.2f} MB)")
                        
                        # Check for advanced report
                        adv_report = sens_results_path / "advanced_sensitivity_report.json"
                        if adv_report.exists():
                            logger.info(f"[INFO] Advanced analysis summary: {adv_report}")
                else:
                    logger.error("[ERROR] Sensitivity analysis failed - no report generated")
                    
            except Exception as e:
                logger.error(f"[ERROR] Sensitivity analysis failed: {str(e)}")
                logger.exception("Full traceback:")
                sensitivity_report = None
            
            logger.info("[INFO] ========== SENSITIVITY ANALYSIS COMPLETE ==========")
    # -------------------------------------------------------------------------
    # 12) Surrogate Modeling
    # -------------------------------------------------------------------------
    check_canceled_func()
    if sur_cfg.get("perform_surrogate", False):
        with step_timer(logger, "surrogate modeling"):
            run_surrogate_modeling(
                sur_cfg=sur_cfg,
                job_output_dir=job_output_dir,
                logger=logger
            )

    # -------------------------------------------------------------------------
    # 13) Calibration
    # -------------------------------------------------------------------------
    check_canceled_func()
    if cal_cfg.get("perform_calibration", False):
        with step_timer(logger, "calibration"):
            run_calibration(
                cal_cfg=cal_cfg,
                job_output_dir=job_output_dir,
                logger=logger
            )

    # -------------------------------------------------------------------------
    # 14) Post-processing (Zip & Email)
    # -------------------------------------------------------------------------
    with step_timer(logger, "zipping and email"):
        run_post_processing(
            user_configs_folder=user_configs_folder,
            job_output_dir=job_output_dir,
            logger=logger
        )

    # -------------------------------------------------------------------------
    # 15) Cleanup old results
    # -------------------------------------------------------------------------
    cleanup_old_results_safe(logger)

    total_time = time.perf_counter() - overall_start
    logger.info(f"=== End of orchestrate_workflow (took {total_time:.2f} seconds) ===")