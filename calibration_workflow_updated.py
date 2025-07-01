"""
Updated Calibration Workflow using new data structure
Uses modifications parquet data and properly aligned scenario files
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


class UpdatedCalibrationWorkflow:
    """Updated calibration workflow using new data structure"""
    
    def __init__(self, output_dir: str):
        """
        Initialize workflow with output directory
        
        Args:
            output_dir: Path to simulation output directory
        """
        self.output_dir = Path(output_dir)
        self.calibration_params = None
        self.modifications_data = None
        self.simulation_results = None
        self.param_specs = []
        
    def load_calibration_data(self):
        """Load calibration data from new structure"""
        logger.info("Loading calibration data from new structure...")
        
        # Load calibration parameters from new location
        calib_dir = self.output_dir / "calibration_scenarios"
        if not calib_dir.exists():
            raise FileNotFoundError(f"Calibration scenarios directory not found at {calib_dir}")
        
        # Load main calibration parameters
        main_params_file = calib_dir / "calibration_parameters_all.csv"
        if main_params_file.exists():
            self.calibration_params = pd.read_csv(main_params_file)
            logger.info(f"Loaded {len(self.calibration_params)} calibration parameters")
        else:
            raise FileNotFoundError(f"Main calibration parameters file not found at {main_params_file}")
        
        # Load modifications data
        mod_files = list((self.output_dir / "modified_idfs").glob("modifications_detail_wide_*.parquet"))
        if mod_files:
            self.modifications_data = pd.read_parquet(mod_files[0])
            logger.info(f"Loaded modifications data with {len(self.modifications_data)} parameters")
        
        # Load summary if available
        summary_file = calib_dir / "calibration_scenarios_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                self.calibration_summary = json.load(f)
                logger.info(f"Loaded calibration summary: {self.calibration_summary['total_parameters']} parameters")
    
    def load_simulation_results(self, variant_id: Optional[int] = None):
        """
        Load simulation results for calibration
        
        Args:
            variant_id: Specific variant to load, or None for all
        """
        logger.info("Loading simulation results...")
        
        # Check for parsed results
        parsed_dir = self.output_dir / "parsed_modified_results"
        if parsed_dir.exists():
            # Load comparison data
            comparisons_dir = parsed_dir / "comparisons"
            if comparisons_dir.exists():
                # Find available result files
                result_files = list(comparisons_dir.glob("*.parquet"))
                logger.info(f"Found {len(result_files)} result files in comparisons")
                
                # Load a sample to understand structure
                if result_files:
                    sample_df = pd.read_parquet(result_files[0])
                    logger.info(f"Sample result shape: {sample_df.shape}, columns: {list(sample_df.columns)}")
        
        # For full calibration, we need to extract variant-specific results
        # This would involve parsing SQL files from Modified_Sim_Results
        modified_results_dir = self.output_dir / "Modified_Sim_Results"
        if modified_results_dir.exists():
            logger.info(f"Modified simulation results available at {modified_results_dir}")
    
    def select_calibration_parameters(self, 
                                    selection_criteria: str = "high_priority",
                                    top_n: Optional[int] = None) -> List[ParamSpec]:
        """
        Select parameters for calibration based on criteria
        
        Args:
            selection_criteria: One of "high_priority", "surrogate", "top_sensitivity", "all"
            top_n: Number of parameters to select (for top_sensitivity)
            
        Returns:
            List of ParamSpec objects
        """
        if self.calibration_params is None:
            raise ValueError("No calibration parameters loaded")
        
        # Select based on criteria
        if selection_criteria == "high_priority":
            selected = self.calibration_params[
                self.calibration_params['calibration_priority'] == 'high'
            ]
        elif selection_criteria == "surrogate":
            # Load surrogate-specific parameters
            surrogate_file = self.output_dir / "calibration_scenarios" / "calibration_parameters_surrogate.csv"
            if surrogate_file.exists():
                selected = pd.read_csv(surrogate_file)
            else:
                # Fallback to main file filtered by surrogate flag
                selected = self.calibration_params
        elif selection_criteria == "top_sensitivity":
            if top_n is None:
                top_n = 10
            selected = self.calibration_params.nlargest(top_n, 'sensitivity_score')
        else:  # "all"
            selected = self.calibration_params
        
        logger.info(f"Selected {len(selected)} parameters with criteria '{selection_criteria}'")
        
        # Create ParamSpec objects
        param_specs = []
        for _, row in selected.iterrows():
            param_name = row['param_name']
            
            # Handle cases where min > max
            min_val = float(row['min_value'])
            max_val = float(row['max_value'])
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            
            # Ensure we have a valid range
            if min_val == max_val:
                # Add small variation
                current = float(row.get('current_value', min_val))
                min_val = current * 0.9
                max_val = current * 1.1
            
            param_specs.append(
                ParamSpec(param_name, min_val, max_val)
            )
        
        self.param_specs = param_specs
        return param_specs
    
    def extract_variant_results(self, output_variables: List[str]) -> pd.DataFrame:
        """
        Extract simulation results for all variants
        
        Args:
            output_variables: List of output variables to extract
            
        Returns:
            DataFrame with variant results
        """
        logger.info("Extracting variant-specific results...")
        
        results = []
        
        # Get variant columns from modifications data
        if self.modifications_data is not None:
            variant_cols = [col for col in self.modifications_data.columns if col.startswith('variant_')]
            n_variants = len(variant_cols)
            logger.info(f"Found {n_variants} variants to process")
            
            # For each variant, we would need to:
            # 1. Find the corresponding simulation results
            # 2. Extract the specified output variables
            # 3. Aggregate to match calibration time scale
            
            # This is a placeholder - actual implementation would parse SQL files
            for i, variant_col in enumerate(variant_cols):
                variant_num = int(variant_col.split('_')[1])
                
                # Create variant result entry
                result_entry = {
                    'variant_id': variant_num,
                    'variant_name': variant_col
                }
                
                # Add parameter values for this variant
                for _, param_row in self.modifications_data.iterrows():
                    param_name = f"{param_row['category']}*{param_row['object_type']}*{param_row['object_name']}*{param_row['field']}"
                    result_entry[param_name] = param_row[variant_col]
                
                # Add placeholder output values
                # In real implementation, these would come from SQL parsing
                for var in output_variables:
                    result_entry[var] = np.random.normal(1000, 100)  # Placeholder
                
                results.append(result_entry)
        
        return pd.DataFrame(results)
    
    def prepare_calibration_data(self, target_variable: str = "Electricity:Facility") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare data for calibration in the expected format
        
        Args:
            target_variable: Target output variable for calibration
            
        Returns:
            Tuple of (parameter_data, output_data)
        """
        logger.info(f"Preparing calibration data for {target_variable}...")
        
        # Extract variant results
        variant_results = self.extract_variant_results([target_variable])
        
        # Separate parameters and outputs
        param_cols = [col for col in variant_results.columns 
                     if '*' in col]  # Parameter columns have * separator
        output_cols = [col for col in variant_results.columns 
                      if col not in param_cols and col not in ['variant_id', 'variant_name']]
        
        parameter_data = variant_results[['variant_id'] + param_cols]
        output_data = variant_results[['variant_id'] + output_cols]
        
        logger.info(f"Prepared {len(parameter_data)} samples with {len(param_cols)} parameters")
        
        return parameter_data, output_data
    
    def run_calibration(self, measured_data: pd.DataFrame,
                       target_variable: str = "Electricity:Facility",
                       algorithm: str = 'PSO',
                       max_iter: int = 50) -> Dict:
        """
        Run calibration using the updated workflow
        
        Args:
            measured_data: Measured data for calibration
            target_variable: Target variable to calibrate
            algorithm: Optimization algorithm
            max_iter: Maximum iterations
            
        Returns:
            Calibration results
        """
        logger.info(f"Running calibration with {algorithm}...")
        
        # Check if we can use surrogate models
        surrogate_dir = self.output_dir / "surrogate_models"
        use_surrogate = surrogate_dir.exists() and any(surrogate_dir.glob("*.joblib"))
        
        if use_surrogate:
            logger.info("Using surrogate models for fast calibration")
            # Use existing surrogate-based calibration
            calibrator = create_surrogate_calibrator(str(self.output_dir), measured_data)
        else:
            logger.info("Surrogate models not available, using direct simulation")
            # Would need to implement direct simulation calibration
            raise NotImplementedError("Direct simulation calibration not yet implemented")
        
        # Create optimizer
        if algorithm == 'PSO':
            optimizer = ParticleSwarmOptimizer(n_particles=20, max_iter=max_iter)
        elif algorithm == 'DE':
            optimizer = DifferentialEvolution(pop_size=20, max_iter=max_iter)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Define objective function
        def objective(params_dict):
            return calibrator.evaluate_params(params_dict)
        
        # Run optimization
        result = optimizer.optimize(objective, self.param_specs, verbose=True)
        
        return {
            'best_parameters': result.best_params,
            'best_objective': result.best_objective,
            'convergence_history': result.history,
            'algorithm': algorithm,
            'n_parameters': len(self.param_specs)
        }
    
    def save_results(self, results: Dict, output_name: str = "calibration_results"):
        """Save calibration results"""
        output_dir = self.output_dir / output_name
        output_dir.mkdir(exist_ok=True)
        
        # Save parameters
        params_df = pd.DataFrame([
            {'parameter': k, 'calibrated_value': v}
            for k, v in results['best_parameters'].items()
        ])
        params_df.to_csv(output_dir / "calibrated_parameters.csv", index=False)
        
        # Save full results
        with open(output_dir / "calibration_results.json", 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            json_results = {
                'best_parameters': results['best_parameters'],
                'best_objective': float(results['best_objective']),
                'algorithm': results['algorithm'],
                'n_parameters': results['n_parameters'],
                'convergence_history': [float(x) for x in results['convergence_history']]
            }
            json.dump(json_results, f, indent=2)
        
        logger.info(f"Saved calibration results to {output_dir}")


def main():
    """Example usage of updated calibration workflow"""
    
    # Initialize workflow
    output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb"
    workflow = UpdatedCalibrationWorkflow(output_dir)
    
    # Load data
    workflow.load_calibration_data()
    workflow.load_simulation_results()
    
    # Select parameters
    param_specs = workflow.select_calibration_parameters(
        selection_criteria="surrogate",  # Use surrogate-enabled parameters
        top_n=None
    )
    print(f"\nSelected {len(param_specs)} parameters for calibration")
    
    # Create dummy measured data for demonstration
    measured_data = pd.DataFrame({
        'electricity_total': np.random.normal(1000, 100, 12),
        'month': range(1, 13)
    })
    
    # Run calibration
    try:
        results = workflow.run_calibration(
            measured_data,
            target_variable="Electricity:Facility",
            algorithm='PSO',
            max_iter=30
        )
        
        print(f"\nCalibration Results:")
        print(f"Best objective: {results['best_objective']:.4f}")
        print(f"Number of parameters: {results['n_parameters']}")
        
        # Save results
        workflow.save_results(results)
        
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        print(f"\nNote: {e}")
        print("This is expected if surrogate models haven't been trained yet.")
        print("First run the surrogate training pipeline, then calibration can proceed.")


if __name__ == "__main__":
    main()