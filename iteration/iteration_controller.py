import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class IterationStatus(Enum):
    """Status of an iteration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CONVERGED = "converged"
    HUMAN_REVIEW = "human_review"


@dataclass
class IterationMetrics:
    """Metrics for a single iteration"""
    iteration_id: int
    timestamp: datetime
    rmse: float
    cv_rmse: float
    nmbe: float
    r2: float
    parameter_changes: Dict[str, float]
    convergence_score: float
    status: IterationStatus
    notes: str = ""


@dataclass
class IterationConfig:
    """Configuration for iteration control"""
    strategy: str = "convergence_based"  # fixed_iterations, convergence_based, adaptive, human_guided
    max_iterations: int = 10
    min_iterations: int = 3
    convergence_tolerance: float = 0.01
    convergence_metric: str = "cv_rmse"  # rmse, cv_rmse, nmbe, r2, combined
    check_interval: int = 1
    parallel_variants: int = 5
    learning_rate: float = 0.1
    human_review_threshold: float = 0.05
    store_all_iterations: bool = True
    resume_from_iteration: Optional[int] = None


class IterationController:
    """
    Controls the iteration loop for calibration workflow
    """
    
    def __init__(self, job_id: str, config_path: Optional[str] = None):
        self.job_id = job_id
        self.base_dir = Path(f"iterations/{job_id}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create configuration
        self.config = self._load_config(config_path)
        
        # Initialize iteration tracking
        self.current_iteration = 0
        self.iteration_history: List[IterationMetrics] = []
        self.best_parameters: Optional[Dict[str, Any]] = None
        self.best_metrics: Optional[IterationMetrics] = None
        
        # State management
        self.state_file = self.base_dir / "iteration_state.json"
        self._load_state()
        
    def _load_config(self, config_path: Optional[str]) -> IterationConfig:
        """Load iteration configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                return IterationConfig(**config_data.get('iteration', {}))
        return IterationConfig()
    
    def _load_state(self):
        """Load previous iteration state if exists"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.current_iteration = state.get('current_iteration', 0)
                self.best_parameters = state.get('best_parameters')
                # Reconstruct iteration history
                for metric_data in state.get('iteration_history', []):
                    metric_data['timestamp'] = datetime.fromisoformat(metric_data['timestamp'])
                    metric_data['status'] = IterationStatus(metric_data['status'])
                    self.iteration_history.append(IterationMetrics(**metric_data))
    
    def _save_state(self):
        """Save current iteration state"""
        state = {
            'job_id': self.job_id,
            'current_iteration': self.current_iteration,
            'best_parameters': self.best_parameters,
            'iteration_history': [
                {
                    **asdict(m),
                    'timestamp': m.timestamp.isoformat(),
                    'status': m.status.value
                }
                for m in self.iteration_history
            ]
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def should_continue(self) -> bool:
        """Determine if iteration should continue"""
        if self.current_iteration >= self.config.max_iterations:
            logger.info(f"Reached maximum iterations: {self.config.max_iterations}")
            return False
        
        if self.current_iteration < self.config.min_iterations:
            return True
        
        # Check convergence based on strategy
        if self.config.strategy == "fixed_iterations":
            return self.current_iteration < self.config.max_iterations
        
        elif self.config.strategy == "convergence_based":
            return not self._check_convergence()
        
        elif self.config.strategy == "adaptive":
            return self._check_adaptive_continuation()
        
        elif self.config.strategy == "human_guided":
            return self._check_human_decision()
        
        return True
    
    def _check_convergence(self) -> bool:
        """Check if convergence criteria are met"""
        if len(self.iteration_history) < 2:
            return False
        
        # Get recent metrics
        recent_metrics = self.iteration_history[-self.config.check_interval:]
        metric_name = self.config.convergence_metric
        
        # Calculate change in metric
        metric_values = [getattr(m, metric_name) for m in recent_metrics]
        metric_change = abs(metric_values[-1] - metric_values[0])
        
        converged = metric_change < self.config.convergence_tolerance
        
        if converged:
            logger.info(f"Convergence achieved: {metric_name} change = {metric_change:.4f}")
        
        return converged
    
    def _check_adaptive_continuation(self) -> bool:
        """Adaptive strategy for continuation"""
        if len(self.iteration_history) < 3:
            return True
        
        # Analyze improvement trend
        recent_metrics = self.iteration_history[-3:]
        improvements = []
        
        for i in range(1, len(recent_metrics)):
            prev = recent_metrics[i-1].cv_rmse
            curr = recent_metrics[i].cv_rmse
            improvement = (prev - curr) / prev if prev > 0 else 0
            improvements.append(improvement)
        
        # Continue if still improving significantly
        avg_improvement = np.mean(improvements)
        return avg_improvement > 0.001  # 0.1% improvement threshold
    
    def _check_human_decision(self) -> bool:
        """Check if human review is needed"""
        if len(self.iteration_history) == 0:
            return True
        
        last_metric = self.iteration_history[-1]
        
        # Request human review if performance is below threshold
        if last_metric.cv_rmse > self.config.human_review_threshold:
            last_metric.status = IterationStatus.HUMAN_REVIEW
            self._save_state()
            logger.info("Human review requested - performance below threshold")
            return False  # Pause for human input
        
        return True
    
    def start_iteration(self) -> Dict[str, Any]:
        """Start a new iteration"""
        self.current_iteration += 1
        logger.info(f"Starting iteration {self.current_iteration}")
        
        # Create iteration directory
        iter_dir = self.base_dir / f"iteration_{self.current_iteration:03d}"
        iter_dir.mkdir(exist_ok=True)
        
        # Prepare parameters for this iteration
        if self.best_parameters:
            # Use best parameters from previous iteration
            parameters = self._adapt_parameters(self.best_parameters)
        else:
            # Use initial parameters
            parameters = self._get_initial_parameters()
        
        # Save iteration config
        iter_config = {
            'iteration': self.current_iteration,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat(),
            'previous_best': None
        }
        
        # Handle previous best metrics serialization
        if self.best_metrics:
            best_dict = asdict(self.best_metrics)
            best_dict['timestamp'] = best_dict['timestamp'].isoformat()
            best_dict['status'] = best_dict['status'].value
            iter_config['previous_best'] = best_dict
        
        with open(iter_dir / 'iteration_config.json', 'w') as f:
            json.dump(iter_config, f, indent=2)
        
        return {
            'iteration': self.current_iteration,
            'parameters': parameters,
            'output_dir': str(iter_dir)
        }
    
    def complete_iteration(self, metrics: Dict[str, float], 
                         parameters: Dict[str, Any],
                         status: IterationStatus = IterationStatus.COMPLETED):
        """Complete current iteration with results"""
        # Calculate convergence score
        convergence_score = self._calculate_convergence_score(metrics)
        
        # Record iteration metrics
        iteration_metrics = IterationMetrics(
            iteration_id=self.current_iteration,
            timestamp=datetime.now(),
            rmse=metrics.get('rmse', float('inf')),
            cv_rmse=metrics.get('cv_rmse', float('inf')),
            nmbe=metrics.get('nmbe', float('inf')),
            r2=metrics.get('r2', 0.0),
            parameter_changes=self._calculate_parameter_changes(parameters),
            convergence_score=convergence_score,
            status=status
        )
        
        self.iteration_history.append(iteration_metrics)
        
        # Update best results if improved
        if self._is_better_result(iteration_metrics):
            self.best_metrics = iteration_metrics
            self.best_parameters = parameters
            logger.info(f"New best result found in iteration {self.current_iteration}")
        
        # Save state
        self._save_state()
        
        # Save detailed results
        self._save_iteration_results(iteration_metrics, parameters)
    
    def _calculate_convergence_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall convergence score"""
        # Weighted combination of metrics
        weights = {
            'cv_rmse': 0.4,
            'rmse': 0.3,
            'nmbe': 0.2,
            'r2': 0.1
        }
        
        score = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                if metric == 'r2':
                    # R2 is better when higher
                    score += weight * metrics[metric]
                else:
                    # Other metrics are better when lower
                    score += weight * (1.0 / (1.0 + metrics[metric]))
        
        return score
    
    def _is_better_result(self, metrics: IterationMetrics) -> bool:
        """Check if current result is better than best"""
        if not self.best_metrics:
            return True
        
        # Compare primary metric
        metric_name = self.config.convergence_metric
        current_value = getattr(metrics, metric_name)
        best_value = getattr(self.best_metrics, metric_name)
        
        if metric_name == 'r2':
            return current_value > best_value
        else:
            return current_value < best_value
    
    def _calculate_parameter_changes(self, parameters: Dict[str, Any]) -> Dict[str, float]:
        """Calculate parameter changes from previous iteration"""
        if not self.best_parameters:
            return {k: 0.0 for k in parameters.keys()}
        
        changes = {}
        for key, value in parameters.items():
            if key in self.best_parameters:
                old_value = self.best_parameters[key]
                if isinstance(value, (int, float)) and isinstance(old_value, (int, float)):
                    change = abs(value - old_value) / (abs(old_value) + 1e-10)
                    changes[key] = change
                else:
                    changes[key] = 0.0 if value == old_value else 1.0
            else:
                changes[key] = 1.0
        
        return changes
    
    def _adapt_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt parameters for next iteration based on learning"""
        # This is a placeholder for more sophisticated adaptation logic
        # Could implement gradient-based updates, genetic algorithms, etc.
        
        adapted = parameters.copy()
        
        # Example: Apply small random perturbations with learning rate
        if self.config.learning_rate > 0:
            for key, value in adapted.items():
                if isinstance(value, (int, float)):
                    # Add controlled noise
                    noise = np.random.normal(0, self.config.learning_rate)
                    adapted[key] = value * (1 + noise)
        
        return adapted
    
    def _get_initial_parameters(self) -> Dict[str, Any]:
        """Get initial parameters for first iteration"""
        # This should be loaded from configuration or previous runs
        # Placeholder implementation
        return {
            'infiltration_rate': 0.5,
            'window_u_value': 2.0,
            'wall_insulation': 0.05,
            'hvac_efficiency': 0.85
        }
    
    def _save_iteration_results(self, metrics: IterationMetrics, parameters: Dict[str, Any]):
        """Save detailed results for iteration"""
        iter_dir = self.base_dir / f"iteration_{self.current_iteration:03d}"
        
        # Save metrics
        with open(iter_dir / 'metrics.json', 'w') as f:
            json.dump(asdict(metrics), f, indent=2, default=str)
        
        # Save parameters
        with open(iter_dir / 'parameters.json', 'w') as f:
            json.dump(parameters, f, indent=2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of iteration history"""
        if not self.iteration_history:
            return {'status': 'no_iterations_completed'}
        
        metrics_df = pd.DataFrame([asdict(m) for m in self.iteration_history])
        
        summary = {
            'total_iterations': self.current_iteration,
            'best_iteration': self.best_metrics.iteration_id if self.best_metrics else None,
            'best_metrics': asdict(self.best_metrics) if self.best_metrics else None,
            'convergence_achieved': any(m.status == IterationStatus.CONVERGED for m in self.iteration_history),
            'metric_trends': {
                'cv_rmse': metrics_df['cv_rmse'].tolist(),
                'rmse': metrics_df['rmse'].tolist(),
                'r2': metrics_df['r2'].tolist()
            },
            'status': self.iteration_history[-1].status.value if self.iteration_history else 'not_started'
        }
        
        return summary
    
    def export_results(self, output_path: str):
        """Export iteration results to file"""
        summary = self.get_summary()
        summary['best_parameters'] = self.best_parameters
        summary['config'] = asdict(self.config)
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Iteration results exported to {output_path}")