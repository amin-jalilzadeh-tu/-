"""
orchestrator/sensitivity_step.py

Enhanced sensitivity analysis step with consolidated modules and time slicing support.
"""

import os
import json
import logging
import warnings
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import numpy as np

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
    Run sensitivity analysis using the consolidated framework with time slicing support
    
    Args:
        sens_cfg: Sensitivity configuration from combined.json
        job_output_dir: Job output directory path
        logger: Logger instance
        
    Returns:
        Path to the sensitivity report or None if failed
    """
    logger.info("[INFO] Starting Sensitivity Analysis...")
    
    # Log time slicing configuration if enabled
    time_slicing_cfg = sens_cfg.get("time_slicing", {})
    if time_slicing_cfg.get("enabled", False):
        logger.info(f"[INFO] Time slicing is enabled: {time_slicing_cfg.get('slice_type', 'custom')}")
        if time_slicing_cfg.get('compare_time_slices', False):
            logger.info("[INFO] Comparative time slice analysis will be performed")
    
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
            
            # Generate time slice summary if time slicing was used
            if time_slicing_cfg.get("enabled", False) and time_slicing_cfg.get("generate_time_slice_report", True):
                generate_time_slice_summary(sensitivity_manager, output_dir, logger)
            
            # Create visualization report if requested
            if sens_cfg.get("generate_visualizations", False) and sens_cfg.get("report_formats", []):
                if "html" in sens_cfg["report_formats"]:
                    generate_html_report(sensitivity_manager, output_dir, logger)
            
            # Consolidate outputs at the end
            consolidate_sensitivity_outputs(output_dir, logger)
            
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
    Generate export files specifically formatted for surrogate modeling with time slice support
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
            
            # Add time slice information if present
            if 'time_slice' in top_params.columns:
                cols_to_keep.append('time_slice')
            
            # Parse parameter components for easier use in surrogate
            if 'parameter' in top_params.columns:
                param_components = top_params['parameter'].apply(_parse_parameter_string)
                top_params['object_name'] = param_components.apply(lambda x: x.get('object_name', ''))
                top_params['field_name'] = param_components.apply(lambda x: x.get('field_name', ''))
                cols_to_keep.extend(['object_name', 'field_name'])
            
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
            'analysis_types': list(manager.results.keys()),
            # Add time slice information
            'time_slice_config': config.get('time_slicing', {}),
            'time_slices_analyzed': list(set(combined_params['time_slice'].tolist())) if 'time_slice' in combined_params.columns else ['full_data']
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
    Generate export files specifically formatted for calibration with time slice support
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
                
                # Parse parameter for detailed info
                param_parts = _parse_parameter_string(row['parameter'])
                param_info.update(param_parts)
                
                # Add time slice info if present
                if 'time_slice' in row:
                    param_info['time_slice'] = row['time_slice']
                
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
            },
            # Add time slice information
            'time_slice_config': config.get('time_slicing', {}),
            'time_slices_analyzed': list(set(p.get('time_slice', 'full_data') for p in param_dict.values()))
        }
        
        json_path = output_dir / 'calibration_parameters.json'
        with open(json_path, 'w') as f:
            json.dump(calibration_export, f, indent=2)
        logger.info(f"[INFO] Saved calibration details to {json_path}")


def generate_time_slice_summary(
    manager: SensitivityManager,
    output_dir: Path,
    logger: logging.Logger
) -> None:
    """
    Generate summary report for time-sliced sensitivity analysis
    """
    logger.info("[INFO] Generating time slice summary...")
    
    if not manager.time_slice_configs:
        logger.info("[INFO] No time slice configurations to summarize")
        return
    
    summary = {
        'analysis_timestamp': datetime.now().isoformat(),
        'time_slices_analyzed': {},
        'parameter_stability_across_slices': {},
        'recommendations': [],
        'temporal_patterns': {}
    }
    
    # Summarize each time slice
    for slice_name, config in manager.time_slice_configs.items():
        if slice_name in manager.results:
            results_df = manager.results[slice_name]
            if isinstance(results_df, pd.DataFrame) and 'sensitivity_score' in results_df.columns:
                # Calculate key metrics
                top_10_params = results_df.nlargest(10, 'sensitivity_score')
                
                summary['time_slices_analyzed'][slice_name] = {
                    'config': config,
                    'n_results': len(results_df),
                    'n_unique_parameters': results_df['parameter'].nunique() if 'parameter' in results_df.columns else 0,
                    'avg_sensitivity': float(results_df['sensitivity_score'].mean()),
                    'max_sensitivity': float(results_df['sensitivity_score'].max()),
                    'std_sensitivity': float(results_df['sensitivity_score'].std()),
                    'top_10_parameters': top_10_params[
                        ['parameter', 'sensitivity_score', 'output_variable']
                    ].to_dict('records') if 'output_variable' in top_10_params.columns else
                    top_10_params[['parameter', 'sensitivity_score']].to_dict('records')
                }
    
    # Analyze parameter stability across time slices
    if len(manager.results) > 1:
        all_params = set()
        param_scores_by_slice = {}
        
        for slice_name, results_df in manager.results.items():
            if isinstance(results_df, pd.DataFrame) and 'parameter' in results_df.columns:
                # Group by parameter and average across output variables
                params = results_df.groupby('parameter')['sensitivity_score'].mean()
                param_scores_by_slice[slice_name] = params
                all_params.update(params.index)
        
        # Calculate stability metrics for each parameter
        for param in all_params:
            scores_across_slices = []
            slices_present = []
            
            for slice_name, param_scores in param_scores_by_slice.items():
                if param in param_scores:
                    scores_across_slices.append(param_scores[param])
                    slices_present.append(slice_name)
            
            if len(scores_across_slices) > 1:
                summary['parameter_stability_across_slices'][param] = {
                    'mean_score': float(np.mean(scores_across_slices)),
                    'std_score': float(np.std(scores_across_slices)),
                    'cv': float(np.std(scores_across_slices) / np.mean(scores_across_slices)) if np.mean(scores_across_slices) > 0 else 0,
                    'min_score': float(min(scores_across_slices)),
                    'max_score': float(max(scores_across_slices)),
                    'range': float(max(scores_across_slices) - min(scores_across_slices)),
                    'present_in_slices': slices_present,
                    'n_slices': len(slices_present),
                    'scores_by_slice': {
                        slice_name: float(score) 
                        for slice_name, score in zip(slices_present, scores_across_slices)
                    }
                }
    
    # Identify temporal patterns
    if summary['parameter_stability_across_slices']:
        # Parameters that are more sensitive during specific periods
        for param, stability_info in summary['parameter_stability_across_slices'].items():
            if stability_info['cv'] > 0.3:  # High variability threshold
                # Find which time slice has highest sensitivity
                scores = stability_info['scores_by_slice']
                max_slice = max(scores, key=scores.get)
                min_slice = min(scores, key=scores.get)
                
                if param not in summary['temporal_patterns']:
                    summary['temporal_patterns'][param] = {}
                
                summary['temporal_patterns'][param] = {
                    'most_sensitive_during': max_slice,
                    'least_sensitive_during': min_slice,
                    'sensitivity_ratio': scores[max_slice] / scores[min_slice] if scores[min_slice] > 0 else float('inf')
                }
    
    # Generate recommendations
    if summary['parameter_stability_across_slices']:
        # Find most stable parameters (low CV)
        stable_params = sorted(
            [(p, info) for p, info in summary['parameter_stability_across_slices'].items()],
            key=lambda x: x[1]['cv']
        )[:10]
        
        summary['recommendations'].append({
            'type': 'stable_parameters',
            'description': 'Parameters with consistent sensitivity across all time slices (good for general calibration)',
            'parameters': [
                {
                    'name': p[0],
                    'avg_sensitivity': p[1]['mean_score'],
                    'coefficient_of_variation': p[1]['cv']
                }
                for p in stable_params
            ]
        })
        
        # Find time-dependent parameters (high CV)
        variable_params = sorted(
            [(p, info) for p, info in summary['parameter_stability_across_slices'].items()],
            key=lambda x: x[1]['cv'],
            reverse=True
        )[:10]
        
        summary['recommendations'].append({
            'type': 'time_dependent_parameters',
            'description': 'Parameters with sensitivity that varies significantly by time slice (consider time-specific calibration)',
            'parameters': [
                {
                    'name': p[0],
                    'sensitivity_range': [p[1]['min_score'], p[1]['max_score']],
                    'coefficient_of_variation': p[1]['cv'],
                    'most_sensitive_during': summary['temporal_patterns'].get(p[0], {}).get('most_sensitive_during', 'unknown')
                }
                for p in variable_params
            ]
        })
        
        # Parameters important only during peak periods
        peak_specific_params = []
        for param, temporal_info in summary['temporal_patterns'].items():
            if temporal_info['sensitivity_ratio'] > 2.0:  # At least 2x more sensitive
                peak_specific_params.append({
                    'parameter': param,
                    'peak_period': temporal_info['most_sensitive_during'],
                    'sensitivity_ratio': temporal_info['sensitivity_ratio']
                })
        
        if peak_specific_params:
            summary['recommendations'].append({
                'type': 'peak_specific_parameters',
                'description': 'Parameters that are significantly more sensitive during specific time periods',
                'parameters': sorted(peak_specific_params, key=lambda x: x['sensitivity_ratio'], reverse=True)[:10]
            })
    
    # Save summary
    summary_path = output_dir / 'time_slice_sensitivity_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"[INFO] Saved time slice summary to {summary_path}")
    
    # Log key findings
    if summary['recommendations']:
        logger.info("[INFO] Key findings from time slice analysis:")
        for rec in summary['recommendations']:
            logger.info(f"  - {rec['type']}: {len(rec['parameters'])} parameters identified")


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
        'parameter_breakdown': {},
        'statistics_by_method': {}
    }
    
    # Aggregate statistics
    all_params = set()
    all_outputs = set()
    param_by_category = {}
    
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
                
                # Count parameters by category
                for param in params:
                    cat = _parse_parameter_string(param).get('category', 'unknown')
                    if cat not in param_by_category:
                        param_by_category[cat] = set()
                    param_by_category[cat].add(param)
            
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
    
    # Parameter breakdown by category
    summary['parameter_breakdown'] = {
        cat: len(params) for cat, params in param_by_category.items()
    }
    
    # Get consensus top parameters if multiple methods were used
    if len(manager.results) > 1 and hasattr(manager, '_combine_analysis_results'):
        combined = manager._combine_analysis_results()
        if combined is not None and 'consensus_score' in combined.columns:
            top_5 = combined.nlargest(5, 'consensus_score')[['parameter', 'consensus_score']]
            summary['top_5_parameters'] = [
                {
                    'parameter': row['parameter'], 
                    'score': float(row['consensus_score']),
                    **_parse_parameter_string(row['parameter'])
                }
                for _, row in top_5.iterrows()
            ]
    elif len(manager.results) == 1:
        # Single method - just get top from that method
        for _, results in manager.results.items():
            if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                top_5 = results.nlargest(5, 'sensitivity_score')[['parameter', 'sensitivity_score']]
                summary['top_5_parameters'] = [
                    {
                        'parameter': row['parameter'], 
                        'score': float(row['sensitivity_score']),
                        **_parse_parameter_string(row['parameter'])
                    }
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
        
        # Add time slice information if available
        if hasattr(manager, 'time_slice_configs') and manager.time_slice_configs:
            results['metadata']['time_slices_analyzed'] = list(manager.time_slice_configs.keys())
            results['metadata']['time_slicing_enabled'] = True
        
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
                            'avg_sensitivity_score': float(p['sensitivity_score']),
                            **_parse_parameter_string(p['parameter'])
                        }
                        for p in top_params
                    ]
        
        # Generate HTML report
        html_path = output_dir / 'sensitivity_report.html'
        reporter.generate_html_report(results, html_path, include_plots=True)
        
        logger.info(f"[INFO] Generated HTML report: {html_path}")
        
    except Exception as e:
        logger.warning(f"[WARN] Failed to generate HTML report: {e}")


def consolidate_sensitivity_outputs(output_dir: Path, logger: logging.Logger) -> None:
    """
    Consolidate sensitivity outputs into minimal set
    """
    logger.info("[INFO] Consolidating sensitivity outputs...")
    
    try:
        # Import the consolidation function
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from consolidate_sensitivity_outputs import consolidate_sensitivity_outputs as consolidate
        
        # Run consolidation
        consolidate(output_dir)
        logger.info("[INFO] Successfully consolidated sensitivity outputs")
        
    except Exception as e:
        logger.warning(f"[WARN] Failed to consolidate outputs: {e}")


def _parse_parameter_string(param_str: str) -> Dict[str, str]:
    """
    Parse parameter string into components
    Format: category*object_type*object_name*field_name
    """
    result = {
        'category': 'unknown',
        'object_type': '',
        'object_name': '',
        'field_name': ''
    }
    
    if '*' in param_str:
        parts = param_str.split('*')
        if len(parts) >= 1:
            result['category'] = parts[0]
        if len(parts) >= 2:
            result['object_type'] = parts[1]
        if len(parts) >= 3:
            result['object_name'] = parts[2]
        if len(parts) >= 4:
            result['field_name'] = parts[3]
    else:
        # Old format - try to extract what we can
        if '_' in param_str:
            parts = param_str.split('_')
            result['category'] = parts[0]
            if len(parts) > 1:
                result['field_name'] = '_'.join(parts[1:])
    
    return result


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


# Add these functions to your existing sensitivity_step.py file:

def _log_configuration_summary(sens_cfg: dict, logger: logging.Logger) -> None:
    """Log a summary of the sensitivity configuration"""
    
    # Basic configuration
    logger.info(f"[CONFIG] Analysis enabled: {sens_cfg.get('enabled', False)}")
    logger.info(f"[CONFIG] Analysis type: {sens_cfg.get('analysis_type', 'traditional')}")
    
    # Time slicing configuration
    time_slicing_cfg = sens_cfg.get("time_slicing", {})
    if time_slicing_cfg.get("enabled", False):
        logger.info(f"[CONFIG] Time slicing enabled: {time_slicing_cfg.get('slice_type', 'custom')}")
        if time_slicing_cfg.get('compare_time_slices', False):
            logger.info("[CONFIG] Comparative time slice analysis will be performed")
    
    # Multi-level analysis
    multi_level_cfg = sens_cfg.get("multi_level_analysis", {})
    if multi_level_cfg.get("enabled", False):
        levels = []
        if multi_level_cfg.get("analyze_building_level", True):
            levels.append("building")
        if multi_level_cfg.get("analyze_zone_level", False):
            levels.append("zone")
        if multi_level_cfg.get("analyze_equipment_level", False):
            levels.append("equipment")
        logger.info(f"[CONFIG] Multi-level analysis enabled for: {', '.join(levels)}")
    
    # Advanced analysis features
    advanced_cfg = sens_cfg.get("advanced_analysis", {})
    if advanced_cfg.get("enabled", False):
        logger.info("[CONFIG] Advanced analysis features enabled:")
        features = []
        if advanced_cfg.get("uncertainty_propagation", False):
            features.append("uncertainty quantification")
        if advanced_cfg.get("threshold_analysis", False):
            features.append("threshold detection")
        if advanced_cfg.get("regional_sensitivity", False):
            features.append("regional sensitivity")
        if advanced_cfg.get("sobol_analysis", False):
            features.append("Sobol decomposition")
        if advanced_cfg.get("temporal_patterns", False):
            features.append("temporal patterns")
        
        for feature in features:
            logger.info(f"  - {feature}")


def _validate_advanced_config(advanced_cfg: dict, logger: logging.Logger) -> bool:
    """Validate advanced analysis configuration"""
    
    is_valid = True
    
    # Check uncertainty configuration
    if advanced_cfg.get("uncertainty_propagation", False):
        if advanced_cfg.get("uncertainty_samples", 0) < 100:
            logger.warning("[WARNING] Uncertainty samples < 100 may give unreliable results")
        
        if "parameter_distributions" in advanced_cfg:
            for param, dist in advanced_cfg["parameter_distributions"].items():
                if "type" not in dist:
                    logger.warning(f"[WARNING] No distribution type specified for {param}")
                    is_valid = False
    
    # Check threshold configuration
    if advanced_cfg.get("threshold_analysis", False):
        min_segment = advanced_cfg.get("min_segment_size", 10)
        if min_segment < 5:
            logger.warning("[WARNING] min_segment_size < 5 may lead to overfitting")
    
    # Check Sobol configuration
    if advanced_cfg.get("sobol_analysis", False):
        n_samples = advanced_cfg.get("sobol_samples", 0)
        if n_samples > 0 and (n_samples & (n_samples - 1)) != 0:
            logger.warning("[WARNING] Sobol samples should be a power of 2 for best results")
    
    # Check temporal configuration
    if advanced_cfg.get("temporal_patterns", False):
        if "time_column" not in advanced_cfg:
            logger.warning("[WARNING] time_column not specified for temporal analysis")
    
    return is_valid


def _log_results_summary(sensitivity_manager: SensitivityManager, logger: logging.Logger) -> None:
    """Log a summary of the analysis results"""
    
    # Summary of traditional/modification results
    for analysis_type, results in sensitivity_manager.results.items():
        if isinstance(results, pd.DataFrame) and not results.empty:
            logger.info(f"[RESULTS] {analysis_type} analysis: {len(results)} sensitivity scores")
            
            # Top 5 parameters
            if 'sensitivity_score' in results.columns:
                top_params = results.nlargest(5, 'sensitivity_score')[
                    ['parameter', 'output_variable', 'sensitivity_score']
                ]
                logger.info(f"[RESULTS] Top 5 sensitive parameters for {analysis_type}:")
                for _, row in top_params.iterrows():
                    logger.info(f"  - {row['parameter'][:50]}... -> {row['output_variable']}: {row['sensitivity_score']:.4f}")
    
    # Summary of advanced results
    if sensitivity_manager.advanced_results:
        logger.info("[RESULTS] Advanced analysis results:")
        
        for method, results in sensitivity_manager.advanced_results.items():
            if isinstance(results, pd.DataFrame) and not results.empty:
                logger.info(f"  - {method}: {len(results)} results")
                
                # Method-specific summaries
                if method == "uncertainty" and 'uncertainty_lower' in results.columns:
                    avg_interval = (results['uncertainty_upper'] - results['uncertainty_lower']).mean()
                    logger.info(f"    Average uncertainty interval: {avg_interval:.4f}")
                
                elif method == "threshold" and 'breakpoint_value' in results.columns:
                    n_breakpoints = results['breakpoint_value'].notna().sum()
                    logger.info(f"    Detected breakpoints: {n_breakpoints}")
                
                elif method == "regional" and 'parameter_region' in results.columns:
                    n_regions = results['parameter_region'].nunique()
                    logger.info(f"    Analyzed regions: {n_regions}")
                
                elif method == "sobol" and 'sobol_first_order' in results.columns:
                    total_var = results.groupby('output_variable')['sobol_first_order'].sum().mean()
                    logger.info(f"    Average variance explained: {total_var:.2%}")
                
                elif method == "temporal" and 'dominant_frequency' in results.columns:
                    n_patterns = results['dominant_frequency'].notna().sum()
                    logger.info(f"    Temporal patterns found: {n_patterns}")


# Update the main run_sensitivity_analysis function to include these calls:
# 1. Add at the beginning:
#    _log_configuration_summary(sens_cfg, logger)
#
# 2. Add after checking prerequisites:
#    if sens_cfg.get("advanced_analysis", {}).get("enabled", False):
#        if not _validate_advanced_config(sens_cfg.get("advanced_analysis", {}), logger):
#            logger.warning("[WARNING] Advanced analysis configuration has issues, some features may be skipped")
#
# 3. Add after successful analysis:
#    _log_results_summary(sensitivity_manager, logger)