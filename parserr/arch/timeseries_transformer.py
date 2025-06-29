"""
Timeseries Transformer Module
Handles transformation of timeseries data between different formats
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging


class TimeseriesTransformer:
    """Transform timeseries data between different formats"""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
    
    def long_to_semi_wide(self, df: pd.DataFrame, 
                         value_col: str = 'Value',
                         time_col: str = 'DateTime',
                         group_cols: List[str] = None) -> pd.DataFrame:
        """
        Transform long format to semi-wide format with dates as columns
        
        Args:
            df: Long format dataframe
            value_col: Column containing values
            time_col: Column containing timestamps
            group_cols: Columns to group by (default: building_id, variant_id, variable, category, zone, unit)
            
        Returns:
            Semi-wide format dataframe
        """
        if group_cols is None:
            group_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units']
        
        # Ensure datetime column is datetime type
        df[time_col] = pd.to_datetime(df[time_col])
        
        # Create date column for pivoting
        df['date'] = df[time_col].dt.date
        
        # Filter to only keep columns that exist
        existing_group_cols = [col for col in group_cols if col in df.columns]
        
        # Pivot the data
        pivot_df = df.pivot_table(
            index=existing_group_cols,
            columns='date',
            values=value_col,
            aggfunc='first'  # Use first value if duplicates
        )
        
        # Reset index to flatten
        pivot_df = pivot_df.reset_index()
        
        # Convert date columns to string format
        date_cols = [col for col in pivot_df.columns if isinstance(col, (pd.Timestamp, np.datetime64))]
        new_cols = {}
        for col in date_cols:
            if hasattr(col, 'strftime'):
                new_cols[col] = col.strftime('%Y-%m-%d')
            else:
                new_cols[col] = pd.to_datetime(str(col)).strftime('%Y-%m-%d')
        
        pivot_df = pivot_df.rename(columns=new_cols)
        
        return pivot_df
    
    def create_variant_comparison(self, base_df: pd.DataFrame, 
                                variant_dfs: Dict[str, pd.DataFrame],
                                variable_name: str,
                                merge_cols: List[str] = None) -> pd.DataFrame:
        """
        Create comparison dataframe with base and variant values side by side
        
        Args:
            base_df: Base simulation dataframe
            variant_dfs: Dictionary of variant_id -> dataframe
            variable_name: Variable to compare
            merge_cols: Columns to merge on (default: timestamp, building_id, zone)
            
        Returns:
            Comparison dataframe with base_value, variant_X_value columns
        """
        if merge_cols is None:
            merge_cols = ['DateTime', 'building_id', 'Zone']
        
        # Filter to specific variable
        base_filtered = base_df[base_df['Variable'] == variable_name].copy()
        base_filtered = base_filtered.rename(columns={'Value': 'base_value'})
        
        # Start with base data
        result = base_filtered[merge_cols + ['base_value', 'category', 'Units']].copy()
        
        # Add each variant
        for variant_id, variant_df in variant_dfs.items():
            variant_filtered = variant_df[variant_df['Variable'] == variable_name].copy()
            variant_filtered = variant_filtered.rename(columns={'Value': f'{variant_id}_value'})
            
            # Merge variant data
            result = result.merge(
                variant_filtered[merge_cols + [f'{variant_id}_value']],
                on=merge_cols,
                how='outer'
            )
        
        # Add variable name column
        result['variable_name'] = variable_name
        
        # Reorder columns
        col_order = merge_cols + ['variable_name', 'category', 'Units', 'base_value']
        variant_cols = [col for col in result.columns if col.endswith('_value') and col != 'base_value']
        col_order.extend(sorted(variant_cols))
        
        return result[col_order]
    
    def merge_building_variants(self, job_output_dir: str) -> Dict[str, pd.DataFrame]:
        """
        Merge base and variant results for each building
        
        Args:
            job_output_dir: Job output directory containing both parsed_data and parsed_modified_results
            
        Returns:
            Dictionary of variable_name -> comparison dataframe
        """
        job_path = Path(job_output_dir)
        base_path = job_path / 'parsed_data' / 'sql_results'
        variant_path = job_path / 'parsed_modified_results' / 'sql_results'
        
        merged_results = {}
        
        # Load base data
        base_files = list((base_path / 'timeseries' / 'hourly').glob('*.parquet'))
        if not base_files:
            self.logger.warning("No base timeseries files found")
            return merged_results
        
        # Load all base data
        base_dfs = []
        for file in base_files:
            df = pd.read_parquet(file)
            base_dfs.append(df)
        
        base_df = pd.concat(base_dfs, ignore_index=True) if base_dfs else pd.DataFrame()
        
        # Load variant data
        variant_dfs = {}
        if variant_path.exists():
            variant_files = list((variant_path / 'timeseries' / 'hourly').glob('*.parquet'))
            
            for file in variant_files:
                df = pd.read_parquet(file)
                # Group by variant_id
                for variant_id in df['variant_id'].unique():
                    if variant_id != 'base':
                        if variant_id not in variant_dfs:
                            variant_dfs[variant_id] = []
                        variant_dfs[variant_id].append(df[df['variant_id'] == variant_id])
        
        # Concatenate variant dataframes
        for variant_id, dfs in variant_dfs.items():
            variant_dfs[variant_id] = pd.concat(dfs, ignore_index=True)
        
        # Get unique variables
        variables = base_df['Variable'].unique() if not base_df.empty else []
        
        # Create comparison for each variable
        for variable in variables:
            comparison_df = self.create_variant_comparison(
                base_df, 
                variant_dfs, 
                variable
            )
            merged_results[variable] = comparison_df
        
        return merged_results
    
    def save_transformed_data(self, df: pd.DataFrame, 
                            output_type: str,
                            category: str,
                            frequency: str,
                            format_type: str = 'semi_wide') -> Path:
        """
        Save transformed data in appropriate structure
        
        Args:
            df: Transformed dataframe
            output_type: 'base' or 'variants'
            category: Variable category
            frequency: Time frequency
            format_type: 'semi_wide' or 'variant_comparison'
            
        Returns:
            Path to saved file
        """
        # Create output path
        # Create output path - ALWAYS use timeseries/ structure
        output_dir = self.base_path / 'timeseries' / output_type / frequency
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        if format_type == 'semi_wide':
            filename = f"{category}_{frequency}.parquet"
        else:
            filename = f"{category}_comparison_{frequency}.parquet"
        
        output_path = output_dir / filename
        
        # Save file
        df.to_parquet(output_path, index=False)
        
        self.logger.info(f"Saved transformed data to {output_path}")
        return output_path
    
    def transform_category_data(self, input_dir: Path, 
                              category: str,
                              frequency: str = 'daily') -> pd.DataFrame:
        """
        Transform all data for a specific category
        
        Args:
            input_dir: Input directory containing raw data
            category: Category to transform
            frequency: Frequency to transform
            
        Returns:
            Transformed dataframe
        """
        # Find files for this category
        pattern = f"{category}_{frequency}.parquet"
        files = list(input_dir.glob(f"**/{pattern}"))
        
        if not files:
            self.logger.warning(f"No files found for {category} at {frequency} frequency")
            return pd.DataFrame()
        
        # Load and concatenate
        dfs = []
        for file in files:
            df = pd.read_parquet(file)
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Transform to semi-wide format
        transformed_df = self.long_to_semi_wide(combined_df)
        
        return transformed_df
    
    def create_unified_comparison(self, base_semi_wide: pd.DataFrame,
                                variant_semi_wide: pd.DataFrame,
                                variant_id: str) -> pd.DataFrame:
        """
        Create unified comparison between base and variant in semi-wide format
        
        Args:
            base_semi_wide: Base data in semi-wide format
            variant_semi_wide: Variant data in semi-wide format
            variant_id: ID of the variant
            
        Returns:
            Unified comparison dataframe
        """
        # Get date columns (all columns that look like dates)
        date_cols = [col for col in base_semi_wide.columns 
                    if col not in ['building_id', 'variant_id', 'Variable', 
                                  'category', 'Zone', 'Units']]
        
        # Merge dataframes
        merge_cols = ['building_id', 'Variable', 'category', 'Zone', 'Units']
        
        # Rename value columns in variant
        variant_renamed = variant_semi_wide.copy()
        for date_col in date_cols:
            if date_col in variant_renamed.columns:
                variant_renamed[f'{date_col}_{variant_id}'] = variant_renamed[date_col]
                variant_renamed = variant_renamed.drop(columns=[date_col])
        
        # Merge
        unified = base_semi_wide.merge(
            variant_renamed,
            on=merge_cols,
            how='outer',
            suffixes=('_base', f'_{variant_id}')
        )
        
        return unified
    

    def create_semi_wide_all_variables(self, df, frequency='daily'):
        """Create semi-wide format with dates as columns for all variables"""
        # Ensure we have DateTime column
        if 'DateTime' not in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create date column based on frequency
        if frequency == 'daily':
            df['date'] = df['DateTime'].dt.date
        elif frequency == 'monthly':
            df['date'] = df['DateTime'].dt.to_period('M')
        elif frequency == 'hourly':
            df['date'] = df['DateTime'].dt.strftime('%Y-%m-%d_%H')
        
        # Pivot to semi-wide format
        index_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units']
        
        # Remove any None/null Zone values
        df['Zone'] = df['Zone'].fillna('Building')
        
        semi_wide = df.pivot_table(
            index=index_cols,
            columns='date',
            values='Value',
            aggfunc='mean'  # Handle any duplicates
        ).reset_index()
        
        return semi_wide

    def create_variant_comparison_format(self, base_dir, variant_dir, 
                                        variant_mapping: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """Create comparison format with base and variant values as columns"""
        results = {}
        
        # Convert to Path objects if they're strings
        base_dir = Path(base_dir) if isinstance(base_dir, str) else base_dir
        variant_dir = Path(variant_dir) if isinstance(variant_dir, str) else variant_dir
        
        # Load base data
        base_path = base_dir / 'sql_results' / 'timeseries' / 'raw' / 'daily'
        base_data = []
        
        if base_path.exists():
            for f in base_path.glob('*.parquet'):
                df = pd.read_parquet(f)
                df['variant_id'] = 'base'
                base_data.append(df)
        
        base_df = pd.concat(base_data) if base_data else pd.DataFrame()
        
        # Load variant data
        variant_path = variant_dir / 'sql_results' / 'timeseries' / 'raw' / 'daily'
        variant_data = []
        
        if variant_path.exists():
            for f in variant_path.glob('*.parquet'):
                df = pd.read_parquet(f)
                variant_data.append(df)
        
        variant_df = pd.concat(variant_data) if variant_data else pd.DataFrame()
        
        # ... rest of the method remains the same ...
        
        # Check if we have data
        if base_df.empty and variant_df.empty:
            return results
        
        # Combine base and variants
        all_data = pd.concat([base_df, variant_df]) if not base_df.empty and not variant_df.empty else base_df if not base_df.empty else variant_df
        
        # Check if Variable column exists
        if 'Variable' not in all_data.columns:
            print("Warning: 'Variable' column not found in data")
            return results
        
        # Group by variable
        for variable in all_data['Variable'].unique():
            var_data = all_data[all_data['Variable'] == variable].copy()
            
            # Ensure we have required columns
            required_cols = ['DateTime', 'building_id', 'Zone', 'category', 'Units', 'variant_id', 'Value']
            missing_cols = [col for col in required_cols if col not in var_data.columns]
            
            # Add missing columns with defaults
            for col in missing_cols:
                if col == 'Zone':
                    var_data[col] = 'Building'
                elif col == 'category':
                    var_data[col] = self._categorize_variable(variable)
                elif col == 'Units':
                    var_data[col] = ''
                elif col == 'variant_id':
                    var_data[col] = 'unknown'
            
            # Pivot to get variants as columns
            try:
                comparison = var_data.pivot_table(
                    index=['DateTime', 'building_id', 'Zone', 'category', 'Units'],
                    columns='variant_id',
                    values='Value',
                    aggfunc='mean'
                ).reset_index()
                
                # Rename columns
                if 'base' in comparison.columns:
                    comparison = comparison.rename(columns={'base': 'base_value'})
                
                for col in comparison.columns:
                    if col.startswith('variant_'):
                        comparison = comparison.rename(columns={col: f'{col}_value'})
                
                comparison['variable_name'] = variable
                results[variable] = comparison
                
            except Exception as e:
                print(f"Error pivoting data for {variable}: {e}")
        
        return results

    def _categorize_variable(self, variable_name: str) -> str:
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
        
    def create_semi_wide_all_variables(self, df: pd.DataFrame, frequency: str = 'daily') -> pd.DataFrame:
        """Create semi-wide format with dates as columns for all variables"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Ensure DateTime column
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create date string based on frequency
        if frequency == 'daily':
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        elif frequency == 'monthly':
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m')
        elif frequency == 'hourly':
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d_%H')
        
        # Define index columns
        index_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units']
        
        # Ensure all columns exist
        for col in index_cols:
            if col not in df.columns:
                if col == 'Zone':
                    df[col] = 'Building'
                elif col == 'variant_id':
                    df[col] = 'base'
                else:
                    df[col] = ''
        
        # Handle None/null in Zone
        df['Zone'] = df['Zone'].fillna('Building')
        
        # Pivot to semi-wide format
        pivot_df = df.pivot_table(
            index=index_cols,
            columns='date_str',
            values='Value',
            aggfunc='mean'  # Handle any duplicates
        ).reset_index()
        
        # Rename Variable to VariableName
        pivot_df = pivot_df.rename(columns={'Variable': 'VariableName'})
        
        return pivot_df