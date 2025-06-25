"""
test_surrogate_fixed.py

Fixed version of the test script that handles target variable discovery
and properly aggregates outputs.
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor
from c_surrogate.unified_surrogate import build_and_save_surrogate_from_preprocessed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def discover_target_variables(extracted_data: dict) -> list:
    """Discover available target variables from the extracted data"""
    print("\nDiscovering target variables...")
    
    base_outputs = extracted_data.get('base_outputs', pd.DataFrame())
    if base_outputs.empty:
        print("  ✗ No base outputs found")
        return []
    
    if 'Variable' not in base_outputs.columns:
        print("  ✗ No Variable column in outputs")
        return []
    
    # Get unique variables
    unique_vars = base_outputs['Variable'].unique()
    print(f"  Found {len(unique_vars)} unique variables")
    
    # Look for energy-related variables
    target_vars = []
    
    # Priority patterns to search for
    patterns = [
        ('heating', ['Zone Air System Sensible Heating Energy', 'Heating:EnergyTransfer']),
        ('cooling', ['Zone Air System Sensible Cooling Energy', 'Cooling:EnergyTransfer']),
        ('electricity', ['Electricity:Facility', 'InteriorLights:Electricity'])
    ]
    
    for category, search_terms in patterns:
        found = False
        for term in search_terms:
            matching = [v for v in unique_vars if term in v]
            if matching:
                target_vars.append(matching[0])
                print(f"  ✓ {category}: {matching[0]}")
                found = True
                break
        if not found:
            print(f"  ✗ {category}: No matching variable found")
    
    return target_vars


def run_fixed_preprocessing(extracted_data: dict, target_variables: list):
    """Run preprocessing with discovered target variables"""
    print(f"\nRunning preprocessing with {len(target_variables)} target variables")
    
    config = {
        'aggregation_level': 'building',
        'temporal_resolution': 'daily',
        'use_sensitivity_filter': False,
        'normalize_features': True,
        'target_variables': target_variables
    }
    
    # Create a custom preprocessor that handles the aggregation better
    preprocessor = SurrogateDataPreprocessorFixed(extracted_data, config)
    processed_data = preprocessor.preprocess_all()
    
    return processed_data


class SurrogateDataPreprocessorFixed(SurrogateDataPreprocessor):
    """Fixed version of preprocessor that handles aggregation correctly"""
    
    def aggregate_outputs(self, aligned_data: pd.DataFrame) -> pd.DataFrame:
        """Fixed aggregation that properly handles the output data structure"""
        logger.info("[Preprocessor] Aggregating outputs (fixed version)")
        
        base_outputs = self.data.get('base_outputs', pd.DataFrame())
        modified_outputs = self.data.get('modified_outputs', pd.DataFrame())
        
        target_variables = self.config['target_variables']
        
        # Debug: show what we're looking for
        logger.info(f"[Preprocessor] Looking for variables: {target_variables}")
        
        # Check what variables are actually in the data
        if not modified_outputs.empty and 'Variable' in modified_outputs.columns:
            available_vars = modified_outputs['Variable'].unique()
            logger.info(f"[Preprocessor] Available variables in modified outputs: {len(available_vars)}")
            for target in target_variables:
                if target in available_vars:
                    logger.info(f"[Preprocessor]   ✓ Found: {target}")
                else:
                    logger.info(f"[Preprocessor]   ✗ Not found: {target}")
        
        # Process outputs for each building/variant
        output_records = []
        unique_pairs = aligned_data[['building_id', 'variant_id']].drop_duplicates()
        
        for _, pair in unique_pairs.iterrows():
            building_id = str(pair['building_id'])
            variant_id = pair['variant_id']
            
            record = {
                'building_id': building_id,
                'variant_id': variant_id
            }
            
            # Get modified outputs for this building/variant
            if 'original_building_id' in modified_outputs.columns:
                mod_mask = (
                    (modified_outputs['original_building_id'] == building_id) &
                    (modified_outputs['variant_id'] == variant_id)
                )
            else:
                mod_mask = (modified_outputs['building_id'] == building_id)
            
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
                        if not base_outputs.empty:
                            base_mask = (
                                (base_outputs['building_id'] == building_id) &
                                (base_outputs['Variable'] == var)
                            )
                            
                            if base_mask.any():
                                base_total = base_outputs[base_mask]['Value'].sum()
                                if base_total != 0:
                                    record[f'{var}_percent_change'] = (
                                        (total_value - base_total) / base_total * 100
                                    )
                    else:
                        # Variable not found - use 0
                        logger.debug(f"[Preprocessor] Variable {var} not found for building {building_id}, variant {variant_id}")
                        record[f'{var}_total'] = 0
                        record[f'{var}_mean'] = 0
                        record[f'{var}_peak'] = 0
            
            output_records.append(record)
        
        output_df = pd.DataFrame(output_records)
        logger.info(f"[Preprocessor] Aggregated outputs: {output_df.shape}")
        
        # Show which columns were created
        output_cols = [col for col in output_df.columns if col not in ['building_id', 'variant_id']]
        logger.info(f"[Preprocessor] Output columns created: {output_cols}")
        
        return output_df


    # Add this method to the SurrogateDataPreprocessor class:

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



def main():
    """Main test function"""
    if len(sys.argv) > 1:
        job_output_dir = sys.argv[1]
    else:
        print("Usage: python test_surrogate_fixed.py <job_output_dir>")
        return
    
    print(f"Testing surrogate pipeline (FIXED) for: {job_output_dir}")
    
    # Create test output directory
    test_output_dir = os.path.join(job_output_dir, "surrogate_test_output_fixed")
    os.makedirs(test_output_dir, exist_ok=True)
    
    try:
        # Step 1: Extract data
        print("\n" + "="*80)
        print("STEP 1: DATA EXTRACTION")
        print("="*80)
        
        extractor = SurrogateDataExtractor(job_output_dir)
        extracted_data = extractor.extract_all()
        print("✓ Data extraction completed")
        
        # Step 2: Discover target variables
        print("\n" + "="*80)
        print("STEP 2: TARGET VARIABLE DISCOVERY")
        print("="*80)
        
        target_variables = discover_target_variables(extracted_data)
        
        if not target_variables:
            print("\n✗ No suitable target variables found!")
            print("Please check that your simulation outputs include energy variables")
            return
        
        # Step 3: Preprocess with correct targets
        print("\n" + "="*80)
        print("STEP 3: DATA PREPROCESSING")
        print("="*80)
        
        processed_data = run_fixed_preprocessing(extracted_data, target_variables)
        
        # Check if we have valid data
        features = processed_data['features']
        targets = processed_data['targets']
        metadata = processed_data['metadata']
        
        print(f"\nPreprocessing results:")
        print(f"  Features shape: {features.shape if features is not None else 'None'}")
        print(f"  Targets shape: {targets.shape if targets is not None else 'None'}")
        print(f"  Target columns: {metadata.get('target_columns', [])}")
        
        # Step 4: Build model if we have targets
        if metadata.get('n_targets', 0) > 0:
            print("\n" + "="*80)
            print("STEP 4: SURROGATE MODEL BUILDING")
            print("="*80)
            
            feature_cols = metadata['feature_columns']
            target_cols = metadata['target_columns']
            
            print(f"Building model with {len(feature_cols)} features and {len(target_cols)} targets")
            
            model_path = os.path.join(test_output_dir, "fixed_surrogate_model.joblib")
            columns_path = os.path.join(test_output_dir, "fixed_surrogate_columns.joblib")
            
            result = build_and_save_surrogate_from_preprocessed(
                features=features,
                targets=targets,
                feature_cols=feature_cols,
                target_cols=target_cols,
                model_out_path=model_path,
                columns_out_path=columns_path,
                test_size=0.2,
                automated_ml=False,
                scale_features=True,
                save_metadata=True
            )
            
            if result:
                print("\n✓ Model built successfully!")
                print(f"  Model metrics: {result['metrics']}")
            else:
                print("\n✗ Model building failed")
        else:
            print("\n✗ No targets found after preprocessing - cannot build model")
            print("This usually means the target variables specified don't match the actual output data")
        
        # Save diagnostic info
        diagnostic_info = {
            'discovered_targets': target_variables,
            'preprocessing_metadata': metadata,
            'data_shapes': {
                'extracted_modifications': extracted_data['modifications'].shape if extracted_data.get('modifications') is not None else None,
                'extracted_base_outputs': extracted_data['base_outputs'].shape if extracted_data.get('base_outputs') is not None else None,
                'extracted_modified_outputs': extracted_data['modified_outputs'].shape if extracted_data.get('modified_outputs') is not None else None,
                'processed_features': features.shape if features is not None else None,
                'processed_targets': targets.shape if targets is not None else None
            }
        }
        
        with open(os.path.join(test_output_dir, 'diagnostic_info.json'), 'w') as f:
            json.dump(diagnostic_info, f, indent=2)
        
        print(f"\n✓ Diagnostic info saved to {test_output_dir}")
        
    except Exception as e:
        print(f"\n✗ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
