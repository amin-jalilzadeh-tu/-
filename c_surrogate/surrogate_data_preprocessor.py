"""
c_surrogate/surrogate_data_preprocessor.py

Preprocesses extracted data for surrogate modeling.
Handles parameter alignment, feature engineering, and data formatting.

Author: Your Team
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import json

logger = logging.getLogger(__name__)


class SurrogateDataPreprocessor:
    """
    Preprocesses data for surrogate modeling, handling multi-level analysis
    and various data transformations.
    """
    
    def __init__(self, extracted_data: Dict[str, pd.DataFrame], config: Dict[str, Any] = None, tracker: Optional['SurrogatePipelineTracker'] = None):
        """
        Initialize the preprocessor with extracted data.
        
        Args:
            extracted_data: Dictionary of DataFrames from SurrogateDataExtractor
            config: Configuration for preprocessing options
            tracker: Optional pipeline tracker for monitoring
        """
        self.data = extracted_data
        self.config = config or {}
        self.tracker = tracker
        
        # Processed data storage
        self.processed = {
            'features': None,
            'targets': None,
            'metadata': {},
            'mappings': {}
        }
        
        # Default configuration
        self.default_config = {
            'aggregation_level': 'building',  # 'building' or 'zone'
            'temporal_resolution': 'daily',
            'use_sensitivity_filter': True,
            'sensitivity_threshold': 0.1,
            'normalize_features': True,
            'handle_categorical': True,
            'create_interactions': False,
            'target_variables': [
                'Heating:EnergyTransfer [J](Hourly)',
                'Cooling:EnergyTransfer [J](Hourly)',
                'Electricity:Facility [J](Hourly)'
            ]
        }
        
        # Merge with provided config
        self.config = {**self.default_config, **self.config}



    def _clean_feature_names(self, df: pd.DataFrame) -> pd.DataFrame:
            """
            Clean feature names to be compatible with all ML libraries.
            Replace special characters that cause issues with LightGBM and other libraries.
            """
            # Create mapping of old to new column names
            column_mapping = {}
            
            for col in df.columns:
                # Skip ID columns
                if col in ['building_id', 'variant_id', 'zone_name', 'ogc_fid']:
                    continue
                    
                # Replace problematic characters
                new_col = col
                new_col = new_col.replace('*', '_')
                new_col = new_col.replace(':', '_')
                new_col = new_col.replace(' ', '_')
                new_col = new_col.replace('(', '_')
                new_col = new_col.replace(')', '_')
                new_col = new_col.replace('[', '_')
                new_col = new_col.replace(']', '_')
                new_col = new_col.replace('/', '_')
                new_col = new_col.replace('\\', '_')
                new_col = new_col.replace('.', '_')
                new_col = new_col.replace(',', '_')
                new_col = new_col.replace('"', '')
                new_col = new_col.replace("'", '')
                
                # Remove multiple underscores
                while '__' in new_col:
                    new_col = new_col.replace('__', '_')
                
                # Remove trailing underscore
                new_col = new_col.rstrip('_')
                
                column_mapping[col] = new_col
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            # Store mapping for reference
            self.processed['feature_name_mapping'] = column_mapping
            
            return df



    
    def preprocess_all(self) -> Dict[str, Any]:
        """
        Run complete preprocessing pipeline.
        
        Returns:
            Dictionary with processed features, targets, and metadata
        """
        logger.info("[Preprocessor] Starting data preprocessing")
        
        # Step 1: Align parameters with outputs
        aligned_data = self.align_parameters_with_outputs()
        
        # Step 2: Filter by sensitivity if requested
        if self.config['use_sensitivity_filter']:
            aligned_data = self.filter_by_sensitivity(aligned_data)
        
        # Step 3: Create parameter matrix
        # Step 3: Create parameter matrix
        param_matrix = self.create_parameter_matrix(aligned_data)
        
        # Track intermediate data
        if self.tracker:
            self.tracker.export_input_data({
                "aligned_data": aligned_data,
                "parameter_matrix": param_matrix
            }, "preprocessing")
        
        # Step 4: Aggregate outputs
        output_matrix = self.aggregate_outputs(aligned_data)
        
        # Step 5: Handle multi-level data if needed
        if self.config['aggregation_level'] == 'zone':
            param_matrix, output_matrix = self.handle_multi_level_data(
                param_matrix, output_matrix
            )
        
        # Step 6: Feature engineering
        features = self.engineer_features(param_matrix)
        
        # Step 7: Final data preparation
        features, targets = self.prepare_final_datasets(features, output_matrix)
        
        # Store results
        # Store results
        self.processed['features'] = features
        self.processed['targets'] = targets
        
        logger.info("[Preprocessor] Preprocessing completed")
        logger.info(f"[Preprocessor] Features shape: {features.shape}")
        logger.info(f"[Preprocessor] Targets shape: {targets.shape}")
        
        # Track preprocessing results
        if self.tracker:
            processing_steps = [
                "align_parameters_with_outputs",
                "filter_by_sensitivity" if self.config['use_sensitivity_filter'] else None,
                "create_parameter_matrix",
                "aggregate_outputs",
                "handle_multi_level_data" if self.config['aggregation_level'] == 'zone' else None,
                "engineer_features",
                "prepare_final_datasets"
            ]
            processing_steps = [s for s in processing_steps if s]
            
            self.tracker.track_preprocessing(
                self.processed['metadata'],
                features,
                targets,
                processing_steps
            )
        
        return self.processed
    
    # In surrogate_data_preprocessor.py, around line 150-170

    def align_parameters_with_outputs(self) -> pd.DataFrame:
        """
        Align modification parameters with simulation outputs.
        Handles both old and new data structures.
        """
        logger.info("[Preprocessor] Aligning parameters with outputs")
        
        # Check if we have pre-consolidated data
        if 'consolidated_features' in self.data and 'consolidated_targets' in self.data:
            logger.info("[Preprocessor] Using pre-consolidated feature-target data")
            features = self.data['consolidated_features']
            targets = self.data['consolidated_targets']
            
            # Merge features and targets for alignment
            aligned = features.merge(
                targets[['building_id', 'variant_id']],
                on=['building_id', 'variant_id'],
                how='inner'
            )
            
            # Add metadata
            aligned['has_outputs'] = True
            
            logger.info(f"[Preprocessor] Aligned {len(aligned)} records from consolidated data")
            return aligned
        
        # Get modifications - prefer wide format
        modifications_wide = self.data.get('modifications_wide', pd.DataFrame())
        modifications = self.data.get('modifications', pd.DataFrame())
        
        if modifications_wide.empty and modifications.empty:
            raise ValueError("No modification data found")
        
        # Get outputs - check for new comparison structure first
        comparison_outputs = self.data.get('comparison_outputs', {})
        aggregated_outputs = self.data.get('aggregated_outputs', pd.DataFrame())
        
        # Fallback to old structure
        base_outputs = self.data.get('base_outputs', pd.DataFrame())
        modified_outputs = self.data.get('modified_outputs', pd.DataFrame())
        
        # Use new structure if available
        if comparison_outputs or not aggregated_outputs.empty:
            logger.info("[Preprocessor] Using new comparison output structure")
            return self._align_with_comparison_outputs()
        elif not modified_outputs.empty:
            logger.info("[Preprocessor] Using legacy output structure")
            # Continue with existing logic
        
        # Create alignment based on building_id and variant_id
        aligned_records = []
        
        # Group modifications by building_id and variant_id to handle multiple modifications per variant
        grouped_mods = modifications.groupby(['building_id', 'variant_id'])
        
        for (building_id, variant_id), mod_group in grouped_mods:
            # Find corresponding outputs - handle both string and numeric building_id
            building_id_str = str(building_id)
            
            if 'original_building_id' in modified_outputs.columns:
                mod_output_mask = (
                    (modified_outputs['original_building_id'] == building_id_str) &
                    (modified_outputs['variant_id'] == variant_id)
                )
            elif 'building_id' in modified_outputs.columns and 'variant_id' in modified_outputs.columns:
                # Direct match on both columns
                mod_output_mask = (
                    (modified_outputs['building_id'] == building_id_str) &
                    (modified_outputs['variant_id'] == variant_id)
                )
            else:
                # Fallback - try to match on building_id containing both IDs
                mod_output_mask = (modified_outputs['building_id'].str.contains(f"{building_id_str}.*{variant_id}"))


            
            if mod_output_mask.any():
                # Get the modified outputs for this building/variant
                variant_outputs = modified_outputs[mod_output_mask]
                
                # Find base outputs
                base_output_mask = base_outputs['building_id'] == str(building_id)
                base_variant_outputs = base_outputs[base_output_mask] if base_output_mask.any() else pd.DataFrame()
                
                # Create aligned records for each modification in this variant
                for _, mod in mod_group.iterrows():
                    record = {
                        'building_id': building_id,
                        'variant_id': variant_id,
                        'parameter': mod['param_id'],
                        'category': mod['category'],
                        'object_type': mod['object_type'],
                        'object_name': mod['object_name'],
                        'field_name': mod['field_name'],
                        'original_value': mod['original_value'],
                        'new_value': mod['new_value'],
                        'relative_change': mod.get('relative_change', 0),
                        'has_base_output': not base_variant_outputs.empty,
                        'has_modified_output': True,
                        'output_rows': len(variant_outputs)
                    }
                    
                    aligned_records.append(record)
            else:
                # Log missing outputs
                logger.warning(f"No outputs found for building {building_id}, variant {variant_id}")
        
        aligned_df = pd.DataFrame(aligned_records)
        
        # Add debug information
        if aligned_df.empty:
            logger.warning("No alignments found. Debugging info:")
            logger.warning(f"Modification building IDs: {modifications['building_id'].unique()}")
            logger.warning(f"Modified output building IDs: {modified_outputs['building_id'].unique()}")
            if 'variant_id' in modified_outputs.columns:
                logger.warning(f"Modified output variant IDs: {modified_outputs['variant_id'].unique()}")
            else:
                logger.warning("No variant_id column in modified outputs")
        else:
            logger.info(f"[Preprocessor] Aligned {len(aligned_df)} parameter-output pairs")
            logger.info(f"[Preprocessor] Unique building-variant combinations: {aligned_df[['building_id', 'variant_id']].drop_duplicates().shape[0]}")
        
        return aligned_df
    
    def _align_with_comparison_outputs(self) -> pd.DataFrame:
        """
        Align parameters with new comparison output structure.
        """
        logger.info("[Preprocessor] Aligning with comparison outputs")
        
        # Get modifications
        modifications_wide = self.data.get('modifications_wide', pd.DataFrame())
        modifications = self.data.get('modifications', pd.DataFrame())
        aggregated_outputs = self.data.get('aggregated_outputs', pd.DataFrame())
        
        # If we have wide format modifications, use them directly
        if not modifications_wide.empty:
            # Wide format already has parameters as rows and variants as columns
            aligned_df = modifications_wide.copy()
            
            # Add metadata
            aligned_df['has_outputs'] = True
            
            logger.info(f"[Preprocessor] Using wide format: {aligned_df.shape}")
            return aligned_df
        
        # Otherwise, work with long format
        if modifications.empty:
            raise ValueError("No modification data available")
        
        # Create alignment records
        aligned_records = []
        
        # Get unique parameter-variant combinations
        param_variants = modifications.groupby(['parameter', 'variant_id'])
        
        for (parameter, variant_id), group in param_variants:
            # Check if we have outputs for this variant
            has_output = False
            if not aggregated_outputs.empty:
                variant_outputs = aggregated_outputs[
                    aggregated_outputs.get('variant_id', '') == variant_id
                ]
                has_output = not variant_outputs.empty
            
            record = {
                'parameter': parameter,
                'variant_id': variant_id,
                'category': group['category'].iloc[0] if 'category' in group else None,
                'original_value': group['original_value'].iloc[0] if 'original_value' in group else None,
                'new_value': group['new_value'].iloc[0] if 'new_value' in group else None,
                'relative_change': group['relative_change'].iloc[0] if 'relative_change' in group else None,
                'has_output': has_output
            }
            
            # Add building_id if available
            if 'building_id' in group:
                record['building_id'] = group['building_id'].iloc[0]
            
            aligned_records.append(record)
        
        aligned_df = pd.DataFrame(aligned_records)
        logger.info(f"[Preprocessor] Aligned {len(aligned_df)} parameter-variant combinations")
        
        return aligned_df
    
    def filter_by_sensitivity(self, aligned_data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter parameters based on sensitivity analysis results.
        """
        logger.info("[Preprocessor] Filtering by sensitivity")
        
        sensitivity = self.data.get('sensitivity', pd.DataFrame())
        if sensitivity.empty:
            logger.warning("[Preprocessor] No sensitivity data available, skipping filter")
            return aligned_data
        
        # Check for surrogate_include flag in new structure
        if 'surrogate_include' in sensitivity.columns:
            # Use explicit surrogate inclusion flag
            important_params = sensitivity[sensitivity['surrogate_include'] == True]['parameter'].tolist()
            logger.info(f"[Preprocessor] Using {len(important_params)} parameters marked for surrogate modeling")
        else:
            # Use threshold-based filtering
            threshold = self.config.get('sensitivity_threshold', 0.1)
            
            # Filter sensitivity data
            if 'sensitivity_score' in sensitivity.columns:
                important_params = sensitivity[
                    sensitivity['sensitivity_score'] >= threshold
                ]['parameter'].tolist()
            else:
                # Use elasticity if sensitivity_score not available
                important_params = sensitivity[
                    abs(sensitivity['elasticity']) >= threshold
                ]['parameter'].tolist()
        
        # Handle both parameter column names
        param_col = 'parameter' if 'parameter' in aligned_data.columns else 'param_id'
        
        # Filter aligned data
        if param_col in aligned_data.columns:
            filtered = aligned_data[aligned_data[param_col].isin(important_params)]
        else:
            # If using wide format, keep metadata columns and filter parameter columns
            # Metadata columns are everything except the variant_X columns
            variant_cols = [col for col in aligned_data.columns if col.startswith('variant_')]
            metadata_cols = [col for col in aligned_data.columns if not col.startswith('variant_')]
            
            # For wide format, we keep all rows but potentially filter parameters
            # The parameters are in the 'field' or 'parameter' column
            if 'field' in aligned_data.columns:
                # Create a parameter identifier from the field components
                aligned_data['param_id'] = aligned_data.apply(
                    lambda row: f"{row['category']}*{row['object_type']}*{row['object_name']}*{row['field']}", 
                    axis=1
                )
                filtered = aligned_data[aligned_data['param_id'].isin(important_params)]
            else:
                # Keep all data if we can't identify parameters
                filtered = aligned_data
        
        logger.info(f"[Preprocessor] Filtered from {len(aligned_data)} to {len(filtered)} parameters")
        logger.info(f"[Preprocessor] Using {len(important_params)} important parameters")
        
        return filtered
    
    def create_parameter_matrix(self, aligned_data: pd.DataFrame) -> pd.DataFrame:
        """
        Create parameter matrix with one row per building/variant and columns for each parameter.
        """
        logger.info("[Preprocessor] Creating parameter matrix")
        
        # Check if data is already in wide format (variant_0, variant_1, etc. columns)
        variant_cols = [col for col in aligned_data.columns if col.startswith('variant_')]
        
        if variant_cols:
            # Data is already in wide format - need to reshape it
            logger.info("[Preprocessor] Data is in wide format, reshaping...")
            
            # Melt the variant columns to create long format
            id_vars = [col for col in aligned_data.columns if not col.startswith('variant_')]
            
            melted_data = []
            for variant_col in variant_cols:
                variant_id = variant_col  # Keep as variant_0, variant_1, etc.
                
                # Create records for each variant
                variant_data = aligned_data[id_vars + [variant_col]].copy()
                variant_data['variant_id'] = variant_id
                variant_data['value'] = variant_data[variant_col]
                variant_data = variant_data.drop(columns=[variant_col])
                
                # Convert to numeric values
                variant_data['value'] = pd.to_numeric(variant_data['value'], errors='coerce')
                if 'original' in variant_data.columns:
                    variant_data['original'] = pd.to_numeric(variant_data['original'], errors='coerce')
                
                # Calculate relative change if we have original values
                if 'original' in variant_data.columns:
                    # Handle cases where original is 0 or NaN
                    variant_data['relative_change'] = 0.0
                    mask = (variant_data['original'].notna()) & (variant_data['value'].notna()) & (variant_data['original'] != 0)
                    variant_data.loc[mask, 'relative_change'] = (
                        (variant_data.loc[mask, 'value'] - variant_data.loc[mask, 'original']) / 
                        variant_data.loc[mask, 'original']
                    )
                else:
                    variant_data['relative_change'] = variant_data['value']
                
                melted_data.append(variant_data)
            
            # Combine all variants
            long_data = pd.concat(melted_data, ignore_index=True)
            
            # Create parameter identifier
            if 'param_id' not in long_data.columns:
                long_data['parameter'] = long_data.apply(
                    lambda row: f"{row['category']}*{row['object_type']}*{row['object_name']}*{row['field']}", 
                    axis=1
                )
            else:
                long_data['parameter'] = long_data['param_id']
            
            # Now pivot to final format
            param_matrix = long_data.pivot_table(
                index=['building_id', 'variant_id'],
                columns='parameter',
                values='relative_change',
                aggfunc='first'
            ).reset_index()
        else:
            # Data is already in long format - use existing logic
            param_matrix = aligned_data.pivot_table(
                index=['building_id', 'variant_id'],
                columns='parameter',
                values='relative_change',
                aggfunc='first'
            ).reset_index()
        
        # Fill NaN with 0 (no change)
        param_cols = [col for col in param_matrix.columns if col not in ['building_id', 'variant_id']]
        param_matrix[param_cols] = param_matrix[param_cols].fillna(0)
        
        # Add category-level aggregations if we have the required data
        if variant_cols and 'category' in aligned_data.columns:
            # For wide format, calculate category aggregations from long_data
            category_changes = long_data.groupby(
                ['building_id', 'variant_id', 'category']
            )['relative_change'].mean().reset_index()
            
            category_pivot = category_changes.pivot_table(
                index=['building_id', 'variant_id'],
                columns='category',
                values='relative_change'
            ).reset_index()
            
            # Rename category columns
            category_cols = [col for col in category_pivot.columns if col not in ['building_id', 'variant_id']]
            category_pivot.columns = ['building_id', 'variant_id'] + [f'category_{col}_mean_change' for col in category_cols]
            
            # Merge with parameter matrix
            param_matrix = param_matrix.merge(
                category_pivot,
                on=['building_id', 'variant_id'],
                how='left'
            )
        elif 'category' in aligned_data.columns and 'relative_change' in aligned_data.columns:
            # Original logic for long format
            category_changes = aligned_data.groupby(
                ['building_id', 'variant_id', 'category']
            )['relative_change'].mean().reset_index()
            
            category_pivot = category_changes.pivot_table(
                index=['building_id', 'variant_id'],
                columns='category',
                values='relative_change'
            ).reset_index()
            
            # Rename category columns
            category_cols = [col for col in category_pivot.columns if col not in ['building_id', 'variant_id']]
            category_pivot.columns = ['building_id', 'variant_id'] + [f'category_{col}_mean_change' for col in category_cols]
            
            # Merge with parameter matrix
            param_matrix = param_matrix.merge(
                category_pivot,
                on=['building_id', 'variant_id'],
                how='left'
            )
        
        logger.info(f"[Preprocessor] Created parameter matrix: {param_matrix.shape}")
        
        return param_matrix
    
    def aggregate_outputs(self, aligned_data: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate simulation outputs to match parameter matrix.
        Handles both old and new output structures.
        """
        logger.info("[Preprocessor] Aggregating outputs")
        
        # Check if we have pre-consolidated targets
        if 'consolidated_targets' in self.data:
            logger.info("[Preprocessor] Using pre-consolidated target data")
            targets = self.data['consolidated_targets']
            
            # Ensure we only include aligned building/variant pairs
            aligned_pairs = aligned_data[['building_id', 'variant_id']].drop_duplicates()
            targets_aligned = targets.merge(
                aligned_pairs,
                on=['building_id', 'variant_id'],
                how='inner'
            )
            
            logger.info(f"[Preprocessor] Using {len(targets_aligned)} target records")
            return targets_aligned
        
        # Check for new comparison structure first
        comparison_outputs = self.data.get('comparison_outputs', {})
        aggregated_outputs = self.data.get('aggregated_outputs', pd.DataFrame())
        
        if comparison_outputs or not aggregated_outputs.empty:
            return self._aggregate_comparison_outputs(aligned_data)
        
        # Fallback to old structure
        base_outputs = self.data.get('base_outputs', pd.DataFrame())
        modified_outputs = self.data.get('modified_outputs', pd.DataFrame())
        
        # Get target variables from config
        target_variables = self.config['target_variables']
        
        # Process outputs for each building/variant
        output_records = []
        
        unique_pairs = aligned_data[['building_id', 'variant_id']].drop_duplicates()
        
        for _, pair in unique_pairs.iterrows():
            building_id = pair['building_id']
            variant_id = pair['variant_id']
            
            record = {
                'building_id': building_id,
                'variant_id': variant_id
            }
            
            # Get modified outputs
            mod_mask = (
                (modified_outputs['original_building_id'] == str(building_id)) &
                (modified_outputs['variant_id'] == variant_id)
            )
            
            if mod_mask.any():
                variant_outputs = modified_outputs[mod_mask]
                
                # Aggregate each target variable
                for var in target_variables:
                    var_data = variant_outputs[variant_outputs['Variable'] == var]
                    
                    if not var_data.empty:
                        # Sum across all zones and time
                        total_value = var_data['Value'].sum()
                        record[f'{var}_total'] = total_value
                        
                        # Also calculate mean and peak
                        record[f'{var}_mean'] = var_data['Value'].mean()
                        record[f'{var}_peak'] = var_data['Value'].max()
                        
                        # Calculate change from base if available
                        base_mask = (
                            (base_outputs['building_id'] == str(building_id)) &
                            (base_outputs['Variable'] == var)
                        )
                        
                        if base_mask.any():
                            base_total = base_outputs[base_mask]['Value'].sum()
                            if base_total != 0:
                                record[f'{var}_percent_change'] = (
                                    (total_value - base_total) / base_total * 100
                                )
            
            output_records.append(record)
        
        output_df = pd.DataFrame(output_records)
        logger.info(f"[Preprocessor] Aggregated outputs: {output_df.shape}")
        
        return output_df
    
    def _aggregate_comparison_outputs(self, aligned_data: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate outputs from new comparison structure.
        """
        logger.info("[Preprocessor] Aggregating comparison outputs")
        
        comparison_outputs = self.data.get('comparison_outputs', {})
        logger.info(f"[Preprocessor] Comparison outputs available: {len(comparison_outputs)} datasets")
        
        # Get target variables from config
        target_variables = self.config.get('target_variables', [
            'electricity_facility_na',
            'heating_energytransfer_na', 
            'cooling_energytransfer_na'
        ])
        
        # Get unique building IDs and variant IDs
        logger.debug(f"[Preprocessor] Aligned data columns: {list(aligned_data.columns)}")
        logger.debug(f"[Preprocessor] Aligned data shape: {aligned_data.shape}")
        
        if 'building_id' in aligned_data.columns and 'variant_id' in aligned_data.columns:
            unique_pairs = aligned_data[['building_id', 'variant_id']].drop_duplicates()
            logger.debug(f"[Preprocessor] Found {len(unique_pairs)} unique building-variant pairs")
        else:
            # For wide format, we need to create records for each variant column
            variant_cols = [col for col in aligned_data.columns if col.startswith('variant_')]
            building_id = aligned_data['building_id'].iloc[0] if 'building_id' in aligned_data.columns else None
            
            if not building_id:
                logger.error("[Preprocessor] No building_id found in aligned data")
                return pd.DataFrame()
                
            unique_pairs = pd.DataFrame([
                {'building_id': building_id, 'variant_id': col} 
                for col in variant_cols
            ])
            logger.info(f"[Preprocessor] Created {len(unique_pairs)} pairs from wide format")
        
        # Initialize output records
        output_records = []
        
        # For each building/variant pair
        for _, pair in unique_pairs.iterrows():
            building_id = pair['building_id']
            variant_id = pair['variant_id']
            
            record = {
                'building_id': building_id,
                'variant_id': variant_id
            }
            
            # For each target variable  
            for target_var in target_variables:
                # Check if this target exists in comparison outputs
                if target_var not in comparison_outputs:
                    logger.warning(f"[Preprocessor] Target variable {target_var} not found in comparison outputs")
                    continue
                
                # Get the dataframe for this target
                df = comparison_outputs[target_var]
                
                # Extract variant column name (e.g., 'variant_0_value')
                variant_col = f"{variant_id}_value"
                
                if variant_col in df.columns:
                    # Get values for this variant
                    values = df[variant_col].values
                    
                    # Store aggregated values
                    record[f'{target_var}_sum'] = float(values.sum())
                    record[f'{target_var}_mean'] = float(values.mean())
                    record[f'{target_var}_max'] = float(values.max())
                    record[f'{target_var}_min'] = float(values.min())
                    
                    # Calculate percent change if base values exist
                    if 'base_value' in df.columns:
                        base_values = df['base_value'].values
                        base_sum = base_values.sum()
                        if base_sum != 0:
                            record[f'{target_var}_percent_change'] = float(
                                (values.sum() - base_sum) / base_sum * 100
                            )
                else:
                    logger.warning(f"[Preprocessor] Column {variant_col} not found for {target_var}")
            
            # Only add record if we have some output data
            output_cols = [col for col in record.keys() if col not in ['building_id', 'variant_id']]
            if output_cols:
                output_records.append(record)
        
        if output_records:
            output_df = pd.DataFrame(output_records)
            logger.info(f"[Preprocessor] Created output matrix: {output_df.shape}")
            logger.info(f"[Preprocessor] Output columns: {[col for col in output_df.columns if col not in ['building_id', 'variant_id']]}")
            return output_df
        else:
            logger.warning("[Preprocessor] No output records created")
            return pd.DataFrame()
    
    def handle_multi_level_data(self, 
                              param_matrix: pd.DataFrame, 
                              output_matrix: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Handle zone-level vs building-level analysis.
        """
        logger.info("[Preprocessor] Handling multi-level data")
        
        if self.config['aggregation_level'] == 'zone':
            # Get zone mappings
            zone_mappings = self.data.get('zone_mappings', pd.DataFrame())
            
            if zone_mappings.empty:
                logger.warning("[Preprocessor] No zone mappings available, using building level")
                return param_matrix, output_matrix
            
            # Get zone-level outputs
            modified_outputs = self.data.get('modified_outputs', pd.DataFrame())
            
            # Create zone-level records
            zone_records = []
            
            for _, building in param_matrix.iterrows():
                building_id = building['building_id']
                variant_id = building['variant_id']
                
                # Get zones for this building
                building_zones = zone_mappings[
                    zone_mappings['building_id'] == str(building_id)
                ]['sql_zone_name'].unique()
                
                for zone in building_zones:
                    zone_record = building.to_dict()
                    zone_record['zone_name'] = zone
                    
                    # Get zone-specific outputs
                    zone_mask = (
                        (modified_outputs['original_building_id'] == str(building_id)) &
                        (modified_outputs['variant_id'] == variant_id) &
                        (modified_outputs['Zone'] == zone)
                    )
                    
                    if zone_mask.any():
                        zone_outputs = modified_outputs[zone_mask]
                        
                        # Add zone-level metrics
                        for var in self.config['target_variables']:
                            var_data = zone_outputs[zone_outputs['Variable'] == var]
                            if not var_data.empty:
                                zone_record[f'{var}_zone_total'] = var_data['Value'].sum()
                                zone_record[f'{var}_zone_mean'] = var_data['Value'].mean()
                    
                    zone_records.append(zone_record)
            
            zone_param_matrix = pd.DataFrame(zone_records)
            
            # Update output matrix to include zone information
            logger.info(f"[Preprocessor] Created zone-level data: {zone_param_matrix.shape}")
            
            return zone_param_matrix, output_matrix
        
        return param_matrix, output_matrix
    
    def engineer_features(self, param_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Perform feature engineering on parameter matrix.
        """
        logger.info("[Preprocessor] Engineering features")
        
        features = param_matrix.copy()
        
        # Get numeric columns
        id_cols = ['building_id', 'variant_id', 'zone_name'] if 'zone_name' in features.columns else ['building_id', 'variant_id']
        numeric_cols = [col for col in features.columns if col not in id_cols]
        
        # Create interaction features if requested
        if self.config.get('create_interactions', False):
            logger.info("[Preprocessor] Creating interaction features")
            
            # Select top features based on variance
            variances = features[numeric_cols].var()
            top_features = variances.nlargest(10).index.tolist()
            
            # Create pairwise interactions
            for i, feat1 in enumerate(top_features):
                for feat2 in top_features[i+1:]:
                    features[f'{feat1}_X_{feat2}'] = features[feat1] * features[feat2]
        
        # Add aggregate features
        if len(numeric_cols) > 5:
            features['total_changes'] = features[numeric_cols].abs().sum(axis=1)
            features['mean_change'] = features[numeric_cols].mean(axis=1)
            features['max_change'] = features[numeric_cols].abs().max(axis=1)
            
            # Count non-zero changes
            features['num_parameters_changed'] = (features[numeric_cols] != 0).sum(axis=1)
        
        # Add building characteristics if available
        building_registry = self.data.get('building_registry', pd.DataFrame())
        if not building_registry.empty:
            logger.debug(f"[Preprocessor] Building registry columns: {building_registry.columns.tolist()}")
            
            # Define potential characteristic columns
            potential_chars = ['zone_count', 'total_floor_area', 'total_volume', 'floor_area', 'volume',
                            'num_zones', 'building_area', 'building_volume', 'conditioned_floor_area']
            
            # Find which columns actually exist
            available_chars = ['building_id']  # Always include building_id
            for col in potential_chars:
                if col in building_registry.columns:
                    available_chars.append(col)
                    logger.debug(f"[Preprocessor] Found building characteristic: {col}")
            
            if len(available_chars) > 1:  # More than just building_id
                # Extract available characteristics
                building_chars = building_registry[available_chars].drop_duplicates()
                
                # Merge with features
                features = features.merge(
                    building_chars,
                    on='building_id',
                    how='left'
                )
                logger.info(f"[Preprocessor] Added {len(available_chars) - 1} building characteristics")
            else:
                logger.info("[Preprocessor] No building characteristics found to add")
        else:
            logger.info("[Preprocessor] No building registry data available")
        
        logger.info(f"[Preprocessor] Features after engineering: {features.shape}")
        
        return features
    
    
    def prepare_final_datasets(self, 
                            features: pd.DataFrame, 
                            outputs: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare final feature and target datasets for modeling.
        """
        logger.info("[Preprocessor] Preparing final datasets")
        
        # Check if outputs is empty
        if outputs.empty:
            logger.warning("[Preprocessor] Output matrix is empty, creating dummy targets")
            # Create dummy targets with zeros for now
            outputs = features[['building_id', 'variant_id']].copy()
            for target_var in self.config['target_variables']:
                outputs[f'{target_var}_mean'] = 0.0
                outputs[f'{target_var}_percent_change'] = 0.0
        
        # Merge features with outputs
        merge_keys = ['building_id', 'variant_id']
        if 'zone_name' in features.columns and 'zone_name' in outputs.columns:
            merge_keys.append('zone_name')
        
        combined = features.merge(outputs, on=merge_keys, how='inner')
        
        # Separate features and targets
        id_cols = merge_keys + (['zone_name'] if 'zone_name' in combined.columns else [])
        
        # Identify target columns
        target_patterns = ['_total', '_mean', '_peak', '_percent_change']
        target_cols = []
        for col in combined.columns:
            if any(pattern in col for pattern in target_patterns):
                for var in self.config['target_variables']:
                    if var in col:
                        target_cols.append(col)
                        break
        
        # Get feature columns
        feature_cols = [col for col in combined.columns if col not in id_cols + target_cols]
        
        # Create final datasets
        final_features = combined[id_cols + feature_cols].copy()
        final_targets = combined[id_cols + target_cols].copy()
        
        # Clean feature names for ML compatibility
        final_features = self._clean_feature_names(final_features)
        final_targets = self._clean_feature_names(final_targets)
        
        # Update column lists after cleaning
        feature_cols = [col for col in final_features.columns if col not in id_cols]
        target_cols = [col for col in final_targets.columns if col not in id_cols]
        
        # Handle missing values
        numeric_features = [col for col in feature_cols if col in final_features.columns]
        final_features[numeric_features] = final_features[numeric_features].fillna(0)
        
        numeric_targets = [col for col in target_cols if col in final_targets.columns]
        final_targets[numeric_targets] = final_targets[numeric_targets].fillna(0)
        
        # Normalize features if requested
        if self.config.get('normalize_features', True):
            logger.info("[Preprocessor] Normalizing features")
            
            scaler = StandardScaler()
            final_features[numeric_features] = scaler.fit_transform(final_features[numeric_features])
            
            # Save scaler parameters
            self.processed['scaler'] = scaler
            self.processed['scaler_features'] = numeric_features
        
        # Store metadata
        self.processed['metadata'] = {
            'id_columns': id_cols,
            'feature_columns': feature_cols,
            'target_columns': target_cols,
            'n_samples': len(final_features),
            'n_features': len(feature_cols),
            'n_targets': len(target_cols),
            'aggregation_level': self.config['aggregation_level']
        }
        
        logger.info(f"[Preprocessor] Final features: {final_features.shape}")
        logger.info(f"[Preprocessor] Final targets: {final_targets.shape}")
        logger.info(f"[Preprocessor] Target columns: {target_cols}")
        
        return final_features, final_targets
    
    def generate_training_scenarios(self, 
                                  n_scenarios: int = None,
                                  split_ratio: float = 0.8) -> Dict[str, Any]:
        """
        Generate training and testing scenarios from processed data.
        """
        logger.info("[Preprocessor] Generating training scenarios")
        
        features = self.processed['features']
        targets = self.processed['targets']
        
        if features is None or targets is None:
            raise ValueError("Must run preprocess_all() first")
        
        # Get metadata
        id_cols = self.processed['metadata']['id_columns']
        feature_cols = self.processed['metadata']['feature_columns']
        target_cols = self.processed['metadata']['target_columns']
        
        # Create train/test split
        n_samples = len(features)
        n_train = int(n_samples * split_ratio)
        
        # Shuffle indices
        indices = np.random.permutation(n_samples)
        train_indices = indices[:n_train]
        test_indices = indices[n_train:]
        
        # Split data
        scenarios = {
            'train': {
                'features': features.iloc[train_indices][feature_cols],
                'targets': targets.iloc[train_indices][target_cols],
                'ids': features.iloc[train_indices][id_cols]
            },
            'test': {
                'features': features.iloc[test_indices][feature_cols],
                'targets': targets.iloc[test_indices][target_cols],
                'ids': features.iloc[test_indices][id_cols]
            }
        }
        
        logger.info(f"[Preprocessor] Generated {n_train} training and {len(test_indices)} testing scenarios")
        
        return scenarios
    
    def save_preprocessed_data(self, output_dir: str):
        """
        Save preprocessed data and metadata.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save features and targets
        if self.processed['features'] is not None:
            self.processed['features'].to_parquet(
                output_path / 'preprocessed_features.parquet',
                index=False
            )
        
        if self.processed['targets'] is not None:
            self.processed['targets'].to_parquet(
                output_path / 'preprocessed_targets.parquet',
                index=False
            )
        
        # Save metadata
        with open(output_path / 'preprocessing_metadata.json', 'w') as f:
            json.dump(self.processed['metadata'], f, indent=2)
        
        # Save scaler if exists
        if 'scaler' in self.processed:
            import joblib
            joblib.dump(
                self.processed['scaler'],
                output_path / 'feature_scaler.joblib'
            )
        
        logger.info(f"[Preprocessor] Saved preprocessed data to {output_path}")


# Utility functions
def preprocess_for_surrogate(extracted_data: Dict[str, pd.DataFrame], 
                           config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to preprocess data for surrogate modeling.
    
    Args:
        extracted_data: Data from SurrogateDataExtractor
        config: Preprocessing configuration
        
    Returns:
        Dictionary with processed features, targets, and metadata
    """
    preprocessor = SurrogateDataPreprocessor(extracted_data, config)
    return preprocessor.preprocess_all()