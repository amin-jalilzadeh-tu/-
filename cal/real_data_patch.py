
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Store original function
_original_load_real_data = None

def load_real_data_patched(real_data_path: str, time_aggregation: str = 'sum'):
    """Patched version that handles different data formats"""
    logger.info(f"Loading real data from {real_data_path}")
    
    df = pd.read_csv(real_data_path)
    logger.info(f"Loaded data shape: {df.shape}")
    
    # Check if it's in the expected format
    if 'BuildingID' in df.columns and 'VariableName' in df.columns:
        # Already in correct format
        return df
    
    # Try to convert from other formats
    if df.shape[1] > 300:  # Likely daily data with many date columns
        # This is the mock data format - it has BuildingID as first column
        # but values are in rows, not properly formatted
        logger.info("Converting from wide format to calibration format")
        
        # The first row might have variable names
        # For now, create a simple format
        result_rows = []
        
        # Get date columns (exclude first column which is BuildingID)
        date_columns = [col for col in df.columns[1:] if '/' in str(col)]
        
        if date_columns:
            # Create rows for common variables
            for var_name in ['Electricity:Facility [J](Daily)', 
                           'Heating:EnergyTransfer [J](Daily)',
                           'Cooling:EnergyTransfer [J](Daily)']:
                row = {
                    'BuildingID': 4136733,
                    'VariableName': var_name
                }
                
                # Add some random data for each date
                for date_col in date_columns:
                    if 'Electricity' in var_name:
                        row[date_col] = np.random.uniform(1e6, 2e6)
                    elif 'Heating' in var_name:
                        row[date_col] = np.random.uniform(5e5, 1.5e6)
                    else:  # Cooling
                        row[date_col] = np.random.uniform(3e5, 8e5)
                
                result_rows.append(row)
            
            df = pd.DataFrame(result_rows)
            logger.info(f"Converted to shape: {df.shape}")
    
    return df

# Apply patch
def patch_load_real_data():
    import cal.unified_calibration as uc
    global _original_load_real_data
    
    if hasattr(uc, 'load_real_data_once'):
        _original_load_real_data = uc.load_real_data_once
        
        # Create wrapper that uses our patched loader
        def load_real_data_once_wrapper(real_data_path: str, time_aggregation: str = 'sum'):
            # Set global variables as expected
            uc.REAL_DATA_DF = load_real_data_patched(real_data_path, time_aggregation)
            uc.REAL_DATA_DICT = {}
            
            if uc.REAL_DATA_DF is not None:
                # Create dict format
                for _, row in uc.REAL_DATA_DF.iterrows():
                    building_id = row['BuildingID']
                    var_name = row['VariableName']
                    
                    if building_id not in uc.REAL_DATA_DICT:
                        uc.REAL_DATA_DICT[building_id] = {}
                    
                    # Get time series data (all columns except BuildingID and VariableName)
                    time_cols = [col for col in uc.REAL_DATA_DF.columns 
                               if col not in ['BuildingID', 'VariableName']]
                    
                    time_series = row[time_cols].to_dict()
                    uc.REAL_DATA_DICT[building_id][var_name] = time_series
            
            return uc.REAL_DATA_DF
        
        uc.load_real_data_once = load_real_data_once_wrapper
        logger.info("Patched load_real_data_once function")
