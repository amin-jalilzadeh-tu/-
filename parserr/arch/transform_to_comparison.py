"""
Transform variant data to comparison format
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict

def transform_variants_to_comparison(job_output_dir: str, logger):
    """Transform variant data to comparison format"""
    job_path = Path(job_output_dir)
    
    # Create variant mapping
    variant_mapping = {}
    modified_idfs_dir = job_path / 'modified_idfs'
    if modified_idfs_dir.exists():
        for idf in modified_idfs_dir.glob('building_*_variant_*.idf'):
            match = re.search(r'building_(\d+)_variant_(\d+)\.idf', idf.name)
            if match:
                building_id = match.group(1)
                variant_num = int(match.group(2))
                if building_id not in variant_mapping:
                    variant_mapping[building_id] = []
                variant_mapping[building_id].append(variant_num)
    
    logger.info(f"[INFO] Found variants for buildings: {list(variant_mapping.keys())}")
    
    # Process each building
    for building_id, variant_nums in variant_mapping.items():
        logger.info(f"[INFO] Processing building {building_id} with {len(variant_nums)} variants")
        
        # Load base data for this building
        base_data = load_building_base_data(job_path, building_id, logger)
        if base_data.empty:
            logger.warning(f"[WARN] No base data for building {building_id}")
            continue
        
        # Aggregate to daily if needed
        if 'ReportingFrequency' in base_data.columns and base_data['ReportingFrequency'].str.contains('Hourly').any():
            base_data = aggregate_to_daily(base_data)
        
        # Load variant data
        variant_data = {}
        modified_parsed_dir = job_path / 'parsed_modified_results'
        
        for variant_num in sorted(variant_nums):
            # SQL uses bldg(variant_num + 1)
            sql_bldg_num = variant_num + 1
            variant_df = load_variant_data(modified_parsed_dir, building_id, sql_bldg_num, variant_num, logger)
            if not variant_df.empty:
                # Aggregate to daily if needed
                if 'ReportingFrequency' in variant_df.columns and variant_df['ReportingFrequency'].str.contains('Hourly').any():
                    variant_df = aggregate_to_daily(variant_df)
                variant_data[f'variant_{variant_num}'] = variant_df
        
        if not variant_data:
            logger.warning(f"[WARN] No variant data loaded for building {building_id}")
            continue
        
        # Create comparison for each variable
        all_variables = set(base_data['Variable'].unique())
        for vdf in variant_data.values():
            all_variables.update(vdf['Variable'].unique())
        
        output_path = job_path / 'parsed_data' / 'timeseries' / 'variants' / 'daily'
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[INFO] Creating comparison files for {len(all_variables)} variables")
        
        for variable in sorted(all_variables):
            comparison_df = create_variable_comparison(
                variable, building_id, base_data, variant_data
            )
            
            if not comparison_df.empty:
                # Clean variable name
                clean_var = variable.lower().replace(':', '_').replace(' ', '_').replace('[', '').replace(']', '').replace('(', '').replace(')', '')
                output_file = output_path / f"{clean_var}_{building_id}.parquet"
                comparison_df.to_parquet(output_file, index=False)

def load_building_base_data(job_path: Path, building_id: str, logger) -> pd.DataFrame:
    """Load base data for a specific building"""
    all_data = []
    
    # Check multiple possible locations
    paths = [
        job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'hourly',
        job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'aggregated' / 'daily'
    ]
    
    for path in paths:
        if path.exists():
            for parquet_file in path.glob('*.parquet'):
                df = pd.read_parquet(parquet_file)
                if 'building_id' in df.columns:
                    df = df[df['building_id'] == building_id]
                    if 'variant_id' in df.columns:
                        df = df[df['variant_id'] == 'base']
                    if not df.empty:
                        all_data.append(df)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

def load_variant_data(modified_parsed_dir: Path, building_id: str, sql_bldg_num: int, variant_num: int, logger) -> pd.DataFrame:
    """Load variant data"""
    all_data = []
    
    paths = [
        modified_parsed_dir / 'sql_results' / 'timeseries' / 'hourly',
        modified_parsed_dir / 'sql_results' / 'timeseries' / 'aggregated' / 'daily'
    ]
    
    for path in paths:
        if path.exists():
            for parquet_file in path.glob('*.parquet'):
                df = pd.read_parquet(parquet_file)
                # Filter by building_id and variant_id
                if 'building_id' in df.columns and 'variant_id' in df.columns:
                    df = df[(df['building_id'] == building_id) & 
                           (df['variant_id'] == f'variant_{variant_num}')]
                    if not df.empty:
                        all_data.append(df)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

def create_variable_comparison(variable: str, building_id: str,
                             base_df: pd.DataFrame,
                             variant_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create comparison dataframe for a single variable"""
    # Filter base data
    base_var = base_df[base_df['Variable'] == variable].copy()
    if base_var.empty:
        return pd.DataFrame()
    
    base_var = base_var.rename(columns={'Value': 'base_value'})
    
    # Determine merge columns
    merge_cols = ['DateTime']
    if 'Zone' in base_var.columns and not base_var['Zone'].isna().all():
        merge_cols.append('Zone')
    else:
        base_var['Zone'] = 'Building'
    
    # Start with base
    keep_cols = merge_cols + ['category', 'Units', 'base_value']
    keep_cols = [c for c in keep_cols if c in base_var.columns]
    result = base_var[keep_cols].copy()
    
    # Add variants
    for variant_id in sorted(variant_dict.keys()):
        variant_df = variant_dict[variant_id]
        variant_var = variant_df[variant_df['Variable'] == variable].copy()
        
        if not variant_var.empty:
            variant_var = variant_var.rename(columns={'Value': f'{variant_id}_value'})
            if 'Zone' not in variant_var.columns or variant_var['Zone'].isna().all():
                variant_var['Zone'] = 'Building'
            
            result = result.merge(
                variant_var[merge_cols + [f'{variant_id}_value']],
                on=merge_cols,
                how='outer'
            )
    
    # Add metadata
    result['timestamp'] = result['DateTime']
    result['building_id'] = building_id
    result['variable_name'] = variable
    
    if 'category' not in result.columns:
        result['category'] = categorize_variable(variable)
    
    if 'Units' not in result.columns:
        result['Units'] = ''
    
    # Reorder columns
    # Reorder columns
    first_cols = ['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units']
    first_cols = [c for c in first_cols if c in result.columns]
    
    value_cols = ['base_value'] + sorted([c for c in result.columns if c.endswith('_value') and c != 'base_value'])
    
    final_cols = first_cols + value_cols
    result = result[final_cols]
    
    # Sort by available columns
    sort_cols = ['timestamp']
    if 'Zone' in result.columns:
        sort_cols.append('Zone')
    
    return result.sort_values(sort_cols).reset_index(drop=True)

# Include the same helper functions from transform_to_semi_wide.py
def aggregate_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    # Same implementation as above
    pass

def categorize_variable(variable_name: str) -> str:
    # Same implementation as above
    pass