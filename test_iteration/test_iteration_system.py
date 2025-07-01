#!/usr/bin/env python3
"""
Test script for the iteration system
Demonstrates the complete iteration workflow
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from iteration.iteration_controller import IterationController, IterationConfig, IterationStatus
from iteration.parameter_feedback import ParameterFeedback
from iteration.iteration_strategies import create_strategy, StrategyConfig
from iteration.parameter_store import ParameterStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def simulate_workflow_execution(parameters: Dict[str, float], iteration: int) -> Dict[str, float]:
    """
    Simulate the execution of a workflow iteration
    Returns simulated metrics
    """
    logger.info(f"Simulating workflow execution for iteration {iteration}")
    
    # Simulate some computation time
    import time
    time.sleep(0.5)
    
    # Generate metrics based on parameters (with some noise)
    # Better parameters should give better metrics
    base_rmse = 0.15
    
    # Simulate parameter effects
    infiltration_effect = abs(parameters.get('infiltration_rate', 0.5) - 0.3) * 0.2
    window_effect = abs(parameters.get('window_u_value', 2.0) - 1.5) * 0.1
    insulation_effect = abs(parameters.get('wall_insulation', 0.05) - 0.1) * 0.3
    hvac_effect = abs(parameters.get('hvac_efficiency', 0.85) - 0.9) * 0.15
    
    # Calculate RMSE with some randomness
    rmse = base_rmse + infiltration_effect + window_effect + insulation_effect + hvac_effect
    rmse += np.random.normal(0, 0.01)  # Add noise
    
    # Ensure convergence trend
    rmse *= (1 - iteration * 0.02)  # Gradual improvement
    
    # Calculate other metrics
    cv_rmse = rmse / 1.2
    nmbe = rmse * 0.5 + np.random.normal(0, 0.005)
    r2 = max(0, 1 - rmse * 2)
    
    metrics = {
        'rmse': max(0, rmse),
        'cv_rmse': max(0, cv_rmse),
        'nmbe': nmbe,
        'r2': min(1, max(0, r2))
    }
    
    logger.info(f"Simulation complete. CV-RMSE: {cv_rmse:.4f}")
    
    return metrics


def test_iteration_workflow():
    """Test the complete iteration workflow"""
    
    # Test configuration
    job_id = "test_job_001"
    test_dir = Path("test_iteration")
    test_dir.mkdir(exist_ok=True)
    
    # Create iteration configuration
    config = {
        "iteration": {
            "strategy": "adaptive",
            "max_iterations": 8,
            "min_iterations": 3,
            "convergence_tolerance": 0.005,
            "convergence_metric": "cv_rmse",
            "learning_rate": 0.1
        }
    }
    
    config_file = test_dir / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("=" * 60)
    logger.info("Starting Iteration System Test")
    logger.info("=" * 60)
    
    # Initialize components
    logger.info("\n1. Initializing iteration controller...")
    controller = IterationController(job_id, str(config_file))
    
    logger.info("\n2. Initializing parameter feedback...")
    feedback = ParameterFeedback(job_id)
    
    logger.info("\n3. Initializing parameter store...")
    param_store = ParameterStore(job_id)
    
    # Run iteration loop
    logger.info("\n4. Starting iteration loop...")
    
    while controller.should_continue():
        logger.info("\n" + "-" * 50)
        
        # Start new iteration
        iter_info = controller.start_iteration()
        logger.info(f"Iteration {iter_info['iteration']} started")
        logger.info(f"Parameters: {json.dumps(iter_info['parameters'], indent=2)}")
        
        # Simulate workflow execution
        metrics = simulate_workflow_execution(
            iter_info['parameters'], 
            iter_info['iteration']
        )
        
        # Store parameters with version control
        version_id = param_store.store_parameters(
            iteration_id=iter_info['iteration'],
            parameters=iter_info['parameters'],
            metrics=metrics,
            metadata={'strategy': config['iteration']['strategy']},
            parent_version=param_store.index.get(f"v{iter_info['iteration']-1:03d}_*")
        )
        
        logger.info(f"Stored parameter version: {version_id}")
        
        # Convert parameters to modification configs
        mod_configs = feedback.convert_calibration_to_modification(
            iter_info['parameters'],
            iter_info['output_dir']
        )
        
        logger.info(f"Created modification configs: {list(mod_configs.keys())}")
        
        # Complete iteration
        controller.complete_iteration(metrics, iter_info['parameters'])
        
        logger.info(f"Metrics: CV-RMSE={metrics['cv_rmse']:.4f}, RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Iteration Loop Complete")
    logger.info("=" * 60)
    
    # Get summary
    summary = controller.get_summary()
    logger.info(f"\nTotal iterations: {summary['total_iterations']}")
    logger.info(f"Best iteration: {summary['best_iteration']}")
    logger.info(f"Convergence achieved: {summary['convergence_achieved']}")
    
    if summary['best_metrics']:
        logger.info(f"\nBest metrics:")
        logger.info(f"  CV-RMSE: {summary['best_metrics']['cv_rmse']:.4f}")
        logger.info(f"  RMSE: {summary['best_metrics']['rmse']:.4f}")
        logger.info(f"  R2: {summary['best_metrics']['r2']:.4f}")
    
    # Export results
    logger.info("\n5. Exporting results...")
    
    # Export iteration summary
    summary_file = test_dir / "iteration_summary.json"
    controller.export_results(str(summary_file))
    
    # Export parameter evolution
    param_evolution_file = test_dir / "parameter_evolution.csv"
    param_df = param_store.export_parameter_evolution(str(param_evolution_file))
    
    # Export parameter report
    param_report_file = test_dir / "parameter_report.json"
    feedback.export_parameter_report(str(param_report_file))
    
    # Get best parameters
    best_version = param_store.get_best_version()
    if best_version:
        logger.info(f"\nBest parameter version: {best_version.version_id}")
        logger.info("Best parameters:")
        for key, value in best_version.parameters.items():
            logger.info(f"  {key}: {value:.4f}")
    
    # Create visualizations
    create_iteration_plots(summary, param_df, test_dir)
    
    logger.info(f"\nResults saved to {test_dir}")
    logger.info("\nTest completed successfully!")


def create_iteration_plots(summary: Dict, param_df: pd.DataFrame, output_dir: Path):
    """Create plots for iteration results"""
    try:
        import matplotlib.pyplot as plt
        
        # Plot metric trends
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Iteration System Performance', fontsize=16)
        
        iterations = range(1, len(summary['metric_trends']['cv_rmse']) + 1)
        
        # CV-RMSE trend
        axes[0, 0].plot(iterations, summary['metric_trends']['cv_rmse'], 'b-o')
        axes[0, 0].set_title('CV-RMSE Evolution')
        axes[0, 0].set_xlabel('Iteration')
        axes[0, 0].set_ylabel('CV-RMSE')
        axes[0, 0].grid(True)
        
        # RMSE trend
        axes[0, 1].plot(iterations, summary['metric_trends']['rmse'], 'r-o')
        axes[0, 1].set_title('RMSE Evolution')
        axes[0, 1].set_xlabel('Iteration')
        axes[0, 1].set_ylabel('RMSE')
        axes[0, 1].grid(True)
        
        # R2 trend
        axes[1, 0].plot(iterations, summary['metric_trends']['r2'], 'g-o')
        axes[1, 0].set_title('R² Evolution')
        axes[1, 0].set_xlabel('Iteration')
        axes[1, 0].set_ylabel('R²')
        axes[1, 0].grid(True)
        
        # Parameter evolution
        if not param_df.empty:
            param_cols = [col for col in param_df.columns 
                         if col not in ['version_id', 'iteration_id', 'timestamp'] 
                         and not col.startswith('metric_')]
            
            for param in param_cols[:4]:  # Plot first 4 parameters
                axes[1, 1].plot(param_df['iteration_id'], param_df[param], 
                              label=param, marker='o')
            
            axes[1, 1].set_title('Parameter Evolution')
            axes[1, 1].set_xlabel('Iteration')
            axes[1, 1].set_ylabel('Parameter Value')
            axes[1, 1].legend()
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        plot_file = output_dir / 'iteration_results.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created visualization: {plot_file}")
        
    except ImportError:
        logger.warning("Matplotlib not available - skipping plots")


def test_different_strategies():
    """Test different iteration strategies"""
    strategies = ['fixed', 'convergence', 'adaptive', 'human_guided']
    results = {}
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Different Iteration Strategies")
    logger.info("=" * 60)
    
    for strategy_name in strategies:
        logger.info(f"\n\nTesting {strategy_name} strategy...")
        
        job_id = f"test_{strategy_name}_strategy"
        
        # Create config for this strategy
        config = {
            "iteration": {
                "strategy": strategy_name,
                "max_iterations": 6,
                "min_iterations": 2,
                "convergence_tolerance": 0.01,
                "convergence_metric": "cv_rmse"
            }
        }
        
        config_file = Path("test_iteration") / f"config_{strategy_name}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Run simplified test
        controller = IterationController(job_id, str(config_file))
        
        iteration_count = 0
        final_metrics = None
        
        while controller.should_continue() and iteration_count < 10:  # Safety limit
            iter_info = controller.start_iteration()
            metrics = simulate_workflow_execution(iter_info['parameters'], iteration_count + 1)
            controller.complete_iteration(metrics, iter_info['parameters'])
            iteration_count += 1
            final_metrics = metrics
        
        summary = controller.get_summary()
        results[strategy_name] = {
            'iterations': iteration_count,
            'final_cv_rmse': final_metrics['cv_rmse'] if final_metrics else None,
            'converged': summary['convergence_achieved']
        }
        
        logger.info(f"Strategy {strategy_name}: {iteration_count} iterations, "
                   f"final CV-RMSE: {final_metrics['cv_rmse']:.4f if final_metrics else 'N/A'}")
    
    # Compare results
    logger.info("\n\nStrategy Comparison:")
    logger.info("-" * 40)
    for strategy, result in results.items():
        logger.info(f"{strategy:12s}: {result['iterations']} iterations, "
                   f"CV-RMSE: {result['final_cv_rmse']:.4f if result['final_cv_rmse'] else 'N/A':8s}, "
                   f"Converged: {result['converged']}")


if __name__ == "__main__":
    # Run main test
    test_iteration_workflow()
    
    # Test different strategies
    test_different_strategies()