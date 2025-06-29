"""
c_sensitivity/data_manager.py

Data management for sensitivity analysis - handles loading and organizing data.
(This replaces the old sensitivity_data_manager.py)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
import json
from datetime import datetime
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class SensitivityDataManager:
    """
    Manages data loading and organization for sensitivity analysis
    """
    
    def __init__(self, project_root: Union[str, Path], logger: Optional[logging.Logger] = None):
        self.project_root = Path(project_root)
        self.logger = logger or logging.getLogger(__name__)
        
        # Define data paths
        self.parsed_data_path = self.project_root / "parsed_data"
        self.modified_parsed_path = self.project_root / "parsed_modified_results"
        self.modifications_path = self.project_root / "modified_idfs"
        self.scenarios_path = self.project_root / "scenarios"
        
        # Data containers
        self.parameter_data = None
        self.simulation_results = {}
        self.modification_data = None
        self.building_metadata = pd.DataFrame()
        self.time_slice_config = None
        
        # Load building metadata if available
        self._load_building_metadata()
    
    def _load_building_metadata(self):
        """Load building metadata from registry"""
        registry_path = self.parsed_data_path / "metadata" / "building_registry.parquet"
        
        if registry_path.exists():
            try:
                self.building_metadata = pd.read_parquet(registry_path)
                self.logger.info(f"Loaded metadata for {len(self.building_metadata)} buildings")
            except Exception as e:
                self.logger.warning(f"Failed to load building metadata: {e}")
    
    def load_idf_parameters(self, 
                          categories: Optional[List[str]] = None,
                          file_patterns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load IDF parameters from parsed data
        
        Args:
            categories: List of categories to load (e.g., ['hvac', 'materials'])
            file_patterns: List of file patterns to match
            
        Returns:
            DataFrame with parameter data
        """
        self.logger.info("Loading IDF parameters...")
        
        # Check for analysis-ready parameter matrix first
        param_matrix_path = self.parsed_data_path / "analysis_ready" / "parameter_matrix.parquet"
        if param_matrix_path.exists():
            self.logger.info(f"Loading from parameter matrix: {param_matrix_path}")
            self.parameter_data = pd.read_parquet(param_matrix_path)
            return self.parameter_data
        
        # Otherwise, load from category files
        category_path = self.parsed_data_path / "idf_data" / "by_category"
        
        if not category_path.exists():
            self.logger.warning(f"Category data path not found: {category_path}")
            return pd.DataFrame()
        
        # Determine which files to load
        if categories:
            files_to_load = []
            for cat in categories:
                pattern = f"{cat}*.parquet"
                files_to_load.extend(list(category_path.glob(pattern)))
        elif file_patterns:
            files_to_load = []
            for pattern in file_patterns:
                files_to_load.extend(list(category_path.glob(pattern)))
        else:
            # Load all category files
            files_to_load = list(category_path.glob("*.parquet"))
        
        # Load and combine data
        dfs = []
        for file_path in files_to_load:
            try:
                df = pd.read_parquet(file_path)
                # Add category from filename
                category_name = file_path.stem.split('_')[0]
                df['category'] = category_name
                dfs.append(df)
                self.logger.debug(f"Loaded {len(df)} records from {file_path.name}")
            except Exception as e:
                self.logger.warning(f"Failed to load {file_path}: {e}")
        
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            self.parameter_data = combined_df
            self.logger.info(f"Loaded {len(combined_df)} parameter records from {len(files_to_load)} categories")
            return combined_df
        else:
            self.logger.warning("No parameter data loaded")
            return pd.DataFrame()
    
    def load_modification_tracking(self) -> pd.DataFrame:
        """Load modification tracking data"""
        self.logger.info("Loading modification tracking...")
        
        # Find latest modification file
        mod_files = list(self.modifications_path.glob("modifications_detail_*.parquet"))
        if not mod_files:
            self.logger.warning("No modification tracking files found")
            return pd.DataFrame()
        
        latest_file = max(mod_files, key=lambda x: x.stat().st_mtime)
        
        # Load modifications
        df = pd.read_parquet(latest_file)
        
        # Parse numeric values
        df['original_value_numeric'] = pd.to_numeric(df['original_value'], errors='coerce')
        df['new_value_numeric'] = pd.to_numeric(df['new_value'], errors='coerce')
        
        # Calculate changes
        df['value_delta'] = df['new_value_numeric'] - df['original_value_numeric']
        df['value_pct_change'] = (df['value_delta'] / df['original_value_numeric'].replace(0, np.nan)) * 100
        
        # Handle empty field_name
        df['field_name_clean'] = df['field_name'].fillna('').str.strip()
        df['field_name_clean'] = df['field_name_clean'].replace('', 'value')
        
        # Create detailed parameter key
        df['param_key'] = (
            df['category'] + '*' +
            df['object_type'] + '*' +
            df['object_name'] + '*' +
            df['field_name_clean']
        )
        
        self.modification_data = df
        self.logger.info(f"Loaded {len(df)} modifications")
        self.logger.info(f"Unique parameters: {df['param_key'].nunique()}")
        
        return df
    
    def load_simulation_results(self, 
                              result_type: str = 'daily',
                              variables: Optional[List[str]] = None,
                              load_modified: bool = True,
                              time_slice_config: Optional[Dict[str, any]] = None) -> Dict[str, pd.DataFrame]:
        """Load simulation results using new data format only"""
        from .time_slicer import TimeSlicer
        time_slicer = TimeSlicer(self.logger)
        
        self.time_slice_config = time_slice_config
        
        self.logger.info(f"Loading {result_type} simulation results...")
        if time_slice_config and time_slice_config.get('enabled', False):
            self.logger.info(f"With time slice: {time_slice_config.get('slice_type', 'custom')}")
        
        results = {}
        
        # Load base data from new format
        new_base_path = self.parsed_data_path / "timeseries" / f"base_all_{result_type}.parquet"
        if not new_base_path.exists():
            self.logger.error(f"Base data file not found: {new_base_path}")
            return results
        
        results['base'] = self._load_new_base_format(result_type, variables, time_slice_config)
        
        # Load comparison data if modified results requested
        if load_modified:
            comparison_path = self.modified_parsed_path / "comparisons"
            if comparison_path.exists():
                self.logger.info("Loading comparison data")
                comparison_results = self._load_comparison_results(result_type, variables, time_slice_config)
                results.update(comparison_results)
            else:
                self.logger.warning("No comparison directory found - modified results not available")
        
        self.simulation_results = results
        return results
    
    
    def create_analysis_dataset(self,
                              output_variables: Optional[List[str]] = None,
                              use_modifications: bool = True,
                              time_slice_config: Optional[Dict[str, any]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create X (parameters) and y (outputs) datasets for analysis
        
        Args:
            output_variables: List of output variables to include
            use_modifications: Whether to use modification data (True) or parameters (False)
            time_slice_config: Time slicing configuration
            
        Returns:
            Tuple of (X_parameters, y_outputs) DataFrames
        """
        self.logger.info("Creating analysis dataset...")
        if time_slice_config and time_slice_config.get('enabled', False):
            self.logger.info(f"With time slice: {time_slice_config.get('slice_type', 'custom')}")
        
        if use_modifications and self.modification_data is not None:
            # Create from modifications
            return self._create_modification_dataset(output_variables, time_slice_config)
        else:
            # Create from parameters
            return self._create_parameter_dataset(output_variables, time_slice_config)
    
    def _create_modification_dataset(self, 
                                   output_variables: Optional[List[str]] = None,
                                   time_slice_config: Optional[Dict[str, any]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create dataset from modification tracking"""
        if self.modification_data is None:
            self.load_modification_tracking()
        
        if not self.simulation_results:
            self.load_simulation_results(time_slice_config=time_slice_config)
        
        # Create parameter matrix from modifications
        X = self._pivot_modifications()
        
        # Create output matrix
        y = self._extract_output_deltas(output_variables)
        
        # Align indices
        common_buildings = list(set(X.index) & set(y.index))
        X = X.loc[common_buildings]
        y = y.loc[common_buildings]
        
        self.logger.info(f"Created dataset with {len(X)} samples, {X.shape[1]} parameters, {y.shape[1]} outputs")
        
        return X, y
    
    def _create_parameter_dataset(self, 
                                output_variables: Optional[List[str]] = None,
                                time_slice_config: Optional[Dict[str, any]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create dataset from IDF parameters"""
        if self.parameter_data is None:
            self.load_idf_parameters()
        
        if not self.simulation_results:
            self.load_simulation_results(load_modified=False, time_slice_config=time_slice_config)
        
        # Create parameter matrix
        X = self._pivot_parameters()
        
        # Create output matrix
        y = self._extract_outputs(output_variables)
        
        # Align indices
        common_index = X.index.intersection(y.index)
        X = X.loc[common_index]
        y = y.loc[common_index]
        
        self.logger.info(f"Created dataset with {len(X)} samples, {X.shape[1]} parameters, {y.shape[1]} outputs")
        
        return X, y
    
    def _pivot_modifications(self) -> pd.DataFrame:
        """Pivot modification data to wide format"""
        if self.modification_data is None:
            return pd.DataFrame()
        
        # Handle empty field_name by using 'value' as default
        self.modification_data['field_name_clean'] = self.modification_data['field_name'].fillna('').str.strip()
        self.modification_data['field_name_clean'] = self.modification_data['field_name_clean'].replace('', 'value')
        
        # Create parameter key with full detail
        self.modification_data['param_key'] = (
            self.modification_data['category'] + '*' +
            self.modification_data['object_type'] + '*' +
            self.modification_data['object_name'] + '*' +
            self.modification_data['field_name_clean']
        )
        
        # Pivot by building
        pivot_df = self.modification_data.groupby(['building_id', 'param_key']).agg({
            'value_delta': 'mean',
            'value_pct_change': 'mean'
        }).unstack(fill_value=0)
        
        # Flatten column names
        pivot_df.columns = [f"{col[1]}_{col[0]}" for col in pivot_df.columns]
        
        # Log info about the pivot
        self.logger.debug(f"Pivoted modifications: {pivot_df.shape}")
        if pivot_df.shape[1] > 0:
            self.logger.debug(f"Example columns: {list(pivot_df.columns[:5])}")
        
        return pivot_df
    
    def _pivot_parameters(self) -> pd.DataFrame:
        """Pivot parameter data to wide format"""
        if self.parameter_data is None:
            return pd.DataFrame()
        
        # Select numeric columns
        numeric_cols = self.parameter_data.select_dtypes(include=[np.number]).columns.tolist()
        
        # Create parameter name
        if 'field' in self.parameter_data.columns:
            self.parameter_data['param_name'] = (
                self.parameter_data['category'].astype(str) + '_' +
                self.parameter_data['field'].astype(str)
            )
        else:
            # Use first numeric column as parameter
            if numeric_cols:
                self.parameter_data['param_name'] = 'param_' + self.parameter_data.index.astype(str)
        
        # Identify index columns
        index_cols = ['building_id'] if 'building_id' in self.parameter_data.columns else []
        if 'scenario' in self.parameter_data.columns:
            index_cols.append('scenario')
        
        if not index_cols or 'param_name' not in self.parameter_data.columns:
            # Return numeric columns directly
            return self.parameter_data[numeric_cols] if numeric_cols else pd.DataFrame()
        
        # Find value column
        value_col = None
        for col in ['value_numeric', 'value', 'numeric_value'] + numeric_cols:
            if col in self.parameter_data.columns:
                value_col = col
                break
        
        if value_col and index_cols:
            # Pivot to wide format
            try:
                pivot_df = self.parameter_data.pivot_table(
                    index=index_cols,
                    columns='param_name',
                    values=value_col,
                    aggfunc='first'
                )
                return pivot_df
            except Exception as e:
                self.logger.warning(f"Failed to pivot parameters: {e}")
        
        return pd.DataFrame()
    
    def _extract_output_deltas(self, 
                             output_variables: Optional[List[str]] = None) -> pd.DataFrame:
        """Extract output changes from comparison data"""
        if 'comparison_data' not in self.simulation_results:
            self.logger.warning("No comparison data available for delta calculation")
            return pd.DataFrame()
        
        if output_variables is None:
            output_variables = ['Heating:EnergyTransfer', 'Cooling:EnergyTransfer', 'Electricity:Facility']
        
        delta_records = []
        
        # Process each comparison file
        for var_name, df in self.simulation_results['comparison_data'].items():
            # Check if this variable matches requested outputs
            for req_var in output_variables:
                var_clean = req_var.split('[')[0].strip().lower()
                if var_clean in var_name.lower():
                    # Get variant columns
                    variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
                    
                    if variant_cols:
                        # Group by building
                        for building_id in df['building_id'].unique():
                            building_data = df[df['building_id'] == building_id]
                            
                            base_sum = building_data['base_value'].sum()
                            
                            # Calculate average change across variants
                            variant_sums = []
                            for var_col in variant_cols:
                                variant_sums.append(building_data[var_col].sum())
                            
                            avg_variant = np.mean(variant_sums)
                            delta = avg_variant - base_sum
                            pct_change = (delta / base_sum * 100) if base_sum != 0 else 0
                            
                            delta_records.append({
                                'building_id': building_id,
                                f'{var_clean}_base': base_sum,
                                f'{var_clean}_modified': avg_variant,
                                f'{var_clean}_delta': delta,
                                f'{var_clean}_pct_change': pct_change
                            })
        
        if delta_records:
            return pd.DataFrame(delta_records).groupby('building_id').first().reset_index()
        
        return pd.DataFrame()
    
    def _extract_outputs(self, 
                        output_variables: Optional[List[str]] = None) -> pd.DataFrame:
        """Extract output variables from base results"""
        if 'base' not in self.simulation_results:
            self.logger.warning("No base simulation results loaded")
            return pd.DataFrame()
        
        if output_variables is None:
            output_variables = ['Heating:EnergyTransfer', 'Cooling:EnergyTransfer', 'Electricity:Facility']
        
        output_records = []
        
        # Process base data by category
        for category, df in self.simulation_results['base'].items():
            if category == 'summary':
                continue
            
            # Process each requested variable
            for var in output_variables:
                var_clean = var.split('[')[0].strip()
                
                # Filter for this variable
                var_df = df[df['Variable'].str.contains(var_clean, case=False, na=False)]
                
                if not var_df.empty:
                    # Aggregate by building
                    for building_id in var_df['building_id'].unique():
                        building_var_data = var_df[var_df['building_id'] == building_id]
                        total_value = building_var_data['Value'].sum()
                        
                        output_records.append({
                            'building_id': building_id,
                            var_clean: total_value
                        })
        
        if output_records:
            # Combine records by building
            df = pd.DataFrame(output_records)
            return df.groupby('building_id').sum().reset_index()
        
        return pd.DataFrame()
    
    def load_metadata(self) -> pd.DataFrame:
        """Load building metadata - public method"""
        return self.building_metadata
    
    @property
    def metadata(self) -> pd.DataFrame:
        """Property for backward compatibility"""
        return self.building_metadata
    
    def get_building_info(self, building_id: Union[str, int]) -> Dict[str, Any]:
        """Get metadata for a specific building"""
        if self.building_metadata.empty:
            return {}
        
        building_id = str(building_id)
        
        if 'building_id' in self.building_metadata.columns:
            building_data = self.building_metadata[
                self.building_metadata['building_id'].astype(str) == building_id
            ]
            
            if not building_data.empty:
                return building_data.iloc[0].to_dict()
        
        return {}
    
    def get_available_categories(self) -> List[str]:
        """Get list of available parameter categories"""
        category_path = self.parsed_data_path / "idf_data" / "by_category"
        
        if not category_path.exists():
            return []
        
        categories = []
        for file_path in category_path.glob("*.parquet"):
            category = file_path.stem.split('_')[0]
            categories.append(category)
        
        return sorted(list(set(categories)))
    
    def get_available_outputs(self) -> List[str]:
        """Get list of available output variables"""
        outputs = set()
        
        # Check comparison files first
        comparison_path = self.modified_parsed_path / "comparisons"
        if comparison_path.exists():
            for file_path in comparison_path.glob("var_*.parquet"):
                # Extract variable name from filename
                parts = file_path.stem.split('_')
                building_part = next((i for i, p in enumerate(parts) if p.startswith('b')), -1)
                if building_part > 0:
                    variable_name = '_'.join(parts[1:building_part-2])
                    outputs.add(variable_name)
        
        # Also check base data
        if not outputs:
            base_daily = self.parsed_data_path / "timeseries" / "base_all_daily.parquet"
            if base_daily.exists():
                try:
                    df = pd.read_parquet(base_daily)
                    if 'VariableName' in df.columns:
                        for var in df['VariableName'].unique():
                            # Clean up variable name
                            if '[' in var:
                                var_name = var.split('[')[0].strip()
                            else:
                                var_name = var
                            outputs.add(var_name)
                except:
                    pass
        
        return sorted(list(outputs))
    
    def suggest_time_slices(self, output_variable: str = 'Heating:EnergyTransfer') -> Dict[str, Any]:
        """Suggest appropriate time slices based on data analysis"""
        from .time_slicer import TimeSlicer
        time_slicer = TimeSlicer(self.logger)
        
        suggestions = {}
        
        # Load base results if not already loaded
        if not self.simulation_results:
            self.load_simulation_results(load_modified=False)
        
        # Find data containing the output variable
        for category, df in self.simulation_results.get('base', {}).items():
            if category == 'summary':
                continue
            
            # Check if this category has the variable
            if 'Variable' in df.columns:
                var_df = df[df['Variable'].str.contains(output_variable, case=False, na=False)]
                if not var_df.empty and 'DateTime' in var_df.columns:
                    # Analyze peak periods
                    peak_suggestion = time_slicer.suggest_peak_periods(
                        var_df, 'Value', 'DateTime', n_months=3
                    )
                    suggestions.update(peak_suggestion)
                    break
        
        return suggestions
    
    def validate_data_availability(self, 
                                  require_modifications: bool = False,
                                  require_zones: bool = False,
                                  require_hourly: bool = False) -> Dict[str, bool]:
        """Check what data is available for analysis using new format"""
        status = {
            'has_parameters': False,
            'has_base_results': False,
            'has_modified_results': False,
            'has_comparison_files': False,
            'has_modifications': False,
            'has_zone_data': False,
            'has_building_metadata': False,
            'has_hourly_data': False,
            'ready_for_traditional': False,
            'ready_for_modification': False,
            'ready_for_multilevel': False,
            'ready_for_time_slicing': False
        }
        
        # Check parameters
        param_matrix = self.parsed_data_path / "analysis_ready" / "parameter_matrix.parquet"
        category_path = self.parsed_data_path / "idf_data" / "by_category"
        status['has_parameters'] = param_matrix.exists() or (category_path.exists() and list(category_path.glob("*.parquet")))
        
        # Check new format results
        base_daily = self.parsed_data_path / "timeseries" / "base_all_daily.parquet"
        status['has_base_results'] = base_daily.exists()
        
        # Check comparison files
        comparison_path = self.modified_parsed_path / "comparisons"
        if comparison_path.exists():
            comparison_files = list(comparison_path.glob("var_*.parquet"))
            status['has_comparison_files'] = len(comparison_files) > 0
            status['has_modified_results'] = status['has_comparison_files']
        
        # Check modifications
        mod_files = list(self.modifications_path.glob("modifications_detail_*.parquet"))
        status['has_modifications'] = len(mod_files) > 0
        
        # Check zone data - zones are included in the new format base files
        if status['has_base_results']:
            try:
                df = pd.read_parquet(base_daily)
                status['has_zone_data'] = 'Zone' in df.columns and len(df['Zone'].unique()) > 1
            except:
                pass
        
        # Check metadata
        status['has_building_metadata'] = not self.building_metadata.empty
        
        # Check hourly data
        base_hourly = self.parsed_data_path / "timeseries" / "base_all_hourly.parquet"
        status['has_hourly_data'] = base_hourly.exists()
        
        # Determine readiness
        status['ready_for_traditional'] = status['has_parameters'] and status['has_base_results']
        status['ready_for_modification'] = status['has_modifications'] and status['has_base_results'] and status['has_modified_results']
        status['ready_for_multilevel'] = status['ready_for_modification'] and status['has_zone_data']
        status['ready_for_time_slicing'] = status['has_base_results']  # Any frequency works
        
        return status
    
    def _load_comparison_results(self, 
                                result_type: str = 'daily',
                                variables: Optional[List[str]] = None,
                                time_slice_config: Optional[Dict[str, any]] = None) -> Dict[str, pd.DataFrame]:
        """Load results from new comparison file format"""
        from .time_slicer import TimeSlicer
        time_slicer = TimeSlicer(self.logger)
        
        comparison_path = self.modified_parsed_path / "comparisons"
        
        results = {
            'base': {},
            'modified': {},
            'variants': {},
            'comparison_data': {}
        }
        
        # Find all comparison files
        pattern = f"var_*_{result_type}_*.parquet"
        comparison_files = list(comparison_path.glob(pattern))
        
        if not comparison_files:
            self.logger.warning(f"No comparison files found for frequency: {result_type}")
            return {}
        
        self.logger.info(f"Found {len(comparison_files)} comparison files")
        
        # Group files by variable and building
        file_groups = {}
        for file_path in comparison_files:
            # Parse filename: var_{variable_name}_{unit}_{frequency}_b{building_id}.parquet
            parts = file_path.stem.split('_')
            if len(parts) >= 5 and parts[0] == 'var':
                # Extract variable name (may contain underscores)
                building_part = next((i for i, p in enumerate(parts) if p.startswith('b')), -1)
                if building_part > 0:
                    variable_name = '_'.join(parts[1:building_part-2])
                    unit = parts[building_part-2]
                    frequency = parts[building_part-1]
                    building_id = parts[building_part][1:]  # Remove 'b' prefix
                    
                    if frequency == result_type:
                        if variable_name not in file_groups:
                            file_groups[variable_name] = []
                        file_groups[variable_name].append({
                            'path': file_path,
                            'building_id': building_id,
                            'unit': unit
                        })
        
        # Filter by requested variables if specified
        if variables:
            filtered_groups = {}
            for var in variables:
                # Clean variable name more thoroughly - remove colons and brackets
                var_clean = var.split('[')[0].strip().lower()
                var_clean = var_clean.replace(':', '').replace('_', '')  # Remove colons and underscores
                
                for var_name, files in file_groups.items():
                    var_name_clean = var_name.lower().replace('_', '')
                    if var_clean in var_name_clean or var_name_clean in var_clean:
                        filtered_groups[var_name] = files
            file_groups = filtered_groups
        
        # Load data from comparison files
        all_base_data = []
        all_modified_data = []
        variant_data_by_id = {}
        
        for variable_name, file_list in file_groups.items():
            variable_base_data = []
            variable_modified_data = []
            
            for file_info in file_list:
                try:
                    df = pd.read_parquet(file_info['path'])
                    
                    # Apply time slicing if configured
                    if time_slice_config and time_slice_config.get('enabled', False) and 'timestamp' in df.columns:
                        df = time_slicer.slice_data(df, time_slice_config, 'timestamp')
                    
                    # Extract base and variant data
                    if 'base_value' in df.columns:
                        # Select available columns
                        base_cols = ['timestamp', 'building_id', 'variable_name', 'category', 'Units', 'base_value']
                        if 'Zone' in df.columns:
                            base_cols.insert(2, 'Zone')
                        
                        base_df = df[base_cols].copy()
                        base_df.rename(columns={'base_value': 'Value'}, inplace=True)
                        
                        # Add Zone column if missing
                        if 'Zone' not in base_df.columns:
                            base_df['Zone'] = 'Building'
                        
                        variable_base_data.append(base_df)
                    
                    # Find variant columns
                    variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
                    
                    for variant_col in variant_cols:
                        variant_id = variant_col.replace('_value', '')
                        
                        # Select available columns
                        variant_cols_list = ['timestamp', 'building_id', 'variable_name', 'category', 'Units', variant_col]
                        if 'Zone' in df.columns:
                            variant_cols_list.insert(2, 'Zone')
                        
                        variant_df = df[variant_cols_list].copy()
                        variant_df.rename(columns={variant_col: 'Value'}, inplace=True)
                        variant_df['variant_id'] = variant_id
                        
                        # Add Zone column if missing
                        if 'Zone' not in variant_df.columns:
                            variant_df['Zone'] = 'Building'
                        
                        if variant_id not in variant_data_by_id:
                            variant_data_by_id[variant_id] = []
                        variant_data_by_id[variant_id].append(variant_df)
                    
                    # Store comparison data for direct analysis
                    if variable_name not in results['comparison_data']:
                        results['comparison_data'][variable_name] = []
                    results['comparison_data'][variable_name].append(df)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load comparison file {file_info['path']}: {e}")
            
            if variable_base_data:
                all_base_data.extend(variable_base_data)
            if variable_modified_data:
                all_modified_data.extend(variable_modified_data)
        
        # Combine base data
        if all_base_data:
            combined_base = pd.concat(all_base_data, ignore_index=True)
            # Group by category for backward compatibility
            for category in combined_base['category'].unique():
                results['base'][category] = combined_base[combined_base['category'] == category]
        
        # Combine variant data
        if variant_data_by_id:
            # Use the first variant as 'modified' for backward compatibility
            first_variant = next(iter(variant_data_by_id.keys()))
            if variant_data_by_id[first_variant]:
                combined_modified = pd.concat(variant_data_by_id[first_variant], ignore_index=True)
                for category in combined_modified['category'].unique():
                    results['modified'][category] = combined_modified[combined_modified['category'] == category]
            
            # Store all variants
            for variant_id, variant_dfs in variant_data_by_id.items():
                if variant_dfs:
                    results['variants'][variant_id] = pd.concat(variant_dfs, ignore_index=True)
        
        # Concatenate comparison data by variable
        for variable_name, dfs in results['comparison_data'].items():
            if dfs:
                results['comparison_data'][variable_name] = pd.concat(dfs, ignore_index=True)
        
        self.logger.info(f"Loaded comparison data for {len(file_groups)} variables")
        if results['variants']:
            self.logger.info(f"Found {len(results['variants'])} variants")
        
        return results
    
    def _load_new_base_format(self, 
                             result_type: str = 'daily',
                             variables: Optional[List[str]] = None,
                             time_slice_config: Optional[Dict[str, any]] = None) -> Dict[str, pd.DataFrame]:
        """Load data from new semi-wide base format"""
        from .time_slicer import TimeSlicer
        time_slicer = TimeSlicer(self.logger)
        
        file_path = self.parsed_data_path / "timeseries" / f"base_all_{result_type}.parquet"
        
        if not file_path.exists():
            self.logger.warning(f"Base file not found: {file_path}")
            return {}
        
        try:
            # Load the semi-wide format data
            df = pd.read_parquet(file_path)
            
            # Convert from semi-wide to long format
            id_vars = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
            date_cols = [col for col in df.columns if col not in id_vars]
            
            # Melt to long format
            long_df = df.melt(
                id_vars=id_vars,
                value_vars=date_cols,
                var_name='timestamp',
                value_name='Value'
            )
            
            # Convert timestamp to datetime
            long_df['timestamp'] = pd.to_datetime(long_df['timestamp'])
            
            # Apply time slicing if configured
            if time_slice_config and time_slice_config.get('enabled', False):
                long_df = time_slicer.slice_data(long_df, time_slice_config, 'timestamp')
            
            # Filter by variables if specified
            if variables:
                variable_masks = []
                for var in variables:
                    var_clean = var.split('[')[0].strip()
                    variable_masks.append(long_df['VariableName'].str.contains(var_clean, case=False, na=False))
                
                if variable_masks:
                    combined_mask = pd.concat(variable_masks, axis=1).any(axis=1)
                    long_df = long_df[combined_mask]
            
            # Group by category for backward compatibility
            results = {}
            for category in long_df['category'].unique():
                category_df = long_df[long_df['category'] == category].copy()
                category_df.rename(columns={'VariableName': 'Variable'}, inplace=True)
                results[category] = category_df
            
            self.logger.info(f"Loaded {len(long_df)} records from new base format")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to load new base format: {e}")
            return {}
    
    def load_variant_comparison_data(self, 
                                   variable_name: str,
                                   building_id: Optional[str] = None,
                                   frequency: str = 'daily') -> pd.DataFrame:
        """Load comparison data for a specific variable across all variants"""
        comparison_path = self.modified_parsed_path / "comparisons"
        
        # Build file pattern
        if building_id:
            pattern = f"var_{variable_name}_*_{frequency}_b{building_id}.parquet"
        else:
            pattern = f"var_{variable_name}_*_{frequency}_*.parquet"
        
        files = list(comparison_path.glob(pattern))
        
        if not files:
            self.logger.warning(f"No comparison files found for variable: {variable_name}")
            return pd.DataFrame()
        
        dfs = []
        for file_path in files:
            try:
                df = pd.read_parquet(file_path)
                dfs.append(df)
            except Exception as e:
                self.logger.warning(f"Failed to load {file_path}: {e}")
        
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            self.logger.info(f"Loaded comparison data for {variable_name}: {len(combined)} records")
            return combined
        
        return pd.DataFrame()
    
    def get_variant_sensitivity_data(self, frequency: str = 'daily') -> pd.DataFrame:
        """Get data formatted for variant-based sensitivity analysis"""
        comparison_path = self.modified_parsed_path / "comparisons"
        
        # Load modification tracking
        if self.modification_data is None:
            self.load_modification_tracking()
        
        # Find all comparison files
        pattern = f"var_*_{frequency}_*.parquet"
        comparison_files = list(comparison_path.glob(pattern))
        
        if not comparison_files:
            self.logger.warning("No comparison files found")
            return pd.DataFrame()
        
        sensitivity_data = []
        
        for file_path in comparison_files:
            try:
                # Parse filename
                parts = file_path.stem.split('_')
                building_part = next((i for i, p in enumerate(parts) if p.startswith('b')), -1)
                
                if building_part > 0:
                    variable_name = '_'.join(parts[1:building_part-2])
                    building_id = parts[building_part][1:]
                    
                    # Load comparison data
                    df = pd.read_parquet(file_path)
                    
                    # Get variant columns
                    variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
                    
                    for variant_col in variant_cols:
                        variant_id = variant_col.replace('_value', '')
                        
                        # Calculate sensitivity metrics
                        base_values = df['base_value'].values
                        variant_values = df[variant_col].values
                        
                        # Remove NaN values
                        mask = ~(np.isnan(base_values) | np.isnan(variant_values))
                        base_values = base_values[mask]
                        variant_values = variant_values[mask]
                        
                        if len(base_values) > 0:
                            # Calculate various sensitivity metrics
                            abs_change = np.mean(np.abs(variant_values - base_values))
                            
                            # Percentage change (handle zeros)
                            with np.errstate(divide='ignore', invalid='ignore'):
                                pct_changes = (variant_values - base_values) / base_values * 100
                                pct_changes[~np.isfinite(pct_changes)] = 0
                                avg_pct_change = np.mean(np.abs(pct_changes))
                            
                            # Normalized sensitivity (change per unit parameter change)
                            if self.modification_data is not None:
                                # Find parameter changes for this variant
                                variant_mods = self.modification_data[
                                    (self.modification_data['variant_id'] == variant_id) &
                                    (self.modification_data['building_id'] == building_id)
                                ]
                                
                                if not variant_mods.empty:
                                    # Get average parameter change
                                    avg_param_change = variant_mods['value_pct_change'].abs().mean()
                                    
                                    if avg_param_change > 0:
                                        normalized_sensitivity = avg_pct_change / avg_param_change
                                    else:
                                        normalized_sensitivity = 0
                                else:
                                    normalized_sensitivity = avg_pct_change
                            else:
                                normalized_sensitivity = avg_pct_change
                            
                            sensitivity_data.append({
                                'building_id': building_id,
                                'variant_id': variant_id,
                                'output_variable': variable_name,
                                'frequency': frequency,
                                'absolute_change': abs_change,
                                'percent_change': avg_pct_change,
                                'normalized_sensitivity': normalized_sensitivity,
                                'n_observations': len(base_values)
                            })
                            
            except Exception as e:
                self.logger.warning(f"Failed to process {file_path}: {e}")
        
        if sensitivity_data:
            sensitivity_df = pd.DataFrame(sensitivity_data)
            self.logger.info(f"Created sensitivity data with {len(sensitivity_df)} records")
            return sensitivity_df
        
        return pd.DataFrame()