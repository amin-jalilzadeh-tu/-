"""
orchestrator/validation_aggregator.py

Aggregates validation results from multiple stages.
"""

import os
import json
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def aggregate_validation_results(
    job_output_dir: str,
    logger: logging.Logger
) -> Optional[Dict[str, Any]]:
    """
    Aggregate validation results from all stages.
    
    Args:
        job_output_dir: Job output directory
        logger: Logger instance
        
    Returns:
        Combined summary dictionary or None
    """
    validation_dir = Path(job_output_dir) / "validation_results"
    if not validation_dir.exists():
        logger.debug("No validation results directory found")
        return None
    
    # Find all validation stage directories
    stage_dirs = [d for d in validation_dir.iterdir() if d.is_dir()]
    if not stage_dirs:
        logger.debug("No validation stage directories found")
        return None
    
    logger.info(f"[INFO] Found {len(stage_dirs)} validation stage(s) to aggregate")
    
    # Load results from each stage
    all_results = {}
    all_summaries = {}
    
    for stage_dir in stage_dirs:
        stage_name = stage_dir.name
        summary_file = stage_dir / "validation_summary.json"
        
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    stage_data = json.load(f)
                    all_results[stage_name] = stage_data
                    all_summaries[stage_name] = stage_data.get('summary', {})
                    logger.info(f"  - Loaded results for stage: {stage_name}")
            except Exception as e:
                logger.error(f"  - Failed to load results for stage {stage_name}: {e}")
    
    if not all_results:
        logger.warning("No valid validation results found")
        return None
    
    # Create combined summary
    combined_summary = {
        'timestamp': datetime.now().isoformat(),
        'job_id': os.path.basename(job_output_dir),
        'stages_completed': list(all_results.keys()),
        'stage_summaries': all_summaries,
        'overall_metrics': calculate_overall_metrics(all_results),
        'improvement_metrics': calculate_improvement_metrics(all_results),
        'recommendations': generate_combined_recommendations(all_results)
    }
    
    # Save combined summary
    combined_path = validation_dir / "combined_summary.json"
    with open(combined_path, 'w') as f:
        json.dump(combined_summary, f, indent=2)
    
    logger.info(f"[INFO] Saved combined validation summary to: {combined_path}")
    
    # Create comparison report if we have baseline and modified stages
    if 'baseline' in all_results and 'modified' in all_results:
        comparison_report = create_comparison_report(
            all_results['baseline'],
            all_results['modified'],
            validation_dir
        )
        
        if comparison_report:
            combined_summary['comparison_report'] = str(comparison_report)
    
    return combined_summary


def calculate_overall_metrics(all_results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall metrics across all stages."""
    overall = {
        'total_validations': 0,
        'total_passed': 0,
        'buildings_validated': set(),
        'variables_validated': set(),
        'average_pass_rate': 0.0
    }
    
    pass_rates = []
    
    for stage_name, stage_data in all_results.items():
        summary = stage_data.get('summary', {})
        
        overall['total_validations'] += summary.get('successful_validations', 0)
        overall['total_passed'] += summary.get('passed_validations', 0)
        
        # Collect unique buildings and variables
        val_results = stage_data.get('validation_results', [])
        for result in val_results:
            overall['buildings_validated'].add(result.get('building_id'))
            overall['variables_validated'].add(result.get('real_variable'))
        
        # Collect pass rates
        if summary.get('pass_rate') is not None:
            pass_rates.append(summary['pass_rate'])
    
    # Convert sets to counts
    overall['buildings_validated'] = len(overall['buildings_validated'])
    overall['variables_validated'] = len(overall['variables_validated'])
    
    # Calculate average pass rate
    if pass_rates:
        overall['average_pass_rate'] = sum(pass_rates) / len(pass_rates)
    
    # Overall pass rate
    if overall['total_validations'] > 0:
        overall['overall_pass_rate'] = (overall['total_passed'] / overall['total_validations']) * 100
    
    return overall


def calculate_improvement_metrics(all_results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate improvement metrics between baseline and modified stages."""
    if 'baseline' not in all_results or 'modified' not in all_results:
        return {}
    
    baseline_results = all_results['baseline'].get('validation_results', [])
    modified_results = all_results['modified'].get('validation_results', [])
    
    if not baseline_results or not modified_results:
        return {}
    
    # Create DataFrames for easier analysis
    baseline_df = pd.DataFrame(baseline_results)
    modified_df = pd.DataFrame(modified_results)
    
    # Match results by building_id and variable
    improvements = {}
    
    for _, baseline_row in baseline_df.iterrows():
        building_id = baseline_row['building_id']
        variable = baseline_row['real_variable']
        
        # Find corresponding modified result
        modified_match = modified_df[
            (modified_df['building_id'] == building_id) &
            (modified_df['real_variable'] == variable)
        ]
        
        if not modified_match.empty:
            modified_row = modified_match.iloc[0]
            
            # Calculate improvement in CVRMSE
            baseline_cvrmse = baseline_row.get('cvrmse', 0)
            modified_cvrmse = modified_row.get('cvrmse', 0)
            
            if baseline_cvrmse > 0:
                improvement = ((baseline_cvrmse - modified_cvrmse) / baseline_cvrmse) * 100
                
                key = f"{variable}"
                if key not in improvements:
                    improvements[key] = []
                improvements[key].append(improvement)
    
    # Average improvements by variable
    avg_improvements = {}
    for variable, values in improvements.items():
        avg_improvements[variable] = sum(values) / len(values)
    
    # Add overall improvement
    all_improvements = []
    for values in improvements.values():
        all_improvements.extend(values)
    
    if all_improvements:
        avg_improvements['overall'] = sum(all_improvements) / len(all_improvements)
    
    return avg_improvements


def generate_combined_recommendations(all_results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on all validation stages."""
    recommendations = []
    
    # Check overall performance
    overall_metrics = calculate_overall_metrics(all_results)
    overall_pass_rate = overall_metrics.get('overall_pass_rate', 0)
    
    if overall_pass_rate < 50:
        recommendations.append(
            f"Overall validation pass rate is low ({overall_pass_rate:.1f}%). "
            "Consider comprehensive calibration."
        )
    elif overall_pass_rate < 75:
        recommendations.append(
            f"Overall validation pass rate is moderate ({overall_pass_rate:.1f}%). "
            "Focus calibration on failing variables."
        )
    
    # Check improvements
    improvements = calculate_improvement_metrics(all_results)
    if improvements:
        improved_vars = [var for var, imp in improvements.items() if imp > 0 and var != 'overall']
        degraded_vars = [var for var, imp in improvements.items() if imp < -5 and var != 'overall']
        
        if improved_vars:
            recommendations.append(
                f"Modifications improved: {', '.join(improved_vars)}. "
                "Consider applying similar strategies to other variables."
            )
        
        if degraded_vars:
            recommendations.append(
                f"Modifications degraded: {', '.join(degraded_vars)}. "
                "Review modification parameters for these variables."
            )
    
    # Stage-specific recommendations
    for stage_name, stage_data in all_results.items():
        stage_recs = stage_data.get('recommendations', [])
        for rec in stage_recs:
            recommendations.append(f"[{stage_name}] {rec}")
    
    return recommendations


def create_comparison_report(
    baseline_results: Dict[str, Any],
    modified_results: Dict[str, Any],
    output_dir: Path
) -> Optional[Path]:
    """Create a detailed comparison report between baseline and modified results."""
    try:
        baseline_df = pd.DataFrame(baseline_results.get('validation_results', []))
        modified_df = pd.DataFrame(modified_results.get('validation_results', []))
        
        if baseline_df.empty or modified_df.empty:
            return None
        
        # Create comparison DataFrame
        comparison_data = []
        
        for _, baseline_row in baseline_df.iterrows():
            building_id = baseline_row['building_id']
            variable = baseline_row['real_variable']
            
            # Find corresponding modified result
            modified_match = modified_df[
                (modified_df['building_id'] == building_id) &
                (modified_df['real_variable'] == variable)
            ]
            
            if not modified_match.empty:
                modified_row = modified_match.iloc[0]
                
                comparison_data.append({
                    'building_id': building_id,
                    'variable': variable,
                    'baseline_cvrmse': baseline_row['cvrmse'],
                    'modified_cvrmse': modified_row['cvrmse'],
                    'cvrmse_change': modified_row['cvrmse'] - baseline_row['cvrmse'],
                    'cvrmse_improvement_%': ((baseline_row['cvrmse'] - modified_row['cvrmse']) / baseline_row['cvrmse'] * 100) if baseline_row['cvrmse'] > 0 else 0,
                    'baseline_nmbe': baseline_row['nmbe'],
                    'modified_nmbe': modified_row['nmbe'],
                    'nmbe_change': modified_row['nmbe'] - baseline_row['nmbe'],
                    'baseline_pass': baseline_row['pass_cvrmse'] and baseline_row['pass_nmbe'],
                    'modified_pass': modified_row['pass_cvrmse'] and modified_row['pass_nmbe'],
                    'status_change': 'improved' if (not (baseline_row['pass_cvrmse'] and baseline_row['pass_nmbe'])) and (modified_row['pass_cvrmse'] and modified_row['pass_nmbe']) else
                                   'degraded' if (baseline_row['pass_cvrmse'] and baseline_row['pass_nmbe']) and not (modified_row['pass_cvrmse'] and modified_row['pass_nmbe']) else
                                   'unchanged'
                })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            
            # Save comparison report
            report_path = output_dir / "baseline_vs_modified_comparison.csv"
            comparison_df.to_csv(report_path, index=False)
            
            # Also save as parquet
            parquet_path = output_dir / "baseline_vs_modified_comparison.parquet"
            comparison_df.to_parquet(parquet_path, index=False)
            
            return report_path
    
    except Exception as e:
        logging.error(f"Failed to create comparison report: {e}")
        
    return None