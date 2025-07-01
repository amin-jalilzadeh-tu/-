"""
Updated unified calibration to read directly from modifications parquet files
Replaces the old CSV-based approach
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def load_scenario_from_parquet(output_dir: Path) -> pd.DataFrame:
    """
    Load scenario parameters directly from modifications parquet file
    
    Args:
        output_dir: Path to output directory
        
    Returns:
        DataFrame with parameters in calibration format
    """
    # Find modifications parquet file
    mod_files = list((output_dir / "modified_idfs").glob("modifications_detail_wide_*.parquet"))
    if not mod_files:
        raise FileNotFoundError(f"No modifications_detail_wide parquet file found in {output_dir}")
    
    # Load modifications data
    mods_df = pd.read_parquet(mod_files[0])
    logger.info(f"Loaded {len(mods_df)} parameters from {mod_files[0].name}")
    
    # Get variant columns to determine bounds
    variant_cols = [col for col in mods_df.columns if col.startswith('variant_')]
    
    # Convert to calibration format
    parameters = []
    for idx, row in mods_df.iterrows():
        # Create parameter name in expected format
        param_name = f"{row['category']}*{row['object_type']}*{row['object_name']}*{row['field']}"
        
        # Get variant values
        variant_values = []
        for col in variant_cols:
            val = row[col]
            if pd.notna(val):
                try:
                    variant_values.append(float(val))
                except (ValueError, TypeError):
                    continue
        
        if not variant_values:
            continue
        
        # Calculate bounds from actual variant values
        min_val = min(variant_values)
        max_val = max(variant_values)
        
        # Get current/baseline value
        try:
            current_val = float(row['original'])
        except (ValueError, TypeError):
            current_val = np.mean(variant_values)
        
        parameters.append({
            'param_name': param_name,
            'param_value': current_val,
            'param_min': min_val,
            'param_max': max_val,
            'category': row['category'],
            'source_file': f"scenario_params_{row['category']}.csv"  # Add expected source_file
        })
    
    return pd.DataFrame(parameters)


def load_scenario_csvs_replacement(scenario_folder, scenario_files: List[str] = None) -> pd.DataFrame:
    """
    Replacement for load_scenario_csvs that uses parquet files
    
    Args:
        scenario_folder: Path to scenario folder (will look in parent for modified_idfs)
        scenario_files: Ignored, kept for compatibility
        
    Returns:
        DataFrame with all scenario parameters
    """
    # Convert to Path if string
    scenario_folder = Path(scenario_folder)
    
    # Go up one level to find output directory
    output_dir = scenario_folder.parent
    
    # Try new parquet approach first
    try:
        df_scenario = load_scenario_from_parquet(output_dir)
        logger.info(f"Loaded {len(df_scenario)} parameters from parquet file")
        return df_scenario
    except FileNotFoundError:
        # Fall back to old CSV approach if parquet not found
        logger.warning("No parquet file found, falling back to CSV approach")
        
        # Original CSV loading code
        if scenario_files is None:
            scenario_files = ['scenario_params_dhw.csv', 'scenario_params_elec.csv', 
                            'scenario_params_equipment.csv', 'scenario_params_fenez.csv', 
                            'scenario_params_hvac.csv', 'scenario_params_vent.csv']
        
        all_dfs = []
        for csv_file in scenario_files:
            csv_path = scenario_folder / csv_file
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                all_dfs.append(df)
                logger.info(f"Loaded {len(df)} rows from {csv_file}")
        
        if not all_dfs:
            raise FileNotFoundError(f"No scenario files found in {scenario_folder}")
        
        return pd.concat(all_dfs, ignore_index=True)


# Monkey patch to replace the original function
def patch_unified_calibration():
    """Patch the unified calibration module to use parquet loading"""
    import cal.unified_calibration as uc
    
    # Store original function
    if not hasattr(uc, '_original_load_scenario_csvs'):
        uc._original_load_scenario_csvs = uc.load_scenario_csvs
    
    # Replace with our version
    uc.load_scenario_csvs = load_scenario_csvs_replacement
    logger.info("Patched unified_calibration to use parquet files")


def get_sensitivity_metadata(output_dir: Path) -> Optional[pd.DataFrame]:
    """
    Load sensitivity metadata if available
    
    Args:
        output_dir: Path to output directory
        
    Returns:
        DataFrame with sensitivity scores and priorities
    """
    sensitivity_path = output_dir / "sensitivity_results" / "sensitivity_parameters.csv"
    if sensitivity_path.exists():
        return pd.read_csv(sensitivity_path)
    return None


def filter_parameters_by_priority(df_scenario: pd.DataFrame, output_dir: Path, 
                                priority: str = "high") -> pd.DataFrame:
    """
    Filter parameters by calibration priority
    
    Args:
        df_scenario: Full parameter DataFrame
        output_dir: Output directory path
        priority: Priority level (high, medium, low, surrogate)
        
    Returns:
        Filtered DataFrame
    """
    sensitivity_df = get_sensitivity_metadata(output_dir)
    if sensitivity_df is None:
        logger.warning("No sensitivity metadata found, using all parameters")
        return df_scenario
    
    if priority == "surrogate":
        # Get surrogate-enabled parameters
        surrogate_params = sensitivity_df[sensitivity_df['surrogate_include'] == True]['parameter'].tolist()
    else:
        # Get parameters by priority
        surrogate_params = sensitivity_df[sensitivity_df['calibration_priority'] == priority]['parameter'].tolist()
    
    # Filter scenario parameters
    filtered = df_scenario[df_scenario['param_name'].isin(surrogate_params)]
    logger.info(f"Filtered to {len(filtered)} {priority} priority parameters")
    
    return filtered


if __name__ == "__main__":
    # Test the parquet loading
    output_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb")
    
    # Test direct loading
    df = load_scenario_from_parquet(output_dir)
    print(f"Loaded {len(df)} parameters")
    print(f"Categories: {df['category'].unique()}")
    print(f"\nFirst 5 parameters:")
    print(df[['param_name', 'param_value', 'param_min', 'param_max']].head())