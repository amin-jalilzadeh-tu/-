"""
c_surrogate/surrogate_data_extractor.py

Extracts data from EnergyPlus workflow outputs for surrogate modeling.
Handles modifications, simulation results, sensitivity analysis, and zone mappings.

Author: Your Team
"""

import os
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import glob
import json  

logger = logging.getLogger(__name__)


class SurrogateDataExtractor:
    """
    Extracts and consolidates data from multiple sources for surrogate modeling.
    """
    
    def __init__(self, job_output_dir: str, config: Dict[str, Any] = None, tracker: Optional['SurrogatePipelineTracker'] = None):
        """
        Initialize the data extractor.
        
        Args:
            job_output_dir: Base output directory from the job
            config: Configuration dictionary for extraction options
            tracker: Optional pipeline tracker for monitoring
        """
        self.job_output_dir = Path(job_output_dir)
        self.config = config or {}
        self.tracker = tracker
        
        # Define default paths
        self.paths = {
            'parsed_data': self.job_output_dir / 'parsed_data',
            'parsed_modified': self.job_output_dir / 'parsed_modified_results',
            'modifications': self.job_output_dir / 'modified_idfs',
            'sensitivity': self.job_output_dir / 'sensitivity_results',
            'validation': self.job_output_dir / 'validation_results'
        }
        
        # Extracted data storage
        self.data = {
            'modifications': None,
            'base_parameters': None,
            'modified_parameters': None,
            'base_outputs': None,
            'modified_outputs': None,
            'sensitivity': None,
            'zone_mappings': None,
            'building_registry': None
        }
        
    def extract_all(self) -> Dict[str, pd.DataFrame]:
        """
        Extract all relevant data for surrogate modeling.
        
        Returns:
            Dictionary containing all extracted DataFrames
        """
        logger.info("[Extractor] Starting comprehensive data extraction")
        
        # Track extraction start
        if self.tracker:
            self.tracker.log_step("data_extraction", "started")
        
        # Extract modification details
        self.extract_modification_parameters()
        
        # Extract base and modified parameters
        self.extract_idf_parameters()
        
        # Extract simulation outputs - try new structure first
        if (self.paths['parsed_modified'] / 'comparisons').exists():
            self.extract_comparison_outputs()
        else:
            self.extract_simulation_outputs()
        
        # Extract sensitivity results
        self.extract_sensitivity_rankings()
        
        # Extract zone relationships
        self.extract_zone_relationships()
        
        # Extract building registry
        self.extract_building_registry()
        
        # Extract validation results if available
        self.extract_validation_results()
        
        logger.info("[Extractor] Data extraction completed")
    
        # Track extraction results
        if self.tracker:
            # Get summary statistics
            summary = self.get_summary_statistics()
            
            # Export extracted data
            self.tracker.track_extraction(summary, self.data)
            
            # Export data quality reports
            for name, data in self.data.items():
                # Only generate quality reports for DataFrames
                if isinstance(data, pd.DataFrame) and not data.empty:
                    quality_report = self.tracker.generate_data_quality_report(data, name)
                    quality_path = self.tracker.dirs["extraction"] / f"quality_{name}.json"
                    with open(quality_path, "w") as f:
                        json.dump(quality_report, f, indent=2)
                elif isinstance(data, dict) and data:
                    # For dictionaries, log summary info
                    logger.info(f"[Extractor] {name} contains {len(data)} entries (dictionary)")
        
        return self.data
    
    def extract_modification_parameters(self) -> pd.DataFrame:
        """
        Extract parameter modifications from modification tracking files.
        Handles both wide and long format modification files.
        """
        logger.info("[Extractor] Extracting modification parameters")
        
        # Find modification detail files
        mod_pattern = self.paths['modifications'] / 'modifications_detail_*.parquet'
        mod_files = list(glob.glob(str(mod_pattern)))
        
        if not mod_files:
            logger.warning("[Extractor] No modification detail files found")
            return pd.DataFrame()
        
        # Separate wide and long format files
        wide_files = [f for f in mod_files if 'wide' in f]
        long_files = [f for f in mod_files if 'long' in f]
        
        modifications = None
        
        # Prefer wide format for surrogate modeling
        if wide_files:
            logger.info("[Extractor] Using wide format modification file")
            modifications = pd.read_parquet(wide_files[0])
            
            # Wide format has parameters as rows and variants as columns
            # Keep as is for easier feature matrix creation
            self.data['modifications_wide'] = modifications
            
            # Also create long format for compatibility
            value_vars = [col for col in modifications.columns if col.startswith('variant_')]
            id_vars = [col for col in modifications.columns if not col.startswith('variant_')]
            
            modifications_long = pd.melt(
                modifications,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name='variant_id',
                value_name='new_value'
            )
            modifications = modifications_long
            
        elif long_files:
            logger.info("[Extractor] Using long format modification file")
            # Load all long format files
            dfs = []
            for file in long_files:
                df = pd.read_parquet(file)
                df = df.reset_index(drop=True)
                dfs.append(df)
            
            modifications = pd.concat(dfs, ignore_index=True)
            
            # Create wide format for easier feature matrix creation
            if 'parameter' in modifications.columns and 'variant_id' in modifications.columns:
                pivot_cols = ['building_id'] if 'building_id' in modifications.columns else []
                pivot_cols.append('parameter')
                
                modifications_wide = modifications.pivot_table(
                    index=pivot_cols,
                    columns='variant_id',
                    values='new_value',
                    aggfunc='first'
                ).reset_index()
                
                self.data['modifications_wide'] = modifications_wide
        
        if modifications is not None:
            # Create a unique parameter identifier
            param_id_parts = []
            for col in ['category', 'object_type', 'object_name', 'field_name']:
                if col in modifications.columns:
                    param_id_parts.append(modifications[col])
            
            if param_id_parts:
                modifications['param_id'] = param_id_parts[0].astype(str)
                for part in param_id_parts[1:]:
                    modifications['param_id'] = modifications['param_id'] + '*' + part.astype(str)
            elif 'parameter' in modifications.columns:
                modifications['param_id'] = modifications['parameter']
            else:
                modifications['param_id'] = modifications.index.astype(str)
            
            # Calculate relative changes if we have original values
            if 'original_value' in modifications.columns and 'new_value' in modifications.columns:
                modifications['relative_change'] = np.where(
                    pd.to_numeric(modifications['original_value'], errors='coerce') != 0,
                    (pd.to_numeric(modifications['new_value'], errors='coerce') - 
                     pd.to_numeric(modifications['original_value'], errors='coerce')) / 
                    pd.to_numeric(modifications['original_value'], errors='coerce'),
                    np.nan
                )
            
            self.data['modifications'] = modifications
            logger.info(f"[Extractor] Extracted {len(modifications)} modification records")
            
            # Log unique parameters and variants
            if 'parameter' in modifications.columns:
                n_params = modifications['parameter'].nunique()
                logger.info(f"[Extractor] Found {n_params} unique parameters")
            if 'variant_id' in modifications.columns:
                n_variants = modifications['variant_id'].nunique()
                logger.info(f"[Extractor] Found {n_variants} variants")
        
        return modifications
    
    def extract_idf_parameters(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract base and modified IDF parameters by category.
        """
        logger.info("[Extractor] Extracting IDF parameters")
        
        # Categories to extract
        categories = [
            'lighting', 'hvac_equipment', 'materials_materials', 
            'infiltration', 'ventilation', 'dhw', 'equipment',
            'geometry_zones', 'shading'
        ]
        
        base_params = {}
        modified_params = {}
        
        for category in categories:
            # Base parameters
            base_path = self.paths['parsed_data'] / 'idf_data' / 'by_category' / f'{category}.parquet'
            if base_path.exists():
                try:
                    base_df = pd.read_parquet(base_path)
                    # Map columns
                    base_df = self._map_column_names(base_df, category)
                    # Add category column to help identify source
                    base_df['parameter_category'] = category
                    base_params[category] = base_df
                    logger.debug(f"[Extractor] Loaded {len(base_df)} base {category} parameters")
                    logger.debug(f"[Extractor] Columns: {list(base_df.columns)}")
                except Exception as e:
                    logger.warning(f"[Extractor] Failed to load base {category}: {e}")
            
            # Modified parameters
            mod_path = self.paths['parsed_modified'] / 'idf_data' / 'by_category' / f'{category}.parquet'
            if mod_path.exists():
                try:
                    mod_df = pd.read_parquet(mod_path)
                    # Add category column
                    mod_df['parameter_category'] = category
                    modified_params[category] = mod_df
                    logger.debug(f"[Extractor] Loaded {len(mod_df)} modified {category} parameters")
                except Exception as e:
                    logger.warning(f"[Extractor] Failed to load modified {category}: {e}")
        
        # Combine into single DataFrames with better handling
        if base_params:
            # Method 1: Add category prefix to avoid column conflicts
            combined_dfs = []
            for cat, df in base_params.items():
                # Reset index
                df = df.reset_index(drop=True)
                
                # For columns that might conflict, add category prefix
                # but keep common columns like building_id unchanged
                common_cols = ['building_id', 'parameter_category', 'ogc_fid', 'zone_name']
                rename_dict = {}
                
                for col in df.columns:
                    if col not in common_cols and col != 'parameter_category':
                        # Add category prefix to avoid conflicts
                        rename_dict[col] = f"{cat}_{col}"
                
                if rename_dict:
                    df = df.rename(columns=rename_dict)
                
                combined_dfs.append(df)
            
            # Now concat - should work without conflicts
            try:
                base_combined = pd.concat(combined_dfs, ignore_index=True, sort=False)
                self.data['base_parameters'] = base_combined
                logger.info(f"[Extractor] Combined base parameters: {base_combined.shape}")
            except Exception as e:
                logger.error(f"[Extractor] Failed to combine base parameters: {e}")
                # Fallback: just store them separately
                self.data['base_parameters'] = pd.DataFrame()
        
        if modified_params:
            # Same for modified
            combined_dfs = []
            for cat, df in modified_params.items():
                df = df.reset_index(drop=True)
                
                common_cols = ['building_id', 'parameter_category', 'ogc_fid', 'zone_name', 'variant_id']
                rename_dict = {}
                
                for col in df.columns:
                    if col not in common_cols and col != 'parameter_category':
                        rename_dict[col] = f"{cat}_{col}"
                
                if rename_dict:
                    df = df.rename(columns=rename_dict)
                
                combined_dfs.append(df)
            
            try:
                modified_combined = pd.concat(combined_dfs, ignore_index=True, sort=False)
                self.data['modified_parameters'] = modified_combined
                logger.info(f"[Extractor] Combined modified parameters: {modified_combined.shape}")
            except Exception as e:
                logger.error(f"[Extractor] Failed to combine modified parameters: {e}")
                self.data['modified_parameters'] = pd.DataFrame()
        
        return self.data.get('base_parameters'), self.data.get('modified_parameters')
    




    
    def extract_simulation_outputs(self, 
                                temporal_resolution: str = 'daily',
                                output_categories: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Extract simulation outputs for base and modified cases.
        
        Args:
            temporal_resolution: 'hourly', 'daily', or 'monthly'
            output_categories: List of output categories to extract
        """
        logger.info(f"[Extractor] Extracting simulation outputs at {temporal_resolution} resolution")
        
        if output_categories is None:
            output_categories = ['zones', 'hvac', 'ventilation']
        
        base_outputs = {}
        modified_outputs = {}
        
        for category in output_categories:
            # Base outputs
            base_path = (self.paths['parsed_data'] / 'sql_results' / 'timeseries' / 
                        'aggregated' / temporal_resolution / f'{category}_{temporal_resolution}.parquet')
            
            if base_path.exists():
                base_df = pd.read_parquet(base_path)
                base_outputs[category] = base_df
                logger.debug(f"[Extractor] Loaded {len(base_df)} base {category} outputs")
            
            # Modified outputs
            mod_path = (self.paths['parsed_modified'] / 'sql_results' / 'timeseries' / 
                    'aggregated' / temporal_resolution / f'{category}_{temporal_resolution}.parquet')
            
            if mod_path.exists():
                mod_df = pd.read_parquet(mod_path)
                
                # NEW FIX: Handle the case where building_id doesn't contain variant info
                # Check if building_id contains variant pattern
                # Check if building_id contains variant pattern
                if 'variant_id' not in mod_df.columns:
                    if mod_df['building_id'].str.contains('_variant_', na=False).any():
                        # Extract from building_id string (e.g., "4136733_variant_0")
                        mod_df['original_building_id'] = mod_df['building_id'].str.extract(r'^(\d+)')[0]
                        mod_df['variant_id'] = mod_df['building_id'].str.extract(r'(variant_\d+)')[0]
                    else:
                        # Simple case - building_id is just the base ID
                        mod_df['original_building_id'] = mod_df['building_id'].astype(str)
                        # Look for variant_id in the data or default to variant_0
                        if 'variant_id' not in mod_df.columns:
                            mod_df['variant_id'] = 'variant_0'
                else:
                    # NEW: Simple case - building_id is just the base ID
                    # We need to infer variant from context
                    mod_df['original_building_id'] = mod_df['building_id']
                    
                    # Try to load modification details to get variant mapping
                    mod_detail_files = list(self.paths['modifications'].glob('modifications_detail_*.parquet'))
                    if mod_detail_files:
                        # Load the latest modification file
                        latest_mod_file = sorted(mod_detail_files)[-1]
                        mod_details = pd.read_parquet(latest_mod_file)
                        
                        # Get unique building->variant mapping
                        building_variant_map = mod_details[['building_id', 'variant_id']].drop_duplicates()
                        
                        # Merge to get variant_id
                        mod_df = mod_df.merge(
                            building_variant_map,
                            left_on='original_building_id',
                            right_on='building_id',
                            how='left',
                            suffixes=('', '_mod')
                        )
                        
                        # Clean up
                        if 'building_id_mod' in mod_df.columns:
                            mod_df.drop(columns=['building_id_mod'], inplace=True)
                    else:
                        # Fallback: assume variant_0 if no modification details found
                        mod_df['variant_id'] = 'variant_0'
                        
                modified_outputs[category] = mod_df
                logger.debug(f"[Extractor] Loaded {len(mod_df)} modified {category} outputs")
        
        # Store combined outputs
        if base_outputs:
            self.data['base_outputs'] = self._combine_output_categories(base_outputs)
        
        if modified_outputs:
            self.data['modified_outputs'] = self._combine_output_categories(modified_outputs)
        
        return {'base': base_outputs, 'modified': modified_outputs}
    
    def extract_sensitivity_rankings(self) -> pd.DataFrame:
        """Extract sensitivity analysis results for parameter importance."""
        logger.info("[Extractor] Extracting sensitivity rankings")
        
        # New consolidated structure - primary file
        sensitivity_results_path = self.paths['sensitivity'] / 'sensitivity_results.parquet'
        sensitivity_params_path = self.paths['sensitivity'] / 'sensitivity_parameters.csv'
        
        # Fallback to old structure if needed
        old_sensitivity_files = [
            'sensitivity_for_surrogate.parquet',
            'modification_sensitivity_results.parquet',
            'modification_sensitivity_results_peak_months_cooling.parquet'
        ]
        
        sensitivity_data = None
        
        # Try new structure first
        if sensitivity_results_path.exists():
            logger.info("[Extractor] Using new sensitivity structure")
            sensitivity_data = pd.read_parquet(sensitivity_results_path)
            
            # Load additional parameter metadata if available
            if sensitivity_params_path.exists():
                params_metadata = pd.read_csv(sensitivity_params_path)
                # Merge with main results
                sensitivity_data = sensitivity_data.merge(
                    params_metadata[['parameter', 'calibration_priority', 'surrogate_include', 
                                   'min_value', 'max_value', 'current_value', 'units', 'description']],
                    on='parameter',
                    how='left'
                )
        else:
            # Fallback to old structure
            logger.info("[Extractor] Falling back to old sensitivity structure")
            sensitivity_dfs = []
            
            for file in old_sensitivity_files:
                file_path = self.paths['sensitivity'] / file
                if file_path.exists():
                    df = pd.read_parquet(file_path)
                    df['source_file'] = file
                    sensitivity_dfs.append(df)
                    logger.debug(f"[Extractor] Loaded {len(df)} rows from {file}")
            
            if sensitivity_dfs:
                sensitivity_data = pd.concat(sensitivity_dfs, ignore_index=True)
        
        if sensitivity_data is not None and not sensitivity_data.empty:
            # Process sensitivity data
            if 'surrogate_include' in sensitivity_data.columns:
                # Filter for surrogate modeling if flag exists
                surrogate_params = sensitivity_data[sensitivity_data['surrogate_include'] == True].copy()
            else:
                # Use all parameters with significant sensitivity
                surrogate_params = sensitivity_data[
                    (sensitivity_data['sensitivity_score'] > 0) & 
                    (sensitivity_data['p_value'] < 0.05)
                ].copy()
            
            # Ensure we have ranking
            if 'rank' not in surrogate_params.columns:
                surrogate_params['rank'] = surrogate_params['sensitivity_score'].rank(ascending=False)
            
            # Sort by rank
            surrogate_params = surrogate_params.sort_values('rank')
            
            self.data['sensitivity'] = surrogate_params
            logger.info(f"[Extractor] Extracted sensitivity for {len(surrogate_params)} parameters")
            
            # Log top parameters
            if len(surrogate_params) > 0:
                top_params = surrogate_params.head(10)['parameter'].tolist()
                logger.info(f"[Extractor] Top sensitive parameters: {top_params}")
        else:
            logger.warning("[Extractor] No sensitivity data found")
            self.data['sensitivity'] = pd.DataFrame()
        
        return self.data['sensitivity']
    
    def extract_zone_relationships(self) -> Dict[str, pd.DataFrame]:
        """
        Extract zone mappings and equipment assignments.
        """
        logger.info("[Extractor] Extracting zone relationships")
        
        relationships = {}
        
        # Zone mappings
        zone_map_paths = [
            self.paths['parsed_data'] / 'relationships' / 'zone_mappings.parquet',
            self.paths['parsed_modified'] / 'relationships' / 'zone_mappings.parquet'
        ]
        
        zone_mappings = []
        for path in zone_map_paths:
            if path.exists():
                df = pd.read_parquet(path)
                df['source'] = 'base' if 'parsed_data' in str(path) else 'modified'
                zone_mappings.append(df)
        
        if zone_mappings:
            zone_mappings_reset = [df.reset_index(drop=True) for df in zone_mappings]
            relationships['zone_mappings'] = pd.concat(zone_mappings_reset, ignore_index=True)
            logger.debug(f"[Extractor] Loaded {len(relationships['zone_mappings'])} zone mappings")

        # Equipment assignments
        equip_paths = [
            self.paths['parsed_data'] / 'relationships' / 'equipment_assignments.parquet',
            self.paths['parsed_modified'] / 'relationships' / 'equipment_assignments.parquet'
        ]

        equipment_assignments = []
        for path in equip_paths:
            if path.exists():
                df = pd.read_parquet(path)
                df['source'] = 'base' if 'parsed_data' in str(path) else 'modified'
                equipment_assignments.append(df)

        if equipment_assignments:
            equipment_assignments_reset = [df.reset_index(drop=True) for df in equipment_assignments]
            relationships['equipment_assignments'] = pd.concat(equipment_assignments_reset, ignore_index=True)
            logger.debug(f"[Extractor] Loaded {len(relationships['equipment_assignments'])} equipment assignments")

        for path in equip_paths:
            if path.exists():
                df = pd.read_parquet(path)
                df['source'] = 'base' if 'parsed_data' in str(path) else 'modified'
                equipment_assignments.append(df)
        
        if equipment_assignments:
            relationships['equipment_assignments'] = pd.concat(equipment_assignments, ignore_index=True)
            logger.debug(f"[Extractor] Loaded {len(relationships['equipment_assignments'])} equipment assignments")
        
        self.data['zone_mappings'] = relationships.get('zone_mappings', pd.DataFrame())
        return relationships
    
    def extract_building_registry(self) -> pd.DataFrame:
        """
        Extract building registry information.
        """
        logger.info("[Extractor] Extracting building registry")
        
        registry_paths = [
            self.paths['parsed_data'] / 'metadata' / 'building_registry.parquet',
            self.paths['parsed_modified'] / 'metadata' / 'building_registry.parquet'
        ]
        
        registries = []
        for path in registry_paths:
            if path.exists():
                df = pd.read_parquet(path)
                df['source'] = 'base' if 'parsed_data' in str(path) else 'modified'
                registries.append(df)
        
        if registries:
            registries_reset = [df.reset_index(drop=True) for df in registries]
            combined_registry = pd.concat(registries_reset, ignore_index=True)
            self.data['building_registry'] = combined_registry
            logger.info(f"[Extractor] Extracted registry for {len(combined_registry)} building configurations")
        else:
            self.data['building_registry'] = pd.DataFrame()
        
        return self.data['building_registry']
    
    def extract_comparison_outputs(self) -> Dict[str, pd.DataFrame]:
        """
        Extract simulation output comparisons from new structure.
        """
        logger.info("[Extractor] Extracting comparison outputs")
        
        comparison_dir = self.paths['parsed_modified'] / 'comparisons'
        if not comparison_dir.exists():
            logger.warning(f"[Extractor] Comparison directory not found: {comparison_dir}")
            return {}
        
        # Get all comparison files
        comparison_files = list(comparison_dir.glob("*.parquet"))
        logger.info(f"[Extractor] Found {len(comparison_files)} comparison files")
        
        # Organize by variable, aggregation, and time period
        comparisons = {}
        metadata = []
        
        for file in comparison_files:
            # Parse filename: var_{variable}_{aggregation}_{time_period}_b{building_id}.parquet
            parts = file.stem.split('_')
            if len(parts) >= 4 and parts[0] == "var":
                variable = parts[1]
                aggregation = parts[2]
                time_period = parts[3]
                
                # Extract building ID if present
                building_id = None
                for part in parts:
                    if part.startswith('b') and part[1:].isdigit():
                        building_id = int(part[1:])
                        break
                
                key = f"{variable}_{aggregation}_{time_period}"
                
                try:
                    df = pd.read_parquet(file)
                    
                    # Add metadata columns
                    df['variable'] = variable
                    df['aggregation'] = aggregation
                    df['time_period'] = time_period
                    if building_id is not None:
                        df['building_id'] = building_id
                    
                    comparisons[key] = df
                    
                    metadata.append({
                        'variable': variable,
                        'aggregation': aggregation,
                        'time_period': time_period,
                        'building_id': building_id,
                        'n_records': len(df),
                        'columns': list(df.columns)
                    })
                    
                except Exception as e:
                    logger.error(f"[Extractor] Failed to load {file}: {e}")
        
        # Store comparison data
        self.data['comparison_outputs'] = comparisons
        self.data['comparison_metadata'] = pd.DataFrame(metadata)
        
        logger.info(f"[Extractor] Extracted {len(comparisons)} comparison datasets")
        
        # Create aggregated output dataframe for surrogate modeling
        if comparisons:
            # Focus on key variables for surrogate modeling
            key_variables = [
                'electricity_facility',
                'cooling_energytransfer',
                'heating_energytransfer',
                'zone_air_system_sensible_cooling_energy',
                'zone_air_system_sensible_heating_energy'
            ]
            
            aggregated_outputs = []
            for key, df in comparisons.items():
                variable = key.split('_')[0]
                if any(kv in variable for kv in key_variables):
                    # Reshape for surrogate modeling
                    if 'variant_id' in df.columns:
                        aggregated_outputs.append(df)
            
            if aggregated_outputs:
                self.data['aggregated_outputs'] = pd.concat(aggregated_outputs, ignore_index=True)
                logger.info(f"[Extractor] Created aggregated outputs with {len(self.data['aggregated_outputs'])} records")
        
        return comparisons
    
    def extract_validation_results(self) -> Optional[pd.DataFrame]:
        """
        Extract validation results if available.
        """
        logger.info("[Extractor] Extracting validation results")
        
        # Try multiple possible validation file locations
        validation_files = [
            self.paths['validation'] / 'validation_summary.parquet',
            self.paths['validation'] / 'modified' / 'validation_summary.parquet',
            self.paths['validation'] / 'base' / 'validation_summary.parquet'
        ]
        
        validation_dfs = []
        for validation_path in validation_files:
            if validation_path.exists():
                df = pd.read_parquet(validation_path)
                df['source'] = validation_path.parent.name
                validation_dfs.append(df)
                logger.info(f"[Extractor] Loaded validation results from {validation_path}")
        
        if validation_dfs:
            validation_df = pd.concat(validation_dfs, ignore_index=True)
            self.data['validation'] = validation_df
            logger.info(f"[Extractor] Extracted {len(validation_df)} validation results")
            
            # Filter for valid variants only
            if 'validation_status' in validation_df.columns:
                valid_variants = validation_df[validation_df['validation_status'] == 'PASS']
                if len(valid_variants) < len(validation_df):
                    logger.warning(f"[Extractor] {len(validation_df) - len(valid_variants)} variants failed validation")
            
            return validation_df
        else:
            logger.info("[Extractor] No validation results found")
            self.data['validation'] = pd.DataFrame()
            return None
    
    def _combine_output_categories(self, output_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Combine different output categories into a single DataFrame.
        """
        combined_dfs = []
        
        for category, df in output_dict.items():
            df['output_category'] = category
            combined_dfs.append(df)
        
        if combined_dfs:
            return pd.concat(combined_dfs, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics of extracted data.
        """
        summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'data_sources': {}
        }
        
        for key, data in self.data.items():
            # Handle dictionaries (like comparison_outputs)
            if isinstance(data, dict):
                if data:  # non-empty dict
                    summary['data_sources'][key] = {
                        'type': 'dictionary',
                        'keys': list(data.keys()),
                        'num_entries': len(data)
                    }
                    # Add specific info for comparison_outputs
                    if key == 'comparison_outputs':
                        total_rows = sum(len(df) if hasattr(df, '__len__') else 0 for df in data.values())
                        summary['data_sources'][key]['total_rows'] = total_rows
            # Handle DataFrames
            elif data is not None and hasattr(data, 'empty') and not data.empty:
                summary['data_sources'][key] = {
                    'type': 'dataframe',
                    'rows': len(data),
                    'columns': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
                }
                
                # Add specific summaries
                if key == 'modifications' and 'param_id' in data.columns:
                    summary['data_sources'][key]['unique_parameters'] = data['param_id'].nunique()
                    if 'category' in data.columns:
                        summary['data_sources'][key]['categories'] = data['category'].unique().tolist()
                elif key == 'sensitivity' and 'sensitivity_score' in data.columns:
                    summary['data_sources'][key]['high_sensitivity_params'] = len(
                        data[data['sensitivity_score'] > data['sensitivity_score'].quantile(0.75)]
                    )
        
        return summary
    
    def save_extracted_data(self, output_dir: str):
        """
        Save all extracted data to parquet files.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for key, data in self.data.items():
            if data is not None and not data.empty:
                file_path = output_path / f'extracted_{key}.parquet'
                data.to_parquet(file_path, index=False)
                logger.info(f"[Extractor] Saved {key} to {file_path}")



    def _map_column_names(self, df: pd.DataFrame, category: str) -> pd.DataFrame:
        """Map actual column names to expected names."""
        column_mappings = {
            'lighting': {
                'watts_per_zone_floor_area': 'LightingLevel',
                'fraction_radiant': 'FractionRadiant',
                'fraction_visible': 'FractionVisible',
                'schedule_name': 'ScheduleName'
            },
            'hvac_equipment': {
                'maximum_heating_supply_air_temperature': 'MaximumHeatingSupplyAirTemperature',
                'minimum_cooling_supply_air_temperature': 'MinimumCoolingSupplyAirTemperature'
            },
            'materials_materials': {
                'thickness': 'Thickness',
                'conductivity': 'Conductivity',
                'density': 'Density',
                'specific_heat': 'SpecificHeat',
                'name': 'material_name',
                'object_name': 'material_object_name'
            },
            'infiltration': {
                'design_flow_rate': 'DesignFlowRate',
                'design_flow_rate_calculation_method': 'DesignFlowRateCalculationMethod'
            },
            'ventilation': {
                'outdoor_air_method': 'OutdoorAirMethod',
                'outdoor_air_flow_per_person': 'OutdoorAirFlowperPerson'
            }
        }
        
        if category in column_mappings:
            return df.rename(columns=column_mappings[category])
        return df





    # Utility functions
    def extract_for_surrogate(job_output_dir: str, config: Dict[str, Any] = None) -> Dict[str, pd.DataFrame]:
        """
        Convenience function to extract all data needed for surrogate modeling.
        
        Args:
            job_output_dir: Job output directory
            config: Extraction configuration
            
        Returns:
            Dictionary of extracted DataFrames
        """
        extractor = SurrogateDataExtractor(job_output_dir, config)
        return extractor.extract_all()