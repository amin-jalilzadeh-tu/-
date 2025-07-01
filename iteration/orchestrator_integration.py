"""
Integration module to connect iteration system with main orchestrator
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .iteration_controller import IterationController, IterationStatus
from .parameter_feedback import ParameterFeedback
from .parameter_store import ParameterStore

logger = logging.getLogger(__name__)


class OrchestratorIterationAdapter:
    """
    Adapts the iteration system to work with the existing orchestrator workflow
    """
    
    def __init__(self, main_config: Dict[str, Any], job_output_dir: str):
        self.main_config = main_config
        self.job_output_dir = Path(job_output_dir)
        self.job_id = main_config.get('job_id', 'unknown')
        
        # Get iteration configuration
        self.iteration_config = main_config.get('iteration', {})
        
        # Initialize components if iteration is enabled
        if self.iteration_config.get('enabled', False):
            self.controller = IterationController(self.job_id, config_dict=self.iteration_config)
            self.feedback = ParameterFeedback(self.job_id)
            self.param_store = ParameterStore(self.job_id)
        else:
            self.controller = None
            self.feedback = None
            self.param_store = None
    
    def should_run_iterations(self) -> bool:
        """Check if iterations should be run"""
        return (
            self.iteration_config.get('enabled', False) and
            self.controller is not None
        )
    
    def run_iteration_loop(self, 
                         initial_workflow_results: Dict[str, Any],
                         workflow_executor) -> Dict[str, Any]:
        """
        Run the iteration loop
        
        Args:
            initial_workflow_results: Results from initial workflow run
            workflow_executor: Function to execute workflow steps
        
        Returns:
            Final iteration results
        """
        if not self.should_run_iterations():
            return initial_workflow_results
        
        logger.info("Starting calibration iteration loop")
        
        # Extract initial metrics from validation or calibration results
        initial_metrics = self._extract_metrics(initial_workflow_results)
        
        # Store initial parameters (baseline)
        initial_params = self._get_initial_parameters()
        self.param_store.store_parameters(
            iteration_id=0,
            parameters=initial_params,
            metrics=initial_metrics,
            metadata={'type': 'baseline'}
        )
        
        # Run iteration loop
        while self.controller.should_continue():
            try:
                # Start new iteration
                iter_info = self.controller.start_iteration()
                logger.info(f"Starting iteration {iter_info['iteration']}")
                
                # Convert parameters to workflow configuration
                workflow_config = self._create_iteration_workflow_config(
                    iter_info['parameters'],
                    iter_info['output_dir']
                )
                
                # Execute workflow with new parameters
                iteration_results = workflow_executor(workflow_config)
                
                # Extract metrics from results
                metrics = self._extract_metrics(iteration_results)
                
                # Store iteration results
                version_id = self.param_store.store_parameters(
                    iteration_id=iter_info['iteration'],
                    parameters=iter_info['parameters'],
                    metrics=metrics,
                    metadata={'workflow_results': iteration_results}
                )
                
                # Complete iteration
                self.controller.complete_iteration(metrics, iter_info['parameters'])
                
                # Create modification configs for next iteration
                if self.controller.should_continue():
                    self._prepare_next_iteration(iter_info['parameters'], metrics)
                
            except Exception as e:
                logger.error(f"Error in iteration {self.controller.current_iteration}: {e}")
                self.controller.complete_iteration(
                    {'error': str(e)}, 
                    iter_info['parameters'],
                    IterationStatus.FAILED
                )
                break
        
        # Get final results
        summary = self.controller.get_summary()
        best_version = self.param_store.get_best_version()
        
        return {
            'iteration_summary': summary,
            'best_parameters': best_version.parameters if best_version else None,
            'best_metrics': best_version.metrics if best_version else None,
            'total_iterations': self.controller.current_iteration
        }
    
    def _extract_metrics(self, workflow_results: Dict[str, Any]) -> Dict[str, float]:
        """Extract metrics from workflow results"""
        metrics = {}
        
        # Try to extract from validation results
        validation_results = workflow_results.get('validation', {})
        if validation_results:
            summary = validation_results.get('summary', {})
            metrics['rmse'] = summary.get('overall_rmse', float('inf'))
            metrics['cv_rmse'] = summary.get('overall_cv_rmse', float('inf'))
            metrics['nmbe'] = summary.get('overall_nmbe', float('inf'))
            metrics['r2'] = summary.get('overall_r2', 0.0)
        
        # Try to extract from calibration results
        calibration_results = workflow_results.get('calibration', {})
        if calibration_results and not metrics:
            best_params = calibration_results.get('best_params', {})
            metrics['rmse'] = best_params.get('final_rmse', float('inf'))
            metrics['cv_rmse'] = best_params.get('final_cv_rmse', float('inf'))
            metrics['nmbe'] = best_params.get('final_nmbe', float('inf'))
            metrics['r2'] = best_params.get('final_r2', 0.0)
        
        # Default metrics if nothing found
        if not metrics:
            logger.warning("Could not extract metrics from workflow results")
            metrics = {
                'rmse': float('inf'),
                'cv_rmse': float('inf'),
                'nmbe': float('inf'),
                'r2': 0.0
            }
        
        return metrics
    
    def _get_initial_parameters(self) -> Dict[str, Any]:
        """Get initial parameters from configuration"""
        # Extract from modification config or use defaults
        mod_config = self.main_config.get('modification', {})
        categories = mod_config.get('categories_to_modify', {})
        
        parameters = {}
        
        # Extract parameters from each category
        for category, cat_config in categories.items():
            if cat_config.get('enabled', False):
                # Get intensity or default values
                if category == 'infiltration':
                    parameters['infiltration_rate'] = cat_config.get('intensity', 0.5)
                elif category == 'materials':
                    parameters['window_u_value'] = 2.0
                    parameters['wall_insulation'] = 0.05
                elif category == 'hvac':
                    parameters['hvac_efficiency'] = 0.85
                    parameters['cooling_cop'] = 3.0
                elif category == 'lighting':
                    parameters['lighting_power_density'] = 10.0
                elif category == 'equipment':
                    parameters['equipment_power_density'] = 15.0
        
        return parameters
    
    def _create_iteration_workflow_config(self, 
                                        parameters: Dict[str, Any],
                                        output_dir: str) -> Dict[str, Any]:
        """Create workflow configuration for iteration"""
        # Deep copy main config
        iter_config = json.loads(json.dumps(self.main_config))
        
        # Update job output directory
        iter_config['job_output_dir'] = output_dir
        
        # Convert parameters to modification configuration
        mod_configs = self.feedback.convert_calibration_to_modification(
            parameters, output_dir
        )
        
        # Update modification config
        if 'modification' not in iter_config:
            iter_config['modification'] = {}
        
        iter_config['modification']['perform_modification'] = True
        iter_config['modification']['scenario_file'] = mod_configs.get('scenario')
        
        # Ensure post-modification steps are enabled
        iter_config['modification']['post_modification'] = {
            'run_simulations': True,
            'parse_results': True
        }
        
        # Enable validation
        iter_config['validation']['perform_validation'] = True
        
        return iter_config
    
    def _prepare_next_iteration(self, 
                              current_params: Dict[str, Any],
                              current_metrics: Dict[str, float]):
        """Prepare configuration for next iteration"""
        # Analyze parameter sensitivity
        param_history = self.feedback.track_parameter_evolution(
            self.controller.current_iteration
        )
        
        if not param_history.empty:
            # Get metrics history
            metrics_history = self._get_metrics_history()
            
            # Calculate sensitivity
            sensitivity_scores = self.feedback.analyze_parameter_sensitivity(
                param_history, metrics_history
            )
            
            # Log sensitivity analysis
            logger.info("Parameter sensitivity scores:")
            for param, score in sorted(sensitivity_scores.items(), 
                                     key=lambda x: x[1], reverse=True):
                logger.info(f"  {param}: {score:.3f}")
    
    def _get_metrics_history(self) -> pd.DataFrame:
        """Get metrics history as DataFrame"""
        import pandas as pd
        
        metrics_data = []
        for metric in self.controller.iteration_history:
            metrics_data.append({
                'iteration': metric.iteration_id,
                'cv_rmse': metric.cv_rmse,
                'rmse': metric.rmse,
                'r2': metric.r2
            })
        
        return pd.DataFrame(metrics_data).set_index('iteration')


def integrate_iteration_system(orchestrator_main):
    """
    Decorator to integrate iteration system into orchestrator
    """
    def wrapped_orchestrator(job_config: dict, cancel_event=None):
        # Check if iteration is enabled
        main_config = job_config.get('main_config', {})
        iteration_config = main_config.get('iteration', {})
        
        if not iteration_config.get('enabled', False):
            # Run normal orchestrator
            return orchestrator_main(job_config, cancel_event)
        
        # Run orchestrator with iteration support
        logger.info("Iteration system enabled - wrapping orchestrator")
        
        # Create adapter
        job_output_dir = job_config.get('job_output_dir')
        adapter = OrchestratorIterationAdapter(main_config, job_output_dir)
        
        # Define workflow executor
        def workflow_executor(config):
            # Update job_config with iteration config
            job_config['main_config'] = config
            return orchestrator_main(job_config, cancel_event)
        
        # Run initial workflow
        logger.info("Running initial workflow (baseline)")
        initial_results = orchestrator_main(job_config, cancel_event)
        
        # Run iteration loop
        if adapter.should_run_iterations():
            logger.info("Starting iteration loop")
            final_results = adapter.run_iteration_loop(
                initial_results, 
                workflow_executor
            )
            
            # Merge results
            initial_results['iteration_results'] = final_results
            
            # Save iteration summary
            summary_path = Path(job_output_dir) / "iteration_summary.json"
            with open(summary_path, 'w') as f:
                json.dump(final_results, f, indent=2, default=str)
            
            logger.info(f"Iteration summary saved to {summary_path}")
        
        return initial_results
    
    return wrapped_orchestrator