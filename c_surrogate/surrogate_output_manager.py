"""
c_surrogate/surrogate_output_manager.py

Manages surrogate model outputs, predictions, and integration with downstream tools.
Provides interfaces for optimization, validation, and reporting.

Author: Your Team
"""

import os
import pandas as pd
import numpy as np
import logging
import json
import joblib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

logger = logging.getLogger(__name__)


class SurrogateOutputManager:
    """
    Manages surrogate model artifacts, predictions, and outputs.
    """
    
    def __init__(self, model_artifacts: Dict[str, Any], config: Dict[str, Any] = None, tracker: Optional['SurrogatePipelineTracker'] = None):
        """
        Initialize the output manager.
        
        Args:
            model_artifacts: Dictionary containing model, metadata, etc. from training
            config: Configuration for output management
            tracker: Optional pipeline tracker for monitoring
        """
        self.model_artifacts = model_artifacts
        self.config = config or {}
        self.tracker = tracker
        
        # Extract key components
        self.model = model_artifacts.get('model')
        self.feature_columns = model_artifacts.get('feature_columns', [])
        self.target_columns = model_artifacts.get('target_columns', [])
        self.metadata = model_artifacts.get('metadata', {})
        self.scaler = model_artifacts.get('scaler')
        
        # Storage for predictions and validations
        self.predictions = {}
        self.validation_results = {}
        self.optimization_interfaces = {}
        
        # Version tracking
        self.version_info = {
            'version': self.config.get('version', '1.0'),
            'created_at': datetime.now().isoformat(),
            'model_type': self.metadata.get('model_type', 'unknown')
        }
    
    def save_surrogate_artifacts(self, output_dir: str):
        """
        Save all surrogate model artifacts in organized structure.
        """
        logger.info(f"[OutputManager] Saving surrogate artifacts to {output_dir}")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create versioned subdirectory
        version_dir = output_path / f"v{self.version_info['version']}"
        version_dir.mkdir(exist_ok=True)
        
        # Save model
        model_path = version_dir / 'surrogate_model.joblib'
        joblib.dump(self.model, model_path)
        logger.info(f"[OutputManager] Saved model to {model_path}")
        
        # Save scaler if exists
        if self.scaler is not None:
            scaler_path = version_dir / 'feature_scaler.joblib'
            joblib.dump(self.scaler, scaler_path)
            logger.info(f"[OutputManager] Saved scaler to {scaler_path}")
        
        # Save metadata
        metadata_complete = {
            **self.metadata,
            'version_info': self.version_info,
            'feature_columns': self.feature_columns,
            'target_columns': self.target_columns,
            'model_path': str(model_path),
            'scaler_path': str(scaler_path) if self.scaler else None
        }
        
        with open(version_dir / 'surrogate_metadata.json', 'w') as f:
            json.dump(metadata_complete, f, indent=2)
        
        # Save feature importance if available
        if hasattr(self.model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            importance_df.to_csv(version_dir / 'feature_importance.csv', index=False)
            logger.info("[OutputManager] Saved feature importance")
        
        # Create a simple prediction interface script
        self._create_prediction_script(version_dir)
        
        # Create version summary
        self._create_version_summary(output_path)
        
        logger.info(f"[OutputManager] All artifacts saved to {version_dir}")
    
    def generate_prediction_interface(self, 
                                    interface_type: str = 'function',
                                    include_uncertainty: bool = False) -> Union[Callable, Dict]:
        """
        Generate a prediction interface for easy model use.
        
        Args:
            interface_type: 'function', 'class', or 'api'
            include_uncertainty: Whether to include uncertainty estimates
            
        Returns:
            Prediction interface based on type
        """
        logger.info(f"[OutputManager] Generating {interface_type} prediction interface")
        
        if interface_type == 'function':
            def predict(parameter_changes: Dict[str, float], 
                       building_id: str = None,
                       return_all_outputs: bool = False) -> Dict[str, Any]:
                """
                Make predictions using the surrogate model.
                
                Args:
                    parameter_changes: Dictionary of parameter changes
                    building_id: Optional building identifier
                    return_all_outputs: Return all target variables
                    
                Returns:
                    Dictionary with predictions
                """
                # Prepare features
                feature_vector = np.zeros(len(self.feature_columns))
                
                for param, value in parameter_changes.items():
                    if param in self.feature_columns:
                        idx = self.feature_columns.index(param)
                        feature_vector[idx] = value
                
                # Scale if needed
                if self.scaler is not None:
                    feature_vector = self.scaler.transform(feature_vector.reshape(1, -1))
                
                # Predict
                predictions = self.model.predict(feature_vector.reshape(1, -1))
                
                # Format output
                if return_all_outputs:
                    result = {
                        target: pred for target, pred in zip(self.target_columns, predictions[0])
                    }
                else:
                    # Return primary target
                    result = {
                        'prediction': predictions[0][0],
                        'target_variable': self.target_columns[0]
                    }
                
                if building_id:
                    result['building_id'] = building_id
                
                return result
            
            self.optimization_interfaces['function'] = predict
            return predict
        
        elif interface_type == 'class':
            # Create a class-based interface
            class SurrogatePredictor:
                def __init__(self, model, feature_columns, target_columns, scaler=None):
                    self.model = model
                    self.feature_columns = feature_columns
                    self.target_columns = target_columns
                    self.scaler = scaler
                
                def predict(self, parameter_df: pd.DataFrame) -> pd.DataFrame:
                    """Predict from DataFrame of parameters."""
                    features = parameter_df[self.feature_columns].values
                    
                    if self.scaler:
                        features = self.scaler.transform(features)
                    
                    predictions = self.model.predict(features)
                    
                    result_df = parameter_df.copy()
                    for i, target in enumerate(self.target_columns):
                        result_df[f'predicted_{target}'] = predictions[:, i]
                    
                    return result_df
                
                def predict_single(self, parameters: Dict) -> Dict:
                    """Predict from single parameter set."""
                    df = pd.DataFrame([parameters])
                    result = self.predict(df)
                    return result.iloc[0].to_dict()
            
            predictor = SurrogatePredictor(
                self.model, 
                self.feature_columns, 
                self.target_columns,
                self.scaler
            )
            
            self.optimization_interfaces['class'] = predictor
            return predictor
        
        elif interface_type == 'api':
            # Create API specification
            api_spec = {
                'endpoint': '/predict',
                'method': 'POST',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                param: {'type': 'number'} for param in self.feature_columns
                            }
                        },
                        'building_id': {'type': 'string'},
                        'include_all_outputs': {'type': 'boolean'}
                    },
                    'required': ['parameters']
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'predictions': {
                            'type': 'object',
                            'properties': {
                                target: {'type': 'number'} for target in self.target_columns
                            }
                        },
                        'metadata': {'type': 'object'}
                    }
                }
            }
            
            self.optimization_interfaces['api'] = api_spec
            return api_spec
    
    def export_for_optimization(self, 
                              optimization_framework: str = 'generic',
                              constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Export surrogate model in format suitable for optimization tools.
        
        Args:
            optimization_framework: 'generic', 'pyomo', 'gekko', 'scipy'
            constraints: Optional constraints on parameters
            
        Returns:
            Dictionary with optimization-ready format
        """
        logger.info(f"[OutputManager] Exporting for {optimization_framework} optimization")
        
        export_data = {
            'framework': optimization_framework,
            'timestamp': datetime.now().isoformat()
        }
        
        if optimization_framework == 'generic':
            # Generic format suitable for most optimizers
            export_data.update({
                'objective_function': self.generate_prediction_interface('function'),
                'decision_variables': self.feature_columns,
                'n_variables': len(self.feature_columns),
                'objectives': self.target_columns,
                'n_objectives': len(self.target_columns),
                'variable_bounds': self._get_variable_bounds(),
                'constraints': constraints or {}
            })
        
        elif optimization_framework == 'scipy':
            # Format for scipy.optimize
            def objective(x):
                """Objective function for scipy optimization."""
                # Prepare parameter dict
                params = {feat: val for feat, val in zip(self.feature_columns, x)}
                
                # Get prediction
                pred_func = self.optimization_interfaces.get('function')
                if not pred_func:
                    pred_func = self.generate_prediction_interface('function')
                
                result = pred_func(params, return_all_outputs=True)
                
                # Return first objective (minimize)
                return result[self.target_columns[0]]
            
            export_data.update({
                'objective': objective,
                'x0': np.zeros(len(self.feature_columns)),  # Initial guess
                'bounds': self._get_scipy_bounds(),
                'method_recommendation': 'L-BFGS-B'
            })
        
        elif optimization_framework == 'pyomo':
            # Format for Pyomo optimization
            export_data.update({
                'model_type': 'sklearn',
                'feature_names': self.feature_columns,
                'target_names': self.target_columns,
                'model_path': self.model_artifacts.get('model_path'),
                'scaler_path': self.model_artifacts.get('scaler_path'),
                'pyomo_code_template': self._generate_pyomo_template()
            })
        
        return export_data
    
    def create_validation_reports(self, 
                                test_data: Dict[str, pd.DataFrame],
                                output_dir: str = None) -> Dict[str, Any]:
        """
        Create comprehensive validation reports comparing predictions with actual.
        
        Args:
            test_data: Dictionary with 'features' and 'targets' DataFrames
            output_dir: Directory to save reports
            
        Returns:
            Dictionary with validation metrics
        """
        logger.info("[OutputManager] Creating validation reports")
        
        features = test_data['features']
        actual = test_data['targets']
        
        # Make predictions
        if self.scaler:
            features_scaled = self.scaler.transform(features[self.feature_columns])
        else:
            features_scaled = features[self.feature_columns].values
        
        predictions = self.model.predict(features_scaled)
        
        # Calculate metrics for each target
        validation_metrics = {}
        
        for i, target in enumerate(self.target_columns):
            y_true = actual[target].values
            y_pred = predictions[:, i] if len(predictions.shape) > 1 else predictions
            
            metrics = {
                'r2': r2_score(y_true, y_pred),
                'mae': mean_absolute_error(y_true, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
                'mape': np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if y_true.mean() != 0 else np.nan,
                'bias': np.mean(y_pred - y_true)
            }
            
            validation_metrics[target] = metrics
            
            # Store for plotting
            self.validation_results[target] = {
                'actual': y_true,
                'predicted': y_pred,
                'metrics': metrics
            }
        
        # Create visualizations if output directory provided
        if output_dir:
            self._create_validation_plots(output_dir)
        
        # Create summary report
        summary = {
            'validation_date': datetime.now().isoformat(),
            'n_samples': len(features),
            'overall_metrics': self._calculate_overall_metrics(validation_metrics),
            'target_metrics': validation_metrics,
            'model_info': self.version_info
        }
        
        # Save report if output directory provided
        # Save report if output directory provided
        if output_dir:
            report_path = Path(output_dir) / 'validation_report.json'
            with open(report_path, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"[OutputManager] Saved validation report to {report_path}")
        
        # Track validation results
        if self.tracker:
            # Generate prediction examples
            example_params = {}
            for i, col in enumerate(self.feature_columns[:5]):
                example_params[col] = 0.1  # Small change
            
            pred_func = self.generate_prediction_interface('function')
            example_prediction = pred_func(example_params, return_all_outputs=True)
            
            self.tracker.track_output_generation(
                validation_results=summary,
                prediction_examples={"example_input": example_params, "example_output": example_prediction},
                artifacts_saved=[str(report_path)]
            )
        
        return summary
    
    def manage_model_versions(self, 
                            base_dir: str,
                            action: str = 'list',
                            version: str = None) -> Union[List[str], Dict[str, Any]]:
        """
        Manage different versions of surrogate models.
        
        Args:
            base_dir: Base directory containing model versions
            action: 'list', 'load', 'compare', 'activate'
            version: Specific version for actions
            
        Returns:
            Version information or loaded model
        """
        logger.info(f"[OutputManager] Managing model versions - action: {action}")
        
        base_path = Path(base_dir)
        
        if action == 'list':
            # List all versions
            versions = []
            for item in base_path.iterdir():
                if item.is_dir() and item.name.startswith('v'):
                    metadata_path = item / 'surrogate_metadata.json'
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        versions.append({
                            'version': item.name,
                            'created_at': metadata.get('version_info', {}).get('created_at'),
                            'model_type': metadata.get('model_type'),
                            'n_features': metadata.get('n_features'),
                            'path': str(item)
                        })
            
            return sorted(versions, key=lambda x: x['version'], reverse=True)
        
        elif action == 'load' and version:
            # Load specific version
            version_path = base_path / version
            metadata_path = version_path / 'surrogate_metadata.json'
            
            if not metadata_path.exists():
                raise ValueError(f"Version {version} not found")
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Load model
            model = joblib.load(version_path / 'surrogate_model.joblib')
            
            # Load scaler if exists
            scaler = None
            if metadata.get('scaler_path'):
                scaler_path = version_path / 'feature_scaler.joblib'
                if scaler_path.exists():
                    scaler = joblib.load(scaler_path)
            
            return {
                'model': model,
                'metadata': metadata,
                'scaler': scaler,
                'version': version
            }
        
        elif action == 'compare':
            # Compare multiple versions
            versions = self.manage_model_versions(base_dir, 'list')
            comparison = []
            
            for ver in versions:
                ver_data = self.manage_model_versions(base_dir, 'load', ver['version'])
                metadata = ver_data['metadata']
                
                comparison.append({
                    'version': ver['version'],
                    'created_at': ver['created_at'],
                    'model_type': metadata.get('model_type'),
                    'n_features': metadata.get('n_features'),
                    'n_samples': metadata.get('n_samples'),
                    'r2_score': metadata.get('validation_metrics', {}).get('r2')
                })
            
            return pd.DataFrame(comparison)
        
        return []
    
    def generate_uncertainty_estimates(self, 
                                     parameter_sets: pd.DataFrame,
                                     method: str = 'bootstrap',
                                     n_iterations: int = 100) -> pd.DataFrame:
        """
        Generate uncertainty estimates for predictions.
        
        Args:
            parameter_sets: DataFrame of parameter combinations
            method: 'bootstrap', 'dropout', or 'ensemble'
            n_iterations: Number of iterations for uncertainty estimation
            
        Returns:
            DataFrame with predictions and uncertainty bounds
        """
        logger.info(f"[OutputManager] Generating uncertainty estimates using {method}")
        
        # Prepare features
        features = parameter_sets[self.feature_columns].values
        if self.scaler:
            features = self.scaler.transform(features)
        
        if method == 'bootstrap':
            # For tree-based models, use predictions from individual trees
            if hasattr(self.model, 'estimators_'):
                predictions = []
                for estimator in self.model.estimators_[:n_iterations]:
                    pred = estimator.predict(features)
                    predictions.append(pred)
                
                predictions = np.array(predictions)
                mean_pred = predictions.mean(axis=0)
                std_pred = predictions.std(axis=0)
                
                lower_bound = mean_pred - 1.96 * std_pred
                upper_bound = mean_pred + 1.96 * std_pred
            else:
                # Fallback to point estimates
                mean_pred = self.model.predict(features)
                std_pred = np.zeros_like(mean_pred)
                lower_bound = mean_pred
                upper_bound = mean_pred
        
        # Create results DataFrame
        results = parameter_sets.copy()
        
        for i, target in enumerate(self.target_columns):
            if len(mean_pred.shape) > 1:
                results[f'{target}_prediction'] = mean_pred[:, i]
                results[f'{target}_std'] = std_pred[:, i] if std_pred.ndim > 1 else std_pred
                results[f'{target}_lower_95'] = lower_bound[:, i] if lower_bound.ndim > 1 else lower_bound
                results[f'{target}_upper_95'] = upper_bound[:, i] if upper_bound.ndim > 1 else upper_bound
            else:
                results[f'{target}_prediction'] = mean_pred
                results[f'{target}_std'] = std_pred
                results[f'{target}_lower_95'] = lower_bound
                results[f'{target}_upper_95'] = upper_bound
        
        return results
    
    def _create_prediction_script(self, output_dir: Path):
        """Create a standalone prediction script."""
        script_content = f'''"""
Standalone prediction script for surrogate model v{self.version_info['version']}
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import numpy as np
import pandas as pd
import joblib
import json

# Load model and metadata
model = joblib.load('surrogate_model.joblib')
with open('surrogate_metadata.json', 'r') as f:
    metadata = json.load(f)

feature_columns = metadata['feature_columns']
target_columns = metadata['target_columns']

# Load scaler if exists
scaler = None
if metadata.get('scaler_path'):
    try:
        scaler = joblib.load('feature_scaler.joblib')
    except:
        print("Warning: Could not load scaler")

def predict(parameters):
    """
    Make predictions using the surrogate model.
    
    Args:
        parameters: Dictionary of parameter values
        
    Returns:
        Dictionary of predictions
    """
    # Create feature vector
    features = np.zeros(len(feature_columns))
    for i, col in enumerate(feature_columns):
        if col in parameters:
            features[i] = parameters[col]
    
    # Scale if needed
    if scaler is not None:
        features = scaler.transform(features.reshape(1, -1))
    else:
        features = features.reshape(1, -1)
    
    # Predict
    predictions = model.predict(features)
    
    # Format output
    results = {{}}
    for i, target in enumerate(target_columns):
        results[target] = float(predictions[0][i] if len(predictions.shape) > 1 else predictions[0])
    
    return results

# Example usage
if __name__ == "__main__":
    # Example parameters (modify as needed)
    example_params = {{col: 0.0 for col in feature_columns[:5]}}
    
    print("Example prediction:")
    print(predict(example_params))
'''
        
        with open(output_dir / 'predict.py', 'w') as f:
            f.write(script_content)
    
    def _create_version_summary(self, base_dir: Path):
        """Create a summary of all model versions."""
        versions = []
        for version_dir in base_dir.iterdir():
            if version_dir.is_dir() and version_dir.name.startswith('v'):
                metadata_path = version_dir / 'surrogate_metadata.json'
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    versions.append({
                        'version': version_dir.name,
                        'created': metadata.get('version_info', {}).get('created_at'),
                        'model_type': metadata.get('model_type'),
                        'features': metadata.get('n_features'),
                        'samples': metadata.get('n_samples')
                    })
        
        if versions:
            summary_df = pd.DataFrame(versions)
            summary_df.to_csv(base_dir / 'version_summary.csv', index=False)
    
    def _create_validation_plots(self, output_dir: str):
        """Create validation visualization plots."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create subplots for each target
        n_targets = len(self.target_columns)
        fig, axes = plt.subplots(1, n_targets, figsize=(6*n_targets, 5))
        
        if n_targets == 1:
            axes = [axes]
        
        for i, (target, data) in enumerate(self.validation_results.items()):
            ax = axes[i]
            
            # Scatter plot
            ax.scatter(data['actual'], data['predicted'], alpha=0.5, s=20)
            
            # Perfect prediction line
            min_val = min(data['actual'].min(), data['predicted'].min())
            max_val = max(data['actual'].max(), data['predicted'].max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
            
            # Labels and title
            ax.set_xlabel('Actual')
            ax.set_ylabel('Predicted')
            ax.set_title(f'{target}\nR² = {data["metrics"]["r2"]:.3f}')
            
            # Add text with metrics
            metrics_text = f'MAE: {data["metrics"]["mae"]:.2e}\nRMSE: {data["metrics"]["rmse"]:.2e}'
            ax.text(0.05, 0.95, metrics_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(output_path / 'validation_plots.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create residual plots
        fig, axes = plt.subplots(1, n_targets, figsize=(6*n_targets, 5))
        
        if n_targets == 1:
            axes = [axes]
        
        for i, (target, data) in enumerate(self.validation_results.items()):
            ax = axes[i]
            
            residuals = data['predicted'] - data['actual']
            ax.scatter(data['predicted'], residuals, alpha=0.5, s=20)
            ax.axhline(y=0, color='r', linestyle='--')
            
            ax.set_xlabel('Predicted')
            ax.set_ylabel('Residuals')
            ax.set_title(f'{target} Residuals')
        
        plt.tight_layout()
        plt.savefig(output_path / 'residual_plots.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _get_variable_bounds(self) -> Dict[str, Tuple[float, float]]:
        """Get bounds for decision variables."""
        bounds = {}
        for col in self.feature_columns:
            # Default bounds based on parameter type
            if 'relative_change' in col or 'percent' in col:
                bounds[col] = (-1.0, 1.0)  # -100% to +100%
            else:
                bounds[col] = (-np.inf, np.inf)
        return bounds
    
    def _get_scipy_bounds(self) -> List[Tuple[float, float]]:
        """Get bounds in scipy format."""
        bounds = self._get_variable_bounds()
        return [bounds.get(col, (-np.inf, np.inf)) for col in self.feature_columns]
    
    def _generate_pyomo_template(self) -> str:
        """Generate Pyomo optimization template."""
        return '''
# Pyomo optimization template for surrogate model

from pyomo.environ import *
import joblib
import numpy as np

# Load surrogate model
model = joblib.load('{model_path}')
scaler = joblib.load('{scaler_path}') if '{scaler_path}' else None

# Create Pyomo model
m = ConcreteModel()

# Decision variables
{decision_vars}

# Objective function using surrogate
def surrogate_objective(m):
    features = np.array([{feature_list}])
    if scaler:
        features = scaler.transform(features.reshape(1, -1))
    prediction = model.predict(features.reshape(1, -1))
    return prediction[0]

m.objective = Objective(rule=surrogate_objective, sense=minimize)

# Constraints (add as needed)
# m.constraint1 = Constraint(expr=...)

# Solve
solver = SolverFactory('ipopt')
results = solver.solve(m, tee=True)

# Display results
m.display()
'''.format(
            model_path=self.model_artifacts.get('model_path', 'surrogate_model.joblib'),
            scaler_path=self.model_artifacts.get('scaler_path', ''),
            decision_vars='\n'.join([f"m.{col} = Var(bounds={self._get_variable_bounds().get(col, '(None, None)')})" 
                                   for col in self.feature_columns]),
            feature_list=', '.join([f"m.{col}" for col in self.feature_columns])
        )
    
    def _calculate_overall_metrics(self, target_metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate overall metrics across all targets."""
        all_r2 = [m['r2'] for m in target_metrics.values()]
        all_mae = [m['mae'] for m in target_metrics.values()]
        all_rmse = [m['rmse'] for m in target_metrics.values()]
        
        return {
            'mean_r2': np.mean(all_r2),
            'min_r2': np.min(all_r2),
            'mean_mae': np.mean(all_mae),
            'mean_rmse': np.mean(all_rmse)
        }


# Utility functions
def create_surrogate_outputs(model_artifacts: Dict[str, Any],
                           test_data: Dict[str, pd.DataFrame] = None,
                           output_dir: str = None,
                           config: Dict[str, Any] = None) -> SurrogateOutputManager:
    """
    Convenience function to create and setup output manager.
    
    Args:
        model_artifacts: Model training artifacts
        test_data: Optional test data for validation
        output_dir: Directory to save outputs
        config: Configuration options
        
    Returns:
        Configured SurrogateOutputManager instance
    """
    manager = SurrogateOutputManager(model_artifacts, config)
    
    # Save artifacts if output directory provided
    if output_dir:
        manager.save_surrogate_artifacts(output_dir)
    
    # Create validation reports if test data provided
    if test_data:
        manager.create_validation_reports(test_data, output_dir)
    
    # Generate default prediction interface
    manager.generate_prediction_interface('function')
    
    return manager