"""
Test the calibration process with actual data
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append('/mnt/d/Documents/daily/E_Plus_2040_py')

def test_calibration_workflow():
    """Test the calibration workflow step by step"""
    
    output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99"
    
    logger.info("=== STEP 1: Testing data loading ===")
    from calibration_workflow_integrated import IntegratedCalibrationWorkflow
    
    workflow = IntegratedCalibrationWorkflow(output_dir)
    
    try:
        workflow.load_existing_results()
        logger.info("✓ Successfully loaded existing results")
        
        if workflow.sensitivity_results is not None:
            logger.info(f"  - Sensitivity results: {len(workflow.sensitivity_results)} parameters")
            logger.info(f"  - Top parameter: {workflow.sensitivity_results.iloc[0]['parameter']} "
                       f"(score: {workflow.sensitivity_results.iloc[0]['sensitivity_score']:.2f})")
        
        if workflow.modifications_summary is not None:
            logger.info(f"  - Modifications summary: {len(workflow.modifications_summary)} parameters")
            
    except Exception as e:
        logger.error(f"✗ Failed to load results: {str(e)}")
        return
    
    logger.info("\n=== STEP 2: Testing parameter selection ===")
    try:
        param_specs = workflow.select_calibration_parameters(top_n=10, sensitivity_threshold=0.5)
        logger.info(f"✓ Selected {len(param_specs)} parameters for calibration")
        
        for i, spec in enumerate(param_specs[:3]):
            logger.info(f"  {i+1}. {spec.name}: [{spec.min_value:.3f}, {spec.max_value:.3f}]")
            
    except Exception as e:
        logger.error(f"✗ Failed to select parameters: {str(e)}")
        return
    
    logger.info("\n=== STEP 3: Testing surrogate model ===")
    try:
        from calibration_surrogate_adapter import create_surrogate_calibrator
        
        # Create dummy measured data for testing
        measured_data = pd.DataFrame({
            'electricity_total': np.random.normal(50000, 5000, 12),  # kWh per month
            'month': range(1, 13)
        })
        
        calibrator = create_surrogate_calibrator(output_dir, measured_data)
        logger.info("✓ Successfully loaded surrogate model")
        
        # Test a prediction
        test_params = {spec.name: (spec.min_value + spec.max_value) / 2 for spec in param_specs}
        test_result = calibrator.adapter.simulate(test_params)
        logger.info(f"  - Test prediction successful: {list(test_result.keys())}")
        logger.info(f"  - Heating energy: {test_result['Zone_Air_System_Sensible_Heating_Energy_mean']:.2f}")
        logger.info(f"  - Cooling energy: {test_result['Zone_Air_System_Sensible_Cooling_Energy_mean']:.2f}")
        
    except Exception as e:
        logger.error(f"✗ Failed to load/test surrogate model: {str(e)}")
        return
    
    logger.info("\n=== STEP 4: Testing calibration run ===")
    try:
        # Use real validation data if available
        validation_path = Path(output_dir) / "parsed_data" / "validation_results.parquet"
        if validation_path.exists():
            val_data = pd.read_parquet(validation_path)
            if 'real_value' in val_data.columns and not val_data['real_value'].isna().all():
                measured_data = pd.DataFrame({
                    'electricity_total': val_data['real_value'].values,
                    'month': range(1, len(val_data) + 1)
                })
                logger.info("  - Using real validation data for calibration")
        
        results = workflow.run_calibration(
            measured_data,
            algorithm='PSO',
            max_iter=10,  # Quick test
            population_size=10
        )
        
        logger.info("✓ Calibration completed successfully")
        logger.info(f"  - Best objective: {results['best_objective']:.4f}")
        logger.info(f"  - CVRMSE: {results['final_metrics']['CVRMSE']:.2f}%")
        logger.info(f"  - NMBE: {results['final_metrics']['NMBE']:.2f}%")
        logger.info(f"  - Total evaluations: {results['total_evaluations']}")
        
        logger.info("\n  Top calibrated parameters:")
        for param, value in list(results['best_parameters'].items())[:5]:
            logger.info(f"    {param}: {value:.3f}")
            
    except Exception as e:
        logger.error(f"✗ Calibration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("\n=== STEP 5: Testing output saving ===")
    try:
        output_path = Path(output_dir) / "calibrated_parameters"
        workflow.save_calibrated_parameters(results, str(output_path))
        
        # Check if files were created
        csv_files = list(output_path.glob("*.csv"))
        logger.info(f"✓ Saved {len(csv_files)} parameter CSV files")
        
        summary_path = output_path / "calibration_summary.json"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            logger.info("✓ Calibration summary saved successfully")
            logger.info(f"  - Parameters: {len(summary['parameters'])}")
            logger.info(f"  - CVRMSE: {summary['calibration_metrics']['CVRMSE']:.2f}%")
            
    except Exception as e:
        logger.error(f"✗ Failed to save outputs: {str(e)}")
        return
    
    logger.info("\n=== CALIBRATION TEST COMPLETE ===")
    logger.info("All tests passed! The calibration system is ready to use.")


if __name__ == "__main__":
    test_calibration_workflow()