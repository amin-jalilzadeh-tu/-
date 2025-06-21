"""
sensitivity_data_manager.py - Data integration for enhanced sensitivity analysis

Handles:
- Parameter discovery from parsed IDF data
- Simulation results loading and merging
- Validation results integration
- Data preparation for sensitivity analysis
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SensitivityDataManager:
    """Manages data integration for sensitivity analysis"""
    
    def __init__(self, project_root: str):
        """
        Initialize data manager
        
        Args:
            project_root: Root directory containing parsed_data, results, etc.
        """
        self.project_root = Path(project_root)
        self.parsed_data_dir = self.project_root / "parsed_data"
        self.cache_dir = self.project_root / "sensitivity_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Data containers
        self.available_parameters = {}
        self.validation_results = None
        self.building_metadata = None
        
    def discover_parameters(self, 
                          categories: Optional[List[str]] = None,
                          exclude_non_numeric: bool = True) -> pd.DataFrame:
        """
        Discover all modifiable parameters from parsed IDF data
        
        Args:
            categories: List of categories to include (hvac, dhw, etc.)
            exclude_non_numeric: Whether to exclude non-numeric parameters
            
        Returns:
            DataFrame with parameter information
        """
        logger.info("Discovering parameters from parsed IDF data...")
        
        # Define category files to scan
        category_files = {
            'hvac': ['hvac_equipment', 'hvac_systems', 'hvac_thermostats'],
            'dhw': ['dhw'],
            'lighting': ['lighting'],
            'equipment': ['equipment'],
            'infiltration': ['infiltration'],
            'ventilation': ['ventilation'],
            'materials': ['materials_constructions', 'materials_materials'],
            'geometry': ['geometry_zones', 'geometry_surfaces'],
            'shading': ['shading']
        }
        
        # Filter categories if specified
        if categories:
            category_files = {k: v for k, v in category_files.items() if k in categories}
        
        all_params = []
        
        # Scan each category
        for category, files in category_files.items():
            for file_name in files:
                file_path = self.parsed_data_dir / 'idf_data' / 'by_category' / f"{file_name}.parquet"
                
                if file_path.exists():
                    try:
                        df = pd.read_parquet(file_path)
                        
                        # Identify numeric columns (potential parameters)
                        numeric_cols = []
                        for col in df.columns:
                            if col not in ['building_id', 'object_type', 'object_name', 'zone_name']:
                                # Check if column has numeric values
                                if exclude_non_numeric:
                                    try:
                                        test_vals = pd.to_numeric(df[col], errors='coerce')
                                        if not test_vals.isna().all():
                                            numeric_cols.append(col)
                                    except:
                                        pass
                                else:
                                    numeric_cols.append(col)
                        
                        # Create parameter entries
                        for col in numeric_cols:
                            # Get value statistics
                            if pd.api.types.is_numeric_dtype(df[col]):
                                stats = {
                                    'min': df[col].min(),
                                    'max': df[col].max(),
                                    'mean': df[col].mean(),
                                    'std': df[col].std(),
                                    'count': df[col].notna().sum()
                                }
                            else:
                                stats = {
                                    'unique_values': df[col].nunique(),
                                    'count': df[col].notna().sum()
                                }
                            
                            param_info = {
                                'category': category,
                                'source_file': file_name,
                                'parameter_name': col,
                                'data_type': str(df[col].dtype),
                                'buildings_with_data': df['building_id'].nunique() if 'building_id' in df.columns else 0,
                                **stats
                            }
                            
                            all_params.append(param_info)
                            
                    except Exception as e:
                        logger.warning(f"Error reading {file_path}: {e}")
        
        params_df = pd.DataFrame(all_params)
        
        # Cache the discovered parameters
        cache_file = self.cache_dir / "discovered_parameters.parquet"
        params_df.to_parquet(cache_file)
        logger.info(f"Discovered {len(params_df)} parameters across {len(category_files)} categories")
        
        return params_df
    
    def load_validation_results(self, validation_csv: Optional[str] = None) -> pd.DataFrame:
        """
        Load validation results to weight sensitivity analysis
        
        Args:
            validation_csv: Path to validation results CSV
            
        Returns:
            DataFrame with validation metrics per building
        """
        if validation_csv and os.path.exists(validation_csv):
            logger.info(f"Loading validation results from {validation_csv}")
            self.validation_results = pd.read_csv(validation_csv)
            
            # Calculate validation score (inverse of CV-RMSE)
            if 'CV(RMSE)' in self.validation_results.columns:
                # Lower CV-RMSE is better, so invert for weighting
                max_cvrmse = self.validation_results['CV(RMSE)'].max()
                self.validation_results['validation_weight'] = 1 - (
                    self.validation_results['CV(RMSE)'] / max_cvrmse
                )
            
            return self.validation_results
        else:
            logger.warning("No validation results loaded")
            return pd.DataFrame()
    
    def prepare_sensitivity_data(self,
                               scenario_folder: str,
                               results_csv: str,
                               target_variables: Union[str, List[str]],
                               building_filter: Optional[Dict[str, Any]] = None,
                               use_validation_weights: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """
        Prepare data for sensitivity analysis with all enhancements
        
        Args:
            scenario_folder: Folder containing scenario parameter files
            results_csv: Path to simulation results
            target_variables: Variable(s) to analyze
            building_filter: Filter buildings by characteristics
            use_validation_weights: Whether to include validation weights
            
        Returns:
            Tuple of (parameters_df, results_df, metadata_dict)
        """
        logger.info("Preparing data for sensitivity analysis...")
        
        # Load scenario parameters
        params_df = self._load_and_merge_scenarios(scenario_folder)
        
        # Load simulation results
        results_df = pd.read_csv(results_csv)
        
        # Apply building filters if specified
        if building_filter:
            params_df, results_df = self._apply_building_filters(
                params_df, results_df, building_filter
            )
        
        # Add validation weights if available
        if use_validation_weights and self.validation_results is not None:
            params_df = self._add_validation_weights(params_df)
        
        # Calculate parameter statistics
        param_stats = self._calculate_parameter_stats(params_df)
        
        # Prepare metadata
        metadata = {
            'num_scenarios': params_df['scenario_index'].nunique() if 'scenario_index' in params_df.columns else 0,
            'num_parameters': len(params_df.columns) - 2,  # Exclude scenario_index and building_id
            'num_buildings': params_df['ogc_fid'].nunique() if 'ogc_fid' in params_df.columns else 0,
            'target_variables': target_variables if isinstance(target_variables, list) else [target_variables],
            'parameter_stats': param_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        return params_df, results_df, metadata
    



    # Add these methods inside the SensitivityDataManager class in sensitivity_data_manager.py

    def has_parsed_data(self) -> bool:
        """
        Check if parsed data directory exists and contains data
        
        Returns:
            bool: True if parsed data exists
        """
        if not self.parsed_data_dir.exists():
            logger.warning(f"Parsed data directory not found: {self.parsed_data_dir}")
            return False
        
        # Check if there are any parquet files in the parsed data directory
        parquet_files = list(self.parsed_data_dir.glob("*.parquet"))
        
        if not parquet_files:
            logger.warning(f"No parquet files found in: {self.parsed_data_dir}")
            return False
        
        logger.info(f"Found {len(parquet_files)} parquet files in parsed data directory")
        return True

    def has_time_series_data(self) -> bool:
        """
        Check if time series data exists in the project
        
        Returns:
            bool: True if time series data exists
        """
        # Check for time series folders (e.g., hvac_2013, zones_2013, etc.)
        time_series_patterns = [
            "hvac_*",
            "zones_*", 
            "ventilation_*",
            "*_hourly",
            "*_daily",
            "*_monthly",
            "*_2013",
            "*_2014"
        ]
        
        time_series_found = False
        
        # Check in the project root for time series folders
        for pattern in time_series_patterns:
            matching_dirs = list(self.project_root.glob(pattern))
            if matching_dirs:
                time_series_found = True
                logger.info(f"Found time series data matching pattern '{pattern}': {len(matching_dirs)} directories")
                
        # Also check in parsed_data for time series parquet files
        if self.parsed_data_dir.exists():
            for pattern in time_series_patterns:
                matching_files = list(self.parsed_data_dir.glob(f"{pattern}.parquet"))
                if matching_files:
                    time_series_found = True
                    logger.info(f"Found time series files matching pattern '{pattern}.parquet': {len(matching_files)} files")
        
        if not time_series_found:
            logger.warning("No time series data found in project")
        
        return time_series_found
    



















    def _load_and_merge_scenarios(self, scenario_folder: str) -> pd.DataFrame:
        """Load and merge all scenario parameter files"""
        import glob
        
        scenario_files = glob.glob(os.path.join(scenario_folder, "scenario_params_*.csv"))
        all_scenarios = []
        
        for file in scenario_files:
            df = pd.read_csv(file)
            
            # Standardize column names
            if 'assigned_value' not in df.columns and 'param_value' in df.columns:
                df['assigned_value'] = df['param_value']
            
            # Create unique parameter names
            if 'zone_name' in df.columns and 'param_name' in df.columns:
                df['full_param_name'] = df['zone_name'].fillna('') + '_' + df['param_name']
            else:
                df['full_param_name'] = df['param_name']
            
            all_scenarios.append(df)
        
        # Combine all scenarios
        combined_df = pd.concat(all_scenarios, ignore_index=True)
        
        # Pivot to wide format
        pivot_df = combined_df.pivot_table(
            index=['scenario_index', 'ogc_fid'],
            columns='full_param_name',
            values='assigned_value',
            aggfunc='first'
        ).reset_index()
        
        return pivot_df
    
    def _apply_building_filters(self, 
                              params_df: pd.DataFrame,
                              results_df: pd.DataFrame,
                              building_filter: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Apply building characteristic filters"""
        
        # Load building metadata if needed
        if self.building_metadata is None:
            metadata_path = self.project_root / "data" / "df_buildings.csv"
            if metadata_path.exists():
                self.building_metadata = pd.read_csv(metadata_path)
        
        if self.building_metadata is not None:
            # Apply filters
            filtered_metadata = self.building_metadata.copy()
            
            if 'building_function' in building_filter:
                filtered_metadata = filtered_metadata[
                    filtered_metadata['building_function'].isin(building_filter['building_function'])
                ]
            
            if 'age_range' in building_filter:
                filtered_metadata = filtered_metadata[
                    filtered_metadata['age_range'].isin(building_filter['age_range'])
                ]
            
            # Get filtered building IDs
            filtered_ids = filtered_metadata['ogc_fid'].unique()
            
            # Filter parameters and results
            if 'ogc_fid' in params_df.columns:
                params_df = params_df[params_df['ogc_fid'].isin(filtered_ids)]
            
            if 'BuildingID' in results_df.columns:
                results_df = results_df[results_df['BuildingID'].isin(filtered_ids)]
        
        return params_df, results_df
    
    def _add_validation_weights(self, params_df: pd.DataFrame) -> pd.DataFrame:
        """Add validation weights to parameters"""
        if 'ogc_fid' in params_df.columns and 'building_id' in self.validation_results.columns:
            # Merge validation weights
            weight_cols = ['building_id', 'validation_weight']
            if 'CV(RMSE)' in self.validation_results.columns:
                weight_cols.append('CV(RMSE)')
            
            params_df = params_df.merge(
                self.validation_results[weight_cols],
                left_on='ogc_fid',
                right_on='building_id',
                how='left'
            )
            
            # Fill missing weights with default
            params_df['validation_weight'] = params_df['validation_weight'].fillna(0.5)
        
        return params_df
    
    def _calculate_parameter_stats(self, params_df: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate statistics for each parameter"""
        stats = {}
        
        # Identify parameter columns
        exclude_cols = ['scenario_index', 'ogc_fid', 'building_id', 
                       'validation_weight', 'CV(RMSE)']
        param_cols = [col for col in params_df.columns if col not in exclude_cols]
        
        for col in param_cols:
            if pd.api.types.is_numeric_dtype(params_df[col]):
                stats[col] = {
                    'min': params_df[col].min(),
                    'max': params_df[col].max(),
                    'mean': params_df[col].mean(),
                    'std': params_df[col].std(),
                    'range': params_df[col].max() - params_df[col].min(),
                    'cv': params_df[col].std() / params_df[col].mean() if params_df[col].mean() != 0 else 0
                }
        
        return stats
    
    def get_building_groups(self, 
                          group_by: List[str] = ['building_function', 'age_range'],
                          min_buildings: int = 3) -> Dict[str, List[str]]:
        """
        Group buildings for separate sensitivity analyses
        
        Args:
            group_by: Columns to group by
            min_buildings: Minimum buildings per group
            
        Returns:
            Dictionary of group_name -> building_ids
        """
        if self.building_metadata is None:
            return {'all': []}
        
        groups = {}
        
        # Create groups
        for name, group_df in self.building_metadata.groupby(group_by):
            if len(group_df) >= min_buildings:
                group_key = '_'.join([str(v) for v in (name if isinstance(name, tuple) else [name])])
                groups[group_key] = group_df['ogc_fid'].tolist()
        
        # Add an 'all' group
        groups['all'] = self.building_metadata['ogc_fid'].tolist()
        
        return groups
    
    def export_for_surrogate(self, 
                           sensitivity_results: pd.DataFrame,
                           output_path: str,
                           top_n: int = 20):
        """
        Export top sensitive parameters for surrogate modeling
        
        Args:
            sensitivity_results: Results from sensitivity analysis
            output_path: Where to save the export
            top_n: Number of top parameters to export
        """
        # Sort by absolute correlation or sensitivity index
        if 'AbsCorrelation' in sensitivity_results.columns:
            sorted_results = sensitivity_results.nlargest(top_n, 'AbsCorrelation')
        elif 'S1' in sensitivity_results.columns:  # Sobol first-order
            sorted_results = sensitivity_results.nlargest(top_n, 'S1')
        else:
            sorted_results = sensitivity_results.head(top_n)
        
        # Export parameter list and bounds
        export_data = {
            'parameters': sorted_results['Parameter'].tolist() if 'Parameter' in sorted_results.columns else [],
            'sensitivity_scores': sorted_results.to_dict('records'),
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'top_n': top_n,
                'source': 'sensitivity_analysis'
            }
        }
        
        # Save as JSON
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported top {top_n} parameters for surrogate modeling to {output_path}")
    
    def export_for_calibration(self,
                             sensitivity_results: pd.DataFrame,
                             parameter_bounds: pd.DataFrame,
                             output_path: str,
                             sensitivity_threshold: float = 0.1):
        """
        Export parameter bounds and recommendations for calibration
        
        Args:
            sensitivity_results: Results from sensitivity analysis  
            parameter_bounds: Parameter min/max bounds
            output_path: Where to save the export
            sensitivity_threshold: Minimum sensitivity to include parameter
        """
        # Filter parameters by sensitivity threshold
        if 'AbsCorrelation' in sensitivity_results.columns:
            significant_params = sensitivity_results[
                sensitivity_results['AbsCorrelation'] >= sensitivity_threshold
            ]
        else:
            significant_params = sensitivity_results
        
        # Merge with bounds
        calibration_data = []
        
        for _, param in significant_params.iterrows():
            param_name = param.get('Parameter', '')
            
            # Find bounds
            bounds_row = parameter_bounds[parameter_bounds['name'] == param_name]
            if not bounds_row.empty:
                calibration_data.append({
                    'parameter': param_name,
                    'min_value': bounds_row.iloc[0]['min_value'],
                    'max_value': bounds_row.iloc[0]['max_value'],
                    'sensitivity_score': param.get('AbsCorrelation', param.get('S1', 0)),
                    'recommended_for_calibration': True
                })
        
        # Export
        export_dict = {
            'calibration_parameters': calibration_data,
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'sensitivity_threshold': sensitivity_threshold,
                'num_parameters': len(calibration_data)
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_dict, f, indent=2)
        
        logger.info(f"Exported {len(calibration_data)} parameters for calibration to {output_path}")