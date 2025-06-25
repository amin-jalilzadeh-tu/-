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
                              load_modified: bool = True) -> Dict[str, pd.DataFrame]:
        """Load simulation results for base and optionally modified runs"""
        self.logger.info(f"Loading {result_type} simulation results...")
        
        results = {}
        
        # Load base results
        base_path = self.parsed_data_path / f"sql_results/timeseries/aggregated/{result_type}"
        if base_path.exists():
            results['base'] = self._load_results_from_path(base_path, variables)
            self.logger.info(f"Loaded base results: {sum(len(df) for df in results['base'].values())} records")
        
        # Load modified results if requested
        if load_modified:
            mod_path = self.modified_parsed_path / f"sql_results/timeseries/aggregated/{result_type}"
            if mod_path.exists():
                results['modified'] = self._load_results_from_path(mod_path, variables)
                self.logger.info(f"Loaded modified results: {sum(len(df) for df in results['modified'].values())} records")
        
        # Also load summary metrics
        self._load_summary_metrics(results)
        
        self.simulation_results = results
        return results
    
    def _load_results_from_path(self, 
                               path: Path, 
                               variables: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """Load results from a specific path"""
        results = {}
        
        # Categories to load
        categories = ['hvac', 'energy', 'electricity', 'temperature', 'zones', 'ventilation']
        
        for category in categories:
            file_path = path / f"{category}_{path.parent.name}.parquet"
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    
                    # Filter by variables if specified
                    if variables:
                        cols_to_keep = ['Date', 'building_id']
                        if 'Zone' in df.columns:
                            cols_to_keep.append('Zone')
                        
                        # Find matching columns
                        for var in variables:
                            var_clean = var.split('[')[0].strip()
                            matching_cols = [col for col in df.columns 
                                           if var_clean in col and col not in cols_to_keep]
                            cols_to_keep.extend(matching_cols)
                        
                        df = df[cols_to_keep]
                    
                    results[category] = df
                    self.logger.debug(f"Loaded {category}: {len(df)} records")
                except Exception as e:
                    self.logger.warning(f"Failed to load {file_path}: {e}")
        
        return results
    
    def _load_summary_metrics(self, results_dict: Dict[str, Dict[str, pd.DataFrame]]):
        """Load annual summary metrics"""
        for result_type in ['base', 'modified']:
            if result_type not in results_dict:
                continue
            
            if result_type == 'base':
                summary_path = self.parsed_data_path / "sql_results/summary_metrics/annual_summary.parquet"
            else:
                summary_path = self.modified_parsed_path / "sql_results/summary_metrics/annual_summary.parquet"
            
            if summary_path.exists():
                try:
                    results_dict[result_type]['summary'] = pd.read_parquet(summary_path)
                    self.logger.debug(f"Loaded {result_type} summary metrics")
                except Exception as e:
                    self.logger.warning(f"Failed to load summary metrics: {e}")
    
    def create_analysis_dataset(self,
                              output_variables: Optional[List[str]] = None,
                              use_modifications: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create X (parameters) and y (outputs) datasets for analysis
        
        Args:
            output_variables: List of output variables to include
            use_modifications: Whether to use modification data (True) or parameters (False)
            
        Returns:
            Tuple of (X_parameters, y_outputs) DataFrames
        """
        self.logger.info("Creating analysis dataset...")
        
        if use_modifications and self.modification_data is not None:
            # Create from modifications
            return self._create_modification_dataset(output_variables)
        else:
            # Create from parameters
            return self._create_parameter_dataset(output_variables)
    
    def _create_modification_dataset(self, 
                                   output_variables: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create dataset from modification tracking"""
        if self.modification_data is None:
            self.load_modification_tracking()
        
        if not self.simulation_results:
            self.load_simulation_results()
        
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
                                output_variables: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create dataset from IDF parameters"""
        if self.parameter_data is None:
            self.load_idf_parameters()
        
        if not self.simulation_results:
            self.load_simulation_results(load_modified=False)
        
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
        """Extract output changes between base and modified"""
        if 'base' not in self.simulation_results or 'modified' not in self.simulation_results:
            self.logger.warning("Both base and modified results needed for deltas")
            return pd.DataFrame()
        
        if output_variables is None:
            output_variables = ['Heating:EnergyTransfer', 'Cooling:EnergyTransfer', 'Electricity:Facility']
        
        delta_dfs = []
        
        for category in ['hvac', 'energy', 'electricity']:
            if category not in self.simulation_results['base'] or category not in self.simulation_results['modified']:
                continue
            
            base_df = self.simulation_results['base'][category]
            mod_df = self.simulation_results['modified'][category]
            
            # Aggregate by building
            base_agg = base_df.groupby('building_id').sum()
            mod_agg = mod_df.groupby('building_id').sum()
            
            # Calculate deltas for matching columns
            for var in output_variables:
                matching_cols = [col for col in base_agg.columns if var in col]
                
                for col in matching_cols:
                    if col in mod_agg.columns:
                        delta_col = f"{var}_delta"
                        delta_df = pd.DataFrame(index=base_agg.index)
                        delta_df[delta_col] = mod_agg[col] - base_agg[col]
                        delta_df[f"{var}_pct_change"] = (delta_df[delta_col] / base_agg[col].replace(0, np.nan)) * 100
                        delta_dfs.append(delta_df)
        
        if delta_dfs:
            return pd.concat(delta_dfs, axis=1)
        
        return pd.DataFrame()
    
    def _extract_outputs(self, 
                        output_variables: Optional[List[str]] = None) -> pd.DataFrame:
        """Extract output variables from simulation results"""
        if 'base' not in self.simulation_results:
            self.logger.warning("No base simulation results loaded")
            return pd.DataFrame()
        
        if output_variables is None:
            output_variables = ['Heating:EnergyTransfer', 'Cooling:EnergyTransfer', 'Electricity:Facility']
        
        output_dfs = []
        
        for category, df in self.simulation_results['base'].items():
            if category == 'summary':
                continue
            
            # Find matching columns
            for var in output_variables:
                matching_cols = [col for col in df.columns if var in col and col not in ['Date', 'building_id', 'Zone']]
                
                if matching_cols:
                    # Aggregate by building
                    if 'building_id' in df.columns:
                        agg_df = df.groupby('building_id')[matching_cols].sum()
                    else:
                        agg_df = df[matching_cols].sum().to_frame().T
                    
                    output_dfs.append(agg_df)
        
        if output_dfs:
            return pd.concat(output_dfs, axis=1)
        
        return pd.DataFrame()
    
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
        if not self.simulation_results:
            self.load_simulation_results(load_modified=False)
        
        outputs = set()
        
        for result_type, categories in self.simulation_results.items():
            for category, df in categories.items():
                if category == 'summary':
                    continue
                
                # Extract variable names from columns
                for col in df.columns:
                    if col not in ['Date', 'building_id', 'Zone', 'datetime']:
                        # Clean up variable name
                        if '[' in col:
                            var_name = col.split('[')[0].strip()
                            outputs.add(var_name)
        
        return sorted(list(outputs))
    
    def validate_data_availability(self, 
                                  require_modifications: bool = False,
                                  require_zones: bool = False) -> Dict[str, bool]:
        """Check what data is available for analysis"""
        status = {
            'has_parameters': False,
            'has_base_results': False,
            'has_modified_results': False,
            'has_modifications': False,
            'has_zone_data': False,
            'has_building_metadata': False,
            'ready_for_traditional': False,
            'ready_for_modification': False,
            'ready_for_multilevel': False
        }
        
        # Check parameters
        param_matrix = self.parsed_data_path / "analysis_ready" / "parameter_matrix.parquet"
        category_path = self.parsed_data_path / "idf_data" / "by_category"
        status['has_parameters'] = param_matrix.exists() or (category_path.exists() and list(category_path.glob("*.parquet")))
        
        # Check results
        base_path = self.parsed_data_path / "sql_results/timeseries/aggregated/daily"
        status['has_base_results'] = base_path.exists() and list(base_path.glob("*.parquet"))
        
        mod_path = self.modified_parsed_path / "sql_results/timeseries/aggregated/daily"
        status['has_modified_results'] = mod_path.exists() and list(mod_path.glob("*.parquet"))
        
        # Check modifications
        mod_files = list(self.modifications_path.glob("modifications_detail_*.parquet"))
        status['has_modifications'] = len(mod_files) > 0
        
        # Check zone data
        zone_path = base_path / "zones_daily.parquet"
        status['has_zone_data'] = zone_path.exists()
        
        # Check metadata
        status['has_building_metadata'] = not self.building_metadata.empty
        
        # Determine readiness
        status['ready_for_traditional'] = status['has_parameters'] and status['has_base_results']
        status['ready_for_modification'] = status['has_modifications'] and status['has_base_results'] and status['has_modified_results']
        status['ready_for_multilevel'] = status['ready_for_modification'] and status['has_zone_data']
        
        return status
