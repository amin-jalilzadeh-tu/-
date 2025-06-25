"""
c_sensitivity/sensitivity_data_manager.py

Enhanced data manager for sensitivity analysis with modification support.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple, Any
import json
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

class SensitivityDataManager:
    """Manages data loading and preprocessing for sensitivity analysis"""
    
    def __init__(self, project_root: Path, logger: Optional[logging.Logger] = None):
        self.project_root = Path(project_root)
        self.logger = logger or logging.getLogger(__name__)
        
        # Define standard paths
        self.parsed_data_path = self.project_root / "parsed_data"
        self.modified_parsed_path = self.project_root / "parsed_modified_results"
        self.modifications_path = self.project_root / "modified_idfs"
        self.scenarios_path = self.project_root / "scenarios"
        
        # Data containers
        self.parameter_data = {}
        self.simulation_results = {}
        self.modification_data = None
        self.building_metadata = {}
        
    def has_parsed_data(self) -> bool:
        """Check if parsed data exists"""
        return self.parsed_data_path.exists() and any(self.parsed_data_path.iterdir())
    
    def has_modification_data(self) -> bool:
        """Check if modification tracking data exists"""
        if not self.modifications_path.exists():
            return False
        mod_files = list(self.modifications_path.glob("modifications_detail_*.parquet"))
        return len(mod_files) > 0
    
    def has_time_series_data(self) -> bool:
        """Check if time series data exists"""
        ts_path = self.parsed_data_path / "sql_results" / "timeseries"
        return ts_path.exists() and any(ts_path.rglob("*.parquet"))
    
    def load_idf_parameters(self, categories: Optional[List[str]] = None) -> pd.DataFrame:
        """Load IDF parameters from parsed data"""
        self.logger.info("Loading IDF parameters from parsed data...")
        
        # Define category paths
        category_path = self.parsed_data_path / "idf_data" / "by_category"
        
        if not category_path.exists():
            raise FileNotFoundError(f"Category data path not found: {category_path}")
        
        # Get available categories
        available_files = list(category_path.glob("*.parquet"))
        available_categories = [f.stem for f in available_files]
        
        if categories:
            # Filter to requested categories
            files_to_load = [f for f in available_files if f.stem in categories]
        else:
            files_to_load = available_files
        
        all_params = []
        
        for file_path in files_to_load:
            category = file_path.stem
            self.logger.debug(f"Loading category: {category}")
            
            try:
                df = pd.read_parquet(file_path)
                
                # Add category column
                df['category'] = category
                
                # Extract numeric parameters
                numeric_cols = [col for col in df.columns if '_numeric' in col or col in ['value', 'Value']]
                
                # Melt to long format for easier analysis
                if numeric_cols:
                    id_vars = ['building_id', 'category']
                    if 'object_name' in df.columns:
                        id_vars.append('object_name')
                    if 'object_type' in df.columns:
                        id_vars.append('object_type')
                    
                    param_df = df.melt(
                        id_vars=id_vars,
                        value_vars=numeric_cols,
                        var_name='parameter',
                        value_name='value'
                    )
                    
                    # Clean parameter names
                    param_df['parameter'] = param_df['parameter'].str.replace('_numeric', '')
                    
                    # Remove nulls
                    param_df = param_df.dropna(subset=['value'])
                    
                    all_params.append(param_df)
                    
            except Exception as e:
                self.logger.warning(f"Error loading {category}: {e}")
        
        if all_params:
            combined_df = pd.concat(all_params, ignore_index=True)
            self.parameter_data['idf'] = combined_df
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
        
        self.modification_data = df
        self.logger.info(f"Loaded {len(df)} modifications")
        
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
        
        # Load modified results if requested and available
        if load_modified and self.modified_parsed_path.exists():
            mod_path = self.modified_parsed_path / f"sql_results/timeseries/aggregated/{result_type}"
            if mod_path.exists():
                results['modified'] = self._load_results_from_path(mod_path, variables)
                self.logger.info(f"Loaded modified results: {sum(len(df) for df in results['modified'].values())} records")
        
        self.simulation_results = results
        return results
    
    def _load_results_from_path(self, path: Path, variables: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """Load result files from a specific path"""
        results = {}
        
        for parquet_file in path.glob("*.parquet"):
            category = parquet_file.stem.replace(f"_{path.parent.name}", "")
            
            try:
                df = pd.read_parquet(parquet_file)
                
                # Filter to requested variables if specified
                if variables and 'Variable' in df.columns:
                    df = df[df['Variable'].isin(variables)]
                
                if len(df) > 0:
                    results[category] = df
                    
            except Exception as e:
                self.logger.warning(f"Error loading {parquet_file}: {e}")
        
        return results
    
    def create_parameter_matrix(self, 
                              use_modifications: bool = True,
                              parameter_filter: Optional[Dict] = None) -> pd.DataFrame:
        """Create parameter matrix for sensitivity analysis"""
        self.logger.info("Creating parameter matrix...")
        
        if use_modifications and self.has_modification_data():
            # Use modification tracking data
            if self.modification_data is None:
                self.load_modification_tracking()
            
            # Pivot modifications to wide format
            param_matrix = self.modification_data.pivot_table(
                index=['building_id', 'variant_id'],
                columns=['category', 'field_name'],
                values='new_value_numeric',
                aggfunc='mean'
            )
            
            # Flatten column names
            param_matrix.columns = ['_'.join(col) for col in param_matrix.columns]
            param_matrix = param_matrix.reset_index()
            
        else:
            # Use parsed IDF data
            if 'idf' not in self.parameter_data:
                self.load_idf_parameters()
            
            df_params = self.parameter_data['idf']
            
            # Create matrix from parameters
            param_matrix = df_params.pivot_table(
                index='building_id',
                columns=['category', 'parameter'],
                values='value',
                aggfunc='mean'
            )
            
            # Flatten column names
            param_matrix.columns = ['_'.join(col) for col in param_matrix.columns]
            param_matrix = param_matrix.reset_index()
        
        # Apply filters if provided
        if parameter_filter:
            if 'categories' in parameter_filter:
                cols_to_keep = ['building_id']
                if 'variant_id' in param_matrix.columns:
                    cols_to_keep.append('variant_id')
                    
                for cat in parameter_filter['categories']:
                    cat_cols = [col for col in param_matrix.columns if col.startswith(f"{cat}_")]
                    cols_to_keep.extend(cat_cols)
                
                param_matrix = param_matrix[cols_to_keep]
            
            if 'parameters' in parameter_filter:
                cols_to_keep = ['building_id']
                if 'variant_id' in param_matrix.columns:
                    cols_to_keep.append('variant_id')
                    
                for param in parameter_filter['parameters']:
                    param_cols = [col for col in param_matrix.columns if param in col]
                    cols_to_keep.extend(param_cols)
                
                param_matrix = param_matrix[cols_to_keep]
        
        self.logger.info(f"Created parameter matrix: {param_matrix.shape}")
        return param_matrix
    
    def create_output_matrix(self, 
                           variables: List[str],
                           aggregation: str = 'sum',
                           use_modified: bool = False) -> pd.DataFrame:
        """Create output matrix for sensitivity analysis"""
        self.logger.info("Creating output matrix...")
        
        if not self.simulation_results:
            self.load_simulation_results()
        
        # Choose base or modified results
        results_to_use = self.simulation_results.get('modified' if use_modified else 'base', {})
        
        output_records = []
        
        # Process each result category
        for category, df in results_to_use.items():
            if 'Variable' in df.columns:
                # Filter to requested variables
                for var in variables:
                    var_data = df[df['Variable'] == var]
                    
                    if len(var_data) > 0:
                        # Aggregate by building
                        if aggregation == 'sum':
                            agg_data = var_data.groupby('building_id')['Value'].sum()
                        elif aggregation == 'mean':
                            agg_data = var_data.groupby('building_id')['Value'].mean()
                        else:  # max
                            agg_data = var_data.groupby('building_id')['Value'].max()
                        
                        for building_id, value in agg_data.items():
                            output_records.append({
                                'building_id': building_id,
                                var: value
                            })
        
        # Convert to DataFrame
        if output_records:
            output_matrix = pd.DataFrame(output_records)
            
            # Aggregate duplicates
            output_matrix = output_matrix.groupby('building_id').sum().reset_index()
            
            self.logger.info(f"Created output matrix: {output_matrix.shape}")
            return output_matrix
        else:
            self.logger.warning("No output data found for specified variables")
            return pd.DataFrame()
    
    def load_building_metadata(self) -> pd.DataFrame:
        """Load building metadata for grouping analysis"""
        self.logger.info("Loading building metadata...")
        
        # Try to load from extracted buildings file
        extracted_path = self.project_root / "extracted_idf_buildings.csv"
        if extracted_path.exists():
            metadata = pd.read_csv(extracted_path)
            
            # Store key fields
            self.building_metadata = metadata[['ogc_fid', 'building_function', 
                                             'building_type', 'age_range']].copy()
            self.building_metadata.rename(columns={'ogc_fid': 'building_id'}, inplace=True)
            
            return self.building_metadata
        
        # Try to load from parsed data
        building_path = self.parsed_data_path / "idf_data" / "by_building"
        if building_path.exists():
            # Load first building file to get metadata
            building_files = list(building_path.glob("*_snapshot.parquet"))
            if building_files:
                sample_df = pd.read_parquet(building_files[0])
                # Extract metadata from first row if available
                # This is a fallback - actual implementation depends on data structure
                
        return pd.DataFrame()
    
    def create_analysis_dataset(self,
                              parameter_groups: Optional[Dict[str, List[str]]] = None,
                              output_variables: Optional[List[str]] = None,
                              use_modifications: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create complete dataset for sensitivity analysis"""
        self.logger.info("Creating analysis dataset...")
        
        # Create parameter matrix
        param_filter = {'categories': list(parameter_groups.keys())} if parameter_groups else None
        X = self.create_parameter_matrix(use_modifications=use_modifications, 
                                       parameter_filter=param_filter)
        
        # Create output matrix
        if output_variables:
            y = self.create_output_matrix(output_variables, use_modified=use_modifications)
        else:
            # Use default energy outputs
            default_vars = ['Heating:EnergyTransfer', 'Cooling:EnergyTransfer', 
                          'Electricity:Facility']
            y = self.create_output_matrix(default_vars, use_modified=use_modifications)
        
        # Merge on building_id (and variant_id if present)
        merge_cols = ['building_id']
        if 'variant_id' in X.columns and 'variant_id' in y.columns:
            merge_cols.append('variant_id')
        
        # Ensure both have same index structure
        X_indexed = X.set_index(merge_cols)
        y_indexed = y.set_index(merge_cols)
        
        # Find common indices
        common_idx = X_indexed.index.intersection(y_indexed.index)
        
        if len(common_idx) == 0:
            self.logger.warning("No common buildings between parameters and outputs")
            return pd.DataFrame(), pd.DataFrame()
        
        # Filter to common indices
        X_final = X_indexed.loc[common_idx].reset_index()
        y_final = y_indexed.loc[common_idx].reset_index()
        
        self.logger.info(f"Created dataset with {len(X_final)} samples, "
                        f"{X_final.shape[1] - len(merge_cols)} parameters, "
                        f"{y_final.shape[1] - len(merge_cols)} outputs")
        
        return X_final, y_final
    
    def save_processed_data(self, output_dir: Path):
        """Save processed data for later use"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save parameter data
        if self.parameter_data:
            for key, df in self.parameter_data.items():
                df.to_parquet(output_dir / f"parameters_{key}.parquet")
        
        # Save modification data
        if self.modification_data is not None:
            self.modification_data.to_parquet(output_dir / "modifications.parquet")
        
        # Save metadata
        metadata = {
            'project_root': str(self.project_root),
            'has_modifications': self.has_modification_data(),
            'has_parsed_data': self.has_parsed_data(),
            'categories_loaded': list(self.parameter_data.keys()) if self.parameter_data else []
        }
        
        with open(output_dir / "data_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Saved processed data to: {output_dir}")