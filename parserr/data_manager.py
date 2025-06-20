"""
Enhanced Data Manager Module v3.1 - With Consolidated Output Support
Handles hierarchical data storage with consolidated output definitions
"""

import os
import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import numpy as np

class EnhancedHierarchicalDataManager:
    """Enhanced data manager with consolidated output support"""
    
    def __init__(self, base_path: Union[str, Path]):
        """Initialize data manager with base path"""
        self.base_path = Path(base_path)
        self._initialize_structure()
        self._category_buffers = {}  # Buffer for accumulating category data
        
    def _initialize_structure(self):
        """Create enhanced directory structure"""
        directories = [
            'metadata',
            'idf_data/by_category',
            'idf_data/by_building',
            # Removed 'idf_data/outputs' - no longer needed
            'sql_results/timeseries/hourly',
            'sql_results/timeseries/aggregated/daily',
            'sql_results/timeseries/aggregated/monthly',
            'sql_results/schedules',
            'sql_results/summary_metrics',
            'sql_results/output_validation',
            'relationships',
            'analysis_ready/feature_sets',
            'analysis_ready/output_analysis'
        ]
        
        for dir_path in directories:
            (self.base_path / dir_path).mkdir(parents=True, exist_ok=True)
    
    def update_project_manifest(self, total_buildings: int, categories: List[str]):
        """Update project manifest with enhanced metadata"""
        manifest = {
            'project_id': self.base_path.name,
            'created': datetime.now().isoformat(),
            'total_buildings': total_buildings,
            'categories_tracked': categories,
            'last_updated': datetime.now().isoformat(),
            'data_version': '3.1',
            'file_structure': {
                'idf_data': {
                    'by_category': 'Consolidated category files across all buildings',
                    'by_building': 'Complete parameter snapshots per building',
                    # Note: outputs are now included in by_category
                },
                'sql_results': {
                    'timeseries': 'Time series data by category and frequency',
                    'summary_metrics': 'Aggregated metrics',
                    'output_validation': 'Output completeness validation results'
                }
            }
        }
        
        manifest_path = self.base_path / 'metadata' / 'project_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def update_building_registry(self, building_data: pd.DataFrame):
        """Update building registry with enhanced fields"""
        registry_path = self.base_path / 'metadata' / 'building_registry.parquet'
        
        # Ensure required columns including new output fields
        required_cols = ['building_id', 'ogc_fid', 'idf_path', 'sql_path', 
                        'zone_count', 'output_variables', 'output_meters', 
                        'status', 'last_modified']
        
        # Add missing columns with defaults
        for col in required_cols:
            if col not in building_data.columns:
                if col == 'last_modified':
                    building_data[col] = datetime.now()
                elif col == 'status':
                    building_data[col] = 'completed'
                elif col in ['output_variables', 'output_meters']:
                    building_data[col] = 0
                else:
                    building_data[col] = None
        
        building_data[required_cols].to_parquet(registry_path, index=False)
    
    def save_output_definitions(self, output_type: str, data: pd.DataFrame):
        """DEPRECATED - Use buffer_category_data with 'outputs_all' instead"""
        # This method is kept for compatibility but should not be used
        # All outputs should go through buffer_category_data('outputs_all', data)
        print(f"Warning: save_output_definitions is deprecated. Output data will be saved to consolidated file.")
        if not data.empty:
            # Add output_type column if not present
            if 'output_type' not in data.columns:
                data['output_type'] = output_type
            self.buffer_category_data('outputs_all', data)
    
    def save_output_validation_results(self, validation_data: pd.DataFrame):
        """Save output validation results"""
        if validation_data.empty:
            return
            
        output_path = self.base_path / 'sql_results' / 'output_validation' / 'validation_results.parquet'
        validation_data.to_parquet(output_path, index=False)
    
    def save_missing_outputs(self, missing_data: pd.DataFrame):
        """Save details of missing outputs"""
        if missing_data.empty:
            return
            
        output_path = self.base_path / 'sql_results' / 'output_validation' / 'missing_outputs.parquet'
        missing_data.to_parquet(output_path, index=False)
    
    def save_output_analysis(self, analysis_type: str, data: Union[pd.DataFrame, Dict]):
        """Save output analysis results"""
        output_dir = self.base_path / 'analysis_ready' / 'output_analysis'
        
        if isinstance(data, pd.DataFrame):
            output_path = output_dir / f"{analysis_type}.parquet"
            data.to_parquet(output_path, index=False)
        else:
            output_path = output_dir / f"{analysis_type}.json"
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def load_output_definitions(self, output_type: str = 'all') -> pd.DataFrame:
        """Load output definitions from consolidated file"""
        file_path = self.base_path / 'idf_data' / 'by_category' / 'outputs_all.parquet'
        
        if file_path.exists():
            df = pd.read_parquet(file_path)
            # Filter by output_type if specified
            if output_type != 'all' and 'output_type' in df.columns:
                df = df[df['output_type'] == output_type]
            return df
        
        return pd.DataFrame()
    
    def load_output_validation_results(self) -> pd.DataFrame:
        """Load output validation results"""
        file_path = self.base_path / 'sql_results' / 'output_validation' / 'validation_results.parquet'
        
        if file_path.exists():
            return pd.read_parquet(file_path)
        
        return pd.DataFrame()
    
    def get_output_coverage_summary(self) -> Dict[str, Any]:
        """Get summary of output coverage across buildings"""
        validation_results = self.load_output_validation_results()
        
        if validation_results.empty:
            return {'status': 'No validation data available'}
        
        summary = {
            'total_buildings': len(validation_results),
            'average_coverage': validation_results['coverage'].mean(),
            'min_coverage': validation_results['coverage'].min(),
            'max_coverage': validation_results['coverage'].max(),
            'perfect_coverage_count': len(validation_results[validation_results['coverage'] == 100.0]),
            'buildings_with_issues': len(validation_results[validation_results['coverage'] < 100.0])
        }
        
        # Get most commonly missing outputs
        missing_path = self.base_path / 'sql_results' / 'output_validation' / 'missing_outputs.parquet'
        if missing_path.exists():
            missing_df = pd.read_parquet(missing_path)
            missing_counts = missing_df.groupby('variable').size().sort_values(ascending=False)
            summary['top_missing_outputs'] = missing_counts.head(10).to_dict()
        
        return summary
    
    def create_output_frequency_matrix(self) -> pd.DataFrame:
        """Create matrix showing output frequencies across buildings"""
        outputs_df = self.load_output_definitions('variable')
        
        if outputs_df.empty:
            return pd.DataFrame()
        
        # Filter to variables only (not meters, tables, control)
        if 'output_type' in outputs_df.columns:
            variables_df = outputs_df[outputs_df['output_type'] == 'variable']
        else:
            variables_df = outputs_df
        
        # Pivot to create matrix
        if 'name' in variables_df.columns and 'reporting_frequency' in variables_df.columns:
            matrix = variables_df.pivot_table(
                index='building_id',
                columns='name',
                values='reporting_frequency',
                aggfunc='first'
            )
            return matrix
        
        return pd.DataFrame()
    
    # Keep all existing methods from original HierarchicalDataManager
    def save_idf_category_data(self, category_file: str, data: pd.DataFrame, 
                              mode: str = 'append'):
        """Save IDF data to consolidated category files"""
        if data.empty:
            return
            
        file_path = self.base_path / 'idf_data' / 'by_category' / f"{category_file}.parquet"
        
        if mode == 'append' and file_path.exists():
            # Read existing data and append
            existing_data = pd.read_parquet(file_path)
            combined_data = pd.concat([existing_data, data], ignore_index=True)
            
            # Remove duplicates if any (based on building_id and object_name)
            if 'building_id' in combined_data.columns and 'object_name' in combined_data.columns:
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id', 'object_name'], 
                    keep='last'
                )
            
            combined_data.to_parquet(file_path, index=False)
        else:
            # Write new file
            data.to_parquet(file_path, index=False)
    
    def buffer_category_data(self, category_file: str, data: pd.DataFrame):
        """Buffer category data for batch writing"""
        if data.empty:
            return
            
        if category_file not in self._category_buffers:
            self._category_buffers[category_file] = []
        
        self._category_buffers[category_file].append(data)
    
    def flush_category_buffers(self):
        """Flush all buffered category data to disk"""
        for category_file, data_list in self._category_buffers.items():
            if data_list:
                combined_data = pd.concat(data_list, ignore_index=True)
                self.save_idf_category_data(category_file, combined_data)
        
        # Clear buffers
        self._category_buffers.clear()
    
    def save_building_snapshot(self, building_id: str, all_params: pd.DataFrame):
        """Save complete parameter snapshot for a building"""
        snapshot_path = self.base_path / 'idf_data' / 'by_building' / f"{building_id}_snapshot.parquet"
        all_params.to_parquet(snapshot_path, index=False)
    
    def save_timeseries_data(self, data: pd.DataFrame, frequency: str = 'hourly',
                           category: str = None, year: int = None):
        """Save time series data with appropriate partitioning"""
        if data.empty:
            return
            
        if frequency == 'hourly':
            if not year:
                year = data['DateTime'].dt.year.mode()[0]
            
            # Use category-based naming
            file_name = f"{category}_{year}.parquet" if category else f"all_variables_{year}.parquet"
            output_path = self.base_path / 'sql_results' / 'timeseries' / 'hourly' / file_name
        else:
            # Aggregated data
            file_name = f"{category}_{frequency}.parquet" if category else f"all_variables_{frequency}.parquet"
            output_path = self.base_path / 'sql_results' / 'timeseries' / 'aggregated' / frequency / file_name
        
        # Append if file exists
        if output_path.exists():
            existing_data = pd.read_parquet(output_path)
            combined_data = pd.concat([existing_data, data], ignore_index=True)
            
            # Remove duplicates based on key columns
            key_cols = ['building_id', 'DateTime']
            if 'Zone' in combined_data.columns:
                key_cols.append('Zone')
            if 'Variable' in combined_data.columns:
                key_cols.append('Variable')
            
            combined_data = combined_data.drop_duplicates(subset=key_cols, keep='last')
            combined_data.to_parquet(output_path, index=False)
        else:
            data.to_parquet(output_path, index=False)
    
    def save_schedules(self, schedules_data: pd.DataFrame):
        """Save schedule data"""
        if schedules_data.empty:
            return
            
        output_path = self.base_path / 'sql_results' / 'schedules' / 'all_schedules.parquet'
        
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
    
    def save_relationships(self, relationship_type: str, data: pd.DataFrame):
        """Save relationship data"""
        if data.empty:
            return
            
        output_path = self.base_path / 'relationships' / f"{relationship_type}.parquet"
        
        if output_path.exists():
            existing_data = pd.read_parquet(output_path)
            combined_data = pd.concat([existing_data, data], ignore_index=True)
            
            # Remove duplicates based on relationship type
            if relationship_type == 'zone_mappings':
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id', 'idf_zone_name'], 
                    keep='last'
                )
            elif relationship_type == 'equipment_assignments':
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id', 'equipment_name', 'assigned_zone'], 
                    keep='last'
                )
            
            combined_data.to_parquet(output_path, index=False)
        else:
            data.to_parquet(output_path, index=False)
    
    def save_summary_metrics(self, metrics_type: str, data: pd.DataFrame):
        """Save summary metrics"""
        if data.empty:
            return
            
        output_path = self.base_path / 'sql_results' / 'summary_metrics' / f"{metrics_type}.parquet"
        
        if output_path.exists():
            existing_data = pd.read_parquet(output_path)
            combined_data = pd.concat([existing_data, data], ignore_index=True)
            
            # Remove duplicates based on building_id
            if 'building_id' in combined_data.columns:
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id'], 
                    keep='last'
                )
            
            combined_data.to_parquet(output_path, index=False)
        else:
            data.to_parquet(output_path, index=False)
    
    def save_analysis_ready_data(self, data: pd.DataFrame, dataset_name: str):
        """Save analysis-ready datasets"""
        if data.empty:
            return
            
        if dataset_name == 'parameter_matrix':
            output_path = self.base_path / 'analysis_ready' / 'parameter_matrix.parquet'
        else:
            output_path = self.base_path / 'analysis_ready' / 'feature_sets' / f"{dataset_name}.parquet"
        
        data.to_parquet(output_path, index=False)
    
    def load_category_data(self, category_file: str) -> pd.DataFrame:
        """Load IDF data for a specific category file"""
        file_path = self.base_path / 'idf_data' / 'by_category' / f"{category_file}.parquet"
        
        if file_path.exists():
            return pd.read_parquet(file_path)
        
        return pd.DataFrame()
    
    def load_building_snapshot(self, building_id: str) -> pd.DataFrame:
        """Load complete parameter snapshot for a building"""
        snapshot_path = self.base_path / 'idf_data' / 'by_building' / f"{building_id}_snapshot.parquet"
        
        if snapshot_path.exists():
            return pd.read_parquet(snapshot_path)
        return pd.DataFrame()
    
    def load_timeseries_data(self, category: str = None, year: int = None,
                           frequency: str = 'hourly') -> pd.DataFrame:
        """Load time series data"""
        if frequency == 'hourly':
            file_name = f"{category}_{year}.parquet" if category and year else "*.parquet"
            search_path = self.base_path / 'sql_results' / 'timeseries' / 'hourly'
        else:
            file_name = f"{category}_{frequency}.parquet" if category else "*.parquet"
            search_path = self.base_path / 'sql_results' / 'timeseries' / 'aggregated' / frequency
        
        if '*' in file_name:
            # Load multiple files
            all_data = []
            for file_path in search_path.glob(file_name):
                all_data.append(pd.read_parquet(file_path))
            
            if all_data:
                return pd.concat(all_data, ignore_index=True)
        else:
            # Load specific file
            file_path = search_path / file_name
            if file_path.exists():
                return pd.read_parquet(file_path)
        
        return pd.DataFrame()
    
    def create_summary_metrics(self, sql_data: pd.DataFrame, idf_params: pd.DataFrame) -> Dict[str, Any]:
        """Create summary metrics for quick access"""
        metrics = {}
        
        # Building counts
        metrics['total_buildings'] = idf_params['building_id'].nunique() if 'building_id' in idf_params.columns else 0
        
        # Energy metrics from SQL data
        if not sql_data.empty and 'Variable' in sql_data.columns:
            energy_vars = sql_data[sql_data['Variable'].str.contains('Energy', na=False)]
            if not energy_vars.empty:
                metrics['total_energy_consumption'] = energy_vars['Value'].sum()
                metrics['avg_energy_per_building'] = energy_vars.groupby('building_id')['Value'].sum().mean() if 'building_id' in energy_vars.columns else 0
        
        # Zone metrics
        if 'zone_name' in idf_params.columns:
            metrics['total_zones'] = idf_params['zone_name'].nunique()
        
        return metrics
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get enhanced summary of all available data"""
        summary = {
            'base_path': str(self.base_path),
            'categories': {},
            'buildings': [],
            'timeseries': {},
            'relationships': [],
            'outputs': {},
            'validation': {}
        }
        
        # Check category files
        category_path = self.base_path / 'idf_data' / 'by_category'
        for file_path in category_path.glob('*.parquet'):
            category_name = file_path.stem
            try:
                df = pd.read_parquet(file_path)
                summary['categories'][category_name] = {
                    'rows': len(df),
                    'buildings': df['building_id'].nunique() if 'building_id' in df.columns else 0
                }
                
                # Special handling for outputs_all file
                if category_name == 'outputs_all' and 'output_type' in df.columns:
                    # Break down by output type
                    type_counts = df['output_type'].value_counts().to_dict()
                    summary['outputs'] = {
                        'total': len(df),
                        'by_type': type_counts,
                        'buildings': df['building_id'].nunique() if 'building_id' in df.columns else 0
                    }
            except:
                summary['categories'][category_name] = {'error': 'Could not read file'}
        
        # Check buildings
        building_path = self.base_path / 'idf_data' / 'by_building'
        if building_path.exists():
            summary['buildings'] = [f.stem.replace('_snapshot', '') for f in building_path.glob('*_snapshot.parquet')]
        
        # Check timeseries
        hourly_path = self.base_path / 'sql_results' / 'timeseries' / 'hourly'
        if hourly_path.exists():
            summary['timeseries']['hourly'] = [f.stem for f in hourly_path.glob('*.parquet')]
        
        daily_path = self.base_path / 'sql_results' / 'timeseries' / 'aggregated' / 'daily'
        if daily_path.exists():
            summary['timeseries']['daily'] = [f.stem for f in daily_path.glob('*.parquet')]
        
        monthly_path = self.base_path / 'sql_results' / 'timeseries' / 'aggregated' / 'monthly'
        if monthly_path.exists():
            summary['timeseries']['monthly'] = [f.stem for f in monthly_path.glob('*.parquet')]
        
        # Check relationships
        rel_path = self.base_path / 'relationships'
        if rel_path.exists():
            summary['relationships'] = [f.stem for f in rel_path.glob('*.parquet')]
        
        # Check validation results
        validation_path = self.base_path / 'sql_results' / 'output_validation'
        if validation_path.exists():
            summary['validation'] = [f.stem for f in validation_path.glob('*.parquet')]
        
        return summary
    
    def update_category_schemas(self):
        """Save enhanced category schemas including outputs"""
        schemas = {}
        
        # Regular categories
        category_path = self.base_path / 'idf_data' / 'by_category'
        for file_path in category_path.glob('*.parquet'):
            try:
                df = pd.read_parquet(file_path)
                if not df.empty:
                    schemas[file_path.stem] = {
                        'columns': list(df.columns),
                        'dtypes': df.dtypes.astype(str).to_dict(),
                        'row_count': len(df),
                        'building_count': df['building_id'].nunique() if 'building_id' in df.columns else 0
                    }
                    
                    # Add type breakdown for outputs_all
                    if file_path.stem == 'outputs_all' and 'output_type' in df.columns:
                        schemas[file_path.stem]['output_types'] = df['output_type'].value_counts().to_dict()
                else:
                    schemas[file_path.stem] = {
                        'columns': [],
                        'dtypes': {},
                        'row_count': 0,
                        'building_count': 0
                    }
            except Exception as e:
                schemas[file_path.stem] = {'error': f'Could not read schema: {str(e)}'}
        
        schema_path = self.base_path / 'metadata' / 'category_schemas.json'
        with open(schema_path, 'w') as f:
            json.dump(schemas, f, indent=2)


def create_parameter_matrix(data_manager: EnhancedHierarchicalDataManager,
                          building_ids: List[str] = None) -> pd.DataFrame:
    """Create parameter matrix for analysis from consolidated files"""
    all_params = []
    
    # Define which category files to include and their key parameters
    category_files = {
        'geometry_zones': ['volume', 'floor_area', 'ceiling_height'],
        'materials_constructions': ['outside_layer', 'layer_2', 'layer_3'],
        'hvac_equipment': ['cooling_capacity', 'heating_capacity', 'cop'],
        'hvac_thermostats': ['heating_setpoint_temperature_schedule_name', 
                            'cooling_setpoint_temperature_schedule_name'],
        'ventilation': ['design_flow_rate', 'air_changes_per_hour'],
        'infiltration': ['design_flow_rate', 'air_changes_per_hour'],
        'lighting': ['lighting_level', 'watts_per_zone_floor_area'],
        'equipment': ['design_level', 'watts_per_zone_floor_area'],
        'dhw': ['tank_volume', 'heater_maximum_capacity']
    }
    
    for file_name, key_params in category_files.items():
        cat_data = data_manager.load_category_data(file_name)
        if not cat_data.empty:
            # Check if building_id column exists
            if 'building_id' not in cat_data.columns:
                print(f"Warning: No building_id column in {file_name}")
                continue
                
            # Select building_id and key parameters that exist in the data
            cols_to_keep = ['building_id']
            params_found = []
            
            for param in key_params:
                # Try different column naming conventions
                possible_names = [
                    param,
                    param + '_numeric',
                    param.replace('_', ' ').title().replace(' ', '_').lower(),
                    param.replace('_', ' ').lower()
                ]
                
                for col_name in possible_names:
                    if col_name in cat_data.columns:
                        # Check if the column has numeric data
                        try:
                            # Convert to numeric, replacing non-numeric values with NaN
                            test_numeric = pd.to_numeric(cat_data[col_name], errors='coerce')
                            if not test_numeric.isna().all():  # At least some numeric values
                                cols_to_keep.append(col_name)
                                params_found.append(col_name)
                                break
                        except:
                            # If it's a string column with values like 'autocalculate', skip it
                            continue
            
            if len(cols_to_keep) > 1:  # Has at least building_id and one parameter
                subset_data = cat_data[cols_to_keep].copy()
                
                # Aggregate by building (in case of multiple entries per building)
                numeric_cols = subset_data.select_dtypes(include=[np.number]).columns.tolist()
                numeric_cols = [col for col in numeric_cols if col != 'building_id']
                
                if numeric_cols:
                    # Group by building_id and aggregate numeric columns
                    agg_dict = {col: 'mean' for col in numeric_cols}
                    subset_data = subset_data.groupby('building_id').agg(agg_dict).reset_index()
                else:
                    # No numeric columns, just get unique building_id values
                    subset_data = subset_data.groupby('building_id').first().reset_index()
                
                # Prefix columns with category name
                prefix = file_name.split('_')[0]
                subset_data.columns = ['building_id'] + [f"{prefix}_{col}" for col in subset_data.columns[1:]]
                
                all_params.append(subset_data)
    
    if all_params:
        # Merge all parameters
        matrix = all_params[0]
        for df in all_params[1:]:
            matrix = matrix.merge(df, on='building_id', how='outer')
        
        # Filter by building IDs if specified
        if building_ids:
            matrix = matrix[matrix['building_id'].isin(building_ids)]
        
        # Save the matrix
        data_manager.save_analysis_ready_data(matrix, 'parameter_matrix')
        
        return matrix
    
    return pd.DataFrame()


def aggregate_timeseries(data: pd.DataFrame, freq: str = 'D',
                       agg_func: Union[str, Dict] = 'mean') -> pd.DataFrame:
    """Aggregate time series data to specified frequency"""
    if data.empty or 'DateTime' not in data.columns:
        return data
    
    # Ensure DateTime is datetime type
    data['DateTime'] = pd.to_datetime(data['DateTime'])
    
    # Group by relevant columns
    group_cols = [col for col in ['building_id', 'Zone', 'Variable'] if col in data.columns]
    
    # Identify numeric columns for aggregation
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    if 'Value' in data.columns and 'Value' not in numeric_cols:
        # Try to convert Value to numeric if it's not already
        try:
            data['Value'] = pd.to_numeric(data['Value'], errors='coerce')
            numeric_cols.append('Value')
        except:
            pass
    
    # Remove any index-like columns from numeric_cols
    numeric_cols = [col for col in numeric_cols if col not in group_cols]
    
    if not numeric_cols:
        print("Warning: No numeric columns found for aggregation")
        return pd.DataFrame()
    
    if group_cols:
        # Set DateTime as index for resampling
        data_copy = data.copy()
        data_copy = data_copy.set_index('DateTime')
        
        # Only keep group columns and numeric columns
        cols_to_keep = group_cols + numeric_cols
        data_copy = data_copy[cols_to_keep]
        
        # Perform aggregation
        if isinstance(agg_func, dict):
            # Filter agg_func to only include numeric columns
            agg_func_filtered = {k: v for k, v in agg_func.items() if k in numeric_cols}
            aggregated = data_copy.groupby(group_cols).resample(freq).agg(agg_func_filtered)
        else:
            # Apply agg_func only to numeric columns
            aggregated = data_copy.groupby(group_cols)[numeric_cols].resample(freq).agg(agg_func)
        
        # Reset index
        aggregated = aggregated.reset_index()
    else:
        # Simple time-based aggregation
        data_copy = data[['DateTime'] + numeric_cols].copy()
        aggregated = data_copy.set_index('DateTime').resample(freq).agg(agg_func).reset_index()
    
    return aggregated