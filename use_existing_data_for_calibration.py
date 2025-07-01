"""
Use existing parquet/CSV data with the calibration system
Converts data to the format expected by unified_calibration.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prepare_calibration_data(job_dir: str):
    """
    Prepare existing data for calibration
    Uses whatever format exists (parquet, CSV, JSON)
    """
    job_path = Path(job_dir)
    
    # 1. Generate scenario files from existing data
    logger.info("=== Preparing Scenario Files ===")
    scenario_dir = job_path / "scenarios"
    scenario_dir.mkdir(exist_ok=True)
    
    # Check what data sources exist
    data_sources = check_data_sources(job_path)
    logger.info(f"Found data sources: {data_sources}")
    
    if 'sensitivity_parameters' in data_sources:
        create_scenarios_from_sensitivity(data_sources['sensitivity_parameters'], scenario_dir)
    elif 'parameter_matrix' in data_sources:
        create_scenarios_from_matrix(data_sources['parameter_matrix'], scenario_dir)
    elif 'modifications' in data_sources:
        create_scenarios_from_modifications(data_sources['modifications'], scenario_dir)
    else:
        logger.warning("No parameter source found, creating defaults")
        create_default_scenarios(scenario_dir)
    
    # 2. Prepare real/measured data
    logger.info("\n=== Preparing Measured Data ===")
    real_data_path = job_path / "real_data.csv"
    
    # Always try to use the standard measured data file first
    data_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data")
    
    # Try full year file first, then monthly file
    full_year_file = data_dir / "measured_data_daily_2013.csv"
    monthly_file = data_dir / "measured_data_parsed_format_daily_4136733.csv"
    
    if full_year_file.exists():
        create_real_data_from_measured_file(full_year_file, real_data_path)
    elif monthly_file.exists():
        create_real_data_from_measured_file(monthly_file, real_data_path)
    elif 'validation_results' in data_sources:
        create_real_data_from_validation(data_sources['validation_results'], real_data_path)
    elif 'timeseries' in data_sources:
        create_real_data_from_timeseries(data_sources['timeseries'], real_data_path)
    else:
        logger.warning("No measured data found, creating synthetic data")
        create_synthetic_real_data(real_data_path)
    
    logger.info(f"\n✓ Calibration data prepared in: {job_path}")
    logger.info(f"  - Scenario files: {scenario_dir}")
    logger.info(f"  - Real data: {real_data_path}")
    
    return scenario_dir, real_data_path


def check_data_sources(job_path: Path) -> dict:
    """Check what data sources are available"""
    sources = {}
    
    # Check for sensitivity parameters
    sens_csv = job_path / "sensitivity_results" / "sensitivity_parameters.csv"
    sens_parquet = job_path / "sensitivity_results" / "sensitivity_results.parquet"
    if sens_csv.exists():
        sources['sensitivity_parameters'] = sens_csv
    elif sens_parquet.exists():
        sources['sensitivity_parameters'] = sens_parquet
    
    # Check for parameter matrix
    param_matrix = job_path / "parsed_data" / "analysis_ready" / "parameter_matrix.parquet"
    if param_matrix.exists():
        sources['parameter_matrix'] = param_matrix
    
    # Check for modifications
    mods_json = job_path / "modifications_summary.json"
    mods_parquet = job_path / "modified_idfs" / "modifications_summary_*.parquet"
    if mods_json.exists():
        sources['modifications'] = mods_json
    elif list(job_path.glob("modified_idfs/modifications_summary_*.parquet")):
        sources['modifications'] = list(job_path.glob("modified_idfs/modifications_summary_*.parquet"))[0]
    
    # Check for validation results
    val_parquet = job_path / "parsed_data" / "validation_results.parquet"
    if val_parquet.exists():
        sources['validation_results'] = val_parquet
    
    # Check for timeseries data
    ts_monthly = job_path / "parsed_data" / "timeseries_monthly.parquet"
    if ts_monthly.exists():
        sources['timeseries'] = ts_monthly
    
    return sources


def create_scenarios_from_sensitivity(sens_file: Path, scenario_dir: Path):
    """Create scenario files from sensitivity analysis"""
    if sens_file.suffix == '.parquet':
        df = pd.read_parquet(sens_file)
    else:
        df = pd.read_csv(sens_file)
    
    categories = {
        'dhw': [], 'elec': [], 'equipment': [], 
        'fenez': [], 'hvac': [], 'vent': []
    }
    
    cat_mapping = {
        'dhw': 'dhw',
        'lighting': 'elec',
        'equipment': 'equipment',
        'geometry': 'fenez',
        'shading': 'fenez',
        'ventilation': 'vent',
        'materials': 'hvac',
        'hvac': 'hvac',
        'site_location': 'hvac',
        'simulation_control': 'hvac'
    }
    
    for _, row in df.iterrows():
        cat = cat_mapping.get(row.get('category', ''), 'hvac')
        
        # Parse parameter name
        param = str(row.get('parameter', ''))
        if '*' in param:
            parts = param.split('*')
            if len(parts) >= 4:
                param_name = f"{parts[2]}_{parts[3].replace(' ', '_')}"
            else:
                param_name = param.replace('*', '_')
        else:
            param_name = param.replace(' ', '_')
        
        param_data = {
            'param_name': param_name,
            'param_value': float(row.get('current_value', 0)),
            'param_min': float(row.get('min_value', 0)),
            'param_max': float(row.get('max_value', 1))
        }
        
        # Fix bounds
        if param_data['param_min'] > param_data['param_max']:
            param_data['param_min'], param_data['param_max'] = param_data['param_max'], param_data['param_min']
        
        categories[cat].append(param_data)
    
    # Write files
    for cat_name, params in categories.items():
        if params:
            pd.DataFrame(params).to_csv(scenario_dir / f"scenario_params_{cat_name}.csv", index=False)
            logger.info(f"Created scenario_params_{cat_name}.csv with {len(params)} parameters")


def create_scenarios_from_matrix(matrix_file: Path, scenario_dir: Path):
    """Create scenarios from parameter matrix"""
    df = pd.read_parquet(matrix_file)
    
    # Group columns by category
    categories = {
        'dhw': [], 'elec': [], 'equipment': [], 
        'fenez': [], 'hvac': [], 'vent': []
    }
    
    for col in df.columns:
        if col in ['variant_id', 'building_id']:
            continue
        
        col_lower = col.lower()
        if 'dhw' in col_lower or 'water' in col_lower:
            cat = 'dhw'
        elif 'light' in col_lower:
            cat = 'elec'
        elif 'equipment' in col_lower:
            cat = 'equipment'
        elif 'window' in col_lower or 'shading' in col_lower:
            cat = 'fenez'
        elif 'vent' in col_lower or 'outdoor' in col_lower:
            cat = 'vent'
        else:
            cat = 'hvac'
        
        if df[col].dtype in ['float64', 'int64']:
            param_data = {
                'param_name': col,
                'param_value': df[col].mean(),
                'param_min': df[col].min(),
                'param_max': df[col].max()
            }
            categories[cat].append(param_data)
    
    # Write files
    for cat_name, params in categories.items():
        if params:
            pd.DataFrame(params).to_csv(scenario_dir / f"scenario_params_{cat_name}.csv", index=False)


def create_scenarios_from_modifications(mods_file: Path, scenario_dir: Path):
    """Create scenarios from modifications file"""
    if mods_file.suffix == '.json':
        with open(mods_file, 'r') as f:
            mods = json.load(f)
        
        # Process JSON format
        categories = {
            'dhw': [], 'elec': [], 'equipment': [], 
            'fenez': [], 'hvac': [], 'vent': []
        }
        
        for param_key, param_info in mods.items():
            # Determine category
            param_lower = param_key.lower()
            if 'dhw' in param_lower or 'water' in param_lower:
                cat = 'dhw'
            elif 'light' in param_lower:
                cat = 'elec'
            elif 'equipment' in param_lower:
                cat = 'equipment'
            elif 'window' in param_lower or 'shading' in param_lower:
                cat = 'fenez'
            elif 'vent' in param_lower:
                cat = 'vent'
            else:
                cat = 'hvac'
            
            # Extract values
            values = []
            for change in param_info.get('changes', []):
                if 'new_value' in change:
                    try:
                        values.append(float(change['new_value']))
                    except:
                        pass
            
            if values:
                param_data = {
                    'param_name': param_key.replace(' ', '_'),
                    'param_value': np.mean(values),
                    'param_min': min(values) * 0.8,
                    'param_max': max(values) * 1.2
                }
                categories[cat].append(param_data)
    else:
        # Process parquet format
        df = pd.read_parquet(mods_file)
        # Similar logic for parquet...
    
    # Write files
    for cat_name, params in categories.items():
        if params:
            pd.DataFrame(params).to_csv(scenario_dir / f"scenario_params_{cat_name}.csv", index=False)


def create_default_scenarios(scenario_dir: Path):
    """Create minimal default scenarios"""
    defaults = {
        'dhw': [{'param_name': 'heater_efficiency', 'param_value': 0.8, 'param_min': 0.6, 'param_max': 0.95}],
        'elec': [{'param_name': 'lighting_power', 'param_value': 10, 'param_min': 5, 'param_max': 20}],
        'equipment': [{'param_name': 'equipment_power', 'param_value': 10, 'param_min': 5, 'param_max': 20}],
        'fenez': [{'param_name': 'window_area', 'param_value': 1, 'param_min': 0.5, 'param_max': 2}],
        'hvac': [{'param_name': 'system_cop', 'param_value': 3, 'param_min': 2, 'param_max': 4}],
        'vent': [{'param_name': 'air_flow', 'param_value': 0.01, 'param_min': 0.005, 'param_max': 0.02}]
    }
    
    for cat_name, params in defaults.items():
        pd.DataFrame(params).to_csv(scenario_dir / f"scenario_params_{cat_name}.csv", index=False)


def create_real_data_from_measured_file(measured_file: Path, output_path: Path):
    """Create real data CSV from standard measured data file"""
    logger.info(f"Using existing measured data: {measured_file}")
    # Convert to calibration format
    df = pd.read_csv(measured_file)
    
    # Group by month and aggregate
    df['Month'] = pd.to_datetime(df['DateTime']).dt.month
    
    # Create wide format for calibration
    result_data = {'BuildingID': [], 'VariableName': []}
    
    for month in range(1, 13):
        result_data[f'Month_{month}'] = []
    
    # Process each variable
    for var in df['Variable'].unique():
        var_data = df[df['Variable'] == var]
        
        # Map variable names
        if 'Electricity' in var:
            var_name = 'electricity:facility'
        elif 'Heating' in var:
            var_name = 'heating:energy'
        elif 'Cooling' in var:
            var_name = 'cooling:energy'
        else:
            continue
        
        result_data['BuildingID'].append(4136733)
        result_data['VariableName'].append(var_name)
        
        for month in range(1, 13):
            month_data = var_data[var_data['Month'] == month]
            if not month_data.empty:
                # Sum daily values for monthly total
                monthly_sum = month_data['Value'].sum()
                # Convert from J to kWh
                monthly_kwh = monthly_sum / 3.6e6
                result_data[f'Month_{month}'].append(monthly_kwh)
            else:
                result_data[f'Month_{month}'].append(0)
    
    pd.DataFrame(result_data).to_csv(output_path, index=False)
    logger.info(f"Created real data from measured data file")


def create_real_data_from_validation(val_file: Path, output_path: Path):
    """Create real data CSV from validation results"""
    # Try parquet validation results
    df = pd.read_parquet(val_file)
    
    # Convert to expected format
    if 'real_value' in df.columns and 'building_id' in df.columns:
        # Reshape data
        real_data = []
        for bid in df['building_id'].unique():
            building_data = df[df['building_id'] == bid]
            for idx, row in building_data.iterrows():
                real_data.append({
                    'BuildingID': bid,
                    'VariableName': 'electricity:facility',
                    f'Month_{idx+1}': row['real_value']
                })
        
        if real_data:
            result_df = pd.DataFrame(real_data)
            # Pivot to wide format
            result_df = result_df.pivot(index='BuildingID', columns='VariableName')
            result_df.to_csv(output_path)
            logger.info(f"Created real data from validation results")
    else:
        create_synthetic_real_data(output_path)


def create_real_data_from_timeseries(ts_file: Path, output_path: Path):
    """Create real data from timeseries"""
    df = pd.read_parquet(ts_file)
    
    # Use the timeseries data as "real" data for calibration
    # This is useful when you want to calibrate to match previous simulation results
    df.to_csv(output_path)
    logger.info("Created real data from timeseries")


def create_synthetic_real_data(output_path: Path):
    """Create synthetic real data for testing"""
    data = {
        'BuildingID': [4136733],
        'VariableName': ['electricity:facility'],
        'Month_1': [50000], 'Month_2': [48000], 'Month_3': [52000],
        'Month_4': [45000], 'Month_5': [40000], 'Month_6': [38000],
        'Month_7': [42000], 'Month_8': [44000], 'Month_9': [41000],
        'Month_10': [46000], 'Month_11': [49000], 'Month_12': [51000]
    }
    pd.DataFrame(data).to_csv(output_path, index=False)
    logger.info("Created synthetic real data")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        job_dir = sys.argv[1]
    else:
        # Use the latest job directory
        job_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09"
    
    prepare_calibration_data(job_dir)