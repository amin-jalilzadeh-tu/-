#!/usr/bin/env python3
"""
Run surrogate modeling with updated data structure
Demonstrates usage with new sensitivity and comparison outputs
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from c_surrogate.unified_surrogate import run_surrogate_modeling

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_surrogate_config(job_id):
    """Create comprehensive configuration for surrogate modeling"""
    
    config = {
        # Data extraction settings
        "data_extraction": {
            "job_output_dir": f"output/{job_id}",
            "use_integrated_pipeline": True,
            "extract_zone_level_data": False,  # Building level for now
            "parameter_sources": {
                "modifications": True,
                "sensitivity_filtered": True,
                "validation_filtered": True
            }
        },
        
        # Preprocessing settings
        "preprocessing": {
            "feature_selection": {
                "method": "sensitivity_based",
                "use_sensitivity_filter": True,
                "min_sensitivity_score": 1.0,  # Updated for new scale
                "top_n_features": 20,
                "include_interactions": False  # Start simple
            },
            "aggregation": {
                "temporal_method": "peak_months",
                "spatial_level": "building",
                "aggregation_functions": ["mean", "max", "sum"]
            },
            "normalization": {
                "method": "standard",
                "per_feature": True
            }
        },
        
        # Target configuration
        "target_configuration": {
            "primary_targets": [
                "electricity_facility",
                "cooling_energytransfer",
                "heating_energytransfer"
            ],
            "temporal_resolution": "monthly",
            "use_relative_change": True,
            "multi_output": True
        },
        
        # Model configuration
        "modeling": {
            "model_type": "auto",
            "automl_framework": "flaml",
            "time_budget": 300,  # 5 minutes for quick testing
            "ensemble_methods": ["rf", "xgboost", "lightgbm"],
            "hyperparameter_tuning": {
                "strategy": "bayesian",
                "n_trials": 50,
                "cv_folds": 3,
                "scoring": "r2"
            },
            "validation": {
                "test_size": 0.2,
                "random_state": 42
            }
        },
        
        # Output settings
        "output": {
            "save_model": True,
            "save_predictions": True,
            "generate_api": True,
            "export_feature_importance": True,
            "create_visualizations": True,
            "output_dir": f"output/{job_id}/surrogate_models",
            "model_name": f"surrogate_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    
    return config


def main():
    """Main execution"""
    
    # Use the new job ID with updated data structure
    job_id = "e8092d0e-e434-4c6e-99dc-d571defdcd0e"
    
    logger.info(f"Starting surrogate modeling for job: {job_id}")
    
    # Create configuration
    config = create_surrogate_config(job_id)
    
    # Save configuration for reference
    config_path = Path(f"output/{job_id}/surrogate_models/surrogate_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved configuration to: {config_path}")
    
    try:
        # Run surrogate modeling
        logger.info("Running surrogate modeling with integrated pipeline...")
        results = run_surrogate_modeling(
            job_output_dir=f"output/{job_id}",
            config=config,
            use_integrated_pipeline=True,
            save_outputs=True
        )
        
        # Print results summary
        print("\n" + "="*60)
        print("SURROGATE MODELING RESULTS")
        print("="*60)
        print(f"Job ID: {job_id}")
        print(f"Model Type: {results.get('model_type', 'Unknown')}")
        print(f"AutoML Framework: {config['modeling']['automl_framework']}")
        
        # Validation metrics
        metrics = results.get('validation_metrics', {})
        print(f"\nValidation Metrics:")
        print(f"  R² Score: {metrics.get('r2', 'N/A'):.4f}" if isinstance(metrics.get('r2'), (int, float)) else f"  R² Score: {metrics.get('r2', 'N/A')}")
        print(f"  RMSE: {metrics.get('rmse', 'N/A'):.4f}" if isinstance(metrics.get('rmse'), (int, float)) else f"  RMSE: {metrics.get('rmse', 'N/A')}")
        print(f"  MAE: {metrics.get('mae', 'N/A'):.4f}" if isinstance(metrics.get('mae'), (int, float)) else f"  MAE: {metrics.get('mae', 'N/A')}")
        
        # Feature information
        print(f"\nFeature Information:")
        print(f"  Total Features: {len(results.get('feature_names', []))}")
        print(f"  Training Samples: {results.get('n_samples', 'N/A')}")
        
        # Top features
        feature_importance = results.get('feature_importance', {})
        if feature_importance:
            print(f"\nTop 5 Important Features:")
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            for feat, importance in sorted_features:
                print(f"  - {feat}: {importance:.4f}")
        
        print(f"\nOutput Directory: output/{job_id}/surrogate_models/")
        print("="*60)
        
        # Generate report
        report = {
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "configuration": config,
            "results": {
                "model_type": results.get('model_type'),
                "validation_metrics": metrics,
                "n_features": len(results.get('feature_names', [])),
                "n_samples": results.get('n_samples'),
                "feature_importance": feature_importance
            },
            "status": "success"
        }
        
        report_path = Path(f"output/{job_id}/surrogate_models/surrogate_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved report to: {report_path}")
        
    except Exception as e:
        logger.error(f"Error in surrogate modeling: {str(e)}", exc_info=True)
        
        # Save error report
        error_report = {
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "failed"
        }
        
        error_path = Path(f"output/{job_id}/surrogate_models/surrogate_error.json")
        error_path.parent.mkdir(parents=True, exist_ok=True)
        with open(error_path, 'w') as f:
            json.dump(error_report, f, indent=2)
        
        raise


if __name__ == "__main__":
    main()