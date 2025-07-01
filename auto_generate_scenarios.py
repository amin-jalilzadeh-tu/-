"""
Automatically generate scenario CSV files for any job directory
Can be integrated into the workflow or run as needed
"""

import pandas as pd
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def auto_generate_scenario_csvs(job_dir: Path) -> bool:
    """
    Automatically generate scenario CSV files from available data
    
    Returns:
        bool: True if files were generated successfully
    """
    scenarios_dir = job_dir / "scenarios"
    
    # Check if scenario files already exist
    required_files = [
        'scenario_params_dhw.csv',
        'scenario_params_elec.csv', 
        'scenario_params_equipment.csv',
        'scenario_params_fenez.csv',
        'scenario_params_hvac.csv',
        'scenario_params_vent.csv'
    ]
    
    if all((scenarios_dir / f).exists() for f in required_files):
        logger.info("Scenario files already exist")
        return True
    
    # Create scenarios directory
    scenarios_dir.mkdir(exist_ok=True)
    
    # Try multiple sources for parameter data
    generated = False
    
    # 1. Try sensitivity parameters (best source)
    sensitivity_file = job_dir / "sensitivity_results" / "sensitivity_parameters.csv"
    if sensitivity_file.exists():
        generated = generate_from_sensitivity(sensitivity_file, scenarios_dir)
    
    # 2. Try modifications summary
    if not generated:
        mods_file = job_dir / "modifications_summary.json"
        if mods_file.exists():
            generated = generate_from_modifications(mods_file, scenarios_dir)
    
    # 3. Try parsed IDF data
    if not generated:
        parsed_dir = job_dir / "parsed_data" / "idf_data" / "by_category"
        if parsed_dir.exists():
            generated = generate_from_parsed_idf(parsed_dir, scenarios_dir)
    
    # 4. Generate defaults as last resort
    if not generated:
        generated = generate_defaults(scenarios_dir)
    
    return generated


def generate_from_sensitivity(sensitivity_file: Path, scenarios_dir: Path) -> bool:
    """Generate from sensitivity analysis results"""
    try:
        sens_df = pd.read_csv(sensitivity_file)
        
        categories = {
            'dhw': [],
            'elec': [],
            'equipment': [],
            'fenez': [],
            'hvac': [],
            'vent': []
        }
        
        category_mapping = {
            'dhw': 'dhw',
            'lighting': 'elec',
            'equipment': 'equipment',
            'geometry': 'fenez',
            'hvac': 'hvac',
            'ventilation': 'vent',
            'shading': 'fenez',
            'materials': 'hvac',
            'site_location': 'hvac',
        }
        
        for _, row in sens_df.iterrows():
            if row['category'] in category_mapping:
                scenario_cat = category_mapping[row['category']]
                
                param_parts = row['parameter'].split('*')
                if len(param_parts) >= 4:
                    param_name = f"{param_parts[2]}_{param_parts[3].replace(' ', '_')}"
                else:
                    param_name = row['parameter'].replace('*', '_').replace(' ', '_')
                
                param_data = {
                    'param_name': param_name,
                    'param_value': float(row.get('current_value', 0)),
                    'param_min': float(row.get('min_value', -30)),
                    'param_max': float(row.get('max_value', 30))
                }
                
                if param_data['param_min'] > param_data['param_max']:
                    param_data['param_min'], param_data['param_max'] = param_data['param_max'], param_data['param_min']
                
                categories[scenario_cat].append(param_data)
        
        # Write files
        for cat_name, params in categories.items():
            if params:
                df = pd.DataFrame(params)
                df.to_csv(scenarios_dir / f"scenario_params_{cat_name}.csv", index=False)
            else:
                # Create empty file with headers
                pd.DataFrame(columns=['param_name', 'param_value', 'param_min', 'param_max']).to_csv(
                    scenarios_dir / f"scenario_params_{cat_name}.csv", index=False
                )
        
        return True
    except Exception as e:
        logger.error(f"Failed to generate from sensitivity: {e}")
        return False


def generate_from_modifications(mods_file: Path, scenarios_dir: Path) -> bool:
    """Generate from modifications summary"""
    try:
        with open(mods_file, 'r') as f:
            mods = json.load(f)
        
        categories = {
            'dhw': [],
            'elec': [],
            'equipment': [],
            'fenez': [],
            'hvac': [],
            'vent': []
        }
        
        for param_key, param_info in mods.items():
            param_lower = param_key.lower()
            
            if 'dhw' in param_lower or 'water' in param_lower:
                cat = 'dhw'
            elif 'light' in param_lower or 'elec' in param_lower:
                cat = 'elec'
            elif 'equipment' in param_lower:
                cat = 'equipment'
            elif 'window' in param_lower or 'geometry' in param_lower or 'shading' in param_lower:
                cat = 'fenez'
            elif 'vent' in param_lower or 'outdoor' in param_lower:
                cat = 'vent'
            else:
                cat = 'hvac'
            
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
                    'param_value': sum(values) / len(values),
                    'param_min': min(values) * 0.8,
                    'param_max': max(values) * 1.2
                }
                categories[cat].append(param_data)
        
        for cat_name, params in categories.items():
            if params:
                df = pd.DataFrame(params)
                df.to_csv(scenarios_dir / f"scenario_params_{cat_name}.csv", index=False)
            else:
                pd.DataFrame(columns=['param_name', 'param_value', 'param_min', 'param_max']).to_csv(
                    scenarios_dir / f"scenario_params_{cat_name}.csv", index=False
                )
        
        return True
    except Exception as e:
        logger.error(f"Failed to generate from modifications: {e}")
        return False


def generate_from_parsed_idf(parsed_dir: Path, scenarios_dir: Path) -> bool:
    """Generate from parsed IDF data"""
    try:
        categories = {
            'dhw': [],
            'elec': [],
            'equipment': [],
            'fenez': [],
            'hvac': [],
            'vent': []
        }
        
        # Map IDF files to categories
        file_mapping = {
            'dhw.parquet': 'dhw',
            'lighting.parquet': 'elec',
            'equipment.parquet': 'equipment',
            'geometry_surfaces.parquet': 'fenez',
            'hvac_equipment.parquet': 'hvac',
            'ventilation.parquet': 'vent'
        }
        
        for file_name, cat in file_mapping.items():
            file_path = parsed_dir / file_name
            if file_path.exists():
                df = pd.read_parquet(file_path)
                
                # Extract numeric columns as parameters
                numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                for col in numeric_cols[:5]:  # Limit to 5 params per category
                    if df[col].nunique() > 1:  # Only if values vary
                        param_data = {
                            'param_name': col.replace(' ', '_'),
                            'param_value': df[col].mean(),
                            'param_min': df[col].min(),
                            'param_max': df[col].max()
                        }
                        categories[cat].append(param_data)
        
        for cat_name, params in categories.items():
            if params:
                df = pd.DataFrame(params)
                df.to_csv(scenarios_dir / f"scenario_params_{cat_name}.csv", index=False)
            else:
                pd.DataFrame(columns=['param_name', 'param_value', 'param_min', 'param_max']).to_csv(
                    scenarios_dir / f"scenario_params_{cat_name}.csv", index=False
                )
        
        return True
    except Exception as e:
        logger.error(f"Failed to generate from parsed IDF: {e}")
        return False


def generate_defaults(scenarios_dir: Path) -> bool:
    """Generate default scenario files"""
    try:
        default_params = {
            'dhw': [
                {'param_name': 'WaterHeater_Efficiency', 'param_value': 0.8, 'param_min': 0.6, 'param_max': 0.95},
                {'param_name': 'WaterHeater_Loss_Coefficient', 'param_value': 6.0, 'param_min': 2.0, 'param_max': 10.0}
            ],
            'elec': [
                {'param_name': 'Lights_Fraction_Radiant', 'param_value': 0.7, 'param_min': 0.5, 'param_max': 0.9},
                {'param_name': 'Lights_Watts_per_Zone', 'param_value': 10.0, 'param_min': 5.0, 'param_max': 20.0}
            ],
            'equipment': [
                {'param_name': 'Equipment_Level', 'param_value': 10.0, 'param_min': 5.0, 'param_max': 20.0}
            ],
            'fenez': [
                {'param_name': 'Window_Multiplier', 'param_value': 1.0, 'param_min': 0.5, 'param_max': 2.0},
                {'param_name': 'Shading_Setpoint', 'param_value': 20.0, 'param_min': 10.0, 'param_max': 30.0}
            ],
            'hvac': [
                {'param_name': 'Cooling_COP', 'param_value': 3.0, 'param_min': 2.0, 'param_max': 4.0},
                {'param_name': 'Heating_Efficiency', 'param_value': 0.8, 'param_min': 0.6, 'param_max': 0.95}
            ],
            'vent': [
                {'param_name': 'Outdoor_Air_Flow_Rate', 'param_value': 0.01, 'param_min': 0.005, 'param_max': 0.02}
            ]
        }
        
        for cat_name, params in default_params.items():
            df = pd.DataFrame(params)
            df.to_csv(scenarios_dir / f"scenario_params_{cat_name}.csv", index=False)
        
        return True
    except Exception as e:
        logger.error(f"Failed to generate defaults: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        job_dir = Path(sys.argv[1])
    else:
        # Try the latest directory
        job_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09")
    
    if job_dir.exists():
        success = auto_generate_scenario_csvs(job_dir)
        if success:
            print(f"✓ Successfully generated scenario files for: {job_dir}")
        else:
            print(f"✗ Failed to generate scenario files for: {job_dir}")
    else:
        print(f"Directory not found: {job_dir}")