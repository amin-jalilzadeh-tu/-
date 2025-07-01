"""
Auto-generate scenario CSV files when missing
This can be imported and used by the calibration system
"""

import pandas as pd
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def ensure_scenario_files(scenario_folder: Path) -> bool:
    """
    Ensure scenario CSV files exist, generating them if needed
    
    Args:
        scenario_folder: Path to scenarios directory
        
    Returns:
        bool: True if files exist or were created
    """
    required_files = [
        'scenario_params_dhw.csv',
        'scenario_params_elec.csv',
        'scenario_params_equipment.csv',
        'scenario_params_fenez.csv',
        'scenario_params_hvac.csv',
        'scenario_params_vent.csv'
    ]
    
    # Check if all files exist
    if all((scenario_folder / f).exists() for f in required_files):
        return True
    
    # Create directory if needed
    scenario_folder.mkdir(parents=True, exist_ok=True)
    
    # Get job directory (parent of scenarios)
    job_dir = scenario_folder.parent
    
    # Try to generate from available data
    if generate_from_job_data(job_dir, scenario_folder):
        logger.info(f"Generated scenario files in {scenario_folder}")
        return True
    
    # Generate minimal defaults
    logger.warning("Generating minimal default scenario files")
    return generate_minimal_defaults(scenario_folder)


def generate_from_job_data(job_dir: Path, scenario_folder: Path) -> bool:
    """Try to generate scenario files from job data"""
    
    # Look for sensitivity results first
    sens_file = job_dir / "sensitivity_results" / "sensitivity_parameters.csv"
    if sens_file.exists():
        return generate_from_sensitivity_data(sens_file, scenario_folder)
    
    # Look for any parameter files
    for param_file in job_dir.glob("**/param*.csv"):
        if generate_from_param_file(param_file, scenario_folder):
            return True
    
    return False


def generate_from_sensitivity_data(sens_file: Path, scenario_folder: Path) -> bool:
    """Generate from sensitivity parameters CSV"""
    try:
        df = pd.read_csv(sens_file)
        
        categories = {
            'dhw': [],
            'elec': [],
            'equipment': [],
            'fenez': [],
            'hvac': [],
            'vent': []
        }
        
        # Category mapping
        cat_map = {
            'dhw': 'dhw',
            'lighting': 'elec',
            'equipment': 'equipment',
            'geometry': 'fenez',
            'shading': 'fenez',
            'ventilation': 'vent',
            'materials': 'hvac',
            'hvac': 'hvac',
            'site_location': 'hvac'
        }
        
        for _, row in df.iterrows():
            cat = cat_map.get(row.get('category', '').lower(), 'hvac')
            
            # Extract parameter name
            param_str = str(row.get('parameter', ''))
            if '*' in param_str:
                parts = param_str.split('*')
                param_name = f"{parts[2]}_{parts[3]}" if len(parts) >= 4 else param_str
            else:
                param_name = param_str
            
            param_name = param_name.replace(' ', '_').replace(':', '_')
            
            param_data = {
                'param_name': param_name,
                'param_value': float(row.get('current_value', 0)),
                'param_min': float(row.get('min_value', 0)),
                'param_max': float(row.get('max_value', 1))
            }
            
            # Fix inverted bounds
            if param_data['param_min'] > param_data['param_max']:
                param_data['param_min'], param_data['param_max'] = param_data['param_max'], param_data['param_min']
            
            categories[cat].append(param_data)
        
        # Write all category files
        for cat_name in ['dhw', 'elec', 'equipment', 'fenez', 'hvac', 'vent']:
            params = categories.get(cat_name, [])
            if not params:
                # Add at least one default parameter
                params = [get_default_param(cat_name)]
            
            pd.DataFrame(params).to_csv(
                scenario_folder / f"scenario_params_{cat_name}.csv", 
                index=False
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating from sensitivity: {e}")
        return False


def generate_from_param_file(param_file: Path, scenario_folder: Path) -> bool:
    """Try to generate from a parameter file"""
    try:
        df = pd.read_csv(param_file)
        
        # Check if it has the right columns
        if not all(col in df.columns for col in ['param_name', 'param_value']):
            return False
        
        # Add min/max if missing
        if 'param_min' not in df.columns:
            df['param_min'] = df['param_value'] * 0.8
        if 'param_max' not in df.columns:
            df['param_max'] = df['param_value'] * 1.2
        
        # Save to all category files (simple approach)
        for cat in ['dhw', 'elec', 'equipment', 'fenez', 'hvac', 'vent']:
            df.to_csv(scenario_folder / f"scenario_params_{cat}.csv", index=False)
        
        return True
        
    except:
        return False


def generate_minimal_defaults(scenario_folder: Path) -> bool:
    """Generate minimal default files"""
    try:
        for cat in ['dhw', 'elec', 'equipment', 'fenez', 'hvac', 'vent']:
            params = [get_default_param(cat)]
            pd.DataFrame(params).to_csv(
                scenario_folder / f"scenario_params_{cat}.csv",
                index=False
            )
        return True
    except:
        return False


def get_default_param(category: str) -> dict:
    """Get a default parameter for a category"""
    defaults = {
        'dhw': {'param_name': 'WaterHeater_Efficiency', 'param_value': 0.8, 'param_min': 0.6, 'param_max': 0.95},
        'elec': {'param_name': 'Lights_Power', 'param_value': 10.0, 'param_min': 5.0, 'param_max': 20.0},
        'equipment': {'param_name': 'Equipment_Power', 'param_value': 10.0, 'param_min': 5.0, 'param_max': 20.0},
        'fenez': {'param_name': 'Window_Area', 'param_value': 1.0, 'param_min': 0.5, 'param_max': 2.0},
        'hvac': {'param_name': 'System_Efficiency', 'param_value': 0.8, 'param_min': 0.6, 'param_max': 0.95},
        'vent': {'param_name': 'Air_Flow_Rate', 'param_value': 0.01, 'param_min': 0.005, 'param_max': 0.02}
    }
    return defaults.get(category, defaults['hvac'])