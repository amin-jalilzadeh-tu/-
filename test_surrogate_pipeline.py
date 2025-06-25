"""
test_surrogate_pipeline.py

A unified test script to demonstrate and debug the surrogate data extraction pipeline.
Run this script with your job output directory to see where issues occur.
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
import traceback

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules
try:
    from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
    from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor
    from c_surrogate.unified_surrogate import build_and_save_surrogate_from_preprocessed
    print("✓ Successfully imported surrogate modules")
except ImportError as e:
    print(f"✗ Failed to import modules: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_data_extraction(job_output_dir: str):
    """Test the data extraction step"""
    print("\n" + "="*80)
    print("STEP 1: DATA EXTRACTION")
    print("="*80)
    
    try:
        # Create extractor
        extractor = SurrogateDataExtractor(job_output_dir)
        print(f"✓ Created extractor for: {job_output_dir}")
        
        # Check available data sources
        print("\nChecking for data sources:")
        for name, path in extractor.paths.items():
            exists = path.exists() if path else False
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {path}")
        
        # Extract all data
        print("\nExtracting data...")
        extracted_data = extractor.extract_all()
        
        # Show what was extracted
        print("\nExtracted data summary:")
        for key, data in extracted_data.items():
            if data is not None and not data.empty if hasattr(data, 'empty') else data is not None:
                if hasattr(data, 'shape'):
                    print(f"  ✓ {key}: {data.shape}")
                    if hasattr(data, 'columns'):
                        print(f"    Columns: {list(data.columns)[:5]}{'...' if len(data.columns) > 5 else ''}")
                else:
                    print(f"  ✓ {key}: {type(data)}")
            else:
                print(f"  ✗ {key}: Empty or None")
        
        # Get summary statistics
        summary = extractor.get_summary_statistics()
        print(f"\nExtraction timestamp: {summary['extraction_timestamp']}")
        
        return extracted_data, True
        
    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        traceback.print_exc()
        return None, False


def test_data_preprocessing(extracted_data: dict):
    """Test the data preprocessing step"""
    print("\n" + "="*80)
    print("STEP 2: DATA PREPROCESSING")
    print("="*80)
    
    try:
        # Create preprocessor with default config
        config = {
            'aggregation_level': 'building',
            'temporal_resolution': 'daily',
            'use_sensitivity_filter': False,  # Disable initially for testing
            'normalize_features': True,
            'target_variables': [
                'Heating:EnergyTransfer [J](Hourly)',
                'Cooling:EnergyTransfer [J](Hourly)',
                'Electricity:Facility [J](Hourly)'
            ]
        }
        
        preprocessor = SurrogateDataPreprocessor(extracted_data, config)
        print(f"✓ Created preprocessor with config: {json.dumps(config, indent=2)}")
        
        # Check data before preprocessing
        print("\nData status before preprocessing:")
        for key, data in extracted_data.items():
            if data is not None and hasattr(data, 'shape'):
                print(f"  - {key}: {data.shape}")
        
        # Run preprocessing
        print("\nRunning preprocessing pipeline...")
        processed_data = preprocessor.preprocess_all()
        
        # Show processed data
        print("\nProcessed data summary:")
        if processed_data['features'] is not None:
            print(f"  ✓ Features shape: {processed_data['features'].shape}")
            print(f"    Feature columns: {processed_data['metadata']['feature_columns'][:5]}...")
        else:
            print("  ✗ Features: None")
            
        if processed_data['targets'] is not None:
            print(f"  ✓ Targets shape: {processed_data['targets'].shape}")
            print(f"    Target columns: {processed_data['metadata']['target_columns']}")
        else:
            print("  ✗ Targets: None")
        
        # Show metadata
        metadata = processed_data.get('metadata', {})
        print(f"\nMetadata:")
        print(f"  - Aggregation level: {metadata.get('aggregation_level')}")
        print(f"  - Number of samples: {metadata.get('n_samples')}")
        print(f"  - Number of features: {metadata.get('n_features')}")
        print(f"  - Number of targets: {metadata.get('n_targets')}")
        
        return processed_data, True
        
    except Exception as e:
        print(f"\n✗ Preprocessing failed: {e}")
        traceback.print_exc()
        return None, False


def test_surrogate_building(processed_data: dict, output_dir: str):
    """Test the surrogate model building step"""
    print("\n" + "="*80)
    print("STEP 3: SURROGATE MODEL BUILDING")
    print("="*80)
    
    try:
        # Get data from processed results
        features = processed_data['features']
        targets = processed_data['targets']
        metadata = processed_data['metadata']
        
        if features is None or targets is None:
            print("✗ No features or targets available for modeling")
            return None, False
        
        feature_cols = metadata['feature_columns']
        target_cols = metadata['target_columns']
        
        print(f"Building model with:")
        print(f"  - Features: {len(feature_cols)}")
        print(f"  - Targets: {len(target_cols)}")
        print(f"  - Samples: {len(features)}")
        
        # Build model
        model_path = os.path.join(output_dir, "test_surrogate_model.joblib")
        columns_path = os.path.join(output_dir, "test_surrogate_columns.joblib")
        
        result = build_and_save_surrogate_from_preprocessed(
            features=features,
            targets=targets,
            feature_cols=feature_cols,
            target_cols=target_cols,
            model_out_path=model_path,
            columns_out_path=columns_path,
            test_size=0.2,
            automated_ml=False,  # Use simple RF for testing
            scale_features=True,
            save_metadata=True
        )
        
        if result:
            print(f"\n✓ Model built successfully!")
            print(f"  - Model saved to: {model_path}")
            print(f"  - Metrics: {result['metrics']}")
            return result, True
        else:
            print("\n✗ Model building returned None")
            return None, False
            
    except Exception as e:
        print(f"\n✗ Model building failed: {e}")
        traceback.print_exc()
        return None, False


def diagnose_data_issues(job_output_dir: str):
    """Diagnose common data issues"""
    print("\n" + "="*80)
    print("DIAGNOSTICS")
    print("="*80)
    
    job_path = Path(job_output_dir)
    
    # Check for key directories
    print("\nChecking directory structure:")
    dirs_to_check = [
        "parsed_data",
        "parsed_modified_results",
        "modified_idfs",
        "sensitivity_results",
        "output_IDFs",
        "Sim_Results"
    ]
    
    for dir_name in dirs_to_check:
        dir_path = job_path / dir_name
        if dir_path.exists():
            # Count files
            num_files = sum(1 for _ in dir_path.rglob("*") if _.is_file())
            print(f"  ✓ {dir_name}: {num_files} files")
        else:
            print(f"  ✗ {dir_name}: Not found")
    
    # Check for modification detail files
    print("\nChecking for modification details:")
    mod_path = job_path / "modified_idfs"
    if mod_path.exists():
        mod_files = list(mod_path.glob("modifications_detail_*.parquet"))
        print(f"  Found {len(mod_files)} modification detail files")
        for f in mod_files[:3]:  # Show first 3
            print(f"    - {f.name}")
    
    # Check for parsed data
    print("\nChecking parsed data structure:")
    parsed_path = job_path / "parsed_data"
    if parsed_path.exists():
        # Check IDF data
        idf_path = parsed_path / "idf_data" / "by_category"
        if idf_path.exists():
            categories = list(idf_path.glob("*.parquet"))
            print(f"  ✓ IDF categories: {len(categories)} found")
        
        # Check SQL results
        sql_path = parsed_path / "sql_results" / "timeseries" / "aggregated" / "daily"
        if sql_path.exists():
            outputs = list(sql_path.glob("*.parquet"))
            print(f"  ✓ SQL outputs: {len(outputs)} found")
            for f in outputs:
                print(f"    - {f.name}")
    
    # Check for modified results
    print("\nChecking modified results:")
    mod_parsed_path = job_path / "parsed_modified_results"
    if mod_parsed_path.exists():
        # Similar checks for modified
        sql_path = mod_parsed_path / "sql_results" / "timeseries" / "aggregated" / "daily"
        if sql_path.exists():
            outputs = list(sql_path.glob("*.parquet"))
            print(f"  ✓ Modified outputs: {len(outputs)} found")


def main():
    """Main test function"""
    # Get job output directory from command line or use default
    if len(sys.argv) > 1:
        job_output_dir = sys.argv[1]
    else:
        print("Usage: python test_surrogate_pipeline.py <job_output_dir>")
        print("Example: python test_surrogate_pipeline.py D:\\Documents\\daily\\E_Plus_2040_py\\output\\a44ec124-a996-4735-a174-0a071cdc0d4b")
        return
    
    print(f"Testing surrogate pipeline for: {job_output_dir}")
    
    # Create test output directory
    test_output_dir = os.path.join(job_output_dir, "surrogate_test_output")
    os.makedirs(test_output_dir, exist_ok=True)
    
    # Run diagnostics first
    diagnose_data_issues(job_output_dir)
    
    # Test extraction
    extracted_data, extraction_success = test_data_extraction(job_output_dir)
    if not extraction_success:
        print("\n✗ Extraction failed. Cannot proceed.")
        return
    
    # Save extracted data for inspection
    if extracted_data:
        for key, data in extracted_data.items():
            if data is not None and hasattr(data, 'to_parquet'):
                try:
                    output_file = os.path.join(test_output_dir, f"extracted_{key}.parquet")
                    data.to_parquet(output_file)
                    print(f"  Saved {key} to {output_file}")
                except Exception as e:
                    print(f"  Could not save {key}: {e}")
    
    # Test preprocessing
    processed_data, preprocess_success = test_data_preprocessing(extracted_data)
    if not preprocess_success:
        print("\n✗ Preprocessing failed. Cannot proceed.")
        return
    
    # Test surrogate building
    model_result, model_success = test_surrogate_building(processed_data, test_output_dir)
    
    # Final summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Extraction: {'✓ Success' if extraction_success else '✗ Failed'}")
    print(f"Preprocessing: {'✓ Success' if preprocess_success else '✗ Failed'}")
    print(f"Model Building: {'✓ Success' if model_success else '✗ Failed'}")
    
    if model_success:
        print(f"\nTest outputs saved to: {test_output_dir}")
        print("\nNext steps:")
        print("1. Check the test output directory for saved data files")
        print("2. Review any error messages above")
        print("3. Ensure your job has completed all prerequisite steps:")
        print("   - IDF creation and simulation")
        print("   - Parsing of results")
        print("   - Modification and re-simulation (if using modifications)")
        print("   - Parsing of modified results")


if __name__ == "__main__":
    main()
