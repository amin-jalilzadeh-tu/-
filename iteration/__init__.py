"""
Iteration System for E_Plus_2040
Manages calibration iteration loops with parameter feedback and convergence control
"""

from .iteration_controller import IterationController, IterationConfig, IterationStatus, IterationMetrics
from .parameter_feedback import ParameterFeedback
from .iteration_strategies import (
    create_strategy, 
    IterationStrategy, 
    StrategyConfig,
    FixedIterationStrategy,
    ConvergenceBasedStrategy,
    AdaptiveStrategy,
    HumanGuidedStrategy,
    HybridStrategy
)
from .parameter_store import ParameterStore, ParameterVersion

__all__ = [
    'IterationController',
    'IterationConfig',
    'IterationStatus',
    'IterationMetrics',
    'ParameterFeedback',
    'create_strategy',
    'IterationStrategy',
    'StrategyConfig',
    'ParameterStore',
    'ParameterVersion'
]

__version__ = '1.0.0'