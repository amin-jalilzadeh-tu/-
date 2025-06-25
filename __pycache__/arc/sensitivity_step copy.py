"""
orchestrator/sensitivity_step.py

Enhanced sensitivity analysis step with consolidated modules.
"""

import os
import json
import logging
import warnings
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import pandas at module level
try:
    import pandas as pd
    HAVE_PANDAS = True
except ImportError:
    pd = None
    HAVE_PANDAS = False
    warnings.warn("pandas not available - some export functions may not work")

# Import sensitivity modules
from c_sensitivity.sensitivity_manager import SensitivityManager
from c_sensitivity.data_manager import SensitivityDataManager
from c_sensitivity.reporter import SensitivityReporter

# Import utility functions
from .utils import patch_if_relative, WorkflowCanceled, check_canceled, step_timer


def run_sensitivity_analysis(
    sens_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger
) -> Optional[str]:
    """
    Run sensitivity analysis using the consolidated framework
    
    Args:
        sens_cfg: Sensitivity configuration from combined.json
        job_output_dir: Job output directory path
        logger: Logger instance
        
    Returns:
        Path to the sensitivity report or None if failed
    """
    logger.info("[INFO] Starting Sensitivity Analysis...")
    
    # Convert to Path object
    job_output_dir = Path(job_output_dir)
    
    # Initialize sensitivity manager
    sensitivity_manager = SensitivityManager(job_output_dir, logger)
    
    # Patch relative paths in config
    if "output_base_dir" in sens_cfg:
        sens_cfg["output_base_dir"] = patch_if_relative(sens_cfg["output_base_dir"], job_output_dir)
    
    if "scenario_folder" in sens_cfg:
        sens_cfg["scenario_folder"] = patch_if_relative(sens_cfg["scenario_folder"], job_output_dir)
    
    if "results_csv" in sens_cfg:
        sens_cfg["results_csv"] = patch_if_relative(sens_cfg["results_csv"], job_output_dir)
    
    if "sensitivity_results_path" in sens_cfg:
        sens_cfg["sensitivity_results_path"] = patch_if_relative(sens_cfg["sensitivity_results_path"], job_output_dir)
    
    try:
        # Log configuration details
        analysis_type = sens_cfg.get("analysis_type", "traditional")
        logger.info(f"[INFO] Analysis type: {analysis_type}")
        
        # Check prerequisites based on analysis type
        if analysis_type == "modification_based":
            if not _check_modification_prerequisites(job_output_dir, logger):
                return None
        
        # Run analysis based on configuration
        report_path = sensitivity_manager.run_analysis(sens_cfg)
        
        if report_path:
            logger.info(f"[SUCCESS] Sensitivity analysis complete. Report saved to: {report_path}")
            
            # Generate additional outputs if needed
            output_dir = Path(sens_cfg.get("output_base_dir", job_output_dir / "sensitivity_results"))
            
            # Check if we need to generate specific file formats for downstream tools
            if sens_cfg.get("export_for_surrogate", False):
                generate_surrogate_export(sensitivity_manager, output_dir, sens_cfg, logger)
            
            if sens_cfg.get("export_for_calibration", False):
                generate_calibration_export(sensitivity_manager, output_dir, sens_cfg, logger)
            
            # Generate enhanced sensitivity CSV for backward compatibility
            if sens_cfg.get("sensitivity_results_path"):
                generate_legacy_csv(sensitivity_manager, sens_cfg["sensitivity_results_path"], logger)
            
            # Generate summary statistics
            generate_summary_statistics(sensitivity_manager, output_dir, logger)
            
            # Create visualization report if requested
            if sens_cfg.get("generate_visualizations", False) and sens_cfg.get("report_formats", []):
                if "html" in sens_cfg["report_formats"]:
                    generate_html_report(sensitivity_manager, output_dir, logger)
            
        else:
            logger.error("[ERROR] Sensitivity analysis failed - no report generated")
            
        return report_path
        
    except WorkflowCanceled:
        logger.info("[INFO] Sensitivity analysis canceled by user")
        raise
    except Exception as e:
        logger.error(f"[ERROR] Sensitivity analysis failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _check_modification_prerequisites(job_output_dir: Path, logger: logging.Logger) -> bool:
    """Check if required files exist for modification-based analysis"""
    
    # Check for modification tracking
    mod_dir = job_output_dir / "modified_idfs"
    if not mod_dir.exists():
        logger.error("[ERROR] No modification directory found. Please run modification step first.")
        return False
    
    mod_files = list(mod_dir.glob("modifications_detail_*.parquet"))
    if not mod_files:
        logger.error("[ERROR] No modification tracking files found. Please run modification step first.")
        return False
    
    # Check for parsed modified results
    parsed_mod_dir = job_output_dir / "parsed_modified_results"
    if not parsed_mod_dir.exists():
        logger.error("[ERROR] No parsed modified results found. Please parse modified simulation results first.")
        return False
    
    # Check for base parsed results
    parsed_base_dir = job_output_dir / "parsed_data"
    if not parsed_base_dir.exists():
        logger.error("[ERROR] No parsed base results found. Please parse base simulation results first.")
        return False
    
    logger.info("[INFO] All prerequisites for modification-based analysis found")
    return True


def generate_surrogate_export(
    manager: SensitivityManager,
    output_dir: Path,
    config: Dict[str, Any],
    logger: logging.Logger
) -> None:
    """
    Generate export files specifically formatted for surrogate modeling
    """
    logger.info("[INFO] Generating surrogate modeling export...")
    
    if not HAVE_PANDAS:
        logger.warning("[WARN] pandas not available - skipping surrogate export")
        return
    
    # Check if we have results to export
    if not manager.results:
        logger.warning("[WARN] No sensitivity results available for surrogate export")
        return
    
    # Create a CSV file with top parameters for easy loading in surrogate step
    top_n = config.get("export_top_n_parameters", 30)
    
    all_params = []
    for analysis_type, results in manager.results.items():
        if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
            # Get top parameters
            top_params = results.nlargest(top_n, 'sensitivity_score').copy()
            top_params['analysis_method'] = analysis_type
            
            # Select relevant columns
            cols_to_keep = ['parameter', 'sensitivity_score', 'analysis_method']
            if 'category' in top_params.columns:
                cols_to_keep.append('category')
            if 'p_value' in top_params.columns:
                cols_to_keep.append('p_value')
            
            all_params.append(top_params[cols_to_keep])
    
    if all_params:
        combined_params = pd.concat(all_params, ignore_index=True)
        
        # Remove duplicates, keeping highest score
        combined_params = combined_params.sort_values('sensitivity_score', ascending=False)
        combined_params = combined_params.drop_duplicates(subset=['parameter'], keep='first')
        
        # Save as CSV for easy loading
        csv_path = output_dir / 'top_sensitive_parameters.csv'
        combined_params.to_csv(csv_path, index=False)
        logger.info(f"[INFO] Saved {len(combined_params)} parameters to {csv_path}")
        
        # Also save as JSON with metadata
        json_export = {
            'parameters': combined_params['parameter'].tolist(),
            'details': combined_params.to_dict('records'),
            'selection_method': 'sensitivity_analysis',
            'top_n_per_method': top_n,
            'total_selected': len(combined_params),
            'analysis_types': list(manager.results.keys())
        }
        
        json_path = output_dir / 'sensitive_parameters_for_surrogate.json'
        with open(json_path, 'w') as f:
            json.dump(json_export, f, indent=2)
        logger.info(f"[INFO] Saved parameter details to {json_path}")


def generate_calibration_export(
    manager: SensitivityManager,
    output_dir: Path,
    config: Dict[str, Any],
    logger: logging.Logger
) -> None:
    """
    Generate export files specifically formatted for calibration
    """
    logger.info("[INFO] Generating calibration export...")
    
    if not HAVE_PANDAS:
        logger.warning("[WARN] pandas not available - skipping calibration export")
        return
    
    # Similar to surrogate but with calibration-specific formatting
    if not manager.results:
        logger.warning("[WARN] No sensitivity results available for calibration export")
        return
    
    top_n = config.get("export_top_n_parameters", 15)
    
    calibration_params = []
    
    for analysis_type, results in manager.results.items():
        if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
            # Get top parameters
            top_params = results.nlargest(top_n, 'sensitivity_score')
            
            # For modification-based results, we might have actual parameter ranges
            for _, row in top_params.iterrows():
                param_info = {
                    'parameter': row['parameter'],
                    'sensitivity_score': float(row['sensitivity_score']),
                    'analysis_method': analysis_type,
                    'category': row.get('category', 'unknown'),
                    'output_variable': row.get('output_variable', 'unknown')
                }
                
                # Add statistical information if available
                if 'p_value' in row:
                    param_info['p_value'] = float(row['p_value'])
                    param_info['significant'] = row['p_value'] < 0.05
                
                if 'ci_lower' in row and 'ci_upper' in row:
                    param_info['confidence_interval'] = [float(row['ci_lower']), float(row['ci_upper'])]
                
                # For calibration, suggest range multiplier based on sensitivity
                param_info['suggested_range_multiplier'] = 1.0 + float(row['sensitivity_score'])
                
                calibration_params.append(param_info)
    
    if calibration_params:
        # Remove duplicates, keeping highest sensitivity score
        param_dict = {}
        for param in calibration_params:
            key = param['parameter']
            if key not in param_dict or param['sensitivity_score'] > param_dict[key]['sensitivity_score']:
                param_dict[key] = param
        
        # Create DataFrame for CSV export
        calib_df = pd.DataFrame(list(param_dict.values()))
        csv_path = output_dir / 'calibration_parameters.csv'
        calib_df.to_csv(csv_path, index=False)
        logger.info(f"[INFO] Saved {len(calib_df)} calibration parameters to {csv_path}")
        
        # Also save detailed JSON
        calibration_export = {
            'parameters': list(param_dict.values()),
            'selection_criteria': 'top_sensitivity',
            'calibration_recommendations': {
                'high_sensitivity': [p['parameter'] for p in param_dict.values() if p['sensitivity_score'] > 0.7],
                'medium_sensitivity': [p['parameter'] for p in param_dict.values() if 0.3 < p['sensitivity_score'] <= 0.7],
                'low_sensitivity': [p['parameter'] for p in param_dict.values() if p['sensitivity_score'] <= 0.3]
            }
        }
        
        json_path = output_dir / 'calibration_parameters.json'
        with open(json_path, 'w') as f:
            json.dump(calibration_export, f, indent=2)
        logger.info(f"[INFO] Saved calibration details to {json_path}")


def generate_legacy_csv(
    manager: SensitivityManager,
    csv_path: str,
    logger: logging.Logger
) -> None:
    """
    Generate legacy enhanced_sensitivity.csv for backward compatibility
    """
    if not HAVE_PANDAS or not manager.results:
        return
    
    logger.info(f"[INFO] Generating legacy sensitivity CSV: {csv_path}")
    
    # Combine all results
    all_results = []
    
    for analysis_type, results in manager.results.items():
        if isinstance(results, pd.DataFrame):
            df_copy = results.copy()
            df_copy['analysis_type'] = analysis_type
            all_results.append(df_copy)
    
    if all_results:
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Ensure required columns exist for legacy format
        if 'parameter' not in combined_df.columns and 'param_key' in combined_df.columns:
            combined_df['parameter'] = combined_df['param_key']
        
        # Save to CSV
        combined_df.to_csv(csv_path, index=False)
        logger.info(f"[INFO] Saved legacy sensitivity CSV with {len(combined_df)} rows")


def generate_summary_statistics(
    manager: SensitivityManager,
    output_dir: Path,
    logger: logging.Logger
) -> None:
    """
    Generate summary statistics file for quick reference
    """
    logger.info("[INFO] Generating summary statistics...")
    
    summary = {
        'analysis_completed': True,
        'methods_used': list(manager.results.keys()),
        'total_parameters_analyzed': 0,
        'total_outputs_analyzed': 0,
        'top_5_parameters': [],
        'statistics_by_method': {}
    }
    
    # Aggregate statistics
    all_params = set()
    all_outputs = set()
    
    for analysis_type, results in manager.results.items():
        if isinstance(results, pd.DataFrame):
            method_stats = {
                'n_results': len(results),
                'n_parameters': 0,
                'n_outputs': 0
            }
            
            if 'parameter' in results.columns:
                params = results['parameter'].unique()
                all_params.update(params)
                method_stats['n_parameters'] = len(params)
            
            if 'output_variable' in results.columns:
                outputs = results['output_variable'].unique()
                all_outputs.update(outputs)
                method_stats['n_outputs'] = len(outputs)
            
            if 'sensitivity_score' in results.columns:
                method_stats['score_range'] = [
                    float(results['sensitivity_score'].min()),
                    float(results['sensitivity_score'].max())
                ]
                method_stats['score_mean'] = float(results['sensitivity_score'].mean())
                method_stats['score_std'] = float(results['sensitivity_score'].std())
            
            summary['statistics_by_method'][analysis_type] = method_stats
    
    summary['total_parameters_analyzed'] = len(all_params)
    summary['total_outputs_analyzed'] = len(all_outputs)
    
    # Get consensus top parameters if multiple methods were used
    if len(manager.results) > 1 and hasattr(manager, '_combine_analysis_results'):
        combined = manager._combine_analysis_results()
        if combined is not None and 'consensus_score' in combined.columns:
            top_5 = combined.nlargest(5, 'consensus_score')[['parameter', 'consensus_score']]
            summary['top_5_parameters'] = [
                {'parameter': row['parameter'], 'score': float(row['consensus_score'])}
                for _, row in top_5.iterrows()
            ]
    elif len(manager.results) == 1:
        # Single method - just get top from that method
        for _, results in manager.results.items():
            if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                top_5 = results.nlargest(5, 'sensitivity_score')[['parameter', 'sensitivity_score']]
                summary['top_5_parameters'] = [
                    {'parameter': row['parameter'], 'score': float(row['sensitivity_score'])}
                    for _, row in top_5.iterrows()
                ]
                break
    
    # Add parameter categories if available
    if HAVE_PANDAS and manager.results:
        categories_found = set()
        for _, results in manager.results.items():
            if isinstance(results, pd.DataFrame) and 'category' in results.columns:
                categories_found.update(results['category'].unique())
        summary['parameter_categories'] = list(categories_found)
    
    # Save summary
    summary_path = output_dir / 'sensitivity_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"[INFO] Saved summary statistics to {summary_path}")


def generate_html_report(
    manager: SensitivityManager,
    output_dir: Path,
    logger: logging.Logger
) -> None:
    """
    Generate comprehensive HTML report
    """
    logger.info("[INFO] Generating HTML report...")
    
    try:
        reporter = SensitivityReporter(logger)
        
        # Prepare results dictionary
        results = {
            'metadata': {
                'job_output_dir': str(manager.job_output_dir),
                'analysis_types': list(manager.results.keys()),
                'n_parameters': sum(
                    len(df['parameter'].unique()) if 'parameter' in df.columns else 0
                    for df in manager.results.values()
                    if isinstance(df, pd.DataFrame)
                ),
                'n_outputs': sum(
                    len(df['output_variable'].unique()) if 'output_variable' in df.columns else 0
                    for df in manager.results.values()
                    if isinstance(df, pd.DataFrame)
                )
            },
            'summary': {}
        }
        
        # Add method-specific results
        for method, df in manager.results.items():
            if isinstance(df, pd.DataFrame):
                results[method] = df
                
                # Add to summary
                if 'sensitivity_score' in df.columns:
                    top_params = df.nlargest(10, 'sensitivity_score')[
                        ['parameter', 'sensitivity_score']
                    ].to_dict('records')
                    
                    results['summary'][f'top_parameters_{method}'] = [
                        {
                            'parameter': p['parameter'],
                            'avg_sensitivity_score': float(p['sensitivity_score'])
                        }
                        for p in top_params
                    ]
        
        # Generate HTML report
        html_path = output_dir / 'sensitivity_report.html'
        reporter.generate_html_report(results, html_path, include_plots=True)
        
        logger.info(f"[INFO] Generated HTML report: {html_path}")
        
    except Exception as e:
        logger.warning(f"[WARN] Failed to generate HTML report: {e}")


# Keep backward compatibility functions for smooth transition
def run_multi_level_sensitivity_analysis(
    sens_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger
) -> Optional[str]:
    """Backward compatibility wrapper"""
    logger.info("[INFO] Redirecting to consolidated sensitivity analysis...")
    return run_sensitivity_analysis(sens_cfg, job_output_dir, logger)


def run_modification_sensitivity_analysis(
    sens_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger
) -> Optional[str]:
    """Backward compatibility wrapper"""
    logger.info("[INFO] Redirecting to consolidated sensitivity analysis...")
    return run_sensitivity_analysis(sens_cfg, job_output_dir, logger)


def run_traditional_sensitivity_analysis(
    sens_cfg: dict,
    job_output_dir: str,
    logger: logging.Logger
) -> Optional[str]:
    """Backward compatibility wrapper"""
    logger.info("[INFO] Redirecting to consolidated sensitivity analysis...")
    return run_sensitivity_analysis(sens_cfg, job_output_dir, logger)


# Legacy support functions
def generate_modification_visualizations(
    sensitivity_results: pd.DataFrame,
    group_analysis: pd.DataFrame,
    output_dir: Path,
    logger: logging.Logger
) -> None:
    """Legacy function for backward compatibility"""
    logger.info("[INFO] Using new visualization system...")
    reporter = SensitivityReporter(logger)
    
    viz_dir = output_dir / "visualizations"
    viz_dir.mkdir(exist_ok=True)
    
    # Generate visualizations using new reporter
    if 'level' in sensitivity_results.columns:
        reporter.create_level_comparison_plot(sensitivity_results, str(viz_dir / 'level_comparison.png'))
    
    reporter.create_parameter_ranking_plot(sensitivity_results, save_path=str(viz_dir / 'parameter_ranking.png'))
    
    if not group_analysis.empty:
        reporter.create_sensitivity_heatmap(sensitivity_results, save_path=str(viz_dir / 'sensitivity_heatmap.png'))


def export_for_surrogate_modeling(
    sensitivity_results: pd.DataFrame,
    output_dir: Path,
    logger: logging.Logger
) -> None:
    """Legacy function for backward compatibility"""
    logger.info("[INFO] Using new export system...")
    # This would be called by the new system automatically
    pass


def export_for_calibration(
    sensitivity_results: pd.DataFrame,
    output_dir: Path,
    logger: logging.Logger
) -> None:
    """Legacy function for backward compatibility"""
    logger.info("[INFO] Using new export system...")
    # This would be called by the new system automatically
    pass