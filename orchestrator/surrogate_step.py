"""
orchestrator/surrogate_step.py

Enhanced surrogate modeling logic with integrated data pipeline support.
Supports both new integrated approach and legacy scenario-based approach.
"""

import os
import logging
from typing import Optional, Any, Dict
from pathlib import Path

from .utils import patch_if_relative

logger = logging.getLogger(__name__)


def run_surrogate_modeling(
    sur_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger,
    main_config: dict = None
) -> Optional[Any]:
    """
    Run surrogate modeling with enhanced features and integrated pipeline support.
    
    Args:
        sur_cfg: Surrogate configuration from main config
        job_output_dir: Job output directory containing all results
        logger: Logger instance
        main_config: Full configuration (optional, for additional context)
    
    Returns:
        The trained surrogate model or None if failed
    """
    logger.info("[INFO] Surrogate Modeling is ENABLED.")
    
    # Determine which approach to use
    use_integrated_pipeline = sur_cfg.get("use_integrated_pipeline", True)
    
    # Check if we have the necessary data for integrated pipeline
    parsed_data_path = Path(job_output_dir) / "parsed_data"
    modified_results_path = Path(job_output_dir) / "parsed_modified_results"
    sensitivity_path = Path(job_output_dir) / "sensitivity_results"
    
    has_integrated_data = (
        parsed_data_path.exists() and 
        (modified_results_path.exists() or not sur_cfg.get("require_modifications", True))
    )
    
    if use_integrated_pipeline and has_integrated_data:
        logger.info("[INFO] Using integrated data pipeline for surrogate modeling")
        return run_integrated_surrogate(sur_cfg, job_output_dir, logger, main_config)
    else:
        logger.info("[INFO] Using legacy scenario-based approach for surrogate modeling")
        return run_legacy_surrogate(sur_cfg, job_output_dir, logger)


def run_integrated_surrogate(
    sur_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger,
    main_config: dict = None
) -> Optional[Any]:
    """
    Run surrogate modeling using the new integrated pipeline.
    """
    try:
        # Import integrated modules
        from c_surrogate.unified_surrogate import build_surrogate_from_job
        from c_surrogate.surrogate_pipeline_tracker import SurrogatePipelineTracker
        
        # Initialize tracker if enabled
        tracker = None
        if sur_cfg.get('tracking', {}).get('enabled', True):
            logger.info("[INFO] Initializing pipeline tracker")
            tracker = SurrogatePipelineTracker(job_output_dir)
            tracker.export_configuration(sur_cfg)
        
        # Prepare output directory for surrogate artifacts
        surrogate_output_dir = os.path.join(job_output_dir, "surrogate_models")
        os.makedirs(surrogate_output_dir, exist_ok=True)
        
        # Update configuration with any runtime adjustments
        sur_cfg_integrated = sur_cfg.copy()
        
        # Add data extraction configuration if not present
        if "data_extraction" not in sur_cfg_integrated:
            sur_cfg_integrated["data_extraction"] = {
                "temporal_resolution": sur_cfg.get("temporal_resolution", "daily"),
                "output_categories": sur_cfg.get("output_categories", ["zones", "hvac", "ventilation"])
            }
        
        # Add preprocessing configuration if not present
        if "preprocessing" not in sur_cfg_integrated:
            sur_cfg_integrated["preprocessing"] = {
                "aggregation_level": sur_cfg.get("aggregation_level", "building"),
                "use_sensitivity_filter": sur_cfg.get("use_sensitivity_filter", True),
                "sensitivity_threshold": sur_cfg.get("sensitivity_threshold", 0.1),
                "normalize_features": sur_cfg.get("scale_features", True),
                "create_interactions": sur_cfg.get("create_interactions", False)
            }
            
            # Ensure target variables are set
            if "target_variable" in sur_cfg:
                target_vars = sur_cfg["target_variable"]
                if isinstance(target_vars, str):
                    target_vars = [target_vars]
                sur_cfg_integrated["preprocessing"]["target_variables"] = target_vars
        
        # Add output management configuration if not present
        if "output_management" not in sur_cfg_integrated:
            sur_cfg_integrated["output_management"] = {
                "save_artifacts": True,
                "create_validation_reports": True,
                "generate_prediction_interface": True,
                "version": sur_cfg.get("model_version", "1.0")
            }
        
        # Add model paths
        # Add model paths - ensure they're absolute and directory exists
        if "model_out" not in sur_cfg_integrated:
            sur_cfg_integrated["model_out"] = os.path.join(
                surrogate_output_dir, 
                "surrogate_model.joblib"
            )
        elif not os.path.isabs(sur_cfg_integrated["model_out"]):
            # Make relative paths absolute
            sur_cfg_integrated["model_out"] = os.path.join(
                job_output_dir,
                sur_cfg_integrated["model_out"]
            )

        if "cols_out" not in sur_cfg_integrated:
            sur_cfg_integrated["cols_out"] = os.path.join(
                surrogate_output_dir,
                "surrogate_columns.joblib"
            )
        elif not os.path.isabs(sur_cfg_integrated["cols_out"]):
            # Make relative paths absolute
            sur_cfg_integrated["cols_out"] = os.path.join(
                job_output_dir,
                sur_cfg_integrated["cols_out"]
            )
            
            # Build surrogate using integrated pipeline
            # Build surrogate using integrated pipeline
            logger.info("[INFO] Building surrogate model with integrated pipeline...")
            result = build_surrogate_from_job(
                job_output_dir=job_output_dir,
                sur_cfg=sur_cfg_integrated,
                output_dir=surrogate_output_dir,
                tracker=tracker
            )
        
        if result:
            # Log success information
            logger.info("[SUCCESS] Surrogate model built successfully")
            logger.info(f"[INFO] Model type: {result['metadata'].get('model_type', 'unknown')}")
            logger.info(f"[INFO] Features: {result['preprocessing_summary']['n_features']}")
            logger.info(f"[INFO] Samples: {result['preprocessing_summary']['n_samples']}")
            logger.info(f"[INFO] Targets: {len(result['metadata'].get('target_columns', []))}")
            
            # Log validation results if available
            if result.get('validation_results'):
                val_metrics = result['validation_results'].get('target_metrics', {})
                for target, metrics in val_metrics.items():
                    logger.info(f"[INFO] {target} - R²: {metrics['r2']:.3f}, RMSE: {metrics['rmse']:.2e}")
            
            # Save summary report
            save_surrogate_summary(result, surrogate_output_dir, logger)
            
            # Finalize tracking
            if tracker:
                # Track final outputs
                if result.get('output_manager'):
                    output_manager = result['output_manager']
                    if hasattr(output_manager, 'tracker'):
                        output_manager.tracker = tracker
                
                # Create final pipeline summary
                tracker.create_pipeline_summary()
                logger.info(f"[INFO] Pipeline tracking report saved to: {tracker.export_dir}")
            
            # Return model for compatibility
            return result['model']
        else:
            logger.warning("[WARN] Integrated surrogate modeling returned no result")
            return None
            
    except ImportError as e:
        logger.error(f"[ERROR] Failed to import integrated surrogate modules: {e}")
        logger.info("[INFO] Falling back to legacy approach")
        return run_legacy_surrogate(sur_cfg, job_output_dir, logger)
        
    except Exception as e:
        logger.error(f"[ERROR] Integrated surrogate modeling failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try legacy approach as fallback
        logger.info("[INFO] Attempting legacy approach as fallback")
        return run_legacy_surrogate(sur_cfg, job_output_dir, logger)


def run_legacy_surrogate(
    sur_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger
) -> Optional[Any]:
    """
    Run surrogate modeling using the legacy scenario-based approach.
    """
    try:
        from c_surrogate.unified_surrogate import (
            load_scenario_params as sur_load_scenario_params,
            pivot_scenario_params,
            load_sim_results,
            aggregate_results,
            merge_params_with_results,
            build_and_save_surrogate
        )
        
        # Patch all paths
        scenario_folder = sur_cfg.get("scenario_folder", "")
        sur_cfg["scenario_folder"] = patch_if_relative(scenario_folder, job_output_dir)

        results_csv = sur_cfg.get("results_csv", "")
        sur_cfg["results_csv"] = patch_if_relative(results_csv, job_output_dir)

        model_out = sur_cfg.get("model_out", "")
        sur_cfg["model_out"] = patch_if_relative(model_out, job_output_dir)

        cols_out = sur_cfg.get("cols_out", "")
        sur_cfg["cols_out"] = patch_if_relative(cols_out, job_output_dir)

        # Get configuration parameters
        target_var = sur_cfg["target_variable"]
        test_size = sur_cfg.get("test_size", 0.3)
        
        # Enhanced parameters
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
        
        # AutoML parameters
        use_automl = sur_cfg.get("use_automl", False)
        automl_framework = sur_cfg.get("automl_framework")
        automl_time_limit = sur_cfg.get("automl_time_limit", 300)
        automl_config = sur_cfg.get("automl_config", {})
        
        # Patch sensitivity path if relative
        if sensitivity_path:
            sensitivity_path = patch_if_relative(sensitivity_path, job_output_dir)

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
            return rf_model
        else:
            logger.warning("[WARN] Surrogate modeling failed or insufficient data.")
            return None
            
    except Exception as e:
        logger.error(f"[ERROR] Legacy surrogate modeling failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_surrogate_summary(result: Dict[str, Any], output_dir: str, logger: logging.Logger):
    """
    Save a summary report of the surrogate modeling results.
    """
    try:
        import json
        from datetime import datetime
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "model_type": result['metadata'].get('model_type', 'unknown'),
            "preprocessing": result['preprocessing_summary'],
            "data_extraction": result['extraction_summary'],
            "features": {
                "count": result['metadata'].get('n_features', 0),
                "names": result['metadata'].get('feature_columns', [])[:20]  # First 20
            },
            "targets": result['metadata'].get('target_columns', []),
            "validation": {}
        }
        
        # Add validation results if available
        if result.get('validation_results'):
            val_results = result['validation_results']
            summary['validation'] = {
                "overall_metrics": val_results.get('overall_metrics', {}),
                "target_metrics": val_results.get('target_metrics', {})
            }
        
        # Save summary
        summary_path = os.path.join(output_dir, "surrogate_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"[INFO] Saved surrogate summary to {summary_path}")
        
        # Also create a simple text report
        report_lines = [
            "SURROGATE MODEL SUMMARY",
            "=" * 50,
            f"Created: {summary['timestamp']}",
            f"Model Type: {summary['model_type']}",
            "",
            "DATA SUMMARY:",
            f"- Total Samples: {summary['preprocessing']['n_samples']}",
            f"- Features: {summary['preprocessing']['n_features']}",
            f"- Targets: {len(summary['targets'])}",
            "",
            "TARGET VARIABLES:",
        ]
        
        for target in summary['targets']:
            report_lines.append(f"- {target}")
        
        if summary['validation']:
            report_lines.extend([
                "",
                "VALIDATION RESULTS:",
            ])
            
            overall = summary['validation'].get('overall_metrics', {})
            if overall:
                report_lines.append(f"- Overall R²: {overall.get('mean_r2', 0):.3f}")
                report_lines.append(f"- Overall RMSE: {overall.get('mean_rmse', 0):.2e}")
            
            target_metrics = summary['validation'].get('target_metrics', {})
            for target, metrics in target_metrics.items():
                report_lines.append(f"\n{target}:")
                report_lines.append(f"  - R²: {metrics.get('r2', 0):.3f}")
                report_lines.append(f"  - RMSE: {metrics.get('rmse', 0):.2e}")
                report_lines.append(f"  - MAE: {metrics.get('mae', 0):.2e}")
        
        report_path = os.path.join(output_dir, "surrogate_report.txt")
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"[INFO] Saved surrogate report to {report_path}")
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to save surrogate summary: {e}")


def check_surrogate_prerequisites(
    job_output_dir: str,
    sur_cfg: dict,
    logger: logging.Logger
) -> tuple[bool, str]:
    """Check if all prerequisites for surrogate modeling are met."""
    issues = []
    warnings = []
    
    # Check for integrated pipeline data
    if sur_cfg.get("use_integrated_pipeline", True):
        parsed_data_path = Path(job_output_dir) / "parsed_data"
        if not parsed_data_path.exists():
            issues.append("No parsed data found")
        
        # Check for sensitivity results if filtering is enabled
        if sur_cfg.get("preprocessing", {}).get("use_sensitivity_filter", True):
            sensitivity_path = Path(job_output_dir) / "sensitivity_results"
            if not sensitivity_path.exists():
                warnings.append("No sensitivity results found - will skip feature filtering")
                # Automatically disable sensitivity filtering
                sur_cfg.setdefault("preprocessing", {})["use_sensitivity_filter"] = False
        
        # Check for modifications if required
        if sur_cfg.get("require_modifications", True):
            modified_path = Path(job_output_dir) / "parsed_modified_results"
            if not modified_path.exists():
                issues.append("No modified results found")
    
    # Check for legacy approach data
    else:
        scenario_folder = sur_cfg.get("scenario_folder", "")
        scenario_path = Path(patch_if_relative(scenario_folder, job_output_dir))
        if not scenario_path.exists():
            issues.append(f"Scenario folder not found: {scenario_path}")
        
        results_csv = sur_cfg.get("results_csv", "")
        results_path = Path(patch_if_relative(results_csv, job_output_dir))
        if not results_path.exists():
            issues.append(f"Results CSV not found: {results_path}")
    
    if issues:
        return False, "Prerequisites not met: " + "; ".join(issues)
    else:
        return True, "All prerequisites met"