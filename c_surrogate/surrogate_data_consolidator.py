"""
c_surrogate/surrogate_data_consolidator.py

Consolidates comparison outputs and other data sources into a unified format
for surrogate modeling. Handles the new data structure with proper alignment.

Author: Your Team
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SurrogateDataConsolidator:
    """
    Consolidates various data sources into a unified format for surrogate modeling.
    """
    
    def __init__(self, extracted_data: Dict[str, Any]):
        """
        Initialize with extracted data from SurrogateDataExtractor.
        
        Args:
            extracted_data: Dictionary containing various data sources
        """
        self.data = extracted_data
        self.consolidated = {}
        
    def consolidate_comparison_outputs(self) -> pd.DataFrame:
        """
        Consolidate comparison outputs dictionary into a single DataFrame.
        """
        comparison_outputs = self.data.get('comparison_outputs', {})
        
        if not comparison_outputs:
            logger.warning("No comparison outputs found")
            return pd.DataFrame()
        
        # Combine all comparison DataFrames
        consolidated_dfs = []
        
        for key, df in comparison_outputs.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Add the key information to the DataFrame
                df_copy = df.copy()
                df_copy['comparison_key'] = key
                consolidated_dfs.append(df_copy)
        
        if not consolidated_dfs:
            return pd.DataFrame()
        
        # Concatenate all DataFrames
        consolidated = pd.concat(consolidated_dfs, ignore_index=True)
        
        logger.info(f"Consolidated {len(comparison_outputs)} comparison outputs into {len(consolidated)} rows")
        
        return consolidated
    
    def create_feature_target_alignment(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create aligned feature and target DataFrames for surrogate modeling.
        
        Returns:
            Tuple of (features_df, targets_df)
        """
        # Get modifications (features)
        modifications = self.data.get('modifications', pd.DataFrame())
        if modifications.empty:
            # Try wide format
            modifications_wide = self.data.get('modifications_wide', pd.DataFrame())
            if not modifications_wide.empty:
                modifications = self._convert_wide_to_long(modifications_wide)
        
        # Get consolidated outputs (targets)
        consolidated_outputs = self.consolidate_comparison_outputs()
        
        # Get sensitivity data for feature selection
        sensitivity = self.data.get('sensitivity', pd.DataFrame())
        
        # Create feature matrix
        features = self._create_feature_matrix(modifications, sensitivity)
        
        # Create target matrix
        targets = self._create_target_matrix(consolidated_outputs)
        
        # Align features and targets
        features_aligned, targets_aligned = self._align_features_targets(features, targets)
        
        return features_aligned, targets_aligned
    
    def _convert_wide_to_long(self, wide_df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert wide format modifications to long format.
        """
        # Melt the DataFrame from wide to long format
        id_vars = ['building_id'] if 'building_id' in wide_df.columns else []
        
        # Get variant columns (typically variant_0, variant_1, etc.)
        variant_cols = [col for col in wide_df.columns if col.startswith('variant_')]
        
        if not variant_cols:
            logger.warning("No variant columns found in wide format")
            return pd.DataFrame()
        
        # Melt the data
        long_df = wide_df.melt(
            id_vars=id_vars + ['parameter', 'category', 'object_type', 'field_name'],
            value_vars=variant_cols,
            var_name='variant_id',
            value_name='new_value'
        )
        
        # Add relative change if we have original values
        if 'original_value' in wide_df.columns:
            long_df = long_df.merge(
                wide_df[['parameter', 'original_value']].drop_duplicates(),
                on='parameter',
                how='left'
            )
            long_df['relative_change'] = (
                (long_df['new_value'] - long_df['original_value']) / 
                long_df['original_value'].replace(0, 1)
            ).fillna(0)
        
        return long_df
    
    def _create_feature_matrix(self, modifications: pd.DataFrame, 
                              sensitivity: pd.DataFrame) -> pd.DataFrame:
        """
        Create feature matrix from modifications.
        """
        if modifications.empty:
            logger.warning("No modifications data for feature matrix")
            return pd.DataFrame()
        
        # Filter by sensitivity if available
        if not sensitivity.empty and 'surrogate_include' in sensitivity.columns:
            important_params = sensitivity[sensitivity['surrogate_include']]['parameter'].tolist()
            modifications = modifications[modifications['parameter'].isin(important_params)]
        
        # Pivot to create feature matrix
        feature_matrix = modifications.pivot_table(
            index=['building_id', 'variant_id'],
            columns='parameter',
            values='relative_change',
            aggfunc='first'
        ).reset_index()
        
        # Fill NaN values with 0 (no change)
        param_cols = [col for col in feature_matrix.columns 
                     if col not in ['building_id', 'variant_id']]
        feature_matrix[param_cols] = feature_matrix[param_cols].fillna(0)
        
        return feature_matrix
    
    def _create_target_matrix(self, consolidated_outputs: pd.DataFrame) -> pd.DataFrame:
        """
        Create target matrix from consolidated outputs.
        """
        if consolidated_outputs.empty:
            logger.warning("No consolidated outputs for target matrix")
            return pd.DataFrame()
        
        # Focus on key energy metrics
        target_variables = [
            'electricity_facility_na_yearly_from_monthly',
            'heating_energytransfer_na_yearly_from_monthly',
            'cooling_energytransfer_na_yearly_from_monthly'
        ]
        
        # Filter for relevant variables
        target_outputs = []
        
        for var in target_variables:
            var_data = consolidated_outputs[
                consolidated_outputs['comparison_key'].str.contains(var, na=False)
            ]
            
            if not var_data.empty:
                # Aggregate by building and variant
                agg_data = var_data.groupby(['building_id', 'variant_id']).agg({
                    'value_modified': 'sum',
                    'value_base': 'sum',
                    'absolute_change': 'sum',
                    'relative_change': 'mean'
                }).reset_index()
                
                # Rename columns to include variable name
                agg_data = agg_data.rename(columns={
                    'value_modified': f'{var}_modified',
                    'value_base': f'{var}_base',
                    'absolute_change': f'{var}_abs_change',
                    'relative_change': f'{var}_rel_change'
                })
                
                target_outputs.append(agg_data)
        
        if not target_outputs:
            logger.warning("No target variables found in outputs")
            return pd.DataFrame()
        
        # Merge all target variables
        target_matrix = target_outputs[0]
        for df in target_outputs[1:]:
            target_matrix = target_matrix.merge(
                df, 
                on=['building_id', 'variant_id'], 
                how='outer'
            )
        
        return target_matrix
    
    def _align_features_targets(self, features: pd.DataFrame, 
                               targets: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align feature and target DataFrames.
        """
        if features.empty or targets.empty:
            logger.warning("Cannot align empty features or targets")
            return pd.DataFrame(), pd.DataFrame()
        
        # Merge on building_id and variant_id
        aligned = features.merge(
            targets,
            on=['building_id', 'variant_id'],
            how='inner'
        )
        
        if aligned.empty:
            logger.warning("No matching records between features and targets")
            return pd.DataFrame(), pd.DataFrame()
        
        # Split back into features and targets
        feature_cols = [col for col in features.columns if col != 'building_id' and col != 'variant_id']
        target_cols = [col for col in targets.columns if col != 'building_id' and col != 'variant_id']
        
        features_aligned = aligned[['building_id', 'variant_id'] + feature_cols]
        targets_aligned = aligned[['building_id', 'variant_id'] + target_cols]
        
        logger.info(f"Aligned {len(features_aligned)} records with {len(feature_cols)} features and {len(target_cols)} targets")
        
        return features_aligned, targets_aligned
    
    def get_validation_data(self) -> Optional[pd.DataFrame]:
        """
        Extract and format validation data if available.
        """
        validation = self.data.get('validation', None)
        
        if validation is None:
            logger.info("No validation data available")
            return None
        
        # Process validation data based on structure
        if isinstance(validation, pd.DataFrame):
            return validation
        elif isinstance(validation, dict):
            # Convert dictionary to DataFrame if needed
            validation_dfs = []
            for key, val in validation.items():
                if isinstance(val, pd.DataFrame):
                    val_copy = val.copy()
                    val_copy['validation_key'] = key
                    validation_dfs.append(val_copy)
            
            if validation_dfs:
                return pd.concat(validation_dfs, ignore_index=True)
        
        return None