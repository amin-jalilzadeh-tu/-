"""
Generate scenario CSV files for calibration from existing sensitivity/modification data
"""

import pandas as pd
import json
from pathlib import Path
import sys

def generate_scenario_csvs(output_dir: str):
    """
    Generate scenario parameter CSV files required by the calibration system
    
    Expected format:
    param_name, param_value, param_min, param_max
    """
    
    output_path = Path(output_dir)
    scenarios_dir = output_path / "scenarios"
    scenarios_dir.mkdir(exist_ok=True)
    
    print(f"Creating scenario CSVs in: {scenarios_dir}")
    
    # Try to load sensitivity parameters first (has min/max values)
    sensitivity_file = output_path / "sensitivity_results" / "sensitivity_parameters.csv"
    if sensitivity_file.exists():
        print(f"Loading sensitivity parameters from: {sensitivity_file}")
        sens_df = pd.read_csv(sensitivity_file)
        
        # Group by category
        categories = {
            'dhw': [],
            'elec': [],  # Note: 'elec' not 'lighting' 
            'equipment': [],
            'fenez': [],  # fenestration/geometry
            'hvac': [],
            'vent': []  # ventilation
        }
        
        # Map sensitivity categories to scenario categories
        category_mapping = {
            'dhw': 'dhw',
            'lighting': 'elec',  # lighting maps to elec
            'equipment': 'equipment',
            'geometry': 'fenez',  # geometry maps to fenez (fenestration)
            'hvac': 'hvac',
            'ventilation': 'vent',
            'shading': 'fenez',  # shading also goes to fenez
            'materials': 'hvac',  # materials go to hvac
            'site_location': 'hvac',  # site params to hvac
        }
        
        for _, row in sens_df.iterrows():
            if row['category'] in category_mapping:
                scenario_cat = category_mapping[row['category']]
                
                # Create simplified parameter name
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
                
                # Ensure min < max
                if param_data['param_min'] > param_data['param_max']:
                    param_data['param_min'], param_data['param_max'] = param_data['param_max'], param_data['param_min']
                
                categories[scenario_cat].append(param_data)
        
        # Write CSV files
        for cat_name, params in categories.items():
            if params:  # Only write if there are parameters
                df = pd.DataFrame(params)
                csv_path = scenarios_dir / f"scenario_params_{cat_name}.csv"
                df.to_csv(csv_path, index=False)
                print(f"Created {csv_path.name} with {len(df)} parameters")
    
    else:
        # Fallback: Try to use modifications summary
        mods_file = output_path / "modifications_summary.json"
        if mods_file.exists():
            print(f"Using modifications summary as fallback")
            with open(mods_file, 'r') as f:
                mods = json.load(f)
            
            # Create basic scenario files from modifications
            categories = {
                'dhw': [],
                'elec': [],
                'equipment': [],
                'fenez': [],
                'hvac': [],
                'vent': []
            }
            
            # Simple mapping based on parameter names
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
                
                # Extract values from changes
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
                        'param_value': sum(values) / len(values),  # average
                        'param_min': min(values) * 0.8,
                        'param_max': max(values) * 1.2
                    }
                    categories[cat].append(param_data)
            
            # Write CSV files
            for cat_name, params in categories.items():
                if params:
                    df = pd.DataFrame(params)
                    csv_path = scenarios_dir / f"scenario_params_{cat_name}.csv"
                    df.to_csv(csv_path, index=False)
                    print(f"Created {csv_path.name} with {len(df)} parameters")
        
        else:
            # Create minimal scenario files with default parameters
            print("Creating default scenario files")
            
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
                csv_path = scenarios_dir / f"scenario_params_{cat_name}.csv"
                df.to_csv(csv_path, index=False)
                print(f"Created {csv_path.name} with {len(df)} parameters")
    
    print(f"\nScenario CSV files created successfully in: {scenarios_dir}")
    return scenarios_dir


if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        # Default to your directory
        output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99"
    
    generate_scenario_csvs(output_dir)
    
    # Also generate for the new directory mentioned in the error
    new_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/1d481a79-bf57-4d04-ab25-0c2121af7e3d"
    if Path(new_dir).exists():
        print(f"\nAlso generating for: {new_dir}")
        generate_scenario_csvs(new_dir)