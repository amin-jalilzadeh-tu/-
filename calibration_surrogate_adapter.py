"""
Surrogate Model Adapter for Calibration
Integrates the trained surrogate model with existing calibration algorithms
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SurrogateModelAdapter:
    """Adapter to use surrogate model in place of EnergyPlus simulations"""
    
    def __init__(self, model_path: str, columns_path: str, scaler_path: Optional[str] = None):
        """
        Initialize surrogate model adapter
        
        Args:
            model_path: Path to saved surrogate model (.joblib)
            columns_path: Path to saved feature columns (.joblib)
            scaler_path: Optional path to feature scaler
        """
        model_data = joblib.load(model_path)
        
        # Handle different model formats
        if isinstance(model_data, dict):
            self.model = model_data.get('model')
            self.feature_columns = model_data.get('feature_columns', joblib.load(columns_path))
            self.scaler = model_data.get('scaler', joblib.load(scaler_path) if scaler_path else None)
        else:
            self.model = model_data
            self.feature_columns = joblib.load(columns_path)
            self.scaler = joblib.load(scaler_path) if scaler_path else None
        
        # Extract base features (excluding aggregated ones)
        self.base_features = [col for col in self.feature_columns 
                             if not col.startswith(('total_', 'mean_', 'category_'))]
        
        logger.info(f"Loaded surrogate model with {len(self.feature_columns)} features")
        
    def simulate(self, params: Dict[str, float]) -> Dict[str, float]:
        """
        Simulate building performance using surrogate model
        
        Args:
            params: Dictionary of parameter values
            
        Returns:
            Dictionary of predicted outputs
        """
        # Create feature vector
        features = self._prepare_features(params)
        
        # Make prediction
        predictions = self.model.predict(features.reshape(1, -1))[0]
        
        # Map to output dictionary
        output_names = [
            'Zone_Air_System_Sensible_Heating_Energy_mean',
            'Zone_Air_System_Sensible_Heating_Energy_percent_change',
            'Zone_Air_System_Sensible_Cooling_Energy_mean',
            'Zone_Air_System_Sensible_Cooling_Energy_percent_change'
        ]
        
        return {name: float(pred) for name, pred in zip(output_names, predictions)}
    
    def _prepare_features(self, params: Dict[str, float]) -> np.ndarray:
        """Prepare feature vector from parameters"""
        # Initialize feature vector
        features = np.zeros(len(self.feature_columns))
        
        # Direct mapping since we're using full feature names now
        param_mapping = {}
        for param_name in params:
            if param_name in self.feature_columns:
                param_mapping[param_name] = param_name
        
        # Fill in base features
        for i, col in enumerate(self.feature_columns):
            if col in param_mapping and param_mapping[col] in params:
                features[i] = params[param_mapping[col]]
            elif col in params:
                features[i] = params[col]
            elif col in self.base_features:
                # Use default/baseline value if not provided
                features[i] = 0.0  # This should be improved with actual baseline values
                
        # Calculate aggregated features
        features = self._calculate_aggregated_features(features)
        
        # Apply scaling if available
        if self.scaler:
            features = self.scaler.transform(features.reshape(1, -1))[0]
            
        return features
    
    def _calculate_aggregated_features(self, features: np.ndarray) -> np.ndarray:
        """Calculate aggregated features like category means and totals"""
        feature_dict = {col: features[i] for i, col in enumerate(self.feature_columns)}
        
        # Calculate category statistics
        categories = {
            'Materials': ['Materials_Concrete_Conductivity', 'Materials_Concrete_Thickness'],
            'Equipment': ['Equipment_Equipment_Level'],
            'Geometry': ['Geometry_win_mult_S', 'Geometry_win_mult_E', 'Geometry_win_mult_W', 'Geometry_win_mult_N'],
            'Elec': ['Elec_Fraction_Radiant', 'Elec_Fraction_Visible', 'Elec_Return_Air_Fraction'],
            'DHW': ['DHW_WaterHeater_Efficiency', 'DHW_WaterHeater_Ambient_Loss_Coefficient'],
            'Shading': ['Shading_win_shading_setpoint'],
            'Ventilation': ['Ventilation_DesignSpecification_Outdoor_Air_Flow_Rate']
        }
        
        # Update aggregated features
        for cat, params in categories.items():
            cat_values = [feature_dict.get(p, 0) for p in params if p in feature_dict]
            if cat_values:
                # Total changes
                total_key = f'total_{cat.lower()}_changes'
                if total_key in feature_dict:
                    feature_dict[total_key] = len([v for v in cat_values if v != 0])
                
                # Mean value
                mean_key = f'mean_{cat.lower()}_value'
                if mean_key in feature_dict:
                    feature_dict[mean_key] = np.mean(cat_values) if cat_values else 0
        
        # Total changes across all categories
        if 'total_changes' in feature_dict:
            feature_dict['total_changes'] = sum(1 for v in features if v != 0)
            
        # Convert back to array
        return np.array([feature_dict[col] for col in self.feature_columns])


class SurrogateCalibrationInterface:
    """Interface between calibration algorithms and surrogate model"""
    
    def __init__(self, adapter: SurrogateModelAdapter, 
                 measured_data: pd.DataFrame,
                 target_variable: str = 'electricity_total'):
        """
        Initialize calibration interface
        
        Args:
            adapter: SurrogateModelAdapter instance
            measured_data: DataFrame with measured data
            target_variable: Variable to calibrate against
        """
        self.adapter = adapter
        self.measured_data = measured_data
        self.target_variable = target_variable
        self.simulation_count = 0
        
    def evaluate_params(self, params: Dict[str, float]) -> float:
        """
        Evaluate parameter set and return objective value
        
        Args:
            params: Parameter values
            
        Returns:
            Objective value (lower is better)
        """
        self.simulation_count += 1
        
        # Get surrogate predictions
        predictions = self.adapter.simulate(params)
        
        # Extract relevant output
        if 'Cooling' in self.target_variable:
            sim_value = predictions['Zone_Air_System_Sensible_Cooling_Energy_mean']
        elif 'Heating' in self.target_variable:
            sim_value = predictions['Zone_Air_System_Sensible_Heating_Energy_mean']
        else:
            # Total energy (simplified - should be customized)
            sim_value = (predictions['Zone_Air_System_Sensible_Cooling_Energy_mean'] + 
                        predictions['Zone_Air_System_Sensible_Heating_Energy_mean'])
        
        # Calculate objective (e.g., RMSE)
        measured_value = self.measured_data[self.target_variable].mean()
        error = abs(sim_value - measured_value) / measured_value
        
        return error
    
    def batch_evaluate(self, param_sets: List[Dict[str, float]]) -> List[float]:
        """Evaluate multiple parameter sets"""
        return [self.evaluate_params(params) for params in param_sets]


def create_surrogate_calibrator(output_dir: str, measured_data: pd.DataFrame) -> SurrogateCalibrationInterface:
    """
    Factory function to create surrogate calibrator from output directory
    
    Args:
        output_dir: Path to simulation output directory
        measured_data: Measured data for calibration
        
    Returns:
        SurrogateCalibrationInterface instance
    """
    output_path = Path(output_dir)
    
    # Find model files
    model_path = output_path / "surrogate_models" / "surrogate_model.joblib"
    columns_path = output_path / "surrogate_models" / "surrogate_columns.joblib"
    scaler_path = output_path / "surrogate_models" / "v1.0" / "feature_scaler.joblib"
    
    # Check if files exist
    if not model_path.exists():
        raise FileNotFoundError(f"Surrogate model not found at {model_path}")
    if not columns_path.exists():
        raise FileNotFoundError(f"Feature columns not found at {columns_path}")
        
    # Create adapter
    adapter = SurrogateModelAdapter(
        str(model_path),
        str(columns_path),
        str(scaler_path) if scaler_path.exists() else None
    )
    
    # Create interface
    return SurrogateCalibrationInterface(adapter, measured_data)


# Example usage for integration with existing calibration
if __name__ == "__main__":
    # Example of how to use with existing calibration algorithms
    from cal.calibration_algorithms import ParticleSwarmOptimizer
    from cal.unified_calibration import ParamSpec
    
    # Load measured data (example)
    measured_data = pd.DataFrame({
        'electricity_total': [1000, 1100, 1200],  # kWh
        'month': [1, 2, 3]
    })
    
    # Create surrogate calibrator
    calibrator = create_surrogate_calibrator(
        "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99",
        measured_data
    )
    
    # Define parameters to calibrate (example)
    param_specs = [
        ParamSpec("Shading_win_shading_setpoint", 20, 10, 30),
        ParamSpec("Ventilation_DesignSpecification_Outdoor_Air_Flow_Rate", 0.01, 0.005, 0.02),
        ParamSpec("Equipment_Equipment_Level", 10, 5, 20)
    ]
    
    # Run PSO with surrogate model
    pso = ParticleSwarmOptimizer(n_particles=20, max_iter=50)
    
    # Create objective function
    def objective(params_dict):
        return calibrator.evaluate_params(params_dict)
    
    # Run optimization
    result = pso.optimize(objective, param_specs)
    
    print(f"Best parameters: {result.best_params}")
    print(f"Best objective: {result.best_objective}")
    print(f"Total surrogate evaluations: {calibrator.simulation_count}")