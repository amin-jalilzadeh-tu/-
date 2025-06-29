#!/usr/bin/env python3
"""
Test script for surrogate modeling pipeline with new data structure.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
from c_surrogate.surrogate_data_consolidator import SurrogateDataConsolidator
from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor
from c_surrogate.unified_surrogate import build_surrogate_from_job

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_data_extraction(job_dir):
    """Test data extraction step."""
    logger.info("=" * 50)
    logger.info("Testing Data Extraction")
    logger.info("=" * 50)
    
    extractor = SurrogateDataExtractor(job_dir)
    extracted_data = extractor.extract_all()
    
    # Get summary
    summary = extractor.get_summary_statistics()
    
    logger.info("Extracted data sources:")
    for key, info in summary['data_sources'].items():
        logger.info(f"  - {key}: {info}")
    
    return extracted_data


def test_data_consolidation(extracted_data):
    """Test data consolidation step."""
    logger.info("=" * 50)
    logger.info("Testing Data Consolidation")
    logger.info("=" * 50)
    
    consolidator = SurrogateDataConsolidator(extracted_data)
    
    # Test comparison output consolidation
    consolidated_outputs = consolidator.consolidate_comparison_outputs()
    logger.info(f"Consolidated outputs shape: {consolidated_outputs.shape}")
    
    if not consolidated_outputs.empty:
        logger.info(f"Consolidated outputs columns: {list(consolidated_outputs.columns)}")
        logger.info(f"Unique comparison keys: {consolidated_outputs['comparison_key'].nunique()}")
    
    # Test feature-target alignment
    features_df, targets_df = consolidator.create_feature_target_alignment()
    
    logger.info(f"Features shape: {features_df.shape}")
    logger.info(f"Targets shape: {targets_df.shape}")
    
    if not features_df.empty:
        logger.info(f"Feature columns: {[col for col in features_df.columns if col not in ['building_id', 'variant_id']][:5]}...")
    
    if not targets_df.empty:
        logger.info(f"Target columns: {[col for col in targets_df.columns if col not in ['building_id', 'variant_id']]}")
    
    return features_df, targets_df


def test_preprocessing(extracted_data):
    """Test preprocessing step."""
    logger.info("=" * 50)
    logger.info("Testing Data Preprocessing")
    logger.info("=" * 50)
    
    # Add consolidated data if available
    consolidator = SurrogateDataConsolidator(extracted_data)
    features_df, targets_df = consolidator.create_feature_target_alignment()
    
    if not features_df.empty and not targets_df.empty:
        extracted_data['consolidated_features'] = features_df
        extracted_data['consolidated_targets'] = targets_df
    
    # Configure preprocessing
    config = {
        'aggregation_level': 'building',
        'use_sensitivity_filter': True,
        'sensitivity_threshold': 0.1,
        'normalize_features': True,
        'target_variables': [
            'electricity_facility_na_yearly_from_monthly',
            'heating_energytransfer_na_yearly_from_monthly',
            'cooling_energytransfer_na_yearly_from_monthly'
        ]
    }
    
    preprocessor = SurrogateDataPreprocessor(extracted_data, config)
    
    try:
        processed_data = preprocessor.preprocess_all()
        
        logger.info("Preprocessing successful!")
        logger.info(f"Features shape: {processed_data['features'].shape}")
        logger.info(f"Targets shape: {processed_data['targets'].shape}")
        logger.info(f"Feature columns: {len(processed_data['metadata']['feature_columns'])}")
        logger.info(f"Target columns: {processed_data['metadata']['target_columns']}")
        
        return processed_data
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        return None


def test_full_pipeline(job_dir):
    """Test the full surrogate modeling pipeline."""
    logger.info("=" * 50)
    logger.info("Testing Full Surrogate Pipeline")
    logger.info("=" * 50)
    
    # Surrogate configuration
    sur_cfg = {
        'enabled': True,
        'data_extraction': {},
        'preprocessing': {
            'aggregation_level': 'building',
            'use_sensitivity_filter': True,
            'sensitivity_threshold': 0.1
        },
        'model_type': 'random_forest',
        'model_out': 'test_surrogate_model.joblib',
        'cols_out': 'test_surrogate_columns.joblib'
    }
    
    try:
        result = build_surrogate_from_job(
            job_output_dir=job_dir,
            sur_cfg=sur_cfg,
            output_dir=job_dir / 'test_surrogate_output'
        )
        
        logger.info("Full pipeline successful!")
        logger.info(f"Model saved: {result.get('model_path', 'Unknown')}")
        logger.info(f"Performance: {result.get('performance', {})}")
        
        return result
    except Exception as e:
        logger.error(f"Full pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function."""
    # Use the provided job output directory
    job_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/caf564d0-df1e-4335-9d21-e68e687f250e")
    
    if not job_dir.exists():
        logger.error(f"Job directory not found: {job_dir}")
        return
    
    # Test individual steps
    logger.info(f"Testing with job directory: {job_dir}")
    
    # Step 1: Test extraction
    extracted_data = test_data_extraction(job_dir)
    
    # Step 2: Test consolidation
    features_df, targets_df = test_data_consolidation(extracted_data)
    
    # Step 3: Test preprocessing
    processed_data = test_preprocessing(extracted_data)
    
    # Step 4: Test full pipeline
    # Commented out to avoid creating actual model files during testing
    # result = test_full_pipeline(job_dir)
    
    logger.info("=" * 50)
    logger.info("Testing completed!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()