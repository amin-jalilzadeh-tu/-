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

logger = logging.getLogger(__name__)


class SurrogateDataExtractor:
    """
    Extracts and consolidates data from multiple sources for surrogate modeling.
    """
    
    def __init__(self, job_output_dir: str, config: Dict[str, Any] = None):
        """
        Initialize the data extractor.
        
        Args:
            job_output_dir: Base output directory from the job
            config: Configuration dictionary for extraction options
        """
        self.job_output_dir = Path(job_output_dir)
        self.config = config or {}
        
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
        
        # Extract modification details
        self.extract_modification_parameters()
        
        # Extract base and modified parameters
        self.extract_idf_parameters()
        
        # Extract simulation outputs
        self.extract_simulation_outputs()
        
        # Extract sensitivity results
        self.extract_sensitivity_rankings()
        
        # Extract zone relationships
        self.extract_zone_relationships()
        
        # Extract building registry
        self.extract_building_registry()
        
        logger.info("[Extractor] Data extraction completed")
        return self.data
    
    def extract_modification_parameters(self) -> pd.DataFrame:
        """
        Extract parameter modifications from modification tracking files.
        """
        logger.info("[Extractor] Extracting modification parameters")
        
        # Find modification detail files
        mod_pattern = self.paths['modifications'] / 'modifications_detail_*.parquet'
        mod_files = list(glob.glob(str(mod_pattern)))
        
        if not mod_files:
            logger.warning("[Extractor] No modification detail files found")
            return pd.DataFrame()
        
        # Load and concatenate all modification files
        dfs = []
        for file in mod_files:
            df = pd.read_parquet(file)
            dfs.append(df)
        
        modifications = pd.concat(dfs, ignore_index=True)
        
        # Create a unique parameter identifier
        modifications['param_id'] = (
            modifications['category'] + '*' +
            modifications['object_type'] + '*' +
            modifications['object_name'] + '*' +
            modifications['field_name']
        )
        
        # Calculate relative changes
        modifications['relative_change'] = np.where(
            pd.to_numeric(modifications['original_value'], errors='coerce') != 0,
            (pd.to_numeric(modifications['new_value'], errors='coerce') - 
             pd.to_numeric(modifications['original_value'], errors='coerce')) / 
            pd.to_numeric(modifications['original_value'], errors='coerce'),
            np.nan
        )
        
        self.data['modifications'] = modifications
        logger.info(f"[Extractor] Extracted {len(modifications)} modifications")
        
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
                base_df = pd.read_parquet(base_path)
                base_params[category] = base_df
                logger.debug(f"[Extractor] Loaded {len(base_df)} base {category} parameters")
            
            # Modified parameters
            mod_path = self.paths['parsed_modified'] / 'idf_data' / 'by_category' / f'{category}.parquet'
            if mod_path.exists():
                mod_df = pd.read_parquet(mod_path)
                modified_params[category] = mod_df
                logger.debug(f"[Extractor] Loaded {len(mod_df)} modified {category} parameters")
        
        # Combine into single DataFrames
        if base_params:
            base_combined = pd.concat(base_params.values(), ignore_index=True, sort=False)
            self.data['base_parameters'] = base_combined
        
        if modified_params:
            modified_combined = pd.concat(modified_params.values(), ignore_index=True, sort=False)
            self.data['modified_parameters'] = modified_combined
        
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
                if mod_df['building_id'].str.contains('variant_', na=False).any():
                    # Original logic - extract from building_id string
                    mod_df['original_building_id'] = mod_df['building_id'].str.extract(r'(\d+)')[0]
                    mod_df['variant_id'] = mod_df['building_id'].str.extract(r'(variant_\d+)')[0]
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
        """
        Extract sensitivity analysis results for parameter importance.
        """
        logger.info("[Extractor] Extracting sensitivity rankings")
        
        sensitivity_files = [
            'sensitivity_for_surrogate.parquet',
            'modification_sensitivity_results_peak_months_cooling.parquet',
            'uncertainty_analysis_results.parquet'
        ]
        
        sensitivity_data = []
        
        for file in sensitivity_files:
            file_path = self.paths['sensitivity'] / file
            if file_path.exists():
                df = pd.read_parquet(file_path)
                df['source_file'] = file
                sensitivity_data.append(df)
                logger.debug(f"[Extractor] Loaded {len(df)} rows from {file}")
        
        if sensitivity_data:
            combined_sensitivity = pd.concat(sensitivity_data, ignore_index=True)
            
            # Calculate average sensitivity score by parameter
            param_importance = combined_sensitivity.groupby('parameter').agg({
                'sensitivity_score': 'mean',
                'elasticity': 'mean',
                'p_value': 'min',
                'confidence_level': lambda x: x.mode()[0] if len(x) > 0 else 'low'
            }).reset_index()
            
            # Rank parameters
            param_importance['rank'] = param_importance['sensitivity_score'].rank(ascending=False)
            
            self.data['sensitivity'] = param_importance
            logger.info(f"[Extractor] Extracted sensitivity for {len(param_importance)} parameters")
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
            relationships['zone_mappings'] = pd.concat(zone_mappings, ignore_index=True)
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
            combined_registry = pd.concat(registries, ignore_index=True)
            self.data['building_registry'] = combined_registry
            logger.info(f"[Extractor] Extracted registry for {len(combined_registry)} building configurations")
        else:
            self.data['building_registry'] = pd.DataFrame()
        
        return self.data['building_registry']
    
    def extract_validation_results(self) -> Optional[pd.DataFrame]:
        """
        Extract validation results if available.
        """
        logger.info("[Extractor] Extracting validation results")
        
        validation_path = self.paths['validation'] / 'validation_summary.parquet'
        
        if validation_path.exists():
            validation_df = pd.read_parquet(validation_path)
            logger.info(f"[Extractor] Extracted {len(validation_df)} validation results")
            return validation_df
        else:
            logger.info("[Extractor] No validation results found")
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
            if data is not None and not data.empty:
                summary['data_sources'][key] = {
                    'rows': len(data),
                    'columns': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
                }
                
                # Add specific summaries
                if key == 'modifications':
                    summary['data_sources'][key]['unique_parameters'] = data['param_id'].nunique()
                    summary['data_sources'][key]['categories'] = data['category'].unique().tolist()
                elif key == 'sensitivity':
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