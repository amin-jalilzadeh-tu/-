"""
Calibration data loader that handles output_matrix.csv format
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def load_calibration_output_matrix(file_path: str) -> pd.DataFrame:
    """
    Load output_matrix.csv and convert to calibration format
    
    The output_matrix has columns: variant_id, variant_name, Month, Cooling:EnergyTransfer, Heating:EnergyTransfer
    We need to convert this to: BuildingID, VariableName, date columns
    """
    logger.info(f"Loading calibration data from {file_path}")
    
    df = pd.read_csv(file_path)
    logger.info(f"Loaded shape: {df.shape}, columns: {list(df.columns)}")
    
    # For calibration, we'll use variant 0 as "measured" data
    variant_0 = df[df['variant_id'] == 0].copy()
    
    # Get output variables (exclude metadata)
    output_vars = [col for col in df.columns 
                  if col not in ['variant_id', 'variant_name', 'Month']]
    
    # Convert to calibration format
    result_rows = []
    
    for var in output_vars:
        row = {
            'BuildingID': 4136733,  # Use the building ID we know
            'VariableName': f"{var} [J](Monthly)"
        }
        
        # Add monthly values
        for _, month_data in variant_0.iterrows():
            month = int(month_data['Month'])
            # Use MM/01 format for dates
            date_col = f"{month:02d}/01"
            row[date_col] = month_data[var]
        
        result_rows.append(row)
    
    result_df = pd.DataFrame(result_rows)
    logger.info(f"Converted to calibration format: {result_df.shape}")
    
    return result_df

def patch_calibration_data_loading():
    """Patch the calibration system to handle our data format"""
    
    import cal.unified_calibration as uc
    
    # Store original
    if not hasattr(uc, '_original_load_real_data_once'):
        uc._original_load_real_data_once = uc.load_real_data_once
    
    def load_real_data_once_patched(real_data_path: str, time_aggregation: str = 'sum'):
        """Patched version that handles different data formats"""
        
        logger.info(f"Loading real data from: {real_data_path}")
        df = pd.read_csv(real_data_path)
        
        # Check format and convert as needed
        if 'building_id' in df.columns and 'Variable' in df.columns:
            # This is the parsed format - need to pivot to wide format
            logger.info("Converting parsed format to calibration format")
            
            # Get unique variables
            variables = df['Variable'].unique()
            result_rows = []
            
            for var in variables:
                var_data = df[df['Variable'] == var]
                if len(var_data) == 0:
                    continue
                    
                # Create row for this variable
                row = {
                    'BuildingID': var_data['building_id'].iloc[0],
                    'VariableName': var
                }
                
                # Add time series data
                for _, data_row in var_data.iterrows():
                    # Use DateTime as column name
                    date_str = str(data_row['DateTime'])
                    # Convert to MM/DD format if it's YYYY-MM-DD
                    if '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts) == 3:
                            date_col = f"{parts[1]}/{parts[2]}"
                        else:
                            date_col = date_str
                    else:
                        date_col = date_str
                    
                    row[date_col] = data_row['Value']
                
                result_rows.append(row)
            
            uc.REAL_DATA_DF = pd.DataFrame(result_rows)
            logger.info(f"Converted to shape: {uc.REAL_DATA_DF.shape}")
            
        elif 'output_matrix.csv' in real_data_path:
            # Use our special loader for output matrix
            uc.REAL_DATA_DF = load_calibration_output_matrix(real_data_path)
        else:
            # Assume it's already in the right format
            uc.REAL_DATA_DF = df
        
        # Create the dictionary format
        uc.REAL_DATA_DICT = {}
        
        if uc.REAL_DATA_DF is not None:
            for _, row in uc.REAL_DATA_DF.iterrows():
                building_id = row.get('BuildingID', row.get('building_id', 0))
                var_name = row.get('VariableName', row.get('Variable', ''))
                
                if building_id not in uc.REAL_DATA_DICT:
                    uc.REAL_DATA_DICT[building_id] = {}
                
                # Get time series data
                time_cols = [col for col in uc.REAL_DATA_DF.columns 
                           if col not in ['BuildingID', 'VariableName', 'building_id', 'Variable']]
                
                time_series = row[time_cols].to_dict()
                uc.REAL_DATA_DICT[building_id][var_name] = time_series
        
        logger.info(f"Loaded real data: {len(uc.REAL_DATA_DICT)} buildings")
        return uc.REAL_DATA_DF
    
    # Apply patch
    uc.load_real_data_once = load_real_data_once_patched
    logger.info("Patched load_real_data_once for multiple formats")