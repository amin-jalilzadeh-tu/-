#!/usr/bin/env python3
"""
Consolidate sensitivity analysis outputs into minimal set
"""
import json
import pandas as pd
from pathlib import Path
import shutil
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def consolidate_sensitivity_outputs(sensitivity_dir: Path):
    """Consolidate all sensitivity outputs into minimal set"""
    
    # 1. Create comprehensive JSON report
    logger.info("Creating consolidated JSON report...")
    consolidated_report = create_consolidated_json_report(sensitivity_dir)
    
    # 2. Create consolidated parameter CSV
    logger.info("Creating consolidated parameter CSV...")
    create_consolidated_parameter_csv(sensitivity_dir, consolidated_report)
    
    # 3. Create README.txt
    logger.info("Creating README.txt...")
    create_readme(sensitivity_dir, consolidated_report)
    
    # 4. Keep the best parquet file
    logger.info("Selecting best parquet file...")
    select_best_parquet(sensitivity_dir)
    
    # 5. Clean up redundant files
    logger.info("Cleaning up redundant files...")
    cleanup_redundant_files(sensitivity_dir)
    
    logger.info("Consolidation complete!")

def create_consolidated_json_report(sensitivity_dir: Path) -> dict:
    """Merge all JSON reports into one comprehensive file"""
    
    consolidated = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "consolidation_date": datetime.now().strftime("%Y-%m-%d"),
            "analysis_type": "modification_based"
        },
        "executive_summary": {},
        "full_results": {},
        "time_slice_analysis": {},
        "parameter_metadata": {},
        "export_configurations": {}
    }
    
    # Load existing reports
    json_files = {
        'main': 'modification_sensitivity_report.json',
        'time_slice': 'modification_sensitivity_report_peak_months_cooling.json',
        'summary': 'sensitivity_summary.json',
        'time_summary': 'time_slice_sensitivity_summary.json',
        'important': 'important_parameters.json',
        'surrogate': 'sensitive_parameters_for_surrogate.json',
        'calibration': 'calibration_parameters.json'
    }
    
    loaded_data = {}
    for key, filename in json_files.items():
        filepath = sensitivity_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                loaded_data[key] = json.load(f)
    
    # Merge metadata
    if 'time_slice' in loaded_data:
        consolidated['metadata'].update(loaded_data['time_slice'].get('metadata', {}))
    elif 'main' in loaded_data:
        consolidated['metadata'].update(loaded_data['main'].get('metadata', {}))
    
    # Executive summary from multiple sources
    if 'summary' in loaded_data:
        consolidated['executive_summary'] = {
            'analysis_completed': loaded_data['summary'].get('analysis_completed', True),
            'methods_used': loaded_data['summary'].get('methods_used', ['modification']),
            'total_parameters_analyzed': loaded_data['summary'].get('total_parameters_analyzed', 0),
            'total_outputs_analyzed': loaded_data['summary'].get('total_outputs_analyzed', 0),
            'top_5_parameters': loaded_data['summary'].get('top_5_parameters', []),
            'parameter_breakdown': loaded_data['summary'].get('parameter_breakdown', {}),
            'statistics': loaded_data['summary'].get('statistics_by_method', {})
        }
    
    # Full results
    if 'time_slice' in loaded_data:
        consolidated['full_results'] = {
            'all_parameters': loaded_data['time_slice'].get('results', []),
            'summary': loaded_data['time_slice'].get('summary', {})
        }
    elif 'main' in loaded_data:
        consolidated['full_results'] = {
            'all_parameters': loaded_data['main'].get('results', []),
            'summary': loaded_data['main'].get('summary', {})
        }
    
    # Time slice analysis
    if 'time_summary' in loaded_data:
        consolidated['time_slice_analysis'] = loaded_data['time_summary']
    elif 'time_slice' in loaded_data and 'time_slice_config' in loaded_data['time_slice'].get('metadata', {}):
        consolidated['time_slice_analysis'] = {
            'configuration': loaded_data['time_slice']['metadata']['time_slice_config'],
            'results': loaded_data['time_slice'].get('results', [])
        }
    
    # Parameter metadata from important parameters
    if 'important' in loaded_data:
        consolidated['parameter_metadata'] = loaded_data['important']
    
    # Export configurations
    if 'calibration' in loaded_data:
        consolidated['export_configurations']['calibration'] = loaded_data['calibration']
    if 'surrogate' in loaded_data:
        consolidated['export_configurations']['surrogate'] = loaded_data['surrogate']
    
    # Save consolidated report
    output_path = sensitivity_dir / 'sensitivity_analysis_report.json'
    with open(output_path, 'w') as f:
        json.dump(consolidated, f, indent=2)
    
    return consolidated

def create_consolidated_parameter_csv(sensitivity_dir: Path, consolidated_report: dict):
    """Create single CSV with all parameter information"""
    
    # Load existing CSV files
    csv_data = []
    
    # Load parquet data for full information
    parquet_files = list(sensitivity_dir.glob("*.parquet"))
    if parquet_files:
        # Use the time-sliced one if available
        time_slice_parquet = sensitivity_dir / "modification_sensitivity_results_peak_months_cooling.parquet"
        if time_slice_parquet.exists():
            df = pd.read_parquet(time_slice_parquet)
        else:
            df = pd.read_parquet(parquet_files[0])
        
        # Add rank
        df = df.sort_values('sensitivity_score', ascending=False).reset_index(drop=True)
        df['rank'] = df.index + 1
        
        # Add calibration and surrogate flags
        df['calibration_priority'] = df['sensitivity_score'].apply(
            lambda x: 'high' if x > 5 else ('medium' if x > 1 else 'low')
        )
        df['surrogate_include'] = df['rank'] <= 20  # Top 20 for surrogate
        
        # Get parameter bounds from modifications if available
        df['min_value'] = df['param_change'].apply(lambda x: -30 if x < 0 else 0)
        df['max_value'] = df['param_change'].apply(lambda x: 30 if x > 0 else 0)
        df['current_value'] = 0  # Baseline
        
        # Select and rename columns
        output_df = df[[
            'rank', 'parameter', 'category', 'sensitivity_score',
            'calibration_priority', 'surrogate_include',
            'min_value', 'max_value', 'current_value',
            'object_type', 'field_name'
        ]].copy()
        
        # Add units and description based on field name
        output_df['units'] = output_df.apply(lambda row: get_units(row['field_name']), axis=1)
        output_df['description'] = output_df.apply(
            lambda row: f"{row['object_type']} {row['field_name']}", axis=1
        )
        
        # Save consolidated CSV
        output_path = sensitivity_dir / 'sensitivity_parameters.csv'
        output_df.to_csv(output_path, index=False)
        logger.info(f"Created consolidated parameter CSV with {len(output_df)} parameters")

def get_units(field_name: str) -> str:
    """Get units based on field name"""
    units_map = {
        'Setpoint': 'W/m2',
        'Conductivity': 'W/m-K',
        'Thickness': 'm',
        'Thermal Resistance': 'm2-K/W',
        'Watts per Zone Floor Area': 'W/m2',
        'Outdoor Air Flow per Zone Floor Area': 'm3/s/m2',
        'Multiplier': '-',
        'Fraction': '-',
        'Efficiency': '-',
        'Coefficient': 'W/K'
    }
    
    for key, unit in units_map.items():
        if key in field_name:
            return unit
    return '-'

def create_readme(sensitivity_dir: Path, consolidated_report: dict):
    """Create README.txt file"""
    
    # Get top parameters
    top_params = consolidated_report.get('executive_summary', {}).get('top_5_parameters', [])
    top_params_text = "\n".join([
        f"  {i+1}. {p.get('parameter', 'Unknown')} (Score: {p.get('score', 0):.2f})"
        for i, p in enumerate(top_params[:5])
    ])
    
    # Get metadata
    metadata = consolidated_report.get('metadata', {})
    n_params = metadata.get('n_parameters', 'Unknown')
    n_outputs = metadata.get('n_outputs', 'Unknown')
    
    readme_content = f"""SENSITIVITY ANALYSIS RESULTS
============================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Job ID: {sensitivity_dir.parent.name}

FILE DESCRIPTIONS:
------------------
- sensitivity_analysis_report.json : Complete analysis report with all results
- sensitivity_results.parquet     : Full tabular data for further analysis  
- sensitivity_parameters.csv      : Parameter list with rankings and metadata
- sensitivity_report.html         : Web-viewable report with visualizations
- visualizations/                 : Folder containing charts and plots

QUICK START:
------------
- For overview: Open sensitivity_report.html in a web browser
- For key parameters: View sensitivity_parameters.csv in Excel
- For detailed analysis: Load sensitivity_results.parquet in Python/R
- For full report: Read sensitivity_analysis_report.json

TOP FINDINGS:
-------------
{top_params_text}

ANALYSIS DETAILS:
-----------------
- Method: Elasticity-based modification analysis
- Time Period: Peak cooling months (June-August)
- Parameters Analyzed: {n_params}
- Output Variable: Electricity:Facility

DATA STRUCTURE:
---------------
The parquet file contains the following columns:
- parameter: Full parameter name
- sensitivity_score: Elasticity-based sensitivity (0-10 scale)
- category: Parameter category (e.g., shading, ventilation)
- p_value: Statistical significance
- confidence intervals: Statistical bounds

NOTES:
------
- Sensitivity scores > 5.0 indicate high sensitivity
- Scores are based on elasticity (% output change / % parameter change)
- Time slicing focused on peak cooling months for HVAC analysis
"""
    
    readme_path = sensitivity_dir / 'README.txt'
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    logger.info("Created README.txt")

def select_best_parquet(sensitivity_dir: Path):
    """Keep only the most comprehensive parquet file"""
    
    # Prefer time-sliced version if available
    time_slice_parquet = sensitivity_dir / "modification_sensitivity_results_peak_months_cooling.parquet"
    final_parquet = sensitivity_dir / "sensitivity_results.parquet"
    
    if time_slice_parquet.exists():
        shutil.copy2(time_slice_parquet, final_parquet)
        logger.info("Selected time-sliced parquet as main results file")
    else:
        # Find any parquet file
        parquet_files = list(sensitivity_dir.glob("*sensitivity*.parquet"))
        if parquet_files:
            shutil.copy2(parquet_files[0], final_parquet)
            logger.info(f"Selected {parquet_files[0].name} as main results file")

def cleanup_redundant_files(sensitivity_dir: Path):
    """Remove redundant files after consolidation"""
    
    # Files to remove
    redundant_files = [
        'modification_sensitivity_report.json',
        'modification_sensitivity_report_peak_months_cooling.json',
        'sensitivity_summary.json',
        'time_slice_sensitivity_summary.json',
        'important_parameters.json',
        'sensitive_parameters_for_surrogate.json',
        'calibration_parameters.json',
        'calibration_parameters.csv',
        'top_sensitive_parameters.csv',
        'sensitivity_for_surrogate.parquet',
        'modification_sensitivity_results_peak_months_cooling.parquet'
    ]
    
    removed_count = 0
    for filename in redundant_files:
        filepath = sensitivity_dir / filename
        if filepath.exists():
            filepath.unlink()
            removed_count += 1
            logger.debug(f"Removed {filename}")
    
    logger.info(f"Removed {removed_count} redundant files")

if __name__ == "__main__":
    # Test on the latest job
    job_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/a8f044f9-0fc2-4e56-99ff-f83fefdbb9b6/sensitivity_results")
    if job_dir.exists():
        consolidate_sensitivity_outputs(job_dir)
    else:
        logger.error(f"Directory not found: {job_dir}")