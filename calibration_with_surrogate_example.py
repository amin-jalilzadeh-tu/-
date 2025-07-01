"""
Example script showing how to use the surrogate model for calibration
without re-running EnergyPlus simulations.

This script demonstrates:
1. Loading a saved surrogate model
2. Using it to predict energy consumption for different parameter combinations
3. Implementing a simple calibration loop using the surrogate
"""

import os
import numpy as np
import pandas as pd
import joblib
import json
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt

# Path to the surrogate model output directory
MODEL_DIR = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/surrogate_models"


def load_surrogate_model(model_dir: str) -> Tuple[object, Dict, object]:
    """
    Load the surrogate model and its metadata.
    
    Returns:
        - model: The trained surrogate model
        - metadata: Model metadata including feature/target columns
        - scaler: Feature scaler (if used)
    """
    # Load the model
    model_path = os.path.join(model_dir, "surrogate_model.joblib")
    model = joblib.load(model_path)
    
    # Load metadata
    metadata_path = os.path.join(model_dir, "surrogate_model_metadata.json")
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Load scaler if exists
    scaler = None
    scaler_path = os.path.join(model_dir, "v1.0", "feature_scaler.joblib")
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
    
    return model, metadata, scaler


def predict_with_surrogate(model, feature_values: Dict[str, float], 
                          feature_columns: List[str], 
                          target_columns: List[str],
                          scaler=None) -> Dict[str, float]:
    """
    Make predictions using the surrogate model.
    
    Args:
        model: Trained surrogate model
        feature_values: Dictionary of parameter values
        feature_columns: List of feature column names in order
        target_columns: List of target column names
        scaler: Feature scaler (optional)
    
    Returns:
        Dictionary of predictions for each target
    """
    # Create feature vector in correct order
    features = np.zeros(len(feature_columns))
    for i, col in enumerate(feature_columns):
        if col in feature_values:
            features[i] = feature_values[col]
    
    # Reshape for prediction
    features = features.reshape(1, -1)
    
    # Scale if needed
    if scaler is not None:
        features = scaler.transform(features)
    
    # Predict
    predictions = model.predict(features)
    
    # Format output
    results = {}
    for i, target in enumerate(target_columns):
        results[target] = float(predictions[0][i] if len(predictions.shape) > 1 else predictions[0])
    
    return results


def simple_calibration_example(model, metadata, scaler, 
                              target_values: Dict[str, float],
                              calibration_params: List[str],
                              param_bounds: Dict[str, Tuple[float, float]],
                              n_iterations: int = 100):
    """
    Simple calibration example using random search with the surrogate model.
    
    Args:
        model: Trained surrogate model
        metadata: Model metadata
        scaler: Feature scaler
        target_values: Target values to calibrate to
        calibration_params: List of parameters to calibrate
        param_bounds: Min/max bounds for each calibration parameter
        n_iterations: Number of random samples to try
    
    Returns:
        Best parameter combination and its predictions
    """
    feature_columns = metadata['features']['names']
    target_columns = metadata['targets']['names']
    
    # Initialize with base values (zeros for simplicity)
    base_params = {col: 0.0 for col in feature_columns}
    
    best_error = float('inf')
    best_params = None
    best_predictions = None
    
    errors_history = []
    
    print(f"Starting calibration with {n_iterations} iterations...")
    
    for i in range(n_iterations):
        # Generate random parameter values within bounds
        trial_params = base_params.copy()
        for param in calibration_params:
            if param in param_bounds:
                min_val, max_val = param_bounds[param]
                trial_params[param] = np.random.uniform(min_val, max_val)
        
        # Predict with surrogate
        predictions = predict_with_surrogate(model, trial_params, 
                                           feature_columns, target_columns, scaler)
        
        # Calculate error (simple MSE for targets we care about)
        error = 0
        n_targets = 0
        for target, target_val in target_values.items():
            if target in predictions:
                error += (predictions[target] - target_val) ** 2
                n_targets += 1
        
        if n_targets > 0:
            error = error / n_targets
            errors_history.append(error)
            
            if error < best_error:
                best_error = error
                best_params = {k: v for k, v in trial_params.items() if k in calibration_params}
                best_predictions = predictions
                print(f"  Iteration {i+1}: New best error = {error:.6f}")
    
    return best_params, best_predictions, errors_history


def main():
    """Main example workflow."""
    
    # Load the surrogate model
    print("Loading surrogate model...")
    model, metadata, scaler = load_surrogate_model(MODEL_DIR)
    
    # Print model information
    print(f"\nModel type: {metadata['model_info']['model_type']}")
    print(f"Number of features: {metadata['features']['count']}")
    print(f"Number of targets: {metadata['targets']['count']}")
    print(f"\nTarget variables:")
    for target in metadata['targets']['names']:
        print(f"  - {target}")
    
    # Example 1: Make a single prediction
    print("\n" + "="*50)
    print("EXAMPLE 1: Single Prediction")
    print("="*50)
    
    # Set some example parameter values
    example_params = {
        'materials_MATERIAL_Concrete_200mm_Conductivity': 1.5,
        'materials_MATERIAL_Concrete_200mm_Thickness': 0.2,
        'equipment_ELECTRICEQUIPMENT_Equip_ALL_ZONES_Watts_per_Zone_Floor_Area': 10.0,
        'lighting_LIGHTS_Lights_ALL_ZONES_Fraction_Radiant': 0.4,
        'ventilation_DESIGNSPECIFICATION_OUTDOORAIR_DSOA_Global_Outdoor_Air_Flow_per_Person': 0.01
    }
    
    predictions = predict_with_surrogate(model, example_params, 
                                       metadata['features']['names'],
                                       metadata['targets']['names'], 
                                       scaler)
    
    print("\nPredictions:")
    for target, value in predictions.items():
        print(f"  {target}: {value:.2f}")
    
    # Example 2: Simple calibration
    print("\n" + "="*50)
    print("EXAMPLE 2: Simple Calibration")
    print("="*50)
    
    # Define target values we want to achieve
    target_values = {
        'Zone_Air_System_Sensible_Heating_Energy_mean': 5000.0,
        'Zone_Air_System_Sensible_Cooling_Energy_mean': 3000.0
    }
    
    # Define parameters to calibrate and their bounds
    calibration_params = [
        'materials_MATERIAL_Concrete_200mm_Conductivity',
        'equipment_ELECTRICEQUIPMENT_Equip_ALL_ZONES_Watts_per_Zone_Floor_Area',
        'ventilation_DESIGNSPECIFICATION_OUTDOORAIR_DSOA_Global_Outdoor_Air_Flow_per_Person'
    ]
    
    param_bounds = {
        'materials_MATERIAL_Concrete_200mm_Conductivity': (0.5, 2.5),
        'equipment_ELECTRICEQUIPMENT_Equip_ALL_ZONES_Watts_per_Zone_Floor_Area': (5.0, 20.0),
        'ventilation_DESIGNSPECIFICATION_OUTDOORAIR_DSOA_Global_Outdoor_Air_Flow_per_Person': (0.005, 0.02)
    }
    
    # Run calibration
    best_params, best_predictions, errors = simple_calibration_example(
        model, metadata, scaler, target_values, 
        calibration_params, param_bounds, n_iterations=200
    )
    
    print("\nCalibration Results:")
    print("Best parameters found:")
    for param, value in best_params.items():
        print(f"  {param}: {value:.4f}")
    
    print("\nPredictions with best parameters:")
    for target, value in best_predictions.items():
        if target in target_values:
            actual = target_values[target]
            error = abs(value - actual) / actual * 100
            print(f"  {target}: {value:.2f} (target: {actual:.2f}, error: {error:.1f}%)")
    
    # Plot convergence
    plt.figure(figsize=(10, 6))
    plt.plot(errors)
    plt.xlabel('Iteration')
    plt.ylabel('Mean Squared Error')
    plt.title('Calibration Convergence')
    plt.yscale('log')
    plt.grid(True)
    plt.savefig('calibration_convergence.png')
    print("\nConvergence plot saved as 'calibration_convergence.png'")
    
    # Example 3: Parameter sensitivity using surrogate
    print("\n" + "="*50)
    print("EXAMPLE 3: Quick Sensitivity Analysis")
    print("="*50)
    
    # Test sensitivity of a single parameter
    test_param = 'materials_MATERIAL_Concrete_200mm_Conductivity'
    param_values = np.linspace(0.5, 2.5, 20)
    
    heating_results = []
    cooling_results = []
    
    base_params = {col: 0.0 for col in metadata['features']['names']}
    
    for val in param_values:
        base_params[test_param] = val
        preds = predict_with_surrogate(model, base_params,
                                     metadata['features']['names'],
                                     metadata['targets']['names'],
                                     scaler)
        heating_results.append(preds['Zone_Air_System_Sensible_Heating_Energy_mean'])
        cooling_results.append(preds['Zone_Air_System_Sensible_Cooling_Energy_mean'])
    
    plt.figure(figsize=(10, 6))
    plt.plot(param_values, heating_results, 'r-', label='Heating Energy')
    plt.plot(param_values, cooling_results, 'b-', label='Cooling Energy')
    plt.xlabel(test_param)
    plt.ylabel('Energy (kWh)')
    plt.title('Parameter Sensitivity Analysis using Surrogate Model')
    plt.legend()
    plt.grid(True)
    plt.savefig('sensitivity_analysis.png')
    print(f"\nSensitivity plot saved as 'sensitivity_analysis.png'")
    
    print("\n" + "="*50)
    print("ADVANTAGES OF SURROGATE-BASED CALIBRATION:")
    print("="*50)
    print("1. Speed: Each prediction takes milliseconds vs hours for EnergyPlus")
    print("2. Exploration: Can test thousands of parameter combinations quickly")
    print("3. Optimization: Can use advanced algorithms without computational constraints")
    print("4. Uncertainty: Can easily perform uncertainty/sensitivity analysis")
    print("5. Interactive: Fast enough for real-time parameter tuning")


if __name__ == "__main__":
    main()