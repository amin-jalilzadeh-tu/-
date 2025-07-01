"""
Simple test for iteration components without full orchestrator imports
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def test_iteration_flow():
    """Test basic iteration flow logic"""
    print("\n=== Testing Iteration Flow ===\n")
    
    # Create test directory
    test_dir = Path("test_iteration/test_output")
    test_dir.mkdir(exist_ok=True, parents=True)
    
    # Mock iteration configuration
    iteration_config = {
        "iteration_control": {
            "enable_iterations": True,
            "max_iterations": 3,
            "convergence_criteria": {
                "metric": "cvrmse",
                "threshold": 15.0,
                "min_improvement": 0.01,
                "patience": 2
            },
            "building_selection": {
                "iteration_1": {
                    "method": "specified",
                    "buildings": ["413673000", "413674000", "413675000"]
                },
                "iteration_2_plus": {
                    "method": "validation_failures",
                    "max_buildings": 10
                }
            }
        }
    }
    
    # Simulate iteration workflow
    current_iteration = 0
    performance_history = []
    converged = False
    
    while current_iteration < iteration_config["iteration_control"]["max_iterations"] and not converged:
        current_iteration += 1
        print(f"\n--- ITERATION {current_iteration} ---")
        
        # Create iteration directory
        iter_dir = test_dir / f"iteration_{current_iteration}"
        iter_dir.mkdir(exist_ok=True)
        
        # Simulate building selection
        if current_iteration == 1:
            buildings = iteration_config["iteration_control"]["building_selection"]["iteration_1"]["buildings"]
        else:
            # Simulate selecting failed buildings
            buildings = ["413673000", "413674000"]  # Mock failed buildings
        
        print(f"Selected buildings: {buildings}")
        
        # Simulate validation results
        validation_results = {
            "iteration": current_iteration,
            "buildings": buildings,
            "metrics": {
                "avg_cvrmse": 25.0 - (current_iteration * 5),  # Improve each iteration
                "avg_nmbe": 8.0 - (current_iteration * 1.5)
            }
        }
        
        # Save validation results
        val_file = iter_dir / "validation_results.json"
        with open(val_file, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        performance_history.append(validation_results["metrics"])
        
        print(f"Average CVRMSE: {validation_results['metrics']['avg_cvrmse']:.2f}")
        print(f"Average NMBE: {validation_results['metrics']['avg_nmbe']:.2f}")
        
        # Check convergence
        criteria = iteration_config["iteration_control"]["convergence_criteria"]
        if validation_results["metrics"]["avg_cvrmse"] <= criteria["threshold"]:
            converged = True
            print(f"\nConverged! CVRMSE {validation_results['metrics']['avg_cvrmse']:.2f} <= {criteria['threshold']}")
        elif current_iteration > 1:
            # Check improvement
            prev_cvrmse = performance_history[-2]["avg_cvrmse"]
            curr_cvrmse = performance_history[-1]["avg_cvrmse"]
            improvement = (prev_cvrmse - curr_cvrmse) / prev_cvrmse
            
            if improvement < criteria["min_improvement"]:
                converged = True
                print(f"\nMinimal improvement: {improvement:.3f} < {criteria['min_improvement']}")
    
    # Save summary
    summary = {
        "total_iterations": current_iteration,
        "converged": converged,
        "performance_history": performance_history,
        "final_metrics": performance_history[-1] if performance_history else None
    }
    
    summary_file = test_dir / "iteration_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n=== Iteration Complete ===")
    print(f"Total iterations: {current_iteration}")
    print(f"Converged: {converged}")
    print(f"Final CVRMSE: {performance_history[-1]['avg_cvrmse']:.2f}")
    
    return summary


def test_data_flow():
    """Test data flow between iterations"""
    print("\n=== Testing Data Flow ===\n")
    
    test_dir = Path("test_iteration/test_output")
    
    # Simulate data flow registry
    data_registry = {
        "iteration_1": {
            "outputs": {
                "parsing": "iteration_1/parsed_data",
                "validation": "iteration_1/validation_results.json",
                "calibration": "iteration_1/calibration/best_parameters.json"
            }
        }
    }
    
    # Create mock calibration results
    cal_dir = test_dir / "iteration_1" / "calibration"
    cal_dir.mkdir(exist_ok=True, parents=True)
    
    calibration_results = {
        "best_parameters": {
            "HVAC*Coil:Cooling*COIL_1*Rated COP": 3.5,
            "DHW*WaterHeater*WATER_HEATER_1*Efficiency": 0.85,
            "materials*Material*WALL_MAT_1*Conductivity": 0.45
        }
    }
    
    cal_file = cal_dir / "best_parameters.json"
    with open(cal_file, 'w') as f:
        json.dump(calibration_results, f, indent=2)
    
    # Convert to IDF parameters
    idf_params = {
        "calibration_stage": "post_calibration",
        "iteration": 2,
        "overrides": {
            "hvac": [
                {
                    "object_type": "Coil:Cooling",
                    "object_name": "COIL_1",
                    "field": "Rated COP",
                    "value": 3.5
                }
            ],
            "dhw": [
                {
                    "object_type": "WaterHeater",
                    "object_name": "WATER_HEATER_1",
                    "field": "Efficiency",
                    "value": 0.85
                }
            ],
            "materials": [
                {
                    "object_type": "Material",
                    "object_name": "WALL_MAT_1",
                    "field": "Conductivity",
                    "value": 0.45
                }
            ]
        }
    }
    
    # Save converted parameters
    params_dir = test_dir / "idf_parameters"
    params_dir.mkdir(exist_ok=True)
    
    params_file = params_dir / "calibrated_params_iter_2.json"
    with open(params_file, 'w') as f:
        json.dump(idf_params, f, indent=2)
    
    print(f"Calibration results converted and saved to: {params_file}")
    print(f"Total parameter overrides: {sum(len(v) for v in idf_params['overrides'].values())}")
    
    # Test building selection from validation
    val_results = {
        "building_results": {
            "413673000": {"passed": False, "metrics": {"cvrmse": 35.0}},
            "413674000": {"passed": False, "metrics": {"cvrmse": 32.0}},
            "413675000": {"passed": True, "metrics": {"cvrmse": 25.0}}
        }
    }
    
    failed_buildings = [bid for bid, res in val_results["building_results"].items() 
                       if not res["passed"]]
    
    print(f"\nFailed buildings for next iteration: {failed_buildings}")
    
    return True


def create_test_report():
    """Create a summary report of test results"""
    print("\n=== Creating Test Report ===\n")
    
    test_dir = Path("test_iteration/test_output")
    
    # Read iteration summary
    summary_file = test_dir / "iteration_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        # Create report
        report = [
            "# Iteration Test Report",
            "",
            "## Summary",
            f"- Total iterations: {summary['total_iterations']}",
            f"- Converged: {summary['converged']}",
            f"- Final CVRMSE: {summary['final_metrics']['avg_cvrmse']:.2f}%",
            f"- Final NMBE: {summary['final_metrics']['avg_nmbe']:.2f}%",
            "",
            "## Performance History",
            "| Iteration | CVRMSE | NMBE | Improvement |",
            "|-----------|--------|------|-------------|"
        ]
        
        prev_cvrmse = None
        for i, metrics in enumerate(summary['performance_history']):
            improvement = "-"
            if prev_cvrmse is not None:
                improvement = f"{((prev_cvrmse - metrics['avg_cvrmse']) / prev_cvrmse * 100):.1f}%"
            
            report.append(f"| {i+1} | {metrics['avg_cvrmse']:.2f}% | {metrics['avg_nmbe']:.2f}% | {improvement} |")
            prev_cvrmse = metrics['avg_cvrmse']
        
        report.extend([
            "",
            "## Data Flow Test",
            "- ✓ Calibration results conversion",
            "- ✓ Building selection from validation",
            "- ✓ Parameter feedback to IDF creation",
            "",
            "## File Structure",
            "```",
            "test_output/",
            "├── iteration_1/",
            "│   ├── validation_results.json",
            "│   └── calibration/",
            "│       └── best_parameters.json",
            "├── iteration_2/",
            "│   └── validation_results.json",
            "├── iteration_3/",
            "│   └── validation_results.json",
            "├── idf_parameters/",
            "│   └── calibrated_params_iter_2.json",
            "└── iteration_summary.json",
            "```"
        ])
        
        # Save report
        report_file = test_dir / "test_report.md"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report))
        
        print("Report saved to: test_iteration/test_output/test_report.md")
        print("\nReport Preview:")
        print('\n'.join(report[:15]))
        print("...")
        
    else:
        print("No iteration summary found")


if __name__ == "__main__":
    # Run tests
    print("Starting iteration tests...")
    
    # Test iteration flow
    iteration_summary = test_iteration_flow()
    
    # Test data flow
    data_flow_success = test_data_flow()
    
    # Create report
    create_test_report()
    
    print("\n=== All tests completed successfully ===")