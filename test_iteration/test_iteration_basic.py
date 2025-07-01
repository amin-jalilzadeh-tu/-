"""
Test script for basic iteration functionality
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.iteration import IterationManager
from orchestrator.iteration.data_pipeline_manager import DataPipelineManager
from orchestrator.iteration.calibration_feedback import CalibrationFeedback
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


def create_mock_validation_results(iteration: int, building_ids: list):
    """Create mock validation results for testing"""
    results = {
        "building_results": {},
        "overall": {
            "cvrmse": 25.0 - (iteration * 3),  # Improve with each iteration
            "nmbe": 8.0 - (iteration * 1)
        }
    }
    
    for i, bid in enumerate(building_ids):
        # Make some buildings fail validation
        cvrmse = 35.0 - (iteration * 5) + (i * 5)
        passed = cvrmse < 30.0
        
        results["building_results"][bid] = {
            "passed": passed,
            "metrics": {
                "cvrmse": cvrmse,
                "nmbe": 10.0 - (iteration * 2) + i,
                "mbe": 5.0 - iteration
            }
        }
    
    return results


def create_mock_calibration_results(iteration: int):
    """Create mock calibration results"""
    return {
        "best_parameters": {
            "HVAC*Coil:Cooling*COIL_1*Rated COP": 3.5 + (iteration * 0.1),
            "DHW*WaterHeater*WATER_HEATER_1*Efficiency": 0.85 + (iteration * 0.02),
            "materials*Material*WALL_MAT_1*Conductivity": 0.5 - (iteration * 0.05)
        },
        "optimization_metrics": {
            "final_objective": 15.0 - (iteration * 2),
            "iterations": 100
        }
    }


def test_iteration_manager():
    """Test the iteration manager functionality"""
    print("\n=== Testing Iteration Manager ===\n")
    
    # Setup test directory
    test_dir = Path("test_iteration/test_output")
    test_dir.mkdir(exist_ok=True, parents=True)
    
    # Load iteration config
    with open("iteration_config.json", 'r') as f:
        config = json.load(f)
    
    # Initialize iteration manager
    iter_manager = IterationManager(config, str(test_dir))
    
    # Test iteration 1
    print("Testing Iteration 1...")
    buildings = iter_manager.select_buildings(pd.DataFrame())  # No previous results
    print(f"Selected buildings: {buildings}")
    
    # Create mock validation results
    val_results = create_mock_validation_results(0, ["413673000", "413674000"])
    val_df = pd.DataFrame([
        {"building_id": bid, "validation_passed": res["passed"], 
         "cvrmse": res["metrics"]["cvrmse"], "nmbe": res["metrics"]["nmbe"]}
        for bid, res in val_results["building_results"].items()
    ])
    
    # Record performance
    iter_manager.record_iteration_performance(val_df)
    
    # Check if should continue
    should_continue = iter_manager.should_continue()
    print(f"Should continue: {should_continue}")
    
    # Increment iteration
    iter_manager.increment_iteration()
    
    # Test iteration 2
    print("\nTesting Iteration 2...")
    buildings = iter_manager.select_buildings(val_df)
    print(f"Selected buildings for iteration 2: {buildings}")
    
    # Get modification intensity
    intensity = iter_manager.get_modification_intensity()
    print(f"Modification intensity: {intensity}")
    
    # Save summary
    iter_manager.save_iteration_summary()
    print("\nIteration summary saved")


def test_data_pipeline_manager():
    """Test the data pipeline manager"""
    print("\n=== Testing Data Pipeline Manager ===\n")
    
    test_dir = Path("test_iteration/test_output")
    pipeline_mgr = DataPipelineManager(str(test_dir), logger)
    
    # Register some outputs
    print("Registering outputs...")
    pipeline_mgr.register_output("parsing", 1, "parsed_data", 
                                str(test_dir / "parsed_data"))
    pipeline_mgr.register_output("calibration", 1, "best_parameters",
                                str(test_dir / "calibration/best_parameters.json"))
    
    # Test retrieving previous output
    prev_output = pipeline_mgr.get_previous_output("parsing", "parsed_data", 2)
    print(f"Previous output path: {prev_output}")
    
    # Create mock calibration results and test linking
    cal_dir = test_dir / "calibration"
    cal_dir.mkdir(exist_ok=True)
    cal_results = create_mock_calibration_results(1)
    
    cal_file = cal_dir / "best_parameters.json"
    with open(cal_file, 'w') as f:
        json.dump(cal_results, f, indent=2)
    
    # Link calibration to IDF
    linked_path = pipeline_mgr.link_calibration_to_idf(str(cal_file), 2)
    print(f"Linked calibration to IDF: {linked_path}")
    
    # Get summary
    summary = pipeline_mgr.get_data_flow_summary()
    print(f"\nData flow summary: {json.dumps(summary, indent=2)}")


def test_calibration_feedback():
    """Test calibration feedback conversion"""
    print("\n=== Testing Calibration Feedback ===\n")
    
    test_dir = Path("test_iteration/test_output")
    cal_feedback = CalibrationFeedback(str(test_dir), logger)
    
    # Create mock calibration results
    cal_results = create_mock_calibration_results(1)
    
    # Convert to IDF parameters
    idf_params = cal_feedback.convert_to_idf_parameters(cal_results, 2)
    print("Converted IDF parameters:")
    print(json.dumps(idf_params, indent=2))
    
    # Test applying to config
    mock_config = {
        "idf_creation": {},
        "user_config_hvac": [],
        "user_config_dhw": []
    }
    
    updated_config = cal_feedback.apply_to_config(mock_config, idf_params)
    print("\nUpdated configuration:")
    print(json.dumps(updated_config, indent=2))
    
    # Save feedback data
    cal_feedback.save_feedback_data(2, cal_results, idf_params)
    print("\nFeedback data saved")


def test_full_iteration_flow():
    """Test a complete iteration flow"""
    print("\n=== Testing Full Iteration Flow ===\n")
    
    test_dir = Path("test_iteration/test_output_full")
    test_dir.mkdir(exist_ok=True, parents=True)
    
    # Load configs
    with open("iteration_config.json", 'r') as f:
        iter_config = json.load(f)
    
    # Initialize managers
    iter_manager = IterationManager(iter_config, str(test_dir))
    pipeline_mgr = DataPipelineManager(str(test_dir), logger)
    cal_feedback = CalibrationFeedback(str(test_dir), logger)
    
    # Simulate 3 iterations
    for iteration in range(3):
        print(f"\n--- ITERATION {iteration + 1} ---")
        
        # Get iteration directory
        iter_dir = iter_manager.get_iteration_dir()
        print(f"Iteration directory: {iter_dir}")
        
        # Select buildings
        if iteration == 0:
            buildings = ["413673000", "413674000", "413675000"]
        else:
            # Load previous validation results
            prev_val_file = iter_manager.get_iteration_dir(iteration - 1) / "validation" / "validation_summary.parquet"
            if prev_val_file.exists():
                prev_df = pd.read_parquet(prev_val_file)
                buildings = iter_manager.select_buildings(prev_df)
            else:
                buildings = ["413673000", "413674000"]
        
        print(f"Processing buildings: {buildings}")
        
        # Simulate workflow steps
        # 1. IDF Creation (with calibrated params if available)
        if iteration > 0:
            cal_path = pipeline_mgr.get_previous_output("calibration", "best_parameters", iteration)
            if cal_path:
                print(f"Using calibrated parameters from: {cal_path}")
        
        # 2. Simulation (mock)
        print("Running simulations...")
        
        # 3. Parsing (mock)
        parsed_dir = iter_dir / "parsed_data"
        parsed_dir.mkdir(exist_ok=True)
        pipeline_mgr.register_output("parsing", iteration, "parsed_data", str(parsed_dir))
        
        # 4. Validation
        val_results = create_mock_validation_results(iteration, buildings)
        val_df = pd.DataFrame([
            {"building_id": bid, "validation_passed": res["passed"], 
             "cvrmse": res["metrics"]["cvrmse"], "nmbe": res["metrics"]["nmbe"]}
            for bid, res in val_results["building_results"].items()
        ])
        
        # Save validation results
        val_dir = iter_dir / "validation"
        val_dir.mkdir(exist_ok=True)
        val_df.to_parquet(val_dir / "validation_summary.parquet")
        
        with open(val_dir / "validation_results.json", 'w') as f:
            json.dump(val_results, f, indent=2)
        
        pipeline_mgr.register_output("validation", iteration, "validation_summary", 
                                   str(val_dir / "validation_summary.parquet"))
        
        # 5. Calibration
        cal_results = create_mock_calibration_results(iteration)
        cal_dir = iter_dir / "calibration"
        cal_dir.mkdir(exist_ok=True)
        
        cal_file = cal_dir / "best_parameters.json"
        with open(cal_file, 'w') as f:
            json.dump(cal_results, f, indent=2)
        
        pipeline_mgr.register_output("calibration", iteration, "best_parameters", str(cal_file))
        
        # Convert and save for next iteration
        idf_params = cal_feedback.convert_to_idf_parameters(cal_results, iteration + 1)
        cal_feedback.save_feedback_data(iteration + 1, cal_results, idf_params)
        
        # Record performance
        iter_manager.record_iteration_performance(val_df)
        
        # Check convergence
        if not iter_manager.should_continue():
            print("\nConvergence reached or max iterations!")
            break
        
        # Increment iteration
        iter_manager.increment_iteration()
    
    # Save final summary
    iter_manager.save_iteration_summary()
    print("\n=== Iteration workflow complete ===")
    
    # Print final summary
    summary_file = test_dir / "tracking" / "iteration_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        print("\nFinal Summary:")
        print(f"Total iterations: {summary['current_iteration']}")
        print(f"Convergence status: {summary['convergence_status']}")
        print("\nPerformance history:")
        for perf in summary['performance_history']:
            print(f"  Iteration {perf['iteration']}: CVRMSE={perf['avg_cvrmse']:.2f}, NMBE={perf['avg_nmbe']:.2f}")


if __name__ == "__main__":
    # Run all tests
    test_iteration_manager()
    test_data_pipeline_manager() 
    test_calibration_feedback()
    test_full_iteration_flow()
    
    print("\n=== All tests completed ===")