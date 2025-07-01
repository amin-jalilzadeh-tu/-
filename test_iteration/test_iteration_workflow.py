#!/usr/bin/env python3
"""
Test script for iteration workflow
"""

import os
import sys
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.iteration.iteration_manager import IterationManager
from orchestrator.iteration.validation_support import extract_building_summary


def setup_test_environment():
    """Set up test directories and logging"""
    test_dir = Path(__file__).parent
    output_dir = test_dir / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = output_dir / f"test_iteration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return output_dir, logging.getLogger(__name__)


def create_mock_validation_results(num_buildings=10):
    """Create mock validation results for testing"""
    import numpy as np
    
    # Create building data with varying performance
    buildings = []
    for i in range(num_buildings):
        # Create some buildings that fail, some that pass
        cvrmse = np.random.uniform(10, 50)  # Some above 30 threshold
        nmbe = np.random.uniform(-15, 15)    # Some above 10 threshold
        
        buildings.append({
            'building_id': f'building_{i:03d}',
            'cvrmse': cvrmse,
            'nmbe': nmbe,
            'validation_passed': cvrmse < 30 and abs(nmbe) < 10,
            'num_variables_validated': 3,
            'num_variables_passed': 2 if cvrmse < 30 else 1
        })
    
    return pd.DataFrame(buildings)


def test_iteration_manager():
    """Test the iteration manager functionality"""
    output_dir, logger = setup_test_environment()
    
    logger.info("Starting iteration workflow test")
    
    # Load test configuration
    config_file = Path(__file__).parent / "test_iteration_config.json"
    with open(config_file) as f:
        config = json.load(f)
    
    # Initialize iteration manager
    iteration_manager = IterationManager(config, str(output_dir))
    
    # Test iteration 0 (baseline)
    logger.info("\n=== Testing Iteration 0 (Baseline) ===")
    mock_validation = create_mock_validation_results(10)
    
    # Save mock validation results
    iter0_dir = iteration_manager.get_iteration_dir(0)
    iter0_dir.mkdir(parents=True, exist_ok=True)
    mock_validation.to_parquet(iter0_dir / "validation_summary.parquet")
    
    # Record baseline performance
    iteration_manager.record_iteration_performance(mock_validation)
    
    # Log baseline stats
    logger.info(f"Baseline validation results:")
    logger.info(f"  - Total buildings: {len(mock_validation)}")
    logger.info(f"  - Passed: {len(mock_validation[mock_validation['validation_passed']])}")
    logger.info(f"  - Average CVRMSE: {mock_validation['cvrmse'].mean():.2f}%")
    logger.info(f"  - Average NMBE: {mock_validation['nmbe'].mean():.2f}%")
    
    # Test building selection
    selected_buildings = iteration_manager.select_buildings(mock_validation)
    logger.info(f"\nSelected {len(selected_buildings)} buildings for iteration 1:")
    for bid in selected_buildings:
        building_data = mock_validation[mock_validation['building_id'] == bid].iloc[0]
        logger.info(f"  - {bid}: CVRMSE={building_data['cvrmse']:.1f}%, NMBE={building_data['nmbe']:.1f}%")
    
    # Test iteration loop
    iteration_count = 0
    while iteration_manager.should_continue() and iteration_count < 3:
        iteration_manager.increment_iteration()
        iteration_count += 1
        
        logger.info(f"\n=== Testing Iteration {iteration_manager.current_iteration} ===")
        
        # Get modification intensity
        intensity = iteration_manager.get_modification_intensity()
        logger.info(f"Modification intensity: {intensity}")
        
        # Simulate improvement (reduce errors by 10-30%)
        improved_validation = mock_validation.copy()
        for bid in selected_buildings:
            idx = improved_validation[improved_validation['building_id'] == bid].index[0]
            improvement_factor = np.random.uniform(0.7, 0.9)
            improved_validation.loc[idx, 'cvrmse'] *= improvement_factor
            improved_validation.loc[idx, 'nmbe'] *= improvement_factor
            
        # Update validation passed status
        improved_validation['validation_passed'] = (
            (improved_validation['cvrmse'] < 30) & 
            (improved_validation['nmbe'].abs() < 10)
        )
        
        # Save iteration results
        iter_dir = iteration_manager.get_iteration_dir()
        iter_dir.mkdir(parents=True, exist_ok=True)
        improved_validation.to_parquet(iter_dir / "validation_summary.parquet")
        
        # Record performance
        iteration_manager.record_iteration_performance(improved_validation)
        
        # Log iteration stats
        logger.info(f"Iteration {iteration_manager.current_iteration} results:")
        logger.info(f"  - Total buildings: {len(improved_validation)}")
        logger.info(f"  - Passed: {len(improved_validation[improved_validation['validation_passed']])}")
        logger.info(f"  - Average CVRMSE: {improved_validation['cvrmse'].mean():.2f}%")
        logger.info(f"  - Average NMBE: {improved_validation['nmbe'].mean():.2f}%")
        
        # Check convergence
        converged, reason = iteration_manager.check_convergence()
        logger.info(f"Convergence check: {converged} - {reason}")
        
        # Update validation results for next iteration
        mock_validation = improved_validation
        
        # Select buildings for next iteration if continuing
        if iteration_manager.should_continue():
            selected_buildings = iteration_manager.select_buildings(mock_validation)
            logger.info(f"\nSelected {len(selected_buildings)} buildings for next iteration")
    
    # Save final summary
    iteration_manager.save_iteration_summary()
    
    # Display performance history
    logger.info("\n=== Performance History ===")
    history_df = pd.DataFrame(iteration_manager.performance_history)
    logger.info("\n" + history_df.to_string())
    
    # Create summary report
    summary_file = output_dir / "test_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("Iteration Workflow Test Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total iterations completed: {iteration_manager.current_iteration}\n")
        f.write(f"Final average CVRMSE: {mock_validation['cvrmse'].mean():.2f}%\n")
        f.write(f"Final buildings passed: {len(mock_validation[mock_validation['validation_passed']])}/{len(mock_validation)}\n")
        f.write("\nPerformance History:\n")
        f.write(history_df.to_string())
    
    logger.info(f"\nTest complete! Results saved to {output_dir}")


if __name__ == "__main__":
    test_iteration_manager()