"""
Integrated Calibration Workflow
Combines surrogate models, sensitivity analysis, and validation results
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from typing import Dict, List, Optional, Tuple
from calibration_surrogate_adapter import create_surrogate_calibrator, SurrogateCalibrationInterface
from cal.calibration_algorithms import ParticleSwarmOptimizer, DifferentialEvolution
from cal.unified_calibration import ParamSpec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedCalibrationWorkflow:
    """Manages the complete calibration workflow using existing outputs"""
    
    def __init__(self, output_dir: str):
        """
        Initialize workflow with output directory
        
        Args:
            output_dir: Path to simulation output directory
        """
        self.output_dir = Path(output_dir)
        self.sensitivity_results = None
        self.validation_results = None
        self.modifications_summary = None
        self.param_specs = []
        
    def load_existing_results(self):
        """Load all existing analysis results"""
        logger.info("Loading existing results...")
        
        # Load sensitivity analysis - try multiple possible locations
        sensitivity_paths = [
            self.output_dir / "sensitivity_results" / "sensitivity_parameters.csv",  # Try CSV first for more info
            self.output_dir / "sensitivity_results" / "sensitivity_results.parquet",
            self.output_dir / "sensitivity_analysis" / "sensitivity_results.parquet",
            self.output_dir / "enhanced_sensitivity.csv"
        ]
        
        for path in sensitivity_paths:
            if path.exists():
                if path.suffix == '.parquet':
                    self.sensitivity_results = pd.read_parquet(path)
                else:
                    self.sensitivity_results = pd.read_csv(path)
                logger.info(f"Loaded {len(self.sensitivity_results)} sensitivity results from {path.name}")
                break
        
        # Load validation results
        validation_path = self.output_dir / "parsed_data" / "validation_results.parquet"
        if validation_path.exists():
            self.validation_results = pd.read_parquet(validation_path)
            logger.info("Loaded validation results")
            
        # Load modifications summary
        mods_path = self.output_dir / "modifications_summary.json"
        if mods_path.exists():
            with open(mods_path, 'r') as f:
                self.modifications_summary = json.load(f)
            logger.info(f"Loaded modifications for {len(self.modifications_summary)} parameters")
            
    def select_calibration_parameters(self, top_n: int = 20, 
                                    sensitivity_threshold: float = 0.1) -> List[ParamSpec]:
        """
        Select parameters for calibration based on sensitivity analysis
        
        Args:
            top_n: Number of top parameters to select
            sensitivity_threshold: Minimum sensitivity score
            
        Returns:
            List of ParamSpec objects
        """
        if self.sensitivity_results is None:
            raise ValueError("No sensitivity results loaded")
            
        # Sort by sensitivity score
        top_params = self.sensitivity_results.nlargest(top_n, 'sensitivity_score')
        
        # Filter by threshold
        top_params = top_params[top_params['sensitivity_score'] >= sensitivity_threshold]
        
        logger.info(f"Selected {len(top_params)} parameters for calibration")
        
        # Create ParamSpec objects
        param_specs = []
        for _, row in top_params.iterrows():
            # Extract parameter info from enhanced sensitivity format
            if 'parameter' in row:
                # Format: category*object_type*object_name*field_name
                # Convert to feature format: category_object_type_object_name_field_name
                param_name = row['parameter'].replace('*', '_').replace(' ', '_')
                
                # Store the full feature name and also create a simplified version
                full_param_name = param_name
                
                # Also store original parameter for reference
                original_param = row['parameter']
            else:
                param_name = str(row.name)
                full_param_name = param_name
                original_param = param_name
            
            # Get bounds from sensitivity data if available
            if 'min_value' in row and 'max_value' in row:
                param_min = float(row['min_value'])
                param_max = float(row['max_value'])
                param_default = float(row.get('current_value', (param_min + param_max) / 2))
            elif 'param_change' in row and row['param_change'] != 0:
                # Use param change to estimate bounds
                baseline = 1.0  # Assume normalized baseline
                change_factor = abs(row['param_change']) / 100.0
                param_min = baseline * (1 - change_factor * 2)
                param_max = baseline * (1 + change_factor * 2)
                param_default = baseline
            else:
                # Default bounds
                param_min = 0.5
                param_max = 2.0
                param_default = 1.0
            
            # For some parameters with min > max (negative ranges), swap them
            if param_min > param_max:
                param_min, param_max = param_max, param_min
            
            # Use full parameter name for the spec
            param_specs.append(
                ParamSpec(full_param_name, param_min, param_max)
            )
        
        # If we have modifications summary, update bounds from there
        if self.modifications_summary:
            for spec in param_specs:
                if spec.name in self.modifications_summary:
                    mod_info = self.modifications_summary[spec.name]
                    values = []
                    for change in mod_info['changes']:
                        if 'new_value' in change:
                            try:
                                values.append(float(change['new_value']))
                            except:
                                pass
                    
                    if values:
                        spec.min_value = min(values) * 0.8
                        spec.max_value = max(values) * 1.2
                    
        self.param_specs = param_specs
        return param_specs
    
    def load_measured_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load measured data for calibration
        
        Args:
            data_path: Path to measured data file
            
        Returns:
            DataFrame with measured data
        """
        if data_path:
            # Load from provided path
            return pd.read_csv(data_path)
        else:
            # Try to find in validation results
            if self.validation_results is not None:
                # Extract measured values from validation
                measured = self.validation_results[['real_value']].copy()
                measured.columns = ['electricity_total']
                return measured
            else:
                # Create dummy data for demonstration
                logger.warning("No measured data found, using dummy data")
                return pd.DataFrame({
                    'electricity_total': np.random.normal(1000, 100, 12),
                    'month': range(1, 13)
                })
    
    def run_calibration(self, measured_data: pd.DataFrame,
                       algorithm: str = 'PSO',
                       max_iter: int = 50,
                       population_size: int = 20) -> Dict:
        """
        Run calibration using surrogate model
        
        Args:
            measured_data: Measured data for calibration
            algorithm: Optimization algorithm ('PSO' or 'DE')
            max_iter: Maximum iterations
            population_size: Population size
            
        Returns:
            Calibration results
        """
        logger.info(f"Running {algorithm} calibration with surrogate model...")
        
        # Create surrogate calibrator
        calibrator = create_surrogate_calibrator(str(self.output_dir), measured_data)
        
        # Select algorithm
        if algorithm == 'PSO':
            optimizer = ParticleSwarmOptimizer(
                n_particles=population_size,
                max_iter=max_iter
            )
        elif algorithm == 'DE':
            optimizer = DifferentialEvolution(
                pop_size=population_size,
                max_iter=max_iter
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Create objective function
        def objective(params_dict):
            return calibrator.evaluate_params(params_dict)
        
        # Run optimization
        result = optimizer.optimize(objective, self.param_specs, verbose=True)
        
        # Add additional metrics
        final_metrics = self._calculate_final_metrics(
            result.best_params, calibrator, measured_data
        )
        
        return {
            'best_parameters': result.best_params,
            'best_objective': result.best_objective,
            'convergence_history': result.history,
            'final_metrics': final_metrics,
            'total_evaluations': calibrator.simulation_count
        }
    
    def _calculate_final_metrics(self, params: Dict[str, float],
                               calibrator: SurrogateCalibrationInterface,
                               measured_data: pd.DataFrame) -> Dict:
        """Calculate detailed metrics for final solution"""
        predictions = calibrator.adapter.simulate(params)
        
        # Extract relevant values
        sim_cooling = predictions['Zone_Air_System_Sensible_Cooling_Energy_mean']
        sim_heating = predictions['Zone_Air_System_Sensible_Heating_Energy_mean']
        sim_total = sim_cooling + sim_heating
        
        measured_total = measured_data['electricity_total'].mean()
        
        # Calculate metrics
        cvrmse = 100 * np.std(sim_total - measured_total) / measured_total
        nmbe = 100 * (sim_total - measured_total) / measured_total
        
        return {
            'CVRMSE': cvrmse,
            'NMBE': nmbe,
            'simulated_total': sim_total,
            'measured_total': measured_total,
            'cooling_energy': sim_cooling,
            'heating_energy': sim_heating
        }
    
    def save_calibrated_parameters(self, results: Dict, output_path: str):
        """Save calibrated parameters in format ready for IDF creation"""
        params = results['best_parameters']
        metrics = results['final_metrics']
        
        # Create parameter CSV for each category
        categories = {
            'shading': ['Shading_'],
            'ventilation': ['Ventilation_'],
            'equipment': ['Equipment_'],
            'materials': ['Materials_'],
            'geometry': ['Geometry_'],
            'dhw': ['DHW_'],
            'elec': ['Elec_']
        }
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for category, prefixes in categories.items():
            cat_params = []
            for param_name, value in params.items():
                if any(param_name.startswith(prefix) for prefix in prefixes):
                    cat_params.append({
                        'param_name': param_name,
                        'param_value': value,
                        'param_min': value * 0.9,  # For future recalibration
                        'param_max': value * 1.1
                    })
            
            if cat_params:
                df = pd.DataFrame(cat_params)
                df.to_csv(output_dir / f'calibrated_params_{category}.csv', index=False)
        
        # Save summary
        summary = {
            'calibration_metrics': metrics,
            'parameters': params,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        with open(output_dir / 'calibration_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Saved calibrated parameters to {output_dir}")


def main():
    """Example usage of integrated calibration workflow"""
    
    # Initialize workflow
    output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99"
    workflow = IntegratedCalibrationWorkflow(output_dir)
    
    # Load existing results
    workflow.load_existing_results()
    
    # Select parameters based on sensitivity
    param_specs = workflow.select_calibration_parameters(top_n=15, sensitivity_threshold=0.5)
    print(f"\nSelected {len(param_specs)} parameters for calibration:")
    for spec in param_specs[:5]:  # Show first 5
        print(f"  {spec.name}: {spec.min_value:.3f} - {spec.max_value:.3f}")
    
    # Load measured data
    measured_data = workflow.load_measured_data()
    
    # Run calibration
    results = workflow.run_calibration(
        measured_data,
        algorithm='PSO',
        max_iter=30,
        population_size=15
    )
    
    print(f"\nCalibration Results:")
    print(f"Best objective: {results['best_objective']:.4f}")
    print(f"Final CVRMSE: {results['final_metrics']['CVRMSE']:.2f}%")
    print(f"Final NMBE: {results['final_metrics']['NMBE']:.2f}%")
    print(f"Total evaluations: {results['total_evaluations']}")
    
    print(f"\nTop 5 calibrated parameters:")
    for param, value in list(results['best_parameters'].items())[:5]:
        print(f"  {param}: {value:.3f}")
    
    # Save results
    workflow.save_calibrated_parameters(results, "calibrated_parameters")


if __name__ == "__main__":
    main()