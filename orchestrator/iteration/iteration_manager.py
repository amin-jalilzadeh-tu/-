"""
Iteration Manager for E_Plus_2040 Workflow

Manages the iterative improvement process for building simulations
based on validation results and performance metrics.
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class IterationManager:
    """Manages workflow iterations based on performance metrics"""
    
    def __init__(self, config: dict, job_output_dir: str):
        self.config = config
        self.job_output_dir = Path(job_output_dir)
        self.iteration_config = config.get('iteration_control', {})
        
        self.current_iteration = 0
        self.max_iterations = self.iteration_config.get('max_iterations', 5)
        self.performance_history = []
        self.selected_buildings_history = {}
        
        self.logger = logging.getLogger(__name__)
        self._setup_directories()
        
    def _setup_directories(self):
        """Create directory structure for iteration tracking"""
        self.iterations_dir = self.job_output_dir / "iterations"
        self.tracking_dir = self.job_output_dir / "tracking"
        
        self.iterations_dir.mkdir(exist_ok=True)
        self.tracking_dir.mkdir(exist_ok=True)
        
    def get_iteration_dir(self, iteration: int = None) -> Path:
        """Get directory for specific iteration"""
        if iteration is None:
            iteration = self.current_iteration
        return self.iterations_dir / f"iteration_{iteration}"
        
    def should_continue(self) -> bool:
        """Check if iterations should continue"""
        if self.current_iteration >= self.max_iterations:
            self.logger.info(f"Reached maximum iterations ({self.max_iterations})")
            return False
            
        if self.current_iteration > 0:
            converged, reason = self.check_convergence()
            if converged:
                self.logger.info(f"Convergence reached: {reason}")
                return False
                
        return True
        
    def check_convergence(self) -> Tuple[bool, str]:
        """Check if convergence criteria are met"""
        if len(self.performance_history) < 2:
            return False, "Not enough iterations"
            
        criteria = self.iteration_config.get('convergence_criteria', {})
        min_improvement = criteria.get('min_improvement', 0.01)
        patience = criteria.get('patience', 2)
        
        # Check recent improvements
        recent_improvements = []
        for i in range(1, min(patience + 1, len(self.performance_history))):
            if i < len(self.performance_history):
                prev = self.performance_history[-i-1]
                curr = self.performance_history[-i]
                improvement = (prev['avg_error'] - curr['avg_error']) / prev['avg_error']
                recent_improvements.append(improvement)
                
        # Check if all recent improvements are below threshold
        if all(imp < min_improvement for imp in recent_improvements):
            return True, f"No significant improvement in last {patience} iterations"
            
        return False, "Convergence not reached"
        
    def select_buildings(self, validation_results: pd.DataFrame) -> List[str]:
        """Select buildings for next iteration based on validation results"""
        strategy = self.iteration_config.get('selection_strategy', 'validation_failure')
        count = self.iteration_config.get('selection_count', 10)
        
        self.logger.info(f"Selecting {count} buildings using strategy: {strategy}")
        
        if strategy == 'validation_failure':
            # Select buildings that failed validation
            failed = validation_results[validation_results['validation_passed'] == False]
            if len(failed) == 0:
                # If no failures, select worst performers
                selected = validation_results.nlargest(count, 'cvrmse')
            else:
                selected = failed.nlargest(min(count, len(failed)), 'cvrmse')
                
        elif strategy == 'worst_performers':
            # Select buildings with highest error metrics
            selected = validation_results.nlargest(count, 'cvrmse')
            
        elif strategy == 'least_improved':
            # Select buildings that improved least (requires history)
            if self.current_iteration == 0:
                # First iteration, use worst performers
                selected = validation_results.nlargest(count, 'cvrmse')
            else:
                # Calculate improvements and select least improved
                improvements = self._calculate_improvements(validation_results)
                selected = improvements.nsmallest(count, 'improvement')
                
        else:
            raise ValueError(f"Unknown selection strategy: {strategy}")
            
        building_ids = selected['building_id'].tolist()
        self.selected_buildings_history[self.current_iteration + 1] = building_ids
        
        # Save selection info
        selection_info = {
            'iteration': self.current_iteration + 1,
            'strategy': strategy,
            'selected_buildings': building_ids,
            'selection_metrics': selected.to_dict('records')
        }
        
        selection_path = self.get_iteration_dir(self.current_iteration + 1) / "selected_buildings.json"
        selection_path.parent.mkdir(exist_ok=True)
        with open(selection_path, 'w') as f:
            json.dump(selection_info, f, indent=2)
            
        return building_ids
        
    def _calculate_improvements(self, current_results: pd.DataFrame) -> pd.DataFrame:
        """Calculate improvement from previous iteration"""
        if self.current_iteration == 0:
            return current_results
            
        # Load previous iteration results
        prev_path = self.get_iteration_dir(self.current_iteration - 1) / "validation_summary.parquet"
        if prev_path.exists():
            prev_results = pd.read_parquet(prev_path)
            
            # Merge and calculate improvements
            merged = current_results.merge(
                prev_results[['building_id', 'cvrmse']], 
                on='building_id', 
                suffixes=('_current', '_prev')
            )
            merged['improvement'] = (merged['cvrmse_prev'] - merged['cvrmse_current']) / merged['cvrmse_prev']
            
            return merged[['building_id', 'improvement', 'cvrmse_current']]
        else:
            self.logger.warning("Previous results not found, using current results")
            current_results['improvement'] = 0
            return current_results
            
    def get_modification_intensity(self) -> str:
        """Get modification intensity for current iteration"""
        progression = self.iteration_config.get('modification_progression', {})
        
        # Default progression if not specified
        default_progression = {
            'iteration_1': {'intensity': 'low'},
            'iteration_2': {'intensity': 'medium'},
            'iteration_3': {'intensity': 'high'},
            'iteration_4': {'intensity': 'high'},
            'iteration_5': {'intensity': 'extreme'}
        }
        
        iteration_key = f'iteration_{self.current_iteration + 1}'
        if iteration_key in progression:
            return progression[iteration_key].get('intensity', 'medium')
        elif iteration_key in default_progression:
            return default_progression[iteration_key]['intensity']
        else:
            return 'high'  # Default to high for later iterations
            
    def record_iteration_performance(self, validation_summary: pd.DataFrame):
        """Record performance metrics for current iteration"""
        metrics = {
            'iteration': self.current_iteration,
            'timestamp': datetime.now().isoformat(),
            'num_buildings': len(validation_summary),
            'num_passed': len(validation_summary[validation_summary['validation_passed'] == True]),
            'avg_cvrmse': validation_summary['cvrmse'].mean(),
            'avg_nmbe': validation_summary['nmbe'].mean(),
            'avg_error': validation_summary['cvrmse'].mean(),  # For convergence checking
            'min_cvrmse': validation_summary['cvrmse'].min(),
            'max_cvrmse': validation_summary['cvrmse'].max()
        }
        
        self.performance_history.append(metrics)
        
        # Save performance history
        history_path = self.tracking_dir / "performance_history.json"
        with open(history_path, 'w') as f:
            json.dump(self.performance_history, f, indent=2)
            
        # Also save as DataFrame for analysis
        df = pd.DataFrame(self.performance_history)
        df.to_parquet(self.tracking_dir / "performance_history.parquet")
        
    def save_iteration_summary(self):
        """Save summary of current iteration"""
        summary = {
            'current_iteration': self.current_iteration,
            'max_iterations': self.max_iterations,
            'performance_history': self.performance_history,
            'selected_buildings_history': self.selected_buildings_history,
            'convergence_status': self.check_convergence() if self.current_iteration > 0 else (False, "First iteration")
        }
        
        summary_path = self.tracking_dir / "iteration_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
            
    def increment_iteration(self):
        """Move to next iteration"""
        self.current_iteration += 1
        self.logger.info(f"Starting iteration {self.current_iteration}")
        
    def get_base_data_path(self) -> Path:
        """Get path to base (iteration 0) parsed data"""
        return self.get_iteration_dir(0) / "parsed_data"
        
    def get_previous_best_results(self, building_id: str) -> Optional[Dict]:
        """Get best performing results for a building across iterations"""
        best_results = None
        best_metric = float('inf')
        
        for i in range(self.current_iteration + 1):
            results_path = self.get_iteration_dir(i) / "validation_summary.parquet"
            if results_path.exists():
                df = pd.read_parquet(results_path)
                building_data = df[df['building_id'] == building_id]
                if not building_data.empty:
                    cvrmse = building_data['cvrmse'].iloc[0]
                    if cvrmse < best_metric:
                        best_metric = cvrmse
                        best_results = {
                            'iteration': i,
                            'cvrmse': cvrmse,
                            'data': building_data.iloc[0].to_dict()
                        }
                        
        return best_results