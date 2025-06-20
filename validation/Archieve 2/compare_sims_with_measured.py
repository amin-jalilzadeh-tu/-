# validation/compare_sims_with_measured.py
# Updated to be a thin wrapper for backward compatibility
# The heavy lifting is now done in data_alignment.py

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def load_csv_as_df(real_data_path, sim_data_path):
    """
    Loads real and simulated data from CSV into DataFrames.
    Simple utility function for backward compatibility.
    
    Args:
        real_data_path: Path to real data CSV
        sim_data_path: Path to simulated data CSV
    
    Returns:
        Tuple of (real_df, sim_df)
    """
    logger.info(f"Loading real data from: {real_data_path}")
    logger.info(f"Loading sim data from: {sim_data_path}")

    df_real = pd.read_csv(real_data_path)
    df_sim = pd.read_csv(sim_data_path)

    logger.info(f"Real data shape: {df_real.shape}")
    logger.info(f"Sim data shape: {df_sim.shape}")
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Real data columns: {df_real.columns.tolist()}")
        logger.debug(f"Sim data columns: {df_sim.columns.tolist()}")
    
    return df_real, df_sim


def align_data_for_variable(df_real, df_sim, real_building_id, sim_building_id, variable_name):
    """
    Returns aligned arrays of sim vs. obs for a given (real_building_id, sim_building_id, variable).
    
    This function maintains backward compatibility with the old interface
    while potentially using new alignment features in the future.
    
    Args:
        df_real: Real data DataFrame (already filtered to building)
        df_sim: Simulated data DataFrame (already filtered to building)
        real_building_id: Real building ID
        sim_building_id: Simulated building ID
        variable_name: Variable name to align
    
    Returns:
        Tuple of (sim_values_array, obs_values_array, merged_dataframe)
    """

    # Filter for specific building and variable
    real_sel = df_real[
        (df_real['BuildingID'] == real_building_id) &
        (df_real['VariableName'] == variable_name)
    ]
    sim_sel = df_sim[
        (df_sim['BuildingID'] == sim_building_id) &
        (df_sim['VariableName'] == variable_name)
    ]

    logger.debug(f"Aligning real Bldg={real_building_id} vs sim Bldg={sim_building_id}, Var={variable_name}")
    logger.debug(f"Real selection shape={real_sel.shape}, Sim selection shape={sim_sel.shape}")

    # If empty, return empty arrays
    if real_sel.empty or sim_sel.empty:
        logger.warning(f"No data found for alignment: Real empty={real_sel.empty}, Sim empty={sim_sel.empty}")
        return np.array([]), np.array([]), pd.DataFrame()

    # Melt from wide to long format
    # Get date columns (exclude ID and name columns)
    id_cols = ['BuildingID', 'VariableName']
    date_cols_real = [col for col in real_sel.columns if col not in id_cols]
    date_cols_sim = [col for col in sim_sel.columns if col not in id_cols]
    
    # Melt real data
    real_long = real_sel.melt(
        id_vars=id_cols,
        value_vars=date_cols_real,
        var_name='Date',
        value_name='Value'
    ).dropna(subset=['Value'])

    # Melt sim data
    sim_long = sim_sel.melt(
        id_vars=id_cols,
        value_vars=date_cols_sim,
        var_name='Date',
        value_name='Value'
    ).dropna(subset=['Value'])

    # Merge on 'Date'
    merged = pd.merge(
        real_long[['Date', 'Value']],
        sim_long[['Date', 'Value']],
        on='Date', 
        how='inner', 
        suffixes=('_obs', '_sim')
    )

    if merged.empty:
        logger.warning(f"No common dates found between real and simulated data")
        return np.array([]), np.array([]), pd.DataFrame()

    # Log alignment results
    logger.info(f"Aligned {len(merged)} data points")
    
    # Check for potential unit issues
    if len(merged) > 0:
        obs_mean = merged['Value_obs'].mean()
        sim_mean = merged['Value_sim'].mean()
        if obs_mean > 0:
            ratio = sim_mean / obs_mean
            if ratio > 100 or ratio < 0.01:
                logger.warning(
                    f"Potential unit mismatch detected! "
                    f"Sim/Obs ratio = {ratio:.2f} "
                    f"(Obs mean = {obs_mean:.2e}, Sim mean = {sim_mean:.2e})"
                )

    # Return arrays plus the merged DataFrame
    return merged['Value_sim'].values, merged['Value_obs'].values, merged