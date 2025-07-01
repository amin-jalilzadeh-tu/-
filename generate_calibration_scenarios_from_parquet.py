"""
Generate calibration scenario files from modifications parquet data
This replaces the old scenario_params_*.csv approach with data from the actual modifications
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json


def generate_calibration_scenarios(output_dir: str):
    """
    Generate scenario parameter files from modifications parquet data
    
    Args:
        output_dir: Path to simulation output directory
    """
    output_path = Path(output_dir)
    
    # Find modifications parquet file
    mod_files = list(output_path.glob("modified_idfs/modifications_detail_wide_*.parquet"))
    if not mod_files:
        raise FileNotFoundError(f"No modifications_detail_wide parquet file found in {output_path}")
    
    # Load modifications data
    print(f"Loading modifications from {mod_files[0]}")
    mods_df = pd.read_parquet(mod_files[0])
    
    # Also load sensitivity parameters if available
    sensitivity_path = output_path / "sensitivity_results" / "sensitivity_parameters.csv"
    sensitivity_df = None
    if sensitivity_path.exists():
        print("Loading sensitivity parameters for additional metadata")
        sensitivity_df = pd.read_csv(sensitivity_path)
    
    # Create scenarios directory
    scenarios_dir = output_path / "calibration_scenarios"
    scenarios_dir.mkdir(exist_ok=True)
    
    # Get unique parameters
    parameters = []
    
    for idx, row in mods_df.iterrows():
        # Create parameter identifier
        param_id = f"{row['category']}*{row['object_type']}*{row['object_name']}*{row['field']}"
        
        # Get variant values (excluding original)
        variant_cols = [col for col in mods_df.columns if col.startswith('variant_')]
        variant_values = [row[col] for col in variant_cols if pd.notna(row[col])]
        
        if not variant_values:
            continue
            
        # Convert values to float where possible
        numeric_values = []
        for val in variant_values:
            try:
                numeric_values.append(float(val))
            except (ValueError, TypeError):
                # Skip non-numeric values
                continue
        
        if not numeric_values:
            continue
            
        # Calculate bounds from variant values
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        
        # Get current/original value
        try:
            current_val = float(row['original'])
        except (ValueError, TypeError):
            current_val = np.mean(numeric_values)
        
        # Get additional metadata from sensitivity if available
        sensitivity_score = 0.0
        calibration_priority = "medium"
        surrogate_include = False
        
        if sensitivity_df is not None:
            sens_match = sensitivity_df[sensitivity_df['parameter'] == param_id]
            if not sens_match.empty:
                sens_row = sens_match.iloc[0]
                sensitivity_score = sens_row.get('sensitivity_score', 0.0)
                calibration_priority = sens_row.get('calibration_priority', 'medium')
                surrogate_include = sens_row.get('surrogate_include', False)
        
        parameters.append({
            'param_name': param_id,
            'category': row['category'],
            'object_type': row['object_type'],
            'object_name': row['object_name'],
            'field': row['field'],
            'current_value': current_val,
            'min_value': min_val,
            'max_value': max_val,
            'n_variants': len(numeric_values),
            'variant_values': numeric_values,
            'sensitivity_score': sensitivity_score,
            'calibration_priority': calibration_priority,
            'surrogate_include': surrogate_include
        })
    
    # Create main scenario file
    main_df = pd.DataFrame(parameters)
    main_df = main_df.sort_values('sensitivity_score', ascending=False)
    
    # Save main scenario file
    main_file = scenarios_dir / "calibration_parameters_all.csv"
    main_df[['param_name', 'current_value', 'min_value', 'max_value', 
             'sensitivity_score', 'calibration_priority']].to_csv(main_file, index=False)
    print(f"Created main scenario file: {main_file}")
    
    # Create category-specific files
    categories = main_df['category'].unique()
    for category in categories:
        cat_df = main_df[main_df['category'] == category]
        cat_file = scenarios_dir / f"calibration_parameters_{category}.csv"
        cat_df[['param_name', 'current_value', 'min_value', 'max_value']].to_csv(cat_file, index=False)
        print(f"Created {category} scenario file with {len(cat_df)} parameters")
    
    # Create high-priority calibration file
    high_priority_df = main_df[main_df['calibration_priority'] == 'high']
    if not high_priority_df.empty:
        high_file = scenarios_dir / "calibration_parameters_high_priority.csv"
        high_priority_df[['param_name', 'current_value', 'min_value', 'max_value', 
                         'sensitivity_score']].to_csv(high_file, index=False)
        print(f"Created high priority file with {len(high_priority_df)} parameters")
    
    # Create surrogate-enabled parameters file
    surrogate_df = main_df[main_df['surrogate_include'] == True]
    if not surrogate_df.empty:
        surrogate_file = scenarios_dir / "calibration_parameters_surrogate.csv"
        surrogate_df[['param_name', 'current_value', 'min_value', 'max_value', 
                     'sensitivity_score']].to_csv(surrogate_file, index=False)
        print(f"Created surrogate parameters file with {len(surrogate_df)} parameters")
    
    # Create summary JSON
    summary = {
        'total_parameters': len(parameters),
        'categories': {cat: len(main_df[main_df['category'] == cat]) for cat in categories},
        'priority_counts': {
            'high': len(main_df[main_df['calibration_priority'] == 'high']),
            'medium': len(main_df[main_df['calibration_priority'] == 'medium']),
            'low': len(main_df[main_df['calibration_priority'] == 'low'])
        },
        'surrogate_enabled': len(main_df[main_df['surrogate_include'] == True]),
        'variants_analyzed': len(variant_cols),
        'source_file': str(mod_files[0].name)
    }
    
    with open(scenarios_dir / "calibration_scenarios_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSummary:")
    print(f"Total parameters: {summary['total_parameters']}")
    print(f"Categories: {summary['categories']}")
    print(f"Files created in: {scenarios_dir}")
    
    return scenarios_dir


if __name__ == "__main__":
    # Example usage
    output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb"
    generate_calibration_scenarios(output_dir)