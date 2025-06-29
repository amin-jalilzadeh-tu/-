"""
calibration_objectives.py

Advanced objective functions for calibration including:
- Multi-metric support (RMSE, MAE, CVRMSE, R2, MAPE)
- Time-based error calculation
- Peak error metrics
- Multi-objective optimization support
- Custom weighted objectives

Author: Your Team
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Union, Tuple, Callable, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CalibrationObjective:
    """Base class for calibration objectives"""
    
    def __init__(self, 
                 target_variable: str,
                 metric: str = "rmse",
                 weight: float = 1.0,
                 tolerance: Optional[float] = None,
                 time_slice_config: Optional[Dict] = None):
        """
        Args:
            target_variable: Variable to calibrate (e.g., "Heating:EnergyTransfer [J](Hourly)")
            metric: Error metric to use
            weight: Weight for multi-objective optimization
            tolerance: Target tolerance for the metric
            time_slice_config: Time filtering configuration
        """
        self.target_variable = target_variable
        self.metric = metric.lower()
        self.weight = weight
        self.tolerance = tolerance
        self.time_slice_config = time_slice_config
        
        # Validate metric
        valid_metrics = ["rmse", "mae", "cvrmse", "r2", "mape", "peak_error", 
                        "peak_relative_error", "nmbe", "cv", "weighted_rmse"]
        if self.metric not in valid_metrics:
            raise ValueError(f"Unknown metric '{metric}'. Valid metrics: {valid_metrics}")
    
    def calculate(self, simulated: np.ndarray, observed: np.ndarray) -> float:
        """Calculate the objective value"""
        if self.metric == "rmse":
            return self._rmse(simulated, observed)
        elif self.metric == "mae":
            return self._mae(simulated, observed)
        elif self.metric == "cvrmse":
            return self._cvrmse(simulated, observed)
        elif self.metric == "r2":
            return 1.0 - self._r2(simulated, observed)  # Minimize 1-R2
        elif self.metric == "mape":
            return self._mape(simulated, observed)
        elif self.metric == "peak_error":
            return self._peak_error(simulated, observed)
        elif self.metric == "peak_relative_error":
            return self._peak_relative_error(simulated, observed)
        elif self.metric == "nmbe":
            return abs(self._nmbe(simulated, observed))
        elif self.metric == "cv":
            return self._cv(simulated, observed)
        elif self.metric == "weighted_rmse":
            return self._weighted_rmse(simulated, observed)
        else:
            raise ValueError(f"Metric '{self.metric}' not implemented")
    
    @staticmethod
    def _rmse(sim: np.ndarray, obs: np.ndarray) -> float:
        """Root Mean Square Error"""
        return np.sqrt(np.mean((sim - obs) ** 2))
    
    @staticmethod
    def _mae(sim: np.ndarray, obs: np.ndarray) -> float:
        """Mean Absolute Error"""
        return np.mean(np.abs(sim - obs))
    
    @staticmethod
    def _cvrmse(sim: np.ndarray, obs: np.ndarray) -> float:
        """Coefficient of Variation of RMSE (%)"""
        rmse = CalibrationObjective._rmse(sim, obs)
        mean_obs = np.mean(obs)
        if mean_obs == 0:
            return float('inf')
        return (rmse / mean_obs) * 100
    
    @staticmethod
    def _r2(sim: np.ndarray, obs: np.ndarray) -> float:
        """R-squared (coefficient of determination)"""
        ss_res = np.sum((obs - sim) ** 2)
        ss_tot = np.sum((obs - np.mean(obs)) ** 2)
        if ss_tot == 0:
            return 0.0
        return 1 - (ss_res / ss_tot)
    
    @staticmethod
    def _mape(sim: np.ndarray, obs: np.ndarray) -> float:
        """Mean Absolute Percentage Error (%)"""
        mask = obs != 0
        if not np.any(mask):
            return float('inf')
        return np.mean(np.abs((obs[mask] - sim[mask]) / obs[mask])) * 100
    
    @staticmethod
    def _peak_error(sim: np.ndarray, obs: np.ndarray) -> float:
        """Maximum absolute error"""
        return np.max(np.abs(sim - obs))
    
    @staticmethod
    def _peak_relative_error(sim: np.ndarray, obs: np.ndarray) -> float:
        """Maximum relative error (%)"""
        mask = obs != 0
        if not np.any(mask):
            return float('inf')
        rel_errors = np.abs((obs[mask] - sim[mask]) / obs[mask]) * 100
        return np.max(rel_errors)
    
    @staticmethod
    def _nmbe(sim: np.ndarray, obs: np.ndarray) -> float:
        """Normalized Mean Bias Error (%)"""
        mean_obs = np.mean(obs)
        if mean_obs == 0:
            return float('inf')
        return (np.mean(sim - obs) / mean_obs) * 100
    
    @staticmethod
    def _cv(sim: np.ndarray, obs: np.ndarray) -> float:
        """Coefficient of Variation (%)"""
        residuals = sim - obs
        mean_obs = np.mean(obs)
        if mean_obs == 0:
            return float('inf')
        return (np.std(residuals) / mean_obs) * 100
    
    @staticmethod
    def _weighted_rmse(sim: np.ndarray, obs: np.ndarray) -> float:
        """Weighted RMSE giving more importance to peak values"""
        # Weight by magnitude of observed values
        weights = obs / np.max(obs) if np.max(obs) > 0 else np.ones_like(obs)
        weighted_errors = weights * (sim - obs) ** 2
        return np.sqrt(np.mean(weighted_errors))


class MultiObjectiveFunction:
    """Handles multiple objectives for calibration"""
    
    def __init__(self, objectives: List[CalibrationObjective]):
        self.objectives = objectives
        
    def calculate_all(self, simulated_dict: Dict[str, np.ndarray], 
                     observed_dict: Dict[str, np.ndarray]) -> List[float]:
        """
        Calculate all objective values
        
        Returns:
            List of objective values (for multi-objective optimization)
        """
        objective_values = []
        
        for obj in self.objectives:
            if obj.target_variable not in simulated_dict:
                logger.warning(f"Target variable {obj.target_variable} not found in simulated data")
                objective_values.append(float('inf'))
                continue
            
            if obj.target_variable not in observed_dict:
                logger.warning(f"Target variable {obj.target_variable} not found in observed data")
                objective_values.append(float('inf'))
                continue
            
            sim = simulated_dict[obj.target_variable]
            obs = observed_dict[obj.target_variable]
            
            # Ensure same shape
            min_len = min(len(sim), len(obs))
            sim = sim[:min_len]
            obs = obs[:min_len]
            
            value = obj.calculate(sim, obs)
            objective_values.append(value)
        
        return objective_values
    
    def calculate_weighted_sum(self, simulated_dict: Dict[str, np.ndarray], 
                              observed_dict: Dict[str, np.ndarray]) -> float:
        """
        Calculate weighted sum of objectives (for single-objective optimization)
        """
        objective_values = self.calculate_all(simulated_dict, observed_dict)
        
        # Normalize weights
        total_weight = sum(obj.weight for obj in self.objectives)
        
        weighted_sum = 0.0
        for i, (obj, value) in enumerate(zip(self.objectives, objective_values)):
            if value == float('inf'):
                return float('inf')
            
            normalized_weight = obj.weight / total_weight
            weighted_sum += normalized_weight * value
        
        return weighted_sum
    
    def check_tolerances(self, simulated_dict: Dict[str, np.ndarray], 
                        observed_dict: Dict[str, np.ndarray]) -> Tuple[bool, Dict[str, float]]:
        """
        Check if all objectives meet their tolerance thresholds
        
        Returns:
            (all_met, metrics_dict)
        """
        metrics = {}
        all_met = True
        
        for obj in self.objectives:
            if obj.target_variable not in simulated_dict or obj.target_variable not in observed_dict:
                metrics[f"{obj.target_variable}_{obj.metric}"] = float('inf')
                all_met = False
                continue
            
            sim = simulated_dict[obj.target_variable]
            obs = observed_dict[obj.target_variable]
            
            value = obj.calculate(sim, obs)
            metrics[f"{obj.target_variable}_{obj.metric}"] = value
            
            if obj.tolerance is not None and value > obj.tolerance:
                all_met = False
        
        return all_met, metrics


def create_ashrae_objectives(variables: List[str], 
                            hourly_cvrmse: float = 30.0,
                            monthly_nmbe: float = 10.0) -> MultiObjectiveFunction:
    """
    Create objectives based on ASHRAE Guideline 14 criteria
    
    Args:
        variables: List of variables to calibrate
        hourly_cvrmse: Target CV(RMSE) for hourly data (%)
        monthly_nmbe: Target NMBE for monthly data (%)
    """
    objectives = []
    
    for var in variables:
        # Hourly CVRMSE
        objectives.append(CalibrationObjective(
            target_variable=var,
            metric="cvrmse",
            weight=0.6,
            tolerance=hourly_cvrmse
        ))
        
        # Monthly NMBE (would need monthly aggregation in practice)
        objectives.append(CalibrationObjective(
            target_variable=var,
            metric="nmbe",
            weight=0.4,
            tolerance=monthly_nmbe
        ))
    
    return MultiObjectiveFunction(objectives)


def create_peak_focused_objectives(variables: List[str],
                                  peak_weight: float = 0.7) -> MultiObjectiveFunction:
    """
    Create objectives that focus on matching peak loads
    """
    objectives = []
    
    for var in variables:
        # Peak error
        objectives.append(CalibrationObjective(
            target_variable=var,
            metric="peak_relative_error",
            weight=peak_weight
        ))
        
        # Overall RMSE
        objectives.append(CalibrationObjective(
            target_variable=var,
            metric="rmse",
            weight=1.0 - peak_weight
        ))
    
    return MultiObjectiveFunction(objectives)


def apply_time_filter_to_data(data: Dict[str, pd.DataFrame], 
                             time_slice_config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Apply time filtering to data dictionary
    
    Args:
        data: Dictionary of variable_name -> time series DataFrame
        time_slice_config: Time filtering configuration
    
    Returns:
        Filtered data dictionary
    """
    # Import here to avoid circular imports
    from cal.time_slice_utils import filter_results_by_time_slice, apply_predefined_slice
    
    filtered_data = {}
    
    for var_name, df in data.items():
        if time_slice_config.get("method") == "predefined":
            slice_name = time_slice_config.get("predefined_slice", "peak_cooling_months")
            filtered_df = apply_predefined_slice(df, slice_name)
        elif time_slice_config.get("method") == "custom":
            custom_config = time_slice_config.get("custom_config", {})
            filtered_df = filter_results_by_time_slice(df, custom_config)
        else:
            filtered_df = df
        
        filtered_data[var_name] = filtered_df
    
    return filtered_data


class TimeBasedObjective(CalibrationObjective):
    """Objective that applies time-based filtering before calculation"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def calculate_with_time_filter(self, 
                                  simulated_df: pd.DataFrame, 
                                  observed_df: pd.DataFrame) -> float:
        """
        Calculate objective with time filtering applied
        
        Args:
            simulated_df: DataFrame with time columns
            observed_df: DataFrame with time columns
        """
        if self.time_slice_config:
            # Apply time filtering
            from cal.time_slice_utils import filter_results_by_time_slice, apply_predefined_slice
            
            if self.time_slice_config.get("method") == "predefined":
                slice_name = self.time_slice_config.get("predefined_slice")
                simulated_df = apply_predefined_slice(simulated_df, slice_name)
                observed_df = apply_predefined_slice(observed_df, slice_name)
            elif self.time_slice_config.get("method") == "custom":
                custom_config = self.time_slice_config.get("custom_config", {})
                simulated_df = filter_results_by_time_slice(simulated_df, custom_config)
                observed_df = filter_results_by_time_slice(observed_df, custom_config)
        
        # Extract values after filtering
        sim_values = simulated_df.select_dtypes(include=[np.number]).values.flatten()
        obs_values = observed_df.select_dtypes(include=[np.number]).values.flatten()
        
        return self.calculate(sim_values, obs_values)


def create_seasonal_objectives(variables: List[str]) -> List[MultiObjectiveFunction]:
    """
    Create separate objective functions for each season
    
    Returns:
        List of MultiObjectiveFunction, one per season
    """
    seasons = {
        "winter": {"months": [12, 1, 2]},
        "spring": {"months": [3, 4, 5]},
        "summer": {"months": [6, 7, 8]},
        "fall": {"months": [9, 10, 11]}
    }
    
    seasonal_objectives = []
    
    for season_name, season_config in seasons.items():
        objectives = []
        
        for var in variables:
            # Create time-based objective for this season
            obj = TimeBasedObjective(
                target_variable=var,
                metric="cvrmse",
                weight=1.0,
                time_slice_config={
                    "method": "custom",
                    "custom_config": season_config
                }
            )
            objectives.append(obj)
        
        seasonal_objectives.append(MultiObjectiveFunction(objectives))
    
    return seasonal_objectives