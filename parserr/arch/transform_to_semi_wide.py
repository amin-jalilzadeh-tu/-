"""
Transform base simulation data to semi-wide format
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Set

def transform_base_to_semi_wide(job_output_dir: str, logger):
    """Transform base simulation data to semi-wide format"""
    job_path = Path(job_output_dir)
    
    # Identify base buildings from output_IDFs
    base_buildings = set()
    base_idfs_dir = job_path / 'output_IDFs'
    if base_idfs_dir.exists():
        for idf in base_idfs_dir.glob('building_*.idf'):
            match = re.search(r'building_(\d+)\.idf', idf.name)
            if match:
                base_buildings.add(match.group(1))
    
    logger.info(f"[INFO] Identified {len(base_buildings)} base buildings: {sorted(base_buildings)}")
    
    # Load base data
    all_base_data = []
    base_sql_paths = [
        job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'hourly',
        job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'aggregated' / 'daily',
        job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'raw' / 'daily'
    ]
    
    for sql_path in base_sql_paths:
        if sql_path.exists():
            for parquet_file in sql_path.glob('*.parquet'):
                logger.debug(f"[DEBUG] Loading {parquet_file}")
                df = pd.read_parquet(parquet_file)
                # Filter to only base buildings
                if 'building_id' in df.columns:
                    df = df[df['building_id'].isin(base_buildings)]
                    df['variant_id'] = 'base'
                    if not df.empty:
                        all_base_data.append(df)
    
    if not all_base_data:
        logger.warning("[WARN] No base data found to transform")
        return
    
    # Combine all base data
    base_df = pd.concat(all_base_data, ignore_index=True)
    logger.info(f"[INFO] Combined base data: {len(base_df)} rows")
    
    # Aggregate to daily if needed
    if 'ReportingFrequency' in base_df.columns and base_df['ReportingFrequency'].str.contains('Hourly').any():
        base_df = aggregate_to_daily(base_df)
    
    # Convert to semi-wide format
    base_df['date_str'] = pd.to_datetime(base_df['DateTime']).dt.strftime('%Y-%m-%d')
    
    index_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units']
    for col in index_cols:
        if col not in base_df.columns:
            if col == 'Zone':
                base_df[col] = 'Building'
            elif col == 'category':
                base_df[col] = base_df['Variable'].apply(categorize_variable)
            else:
                base_df[col] = ''
    
    # Handle None/null in Zone
    base_df['Zone'] = base_df['Zone'].fillna('Building')
    
    # Pivot
    logger.info("[INFO] Pivoting to semi-wide format...")
    pivot_df = base_df.pivot_table(
        index=index_cols,
        columns='date_str',
        values='Value',
        aggfunc='mean'
    ).reset_index()
    
    pivot_df = pivot_df.rename(columns={'Variable': 'VariableName'})
    
    # Save
    output_path = job_path / 'parsed_data' / 'timeseries' / 'base' / 'daily'
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / 'all_variables.parquet'
    pivot_df.to_parquet(output_file, index=False)
    
    logger.info(f"[SUCCESS] Saved semi-wide base data to {output_file}")
    logger.info(f"[INFO] Shape: {pivot_df.shape}")

def aggregate_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly data to daily"""
    # Implementation from FixedSQLTransformer
    df = df.copy()
    df['Date'] = pd.to_datetime(df['DateTime']).dt.date
    
    group_cols = [col for col in df.columns 
                 if col not in ['DateTime', 'Value', 'Date', 'TimeIndex']]
    
    # Energy variables - sum
    energy_mask = df['Variable'].str.contains('Energy|Consumption', na=False)
    
    agg_results = []
    
    if energy_mask.any():
        energy_df = df[energy_mask]
        energy_agg = energy_df.groupby(group_cols + ['Date'])['Value'].sum().reset_index()
        energy_agg['DateTime'] = pd.to_datetime(energy_agg['Date'])
        agg_results.append(energy_agg.drop('Date', axis=1))
    
    if (~energy_mask).any():
        other_df = df[~energy_mask]
        other_agg = other_df.groupby(group_cols + ['Date'])['Value'].mean().reset_index()
        other_agg['DateTime'] = pd.to_datetime(other_agg['Date'])
        agg_results.append(other_agg.drop('Date', axis=1))
    
    if agg_results:
        result = pd.concat(agg_results, ignore_index=True)
        result['ReportingFrequency'] = 'Daily'
        return result
    
    return df

def categorize_variable(variable_name: str) -> str:
    """Categorize variable by name"""
    var_lower = variable_name.lower()
    
    if any(meter in variable_name for meter in ['Electricity:', 'Gas:', 'Cooling:', 'Heating:']):
        return 'energy_meters'
    elif 'zone' in var_lower and any(word in var_lower for word in ['temperature', 'humidity']):
        return 'geometry'
    elif 'surface' in var_lower:
        return 'materials'
    elif 'water heater' in var_lower:
        return 'dhw'
    elif 'equipment' in var_lower:
        return 'equipment'
    elif 'lights' in var_lower:
        return 'lighting'
    elif 'hvac' in var_lower or 'air system' in var_lower:
        return 'hvac'
    elif 'ventilation' in var_lower:
        return 'ventilation'
    elif 'infiltration' in var_lower:
        return 'infiltration'
    else:
        return 'other'