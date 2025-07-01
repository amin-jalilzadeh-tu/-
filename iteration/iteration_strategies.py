import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for iteration strategies"""
    name: str
    max_iterations: int = 10
    min_iterations: int = 3
    convergence_tolerance: float = 0.01
    improvement_threshold: float = 0.001
    stagnation_limit: int = 3
    exploration_rate: float = 0.2
    exploitation_rate: float = 0.8
    adaptive_learning_rate: bool = True


class IterationStrategy(ABC):
    """Base class for iteration strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.iteration_count = 0
        self.convergence_history = []
        self.parameter_history = []
        
    @abstractmethod
    def should_continue(self, metrics: Dict[str, float], 
                       parameters: Dict[str, Any]) -> bool:
        """Determine if iteration should continue"""
        pass
    
    @abstractmethod
    def adapt_parameters(self, current_params: Dict[str, Any],
                        metrics: Dict[str, float]) -> Dict[str, Any]:
        """Adapt parameters for next iteration"""
        pass
    
    def update_history(self, metrics: Dict[str, float], 
                      parameters: Dict[str, Any]):
        """Update iteration history"""
        self.iteration_count += 1
        self.convergence_history.append(metrics)
        self.parameter_history.append(parameters)


class FixedIterationStrategy(IterationStrategy):
    """Simple fixed number of iterations"""
    
    def should_continue(self, metrics: Dict[str, float], 
                       parameters: Dict[str, Any]) -> bool:
        self.update_history(metrics, parameters)
        return self.iteration_count < self.config.max_iterations
    
    def adapt_parameters(self, current_params: Dict[str, Any],
                        metrics: Dict[str, float]) -> Dict[str, Any]:
        """Simple random perturbation"""
        adapted = current_params.copy()
        
        for key, value in adapted.items():
            if isinstance(value, (int, float)):
                # Random walk with decreasing step size
                step_size = 0.1 * (1 - self.iteration_count / self.config.max_iterations)
                perturbation = np.random.normal(0, step_size)
                adapted[key] = value * (1 + perturbation)
        
        return adapted


class ConvergenceBasedStrategy(IterationStrategy):
    """Continue until convergence criteria met"""
    
    def should_continue(self, metrics: Dict[str, float], 
                       parameters: Dict[str, Any]) -> bool:
        self.update_history(metrics, parameters)
        
        if self.iteration_count < self.config.min_iterations:
            return True
        
        if self.iteration_count >= self.config.max_iterations:
            return False
        
        # Check convergence
        if len(self.convergence_history) >= 2:
            current_metric = metrics.get('cv_rmse', float('inf'))
            previous_metric = self.convergence_history[-2].get('cv_rmse', float('inf'))
            
            improvement = abs(previous_metric - current_metric) / (previous_metric + 1e-10)
            
            if improvement < self.config.convergence_tolerance:
                logger.info(f"Convergence achieved: improvement = {improvement:.6f}")
                return False
        
        return True
    
    def adapt_parameters(self, current_params: Dict[str, Any],
                        metrics: Dict[str, float]) -> Dict[str, Any]:
        """Gradient-based adaptation"""
        adapted = current_params.copy()
        
        if len(self.parameter_history) >= 2:
            # Calculate parameter gradients
            prev_params = self.parameter_history[-2]
            prev_metrics = self.convergence_history[-2]
            
            current_performance = metrics.get('cv_rmse', float('inf'))
            prev_performance = prev_metrics.get('cv_rmse', float('inf'))
            
            performance_change = prev_performance - current_performance  # Positive is good
            
            for key, value in adapted.items():
                if isinstance(value, (int, float)) and key in prev_params:
                    param_change = value - prev_params[key]
                    
                    if abs(param_change) > 1e-10:
                        # Estimate gradient
                        gradient = performance_change / param_change
                        
                        # Update parameter in direction of gradient
                        learning_rate = 0.1 * (1 - self.iteration_count / self.config.max_iterations)
                        adapted[key] = value + learning_rate * gradient * abs(value)
        else:
            # First iteration - random exploration
            for key, value in adapted.items():
                if isinstance(value, (int, float)):
                    adapted[key] = value * (1 + np.random.normal(0, 0.1))
        
        return adapted


class AdaptiveStrategy(IterationStrategy):
    """Adaptive strategy that balances exploration and exploitation"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.stagnation_count = 0
        self.best_metric = float('inf')
        self.exploration_phase = True
        
    def should_continue(self, metrics: Dict[str, float], 
                       parameters: Dict[str, Any]) -> bool:
        self.update_history(metrics, parameters)
        
        if self.iteration_count < self.config.min_iterations:
            return True
        
        if self.iteration_count >= self.config.max_iterations:
            return False
        
        current_metric = metrics.get('cv_rmse', float('inf'))
        
        # Check for improvement
        if current_metric < self.best_metric * (1 - self.config.improvement_threshold):
            self.best_metric = current_metric
            self.stagnation_count = 0
        else:
            self.stagnation_count += 1
        
        # Stop if stagnated
        if self.stagnation_count >= self.config.stagnation_limit:
            logger.info(f"Stopping due to stagnation ({self.stagnation_count} iterations without improvement)")
            return False
        
        # Switch between exploration and exploitation
        if self.stagnation_count >= 2:
            self.exploration_phase = True
        elif current_metric < self.best_metric * 1.1:  # Within 10% of best
            self.exploration_phase = False
        
        return True
    
    def adapt_parameters(self, current_params: Dict[str, Any],
                        metrics: Dict[str, float]) -> Dict[str, Any]:
        """Adaptive parameter adjustment"""
        adapted = current_params.copy()
        
        if self.exploration_phase:
            # Exploration: larger random changes
            logger.info("Exploration phase: making larger parameter changes")
            for key, value in adapted.items():
                if isinstance(value, (int, float)):
                    change = np.random.normal(0, self.config.exploration_rate)
                    adapted[key] = value * (1 + change)
        else:
            # Exploitation: smaller, directed changes
            logger.info("Exploitation phase: fine-tuning parameters")
            if len(self.parameter_history) >= 2:
                # Find best performing parameters
                best_idx = np.argmin([m.get('cv_rmse', float('inf')) 
                                     for m in self.convergence_history])
                best_params = self.parameter_history[best_idx]
                
                # Move towards best parameters with noise
                for key, value in adapted.items():
                    if isinstance(value, (int, float)) and key in best_params:
                        target = best_params[key]
                        noise = np.random.normal(0, self.config.exploitation_rate * 0.1)
                        adapted[key] = value + (target - value) * self.config.exploitation_rate + noise
            else:
                # Fallback to small random changes
                for key, value in adapted.items():
                    if isinstance(value, (int, float)):
                        adapted[key] = value * (1 + np.random.normal(0, 0.05))
        
        return adapted


class HumanGuidedStrategy(IterationStrategy):
    """Strategy that incorporates human decisions"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.human_feedback = None
        self.awaiting_human_input = False
        
    def should_continue(self, metrics: Dict[str, float], 
                       parameters: Dict[str, Any]) -> bool:
        self.update_history(metrics, parameters)
        
        if self.iteration_count >= self.config.max_iterations:
            return False
        
        current_metric = metrics.get('cv_rmse', float('inf'))
        
        # Check if human review is needed
        if current_metric > 0.15 or self.iteration_count % 3 == 0:
            self.awaiting_human_input = True
            logger.info(f"Human review requested at iteration {self.iteration_count}")
            logger.info(f"Current CV-RMSE: {current_metric:.4f}")
            
            # In real implementation, this would pause and wait for human input
            # For testing, we'll simulate human decision
            self.human_feedback = self._simulate_human_decision(metrics, parameters)
            
            if self.human_feedback.get('stop', False):
                logger.info("Human decided to stop iterations")
                return False
        
        return True
    
    def adapt_parameters(self, current_params: Dict[str, Any],
                        metrics: Dict[str, float]) -> Dict[str, Any]:
        """Adapt parameters based on human guidance"""
        adapted = current_params.copy()
        
        if self.human_feedback and 'parameter_suggestions' in self.human_feedback:
            # Apply human suggestions
            suggestions = self.human_feedback['parameter_suggestions']
            for key, value in suggestions.items():
                if key in adapted:
                    adapted[key] = value
            logger.info("Applied human parameter suggestions")
        else:
            # Automated adjustment with conservative changes
            for key, value in adapted.items():
                if isinstance(value, (int, float)):
                    # Smaller changes when human is involved
                    change = np.random.normal(0, 0.05)
                    adapted[key] = value * (1 + change)
        
        self.human_feedback = None
        return adapted
    
    def _simulate_human_decision(self, metrics: Dict[str, float], 
                               parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate human decision for testing"""
        cv_rmse = metrics.get('cv_rmse', float('inf'))
        
        # Simulated human logic
        if cv_rmse < 0.05:
            return {'stop': True, 'reason': 'Acceptable performance achieved'}
        elif cv_rmse > 0.20:
            # Suggest significant parameter changes
            return {
                'stop': False,
                'parameter_suggestions': {
                    key: value * 1.2 if np.random.random() > 0.5 else value * 0.8
                    for key, value in parameters.items()
                    if isinstance(value, (int, float))
                }
            }
        else:
            # Continue with minor adjustments
            return {'stop': False}


class HybridStrategy(IterationStrategy):
    """Combines multiple strategies"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.strategies = {
            'convergence': ConvergenceBasedStrategy(config),
            'adaptive': AdaptiveStrategy(config)
        }
        self.active_strategy = 'adaptive'
        
    def should_continue(self, metrics: Dict[str, float], 
                       parameters: Dict[str, Any]) -> bool:
        self.update_history(metrics, parameters)
        
        # Switch strategies based on performance
        if self.iteration_count > 5:
            cv_rmse_trend = [m.get('cv_rmse', float('inf')) 
                           for m in self.convergence_history[-3:]]
            
            if len(cv_rmse_trend) == 3:
                # If improvement is slowing, switch to convergence-based
                improvements = [cv_rmse_trend[i-1] - cv_rmse_trend[i] 
                              for i in range(1, len(cv_rmse_trend))]
                avg_improvement = np.mean(improvements)
                
                if avg_improvement < 0.001:
                    self.active_strategy = 'convergence'
                else:
                    self.active_strategy = 'adaptive'
        
        # Use active strategy
        return self.strategies[self.active_strategy].should_continue(metrics, parameters)
    
    def adapt_parameters(self, current_params: Dict[str, Any],
                        metrics: Dict[str, float]) -> Dict[str, Any]:
        """Use active strategy for parameter adaptation"""
        return self.strategies[self.active_strategy].adapt_parameters(current_params, metrics)


def create_strategy(strategy_name: str, config: Optional[StrategyConfig] = None) -> IterationStrategy:
    """Factory function to create iteration strategies"""
    if config is None:
        config = StrategyConfig(name=strategy_name)
    
    strategies = {
        'fixed': FixedIterationStrategy,
        'convergence': ConvergenceBasedStrategy,
        'adaptive': AdaptiveStrategy,
        'human_guided': HumanGuidedStrategy,
        'hybrid': HybridStrategy
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategies.keys())}")
    
    return strategies[strategy_name](config)