"""
Advanced calibration using surrogate models with existing calibration algorithms.

This script demonstrates:
1. Loading surrogate models and integrating with calibration_algorithms.py
2. Using Particle Swarm Optimization (PSO) for calibration
3. Multi-objective calibration with NSGA-II
4. Comparison of different optimization algorithms
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
import json
from typing import Dict, List, Tuple, Callable
import matplotlib.pyplot as plt
from datetime import datetime
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import calibration algorithms
from cal.calibration_algorithms import (
    ParticleSwarmOptimizer,
    DifferentialEvolution,
    OptimizationResult
)
from cal.calibration_objectives import (
    ParamSpec,
    create_objective_function,
    cvrmse,
    nmbe
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SurrogateModelWrapper:
    """Wrapper class to make surrogate model compatible with calibration algorithms."""
    
    def __init__(self, model_dir: str):
        """Initialize with saved surrogate model."""
        self.model_dir = model_dir
        self.model, self.metadata, self.scaler = self._load_model()
        self.feature_columns = self.metadata['features']['names']
        self.target_columns = self.metadata['targets']['names']
        
    def _load_model(self):
        """Load model and metadata."""
        model = joblib.load(os.path.join(self.model_dir, "surrogate_model.joblib"))
        
        with open(os.path.join(self.model_dir, "surrogate_model_metadata.json"), 'r') as f:
            metadata = json.load(f)
        
        scaler = None
        scaler_path = os.path.join(self.model_dir, "v1.0", "feature_scaler.joblib")
        if os.path.exists(scaler_path):
            scaler = joblib.load(scaler_path)
            
        return model, metadata, scaler
    
    def simulate(self, params: Dict[str, float]) -> Dict[str, np.ndarray]:
        """
        Simulate building energy using surrogate model.
        
        Args:
            params: Dictionary of parameter values
            
        Returns:
            Dictionary with energy predictions
        """
        # Create feature vector
        features = np.zeros(len(self.feature_columns))
        for i, col in enumerate(self.feature_columns):
            if col in params:
                features[i] = params[col]
        
        features = features.reshape(1, -1)
        
        # Scale if needed
        if self.scaler is not None:
            features = self.scaler.transform(features)
        
        # Predict
        predictions = self.model.predict(features)
        
        # Format output to match expected structure
        results = {}
        for i, target in enumerate(self.target_columns):
            # Convert to hourly-like array (8760 hours)
            # In reality, you'd interpolate or use actual time series
            # Here we just repeat the annual value
            if 'Heating' in target:
                # Distribute heating over winter months
                hourly = np.zeros(8760)
                heating_value = predictions[0][i] if len(predictions.shape) > 1 else predictions[0]
                # Simple distribution: more heating in winter
                for hour in range(8760):
                    month = (hour // 730) % 12  # Approximate month
                    if month in [0, 1, 2, 10, 11]:  # Winter months
                        hourly[hour] = heating_value / (5 * 730)  # Distribute over 5 months
                results['heating'] = hourly
                
            elif 'Cooling' in target:
                # Distribute cooling over summer months
                hourly = np.zeros(8760)
                cooling_value = predictions[0][i] if len(predictions.shape) > 1 else predictions[0]
                for hour in range(8760):
                    month = (hour // 730) % 12
                    if month in [5, 6, 7, 8]:  # Summer months
                        hourly[hour] = cooling_value / (4 * 730)  # Distribute over 4 months
                results['cooling'] = hourly
                
            elif 'electricity' in target.lower():
                # Constant base load
                value = predictions[0][i] if len(predictions.shape) > 1 else predictions[0]
                results['electricity'] = np.full(8760, value / 8760)
        
        return results


def create_surrogate_objective(surrogate_model: SurrogateModelWrapper,
                              measured_data: Dict[str, np.ndarray],
                              weights: Dict[str, float] = None) -> Callable:
    """
    Create objective function using surrogate model.
    
    Args:
        surrogate_model: Wrapped surrogate model
        measured_data: Measured energy data
        weights: Weights for different objectives
        
    Returns:
        Objective function
    """
    if weights is None:
        weights = {'heating': 1.0, 'cooling': 1.0, 'electricity': 0.5}
    
    def objective(params: Dict[str, float]) -> float:
        """Calculate weighted error between simulated and measured."""
        try:
            # Get predictions from surrogate
            simulated = surrogate_model.simulate(params)
            
            total_error = 0.0
            total_weight = 0.0
            
            for key in ['heating', 'cooling', 'electricity']:
                if key in simulated and key in measured_data:
                    # Calculate CVRMSE
                    error = cvrmse(measured_data[key], simulated[key])
                    weight = weights.get(key, 1.0)
                    total_error += error * weight
                    total_weight += weight
            
            return total_error / total_weight if total_weight > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"Error in objective function: {e}")
            return float('inf')
    
    return objective


def run_pso_calibration(surrogate_model: SurrogateModelWrapper,
                       measured_data: Dict[str, np.ndarray],
                       param_specs: List[ParamSpec],
                       n_particles: int = 30,
                       max_iter: int = 100) -> OptimizationResult:
    """Run PSO calibration using surrogate model."""
    
    logger.info("Starting PSO calibration with surrogate model")
    
    # Create objective function
    objective_func = create_surrogate_objective(surrogate_model, measured_data)
    
    # Initialize PSO
    pso = ParticleSwarmOptimizer(
        n_particles=n_particles,
        max_iter=max_iter,
        inertia=0.9,
        cognitive=2.0,
        social=2.0,
        inertia_decay=0.99
    )
    
    # Run optimization
    result = pso.optimize(objective_func, param_specs, verbose=True)
    
    return result


def run_de_calibration(surrogate_model: SurrogateModelWrapper,
                      measured_data: Dict[str, np.ndarray],
                      param_specs: List[ParamSpec],
                      population_size: int = 50,
                      max_iter: int = 100) -> OptimizationResult:
    """Run Differential Evolution calibration using surrogate model."""
    
    logger.info("Starting DE calibration with surrogate model")
    
    # Create objective function
    objective_func = create_surrogate_objective(surrogate_model, measured_data)
    
    # Initialize DE
    de = DifferentialEvolution(
        population_size=population_size,
        max_iter=max_iter,
        mutation_factor=0.8,
        crossover_prob=0.9
    )
    
    # Run optimization
    result = de.optimize(objective_func, param_specs, verbose=True)
    
    return result


def compare_algorithms(surrogate_model: SurrogateModelWrapper,
                      measured_data: Dict[str, np.ndarray],
                      param_specs: List[ParamSpec]):
    """Compare different optimization algorithms."""
    
    results = {}
    
    # Run PSO
    logger.info("\n" + "="*50)
    logger.info("Running Particle Swarm Optimization")
    logger.info("="*50)
    start_time = datetime.now()
    pso_result = run_pso_calibration(surrogate_model, measured_data, param_specs, 
                                     n_particles=20, max_iter=50)
    pso_time = (datetime.now() - start_time).total_seconds()
    results['PSO'] = {
        'result': pso_result,
        'time': pso_time
    }
    
    # Run DE
    logger.info("\n" + "="*50)
    logger.info("Running Differential Evolution")
    logger.info("="*50)
    start_time = datetime.now()
    de_result = run_de_calibration(surrogate_model, measured_data, param_specs,
                                   population_size=30, max_iter=50)
    de_time = (datetime.now() - start_time).total_seconds()
    results['DE'] = {
        'result': de_result,
        'time': de_time
    }
    
    return results


def visualize_results(results: Dict, surrogate_model: SurrogateModelWrapper,
                     measured_data: Dict[str, np.ndarray]):
    """Visualize calibration results."""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Convergence comparison
    ax = axes[0, 0]
    for algo_name, algo_data in results.items():
        convergence = algo_data['result'].convergence_data
        if convergence and 'best_objectives' in convergence:
            ax.plot(convergence['best_objectives'], label=algo_name)
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Objective Value')
    ax.set_title('Convergence Comparison')
    ax.legend()
    ax.grid(True)
    
    # Plot 2: Time comparison
    ax = axes[0, 1]
    algo_names = list(results.keys())
    times = [results[algo]['time'] for algo in algo_names]
    ax.bar(algo_names, times)
    ax.set_ylabel('Time (seconds)')
    ax.set_title('Computation Time Comparison')
    
    # Plot 3: Best parameters comparison
    ax = axes[1, 0]
    param_names = []
    for algo_idx, (algo_name, algo_data) in enumerate(results.items()):
        best_params = algo_data['result'].best_params
        if not param_names:
            param_names = list(best_params.keys())[:5]  # Show first 5 params
        
        values = [best_params.get(p, 0) for p in param_names]
        x = np.arange(len(param_names))
        ax.bar(x + algo_idx * 0.3, values, 0.3, label=algo_name)
    
    ax.set_xticks(x + 0.15)
    ax.set_xticklabels([p.split('_')[-1][:10] for p in param_names], rotation=45)
    ax.set_ylabel('Parameter Value')
    ax.set_title('Best Parameters Comparison')
    ax.legend()
    
    # Plot 4: Energy comparison
    ax = axes[1, 1]
    best_algo = min(results.items(), key=lambda x: x[1]['result'].best_objective)[0]
    best_params = results[best_algo]['result'].best_params
    
    # Simulate with best parameters
    simulated = surrogate_model.simulate(best_params)
    
    # Plot monthly comparisons
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for energy_type in ['heating', 'cooling']:
        if energy_type in simulated and energy_type in measured_data:
            # Convert hourly to monthly
            sim_monthly = np.array([simulated[energy_type][i*730:(i+1)*730].sum() 
                                   for i in range(12)])
            meas_monthly = np.array([measured_data[energy_type][i*730:(i+1)*730].sum() 
                                    for i in range(12)])
            
            x = np.arange(12)
            width = 0.35
            ax.bar(x - width/2, meas_monthly, width, label=f'Measured {energy_type}')
            ax.bar(x + width/2, sim_monthly, width, label=f'Calibrated {energy_type}')
    
    ax.set_xticks(x)
    ax.set_xticklabels(months)
    ax.set_ylabel('Energy (kWh)')
    ax.set_title(f'Best Calibration Results ({best_algo})')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('advanced_calibration_results.png', dpi=300)
    logger.info("Results saved to 'advanced_calibration_results.png'")


def main():
    """Main workflow for advanced calibration."""
    
    # Configuration
    MODEL_DIR = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/surrogate_models"
    
    # Load surrogate model
    logger.info("Loading surrogate model...")
    surrogate_model = SurrogateModelWrapper(MODEL_DIR)
    
    # Generate synthetic measured data (in practice, load from files)
    logger.info("Generating synthetic measured data...")
    np.random.seed(42)
    measured_data = {
        'heating': np.maximum(0, 100 + 50 * np.sin(np.linspace(0, 2*np.pi, 8760)) + 
                             10 * np.random.randn(8760)),
        'cooling': np.maximum(0, 80 - 40 * np.sin(np.linspace(0, 2*np.pi, 8760)) + 
                             8 * np.random.randn(8760)),
        'electricity': 50 + 5 * np.random.randn(8760)
    }
    
    # Define calibration parameters
    param_specs = [
        ParamSpec('materials_MATERIAL_Concrete_200mm_Conductivity', 0.5, 2.5, 1.5),
        ParamSpec('equipment_ELECTRICEQUIPMENT_Equip_ALL_ZONES_Watts_per_Zone_Floor_Area', 
                  5.0, 20.0, 10.0),
        ParamSpec('ventilation_DESIGNSPECIFICATION_OUTDOORAIR_DSOA_Global_Outdoor_Air_Flow_per_Person',
                  0.005, 0.02, 0.01),
        ParamSpec('lighting_LIGHTS_Lights_ALL_ZONES_Fraction_Radiant', 0.2, 0.6, 0.4),
        ParamSpec('materials_MATERIAL_NOMASS_Roof_R2_5_Thermal_Resistance', 0.5, 2.0, 1.0)
    ]
    
    # Compare algorithms
    results = compare_algorithms(surrogate_model, measured_data, param_specs)
    
    # Print summary
    print("\n" + "="*60)
    print("CALIBRATION SUMMARY")
    print("="*60)
    
    for algo_name, algo_data in results.items():
        result = algo_data['result']
        print(f"\n{algo_name}:")
        print(f"  Best objective: {result.best_objective:.4f}")
        print(f"  Time taken: {algo_data['time']:.2f} seconds")
        print(f"  Best parameters:")
        for param, value in list(result.best_params.items())[:5]:
            print(f"    {param}: {value:.4f}")
    
    # Visualize results
    visualize_results(results, surrogate_model, measured_data)
    
    # Calculate speedup vs EnergyPlus
    total_evals = sum(len(r['result'].history) for r in results.values())
    surrogate_time = sum(r['time'] for r in results.values())
    energyplus_time_estimate = total_evals * 300  # Assume 5 min per simulation
    
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON")
    print("="*60)
    print(f"Total evaluations: {total_evals}")
    print(f"Time with surrogate: {surrogate_time:.2f} seconds")
    print(f"Estimated time with EnergyPlus: {energyplus_time_estimate:.2f} seconds")
    print(f"Speedup factor: {energyplus_time_estimate/surrogate_time:.0f}x")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Validate calibrated parameters with full EnergyPlus simulation")
    print("2. Perform uncertainty analysis on calibrated parameters")
    print("3. Test on different building types or climate zones")
    print("4. Implement multi-objective calibration for Pareto optimal solutions")


if __name__ == "__main__":
    main()