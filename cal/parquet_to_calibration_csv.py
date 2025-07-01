"""
Utility to convert parquet data files to CSV format expected by calibration system
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


def convert_parquet_to_calibration_csv(
    parquet_file: str,
    output_csv: str,
    variable_mapping: Optional[Dict[str, str]] = None,
    time_aggregation: str = 'sum'
) -> bool:
    """
    Convert parquet data to CSV format expected by calibration system
    
    Args:
        parquet_file: Path to input parquet file
        output_csv: Path to output CSV file
        variable_mapping: Optional mapping of variable names
        time_aggregation: How to aggregate time data ('sum', 'mean')
        
    Returns:
        bool: True if successful
    """
    try:
        # Load parquet data
        df = pd.read_parquet(parquet_file)
        logger.info(f"Loaded {len(df)} rows from {parquet_file}")
        
        # Standardize column names
        if 'building_id' in df.columns:
            df = df.rename(columns={'building_id': 'BuildingID'})
        
        # Handle different formats
        if 'DateTime' in df.columns and 'Variable' in df.columns and 'Value' in df.columns:
            # Long format with DateTime, Variable, Value
            result_df = convert_long_format(df, variable_mapping, time_aggregation)
            
        elif 'VariableName' in df.columns:
            # Already in expected format
            result_df = df
            
        else:
            # Wide format - pivot to expected format
            result_df = convert_wide_format(df, variable_mapping)
        
        # Save to CSV
        result_df.to_csv(output_csv, index=False)
        logger.info(f"Saved calibration data to {output_csv}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error converting parquet to CSV: {e}")
        return False


def convert_long_format(
    df: pd.DataFrame, 
    variable_mapping: Optional[Dict[str, str]] = None,
    time_aggregation: str = 'sum'
) -> pd.DataFrame:
    """Convert long format data to calibration format"""
    
    # Apply variable mapping if provided
    if variable_mapping:
        df['Variable'] = df['Variable'].map(lambda x: variable_mapping.get(x, x))
    
    # Convert EnergyPlus variable names
    variable_name_map = {
        'Total Electricity': 'Electricity:Facility [J](Hourly)',
        'Heating Energy': 'Heating:EnergyTransfer [J](Hourly)',
        'Cooling Energy': 'Cooling:EnergyTransfer [J](Hourly)',
        'Indoor Temperature': 'Zone Mean Air Temperature [C](Hourly)',
        'Gas': 'NaturalGas:Facility [J](Hourly)',
        'Water': 'Water Heater Heating Energy [J](Hourly)'
    }
    
    df['VariableName'] = df['Variable'].map(lambda x: variable_name_map.get(x, x))
    
    # Convert units if needed (kWh to J)
    if 'Units' in df.columns:
        kwh_mask = df['Units'] == 'kWh'
        df.loc[kwh_mask, 'Value'] = df.loc[kwh_mask, 'Value'] * 3.6e6  # kWh to J
    
    # Parse DateTime if string
    if df['DateTime'].dtype == 'object':
        df['DateTime'] = pd.to_datetime(df['DateTime'])
    
    # Create time columns
    df['Hour'] = df['DateTime'].dt.hour
    df['Day'] = df['DateTime'].dt.day
    df['Month'] = df['DateTime'].dt.month
    
    # Pivot to wide format with time columns
    result_dfs = []
    
    for (building_id, var_name), group in df.groupby(['BuildingID', 'VariableName']):
        # Create hourly columns for each day
        pivot_data = {'BuildingID': building_id, 'VariableName': var_name}
        
        # Group by date and hour
        for _, row in group.iterrows():
            col_name = f"{row['Month']:02d}/{row['Day']:02d} {row['Hour']:02d}:00:00"
            pivot_data[col_name] = row['Value']
        
        result_dfs.append(pivot_data)
    
    # Combine all results
    result_df = pd.DataFrame(result_dfs)
    
    # Fill missing values with 0
    time_cols = [col for col in result_df.columns if col not in ['BuildingID', 'VariableName']]
    result_df[time_cols] = result_df[time_cols].fillna(0)
    
    return result_df


def convert_wide_format(
    df: pd.DataFrame,
    variable_mapping: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Convert wide format data to calibration format"""
    
    # Melt wide format to long format
    id_vars = ['BuildingID'] if 'BuildingID' in df.columns else []
    value_vars = [col for col in df.columns if col not in id_vars]
    
    melted = df.melt(id_vars=id_vars, value_vars=value_vars, 
                     var_name='VariableName', value_name='Value')
    
    # Apply variable mapping if provided
    if variable_mapping:
        melted['VariableName'] = melted['VariableName'].map(
            lambda x: variable_mapping.get(x, x)
        )
    
    return melted


def convert_parameter_matrix_to_scenario_csv(
    parquet_file: str,
    output_dir: str,
    param_mapping: Optional[Dict[str, str]] = None
) -> bool:
    """
    Convert parameter matrix parquet to scenario CSV files
    
    Args:
        parquet_file: Path to parameter_matrix.parquet
        output_dir: Output directory for scenario CSV files
        param_mapping: Optional parameter name mapping
        
    Returns:
        bool: True if successful
    """
    try:
        # Load parameter matrix
        df = pd.read_parquet(parquet_file)
        logger.info(f"Loaded parameter matrix with {len(df)} buildings")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Parameter categories
        param_categories = {
            'dhw': ['dhw_tank_volume', 'dhw_heater_maximum_capacity'],
            'elec': ['lighting_watts_per_zone_floor_area'],
            'equipment': ['equipment_watts_per_zone_floor_area'],
            'fenez': [],  # No window parameters in this example
            'hvac': [],   # No HVAC parameters in this example
            'vent': ['ventilation_design_flow_rate', 'infiltration_design_flow_rate']
        }
        
        # Generate scenario CSV files
        for category, params in param_categories.items():
            scenario_data = []
            
            for param in params:
                if param in df.columns:
                    # Calculate statistics across buildings
                    param_name = param_mapping.get(param, param) if param_mapping else param
                    
                    scenario_data.append({
                        'param_name': param_name,
                        'param_value': df[param].mean(),
                        'param_min': df[param].min(),
                        'param_max': df[param].max()
                    })
            
            # Save scenario CSV
            if scenario_data:
                scenario_df = pd.DataFrame(scenario_data)
                output_file = output_path / f"scenario_params_{category}.csv"
                scenario_df.to_csv(output_file, index=False)
                logger.info(f"Created {output_file}")
            else:
                # Create empty file with headers
                empty_df = pd.DataFrame(columns=['param_name', 'param_value', 'param_min', 'param_max'])
                output_file = output_path / f"scenario_params_{category}.csv"
                empty_df.to_csv(output_file, index=False)
                logger.info(f"Created empty {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error converting parameter matrix: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Convert validation data
    convert_parquet_to_calibration_csv(
        parquet_file="data/test_validation_data/measured_data_simple.parquet",
        output_csv="data/calibration_real_data.csv"
    )
    
    # Convert parameter matrix to scenario files
    convert_parameter_matrix_to_scenario_csv(
        parquet_file="_output_example/6f912613-913d-40ea-ba14-eff7e6dc097f/parsed_data/analysis_ready/parameter_matrix.parquet",
        output_dir="output/scenarios"
    )