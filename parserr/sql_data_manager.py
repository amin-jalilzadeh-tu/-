"""
SQL Data Manager Module v3.0
Handles SQL-specific data storage with proper base/variant separation and frequency handling
"""

import os
import json
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set
from datetime import datetime
import numpy as np

import re

class SQLDataManager:
    """Manages SQL-specific data storage with base/variant separation and proper frequency handling"""
    
    def __init__(self, base_path: Union[str, Path]):
        """Initialize SQL data manager"""
        self.base_path = Path(base_path)
        self._initialize_sql_structure()
        self.base_buildings = set()  # Will be populated during analysis
        
    def _initialize_sql_structure(self):
        """Create SQL-specific directory structure"""
        directories = [
            'timeseries',
            'metadata',
            'comparisons'  # Only for modified results
        ]
        
        for dir_path in directories:
            (self.base_path / dir_path).mkdir(parents=True, exist_ok=True)
    
    def set_base_buildings(self, base_buildings: Set[str]):
        """Set the list of base building IDs"""
        self.base_buildings = base_buildings
    
    def save_raw_timeseries(self, data: pd.DataFrame, category: str, 
                           original_frequency: str, variant_id: str = 'base',
                           is_base: bool = True):
        """
        Save raw timeseries data
        
        Args:
            data: Timeseries data
            category: Category name
            original_frequency: Original reporting frequency
            variant_id: Variant identifier
            is_base: Whether this is base data
        """
        if data.empty:
            return
        
        # Ensure variant_id is set in the data
        if 'variant_id' not in data.columns:
            data['variant_id'] = variant_id
        
        # Store in temporary location
        temp_dir = self.base_path / 'temp_raw' / ('base' if is_base else 'variants')
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19]
        filename = f"{category}_{variant_id}_{timestamp}.parquet"
        
        output_path = temp_dir / filename
        data.to_parquet(output_path, index=False)
        print(f"    Saved raw data to: {output_path.relative_to(self.base_path)}")
    
    def transform_and_save_base_data(self):
        """Transform all base data to semi-wide format at appropriate frequencies"""
        print("\nTransforming base data to semi-wide format...")
        
        # Collect all base data
        temp_base_dir = self.base_path / 'temp_raw' / 'base'
        if not temp_base_dir.exists():
            print("No base data to transform")
            return
        
        all_base_data = []
        for parquet_file in temp_base_dir.glob('*.parquet'):
            df = pd.read_parquet(parquet_file)
            # Only include data from base buildings
            if 'building_id' in df.columns and self.base_buildings:
                df = df[df['building_id'].astype(str).isin(self.base_buildings)]
            all_base_data.append(df)
        
        if not all_base_data:
            print("No base data found")
            return
        
        # Combine all base data
        combined_df = pd.concat(all_base_data, ignore_index=True)
        
        # Group by original reporting frequency
        freq_groups = self._group_by_frequency(combined_df)
        
        # Process each frequency group
        for original_freq, freq_data in freq_groups.items():
            print(f"  Processing {original_freq} data ({len(freq_data)} rows)...")
            
            # Convert to semi-wide format at original frequency
            semi_wide_df = self._convert_to_semi_wide(freq_data, original_freq)
            
            if not semi_wide_df.empty:
                # Save at original frequency
                output_path = self.base_path / 'timeseries' / f'base_all_{original_freq}.parquet'
                semi_wide_df.to_parquet(output_path, index=False)
                print(f"    Saved {original_freq} base data: {len(semi_wide_df)} rows")
                
                # Create aggregations for higher frequencies
                self._create_upward_aggregations(freq_data, original_freq, 'base')
        
        # Clean up temp files
        print("\nCleaning up temporary files...")
        for file in temp_base_dir.glob('*.parquet'):
            file.unlink()
        print("  Temporary base files removed")
        
        # Try to remove empty temp directories
        try:
            temp_base_dir.rmdir()
            (self.base_path / 'temp_raw').rmdir()
        except:
            pass
    
    def transform_and_save_variant_comparisons(self, base_data_dir: Path = None):
        """Transform variant data to comparison format at appropriate frequencies"""
        print("\nTransforming variant data to comparison format...")
        start_time = datetime.now()
        
        # Determine where to look for base data
        if base_data_dir:
            base_dir = base_data_dir
        else:
            base_dir = self.base_path
        
        # If we're in parsed_modified_results, look in parent's parsed_data
        if 'parsed_modified_results' in str(self.base_path):
            base_dir = self.base_path.parent / 'parsed_data'
        
        # Collect all variant data
        temp_variant_dir = self.base_path / 'temp_raw' / 'variants'
        if not temp_variant_dir.exists():
            print("No variant data to transform")
            return
        
        print(f"Found variant data in: {temp_variant_dir}")
        variant_files = list(temp_variant_dir.glob('*.parquet'))
        print(f"Number of variant files: {len(variant_files)}")
        
        # Group variant data by building and frequency
        variant_data_by_building_freq = {}
        
        for parquet_file in variant_files:
            print(f"  Reading: {parquet_file.name}")
            df = pd.read_parquet(parquet_file)
            
            # Group by frequency first
            freq_groups = self._group_by_frequency(df)
            
            for freq, freq_df in freq_groups.items():
                if freq not in variant_data_by_building_freq:
                    variant_data_by_building_freq[freq] = {}
                
                # Then group by building
                for building_id in freq_df['building_id'].unique():
                    if building_id not in variant_data_by_building_freq[freq]:
                        variant_data_by_building_freq[freq][building_id] = {}
                    
                    building_df = freq_df[freq_df['building_id'] == building_id]
                    
                    for variant_id in building_df['variant_id'].unique():
                        if variant_id != 'base':
                            variant_df = building_df[building_df['variant_id'] == variant_id]
                            
                            if variant_id not in variant_data_by_building_freq[freq][building_id]:
                                variant_data_by_building_freq[freq][building_id][variant_id] = []
                            
                            variant_data_by_building_freq[freq][building_id][variant_id].append(variant_df)
        
        # Process each frequency separately
        for freq, building_data in variant_data_by_building_freq.items():
            print(f"\nProcessing {freq} frequency data...")
            
            # Load base data for this frequency
            base_data_path = base_dir / 'timeseries' / 'base' / freq / 'all_variables.parquet'
            
            if not base_data_path.exists():
                print(f"  No base data found for {freq} frequency at {base_data_path}")
                # Try aggregated frequencies if original doesn't exist
                base_data_path = self._find_base_data_for_frequency(base_dir, freq)
                
                if not base_data_path:
                    print(f"  Skipping {freq} - no suitable base data found")
                    continue
            
            print(f"  Loading base data from: {base_data_path}")
            base_semi_wide = pd.read_parquet(base_data_path)
            base_long = self._semi_wide_to_long(base_semi_wide)
            
            # Process each building at this frequency
            for building_id, variant_dict in building_data.items():
                building_start = datetime.now()
                print(f"\n  Processing building {building_id} with {len(variant_dict)} variants at {freq} frequency...")
                
                # Get base data for this building
                building_base = base_long[base_long['building_id'] == str(building_id)]
                
                if building_base.empty:
                    print(f"    Skipping building {building_id} - no base data")
                    continue
                
                # Prepare variant data
                variant_dfs = {}
                for variant_id, dfs in variant_dict.items():
                    combined_variant = pd.concat(dfs, ignore_index=True)
                    variant_dfs[variant_id] = combined_variant
                
                print(f"    Creating {freq} comparisons for {len(variant_dfs)} variants")
                
                # Create comparisons at this frequency
                self._create_variable_comparisons_at_frequency(
                    building_id, building_base, variant_dfs, freq
                )
                
                building_time = (datetime.now() - building_start).total_seconds()
                print(f"    Building {building_id} at {freq} processed in {building_time:.1f} seconds")
        
        # Clean up temp files
        print("\nCleaning up temporary files...")
        for file in temp_variant_dir.glob('*.parquet'):
            file.unlink()
        print("  Temporary variant files removed")
        
        total_time = (datetime.now() - start_time).total_seconds()
        print(f"\nVariant transformation completed in {total_time:.1f} seconds")
    
    def _group_by_frequency(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group data by reporting frequency"""
        freq_mapping = {
            'Timestep': 'timestep',
            'Hourly': 'hourly',
            'Daily': 'daily',
            'Monthly': 'monthly',
            'RunPeriod': 'runperiod',
            'Annual': 'yearly'
        }
        
        frequency_groups = {}
        
        if 'ReportingFrequency' in df.columns:
            for orig_freq, mapped_freq in freq_mapping.items():
                freq_df = df[df['ReportingFrequency'] == orig_freq]
                if not freq_df.empty:
                    frequency_groups[mapped_freq] = freq_df
        else:
            # If no frequency column, assume hourly
            frequency_groups['hourly'] = df
        
        return frequency_groups
    
    def _find_base_data_for_frequency(self, base_dir: Path, target_freq: str) -> Optional[Path]:
        """Find suitable base data for a given frequency"""
        # Frequency hierarchy (can aggregate upward)
        freq_hierarchy = {
            'timestep': 0,
            'hourly': 1,
            'daily': 2,
            'monthly': 3,
            'yearly': 4,
            'runperiod': 5
        }
        
        target_level = freq_hierarchy.get(target_freq, -1)
        
        # Look for lower frequency data that can be used
        for freq, level in sorted(freq_hierarchy.items(), key=lambda x: x[1]):
            if level <= target_level:
                candidate_path = base_dir / 'timeseries' / f'base_all_{freq}.parquet'
                if candidate_path.exists():
                    return candidate_path
        
        return None
    
    def _create_upward_aggregations(self, df: pd.DataFrame, source_freq: str, 
                                   data_type: str = 'base'):
        """Create aggregations to higher time frequencies"""
        freq_hierarchy = {
            'timestep': ['hourly', 'daily', 'monthly'],
            'hourly': ['daily', 'monthly'],
            'daily': ['monthly'],
            'monthly': [],
            'yearly': [],
            'runperiod': []
        }
        
        target_freqs = freq_hierarchy.get(source_freq, [])
        
        for target_freq in target_freqs:
            print(f"    Creating {target_freq} aggregation from {source_freq}...")
            
            if target_freq == 'daily' and source_freq in ['timestep', 'hourly']:
                agg_df = self._aggregate_to_daily(df)
            elif target_freq == 'monthly':
                agg_df = self._aggregate_to_monthly(df)
            elif target_freq == 'hourly' and source_freq == 'timestep':
                agg_df = self._aggregate_to_hourly(df)
            else:
                continue
            
            if not agg_df.empty:
                # Convert to semi-wide and save
                semi_wide = self._convert_to_semi_wide(agg_df, target_freq)
                
                if data_type == 'base':
                    output_path = self.base_path / 'timeseries' / 'base' / target_freq / 'all_variables.parquet'
                    semi_wide.to_parquet(output_path, index=False)
                    print(f"      Saved {target_freq} aggregation: {len(semi_wide)} rows")
    
    def _create_variable_comparisons_at_frequency(self, building_id: str, base_df: pd.DataFrame,
                                                 variant_dfs: Dict[str, pd.DataFrame], 
                                                 frequency: str):
        """Create comparison files for each variable at a specific frequency"""
        output_dir = self.base_path / 'comparisons'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"    Creating {frequency} comparisons in: {output_dir}")
        
        # Get all variables
        all_variables = set(base_df['Variable'].unique())
        for vdf in variant_dfs.values():
            all_variables.update(vdf['Variable'].unique())
        
        print(f"    Total variables to process: {len(all_variables)}")
        
        # Process variables in batches
        batch_size = 10
        variable_list = sorted(list(all_variables))
        files_created = 0
        
        for i in range(0, len(variable_list), batch_size):
            batch_vars = variable_list[i:i + batch_size]
            
            for variable in batch_vars:
                try:
                    comparison_df = self._create_single_variable_comparison(
                        variable, building_id, base_df, variant_dfs
                    )
                    
                    if not comparison_df.empty:
                        # Clean variable name for filename
                        # Extract unit from variable name (text within brackets)
                        unit_match = re.search(r'\[(.*?)\]', variable)
                        unit = unit_match.group(1).lower() if unit_match else 'na'
                        unit = unit.replace('/', 'per')  # Handle units like J/kg

                        clean_var_name = (variable.lower()
                                        .replace(':', '_')
                                        .replace(' ', '_')
                                        .replace('[', '')
                                        .replace(']', '')
                                        .replace('(', '')
                                        .replace(')', ''))

                        output_file = output_dir / f"var_{clean_var_name}_{unit}_{frequency}_b{building_id}.parquet"
                        comparison_df.to_parquet(output_file, index=False)
                        files_created += 1
                except Exception as e:
                    print(f"      Error processing {variable}: {e}")
        
        print(f"    Created {files_created} {frequency} comparison files for building {building_id}")
    
    def _convert_to_semi_wide(self, df: pd.DataFrame, frequency: str) -> pd.DataFrame:
        """Convert long format to semi-wide format with dates as columns"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Create date string based on frequency
        if 'DateTime' not in df.columns:
            return df
        
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        if frequency == 'hourly':
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d_%H')
        elif frequency == 'daily':
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        elif frequency == 'monthly':
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m')
        elif frequency == 'yearly':
            df['date_str'] = df['DateTime'].dt.strftime('%Y')
        else:  # timestep or other
            df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d_%H:%M')
        
        # Define index columns
        index_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units']
        
        # Ensure all columns exist
        for col in index_cols:
            if col not in df.columns:
                if col == 'Zone':
                    df[col] = 'Building'
                elif col == 'category':
                    df[col] = ''
                elif col == 'variant_id':
                    df[col] = 'base'
                else:
                    df[col] = ''
        
        # Handle None/null in Zone
        df['Zone'] = df['Zone'].fillna('Building')
        
        # Pivot
        pivot_df = df.pivot_table(
            index=index_cols,
            columns='date_str',
            values='Value',
            aggfunc='mean'
        ).reset_index()
        
        # Rename Variable to VariableName
        pivot_df = pivot_df.rename(columns={'Variable': 'VariableName'})
        
        return pivot_df
    
    def _semi_wide_to_long(self, semi_wide_df: pd.DataFrame) -> pd.DataFrame:
        """Convert semi-wide format back to long format"""
        # Get date columns
        date_cols = [col for col in semi_wide_df.columns 
                    if col not in ['building_id', 'variant_id', 'VariableName', 
                                  'category', 'Zone', 'Units']]
        
        # Melt to long format
        long_df = semi_wide_df.melt(
            id_vars=['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units'],
            value_vars=date_cols,
            var_name='DateTime',
            value_name='Value'
        )
        
        # Convert DateTime to proper format
        long_df['DateTime'] = pd.to_datetime(long_df['DateTime'])
        
        # Rename VariableName back to Variable
        long_df = long_df.rename(columns={'VariableName': 'Variable'})
        
        # Remove rows with NaN values
        long_df = long_df.dropna(subset=['Value'])
        
        return long_df
    
    def _create_single_variable_comparison(self, variable: str, building_id: str,
                                         base_df: pd.DataFrame,
                                         variant_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Create comparison dataframe for a single variable"""
        # Filter base data
        base_var = base_df[base_df['Variable'] == variable].copy()
        
        if base_var.empty:
            # Use first variant as template
            for vdf in variant_dfs.values():
                template = vdf[vdf['Variable'] == variable].copy()
                if not template.empty:
                    base_var = template.copy()
                    base_var['Value'] = np.nan
                    break
        
        if base_var.empty:
            return pd.DataFrame()
        
        # Prepare base data
        base_var = base_var.rename(columns={'Value': 'base_value'})
        
        # Determine merge columns
        merge_cols = ['DateTime']
        if 'Zone' in base_var.columns and not base_var['Zone'].isna().all():
            merge_cols.append('Zone')
        else:
            base_var['Zone'] = 'Building'
        
        # Start with base data
        result = base_var[merge_cols + ['category', 'Units', 'base_value']].copy()
        
        # Add each variant
        for variant_id in sorted(variant_dfs.keys()):
            variant_df = variant_dfs[variant_id]
            variant_var = variant_df[variant_df['Variable'] == variable].copy()
            
            if not variant_var.empty:
                variant_var = variant_var.rename(columns={'Value': f'{variant_id}_value'})
                
                # Ensure Zone consistency
                if 'Zone' not in variant_var.columns or variant_var['Zone'].isna().all():
                    variant_var['Zone'] = 'Building'
                
                # Merge
                result = result.merge(
                    variant_var[merge_cols + [f'{variant_id}_value']],
                    on=merge_cols,
                    how='outer'
                )
        
        # Add metadata
        result['timestamp'] = result['DateTime']
        result['building_id'] = building_id
        result['variable_name'] = variable
        
        # Reorder columns
        first_cols = ['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units']
        first_cols = [c for c in first_cols if c in result.columns]
        
        value_cols = ['base_value'] + sorted([c for c in result.columns if c.endswith('_value') and c != 'base_value'])
        other_cols = [c for c in result.columns if c not in first_cols + value_cols + ['DateTime']]
        
        final_cols = first_cols + value_cols + other_cols
        result = result[[c for c in final_cols if c in result.columns]]
        
        # Sort by available columns
        sort_cols = []
        if 'timestamp' in result.columns:
            sort_cols.append('timestamp')
        if 'Zone' in result.columns:
            sort_cols.append('Zone')
        
        if sort_cols:
            return result.sort_values(sort_cols).reset_index(drop=True)
        else:
            return result.reset_index(drop=True)
    
    def _aggregate_to_hourly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate timestep data to hourly"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Convert DateTime
        if df['DateTime'].dtype == 'object':
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create hour column
        df['Hour'] = df['DateTime'].dt.floor('H')
        
        # Group columns
        group_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units', 'Hour']
        group_cols = [col for col in group_cols if col in df.columns]
        
        # Aggregate based on variable type
        energy_vars = df[df['Variable'].str.contains('Energy|Consumption', na=False, regex=True)]
        other_vars = df[~df['Variable'].str.contains('Energy|Consumption', na=False, regex=True)]
        
        results = []
        
        if not energy_vars.empty:
            energy_agg = energy_vars.groupby(group_cols, as_index=False)['Value'].sum()
            energy_agg['DateTime'] = energy_agg['Hour']
            energy_agg = energy_agg.drop('Hour', axis=1)
            results.append(energy_agg)
        
        if not other_vars.empty:
            other_agg = other_vars.groupby(group_cols, as_index=False)['Value'].mean()
            other_agg['DateTime'] = other_agg['Hour']
            other_agg = other_agg.drop('Hour', axis=1)
            results.append(other_agg)
        
        if results:
            result = pd.concat(results, ignore_index=True)
            result['ReportingFrequency'] = 'Hourly'
            return result
        
        return pd.DataFrame()
    
    def _aggregate_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate to daily frequency"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Convert DateTime
        if df['DateTime'].dtype == 'object':
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        df['Date'] = df['DateTime'].dt.date
        
        # Group columns
        group_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units', 'Date']
        group_cols = [col for col in group_cols if col in df.columns]
        
        # Separate by variable type
        energy_vars = df[df['Variable'].str.contains('Energy|Consumption', na=False, regex=True)]
        other_vars = df[~df['Variable'].str.contains('Energy|Consumption', na=False, regex=True)]
        
        results = []
        
        if not energy_vars.empty:
            energy_agg = energy_vars.groupby(group_cols, as_index=False)['Value'].sum()
            energy_agg['DateTime'] = pd.to_datetime(energy_agg['Date'])
            energy_agg = energy_agg.drop('Date', axis=1)
            results.append(energy_agg)
        
        if not other_vars.empty:
            other_agg = other_vars.groupby(group_cols, as_index=False)['Value'].mean()
            other_agg['DateTime'] = pd.to_datetime(other_agg['Date'])
            other_agg = other_agg.drop('Date', axis=1)
            results.append(other_agg)
        
        if results:
            result = pd.concat(results, ignore_index=True)
            result['ReportingFrequency'] = 'Daily'
            return result
        
        return pd.DataFrame()
    
    def _aggregate_to_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate to monthly frequency"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Convert DateTime
        if df['DateTime'].dtype == 'object':
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create month column
        df['YearMonth'] = df['DateTime'].dt.to_period('M')
        
        # Group columns
        group_cols = ['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units', 'YearMonth']
        group_cols = [col for col in group_cols if col in df.columns]
        
        # Aggregate
        energy_vars = df[df['Variable'].str.contains('Energy|Consumption', na=False, regex=True)]
        other_vars = df[~df['Variable'].str.contains('Energy|Consumption', na=False, regex=True)]
        
        results = []
        
        if not energy_vars.empty:
            energy_agg = energy_vars.groupby(group_cols, as_index=False)['Value'].sum()
            results.append(energy_agg)
        
        if not other_vars.empty:
            other_agg = other_vars.groupby(group_cols, as_index=False)['Value'].mean()
            results.append(other_agg)
        
        if results:
            result = pd.concat(results, ignore_index=True)
            result['DateTime'] = result['YearMonth'].dt.to_timestamp()
            result = result.drop('YearMonth', axis=1)
            result['ReportingFrequency'] = 'Monthly'
            return result
        
        return pd.DataFrame()
    
    def save_schedules(self, schedules_data: pd.DataFrame):
        """Save schedule data"""
        if schedules_data.empty:
            return
            
        output_path = self.base_path / 'metadata' / 'schedules.parquet'
        
        if output_path.exists():
            existing_data = pd.read_parquet(output_path)
            combined_data = pd.concat([existing_data, schedules_data], ignore_index=True)
            combined_data = combined_data.drop_duplicates(
                subset=['building_id', 'ScheduleName'] if 'ScheduleName' in combined_data.columns else ['building_id'],
                keep='last'
            )
            combined_data.to_parquet(output_path, index=False)
        else:
            schedules_data.to_parquet(output_path, index=False)
    
    def cleanup_old_structure(self):
        """Remove old directory structure and files"""
        old_dirs = [
            'sql_results',  # Remove entire old structure
            'timeseries/base',  # Remove old nested structure
            'timeseries/variants'  # Remove old nested structure
        ]
        
        for old_dir in old_dirs:
            dir_path = self.base_path / old_dir
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                print(f"Removed old directory: {old_dir}")