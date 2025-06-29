#!/usr/bin/env python3
"""
Complete test script for surrogate modeling pipeline.
Tests all steps and fixes issues as they arise.
"""

import os
import sys
import logging
from pathlib import Path
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor
from c_surrogate.unified_surrogate import build_surrogate_from_job
from c_surrogate.surrogate_pipeline_tracker import SurrogatePipelineTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_surrogate_pipeline():
    """Test the complete surrogate modeling pipeline."""
    
    # Job directory with data
    job_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/38eb2e7b-709d-43ec-9635-18a7288d7540")
    
    if not job_dir.exists():
        logger.error(f"Job directory not found: {job_dir}")
        return False
    
    logger.info(f"Testing surrogate pipeline with job directory: {job_dir}")
    
    # Create pipeline tracker
    tracker = SurrogatePipelineTracker(job_dir / "test_surrogate_tracker")
    
    # Configuration for surrogate modeling
    sur_cfg = {
        'enabled': True,
        'data_extraction': {
            'include_validation': True,
            'include_zone_data': True
        },
        'preprocessing': {
            'aggregation_level': 'building',
            'use_sensitivity_filter': True,
            'sensitivity_threshold': 0.1,
            'normalize_features': True,
            'create_interactions': False,
            'target_variables': [
                'heating_energytransfer_na',
                'cooling_energytransfer_na'
            ]
        },
        'model_type': 'random_forest',
        'automated_ml': True,
        'model_types': ['random_forest', 'extra_trees'],
        'test_size': 0.2,
        'scale_features': True,
        'save_metadata': True,
        'model_out': str(job_dir / 'test_surrogate_model.joblib'),
        'cols_out': str(job_dir / 'test_surrogate_columns.joblib'),
        'output_management': {
            'create_validation_reports': True,
            'create_prediction_interface': True,
            'version': '1.0'
        }
    }
    
    try:
        # Step 1: Test Data Extraction
        logger.info("="*60)
        logger.info("STEP 1: Testing Data Extraction")
        logger.info("="*60)
        
        tracker.log_step("data_extraction", "started")
        
        extractor = SurrogateDataExtractor(job_dir, sur_cfg['data_extraction'], tracker)
        extracted_data = extractor.extract_all()
        
        summary = extractor.get_summary_statistics()
        logger.info(f"Extraction Summary: {summary}")
        
        # Log what was extracted
        for key, data in extracted_data.items():
            if data is not None:
                if hasattr(data, 'shape'):
                    logger.info(f"  {key}: shape={data.shape}")
                elif isinstance(data, dict):
                    logger.info(f"  {key}: dict with {len(data)} keys")
                else:
                    logger.info(f"  {key}: {type(data)}")
        
        tracker.log_step("data_extraction", "completed", {
            "sources_found": len([d for d in extracted_data.values() if d is not None])
        })
        
        # Step 2: Test Data Preprocessing
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Testing Data Preprocessing")
        logger.info("="*60)
        
        tracker.log_step("preprocessing", "started")
        
        preprocessor = SurrogateDataPreprocessor(extracted_data, sur_cfg['preprocessing'], tracker)
        processed_data = preprocessor.preprocess_all()
        
        logger.info(f"Preprocessing Results:")
        logger.info(f"  Features shape: {processed_data['features'].shape}")
        logger.info(f"  Targets shape: {processed_data['targets'].shape}")
        logger.info(f"  Feature columns: {len(processed_data['metadata']['feature_columns'])}")
        logger.info(f"  Target columns: {processed_data['metadata']['target_columns']}")
        
        tracker.log_step("preprocessing", "completed", {
            "n_features": len(processed_data['metadata']['feature_columns']),
            "n_samples": len(processed_data['features'])
        })
        
        # Step 3: Test Full Pipeline
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Testing Full Surrogate Pipeline")
        logger.info("="*60)
        
        tracker.log_step("full_pipeline", "started")
        
        output_dir = job_dir / 'test_surrogate_output'
        output_dir.mkdir(exist_ok=True)
        
        result = build_surrogate_from_job(
            job_output_dir=str(job_dir),
            sur_cfg=sur_cfg,
            output_dir=str(output_dir),
            tracker=tracker
        )
        
        logger.info("Full pipeline completed successfully!")
        logger.info(f"Results:")
        logger.info(f"  Model type: {result['metadata'].get('model_info', {}).get('model_type')}")
        logger.info(f"  Features used: {result['preprocessing_summary']['n_features']}")
        logger.info(f"  Samples used: {result['preprocessing_summary']['n_samples']}")
        
        if result.get('validation_results'):
            logger.info(f"  Validation R² scores:")
            for target, metrics in result['validation_results']['target_metrics'].items():
                logger.info(f"    {target}: {metrics['r2']:.4f}")
        
        tracker.log_step("full_pipeline", "completed", {
            "model_saved": True,
            "validation_complete": result.get('validation_results') is not None
        })
        
        # Create final summary
        tracker.create_pipeline_summary()
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}")
        logger.error(traceback.format_exc())
        
        tracker.add_error(str(e))
        tracker.log_step("pipeline", "failed", {"error": str(e)})
        tracker.create_pipeline_summary()
        
        return False


if __name__ == "__main__":
    success = test_surrogate_pipeline()
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("SURROGATE PIPELINE TEST COMPLETED SUCCESSFULLY!")
        logger.info("="*60)
    else:
        logger.error("\n" + "="*60)
        logger.error("SURROGATE PIPELINE TEST FAILED!")
        logger.error("="*60)
        sys.exit(1)