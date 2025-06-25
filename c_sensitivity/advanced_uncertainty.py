"""
c_sensitivity/advanced_uncertainty.py

Advanced uncertainty quantification for sensitivity analysis including
Monte Carlo propagation, confidence bounds, and scenario analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from scipy import stats
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


@dataclass
class UncertaintyConfig:
    """Configuration for uncertainty analysis"""
    n_samples: int = 1000
    confidence_level: float = 0.95
    parameter_distributions: Dict[str, Dict[str, Any]] = None
    scenario_weights: Dict[str, float] = None
    bootstrap_iterations: int = 100
    propagation_method: str = 'monte_carlo'  # 'monte_carlo' or 'analytical'


class UncertaintyAnalyzer:
    """
    Performs advanced uncertainty quantification for sensitivity analysis.
    
    Features:
    - Monte Carlo uncertainty propagation
    - Confidence bounds on sensitivity indices
    - Scenario-based uncertainty analysis
    - Bayesian uncertainty quantification
    
    Example usage:
        analyzer = UncertaintyAnalyzer(data_manager, logger)
        config = UncertaintyConfig(n_samples=1000, confidence_level=0.95)
        results = analyzer.analyze(X, y, base_sensitivity_df, config)
    """
    
    def __init__(self, data_manager, logger: Optional[logging.Logger] = None):
        self.data_manager = data_manager
        self.logger = logger or logging.getLogger(__name__)
        
    def analyze(self, 
                X: pd.DataFrame, 
                y: pd.DataFrame,
                base_sensitivity_df: pd.DataFrame,
                config: Union[Dict[str, Any], UncertaintyConfig]) -> pd.DataFrame:
        """
        Perform uncertainty analysis on sensitivity results.
        
        Args:
            X: Input parameters DataFrame
            y: Output variables DataFrame
            base_sensitivity_df: Base sensitivity results to add uncertainty to
            config: Uncertainty analysis configuration
            
        Returns:
            DataFrame with uncertainty bounds added to sensitivity results
        """
        if isinstance(config, dict):
            config = UncertaintyConfig(**config)
            
        self.logger.info(f"Starting uncertainty analysis with {config.n_samples} samples")
        
        results = []
        
        # Group by parameter-output pairs
        for (param, output), group in base_sensitivity_df.groupby(['parameter', 'output_variable']):
            base_score = group['sensitivity_score'].mean()
            
            # Perform uncertainty propagation
            if config.propagation_method == 'monte_carlo':
                uncertainty_bounds = self._monte_carlo_propagation(
                    X, y, param, output, base_score, config
                )
            else:
                uncertainty_bounds = self._analytical_propagation(
                    X, y, param, output, base_score, config
                )
            
            # Add scenario analysis if configured
            if config.scenario_weights:
                scenario_results = self._scenario_analysis(
                    X, y, param, output, config
                )
                uncertainty_bounds['scenario_mean'] = scenario_results['mean']
                uncertainty_bounds['scenario_std'] = scenario_results['std']
            
            # Create result record
            result = {
                'parameter': param,
                'output_variable': output,
                'sensitivity_score': base_score,
                'method': 'uncertainty_propagation',
                'uncertainty_lower': uncertainty_bounds['lower'],
                'uncertainty_upper': uncertainty_bounds['upper'],
                'uncertainty_std': uncertainty_bounds['std'],
                'confidence_level': config.confidence_level,
                'n_uncertainty_samples': config.n_samples
            }
            
            # Add additional fields from original
            for col in group.columns:
                if col not in result:
                    result[col] = group[col].iloc[0]
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def _monte_carlo_propagation(self,
                                X: pd.DataFrame,
                                y: pd.DataFrame,
                                param: str,
                                output: str,
                                base_score: float,
                                config: UncertaintyConfig) -> Dict[str, float]:
        """Propagate uncertainty using Monte Carlo sampling"""
        
        sensitivity_samples = []
        
        for i in range(config.n_samples):
            # Sample parameters based on distributions
            X_sampled = self._sample_parameters(X, config.parameter_distributions)
            
            # Add noise to outputs
            y_sampled = self._add_output_noise(y, output)
            
            # Calculate sensitivity for this sample
            if param in X_sampled.columns and output in y_sampled.columns:
                # Simple correlation as sensitivity measure
                corr = X_sampled[param].corr(y_sampled[output])
                sensitivity_samples.append(abs(corr) if not np.isnan(corr) else 0)
        
        # Calculate confidence bounds
        if sensitivity_samples:
            alpha = 1 - config.confidence_level
            lower = np.percentile(sensitivity_samples, 100 * alpha / 2)
            upper = np.percentile(sensitivity_samples, 100 * (1 - alpha / 2))
            std = np.std(sensitivity_samples)
        else:
            lower = upper = base_score
            std = 0
        
        return {
            'lower': lower,
            'upper': upper,
            'std': std,
            'mean': np.mean(sensitivity_samples) if sensitivity_samples else base_score
        }
    
    def _analytical_propagation(self,
                              X: pd.DataFrame,
                              y: pd.DataFrame,
                              param: str,
                              output: str,
                              base_score: float,
                              config: UncertaintyConfig) -> Dict[str, float]:
        """Analytical uncertainty propagation using error propagation formulas"""
        
        # Estimate parameter uncertainty
        param_std = X[param].std() if param in X.columns else 0.1 * abs(X[param].mean())
        
        # Estimate output uncertainty
        output_std = y[output].std() if output in y.columns else 0.1 * abs(y[output].mean())
        
        # Simple analytical propagation formula
        # Assumes independence and small uncertainties
        relative_param_uncertainty = param_std / (X[param].mean() + 1e-10) if param in X.columns else 0.1
        relative_output_uncertainty = output_std / (y[output].mean() + 1e-10) if output in y.columns else 0.1
        
        # Propagated relative uncertainty
        relative_sensitivity_uncertainty = np.sqrt(
            relative_param_uncertainty**2 + relative_output_uncertainty**2
        )
        
        # Convert to absolute uncertainty
        sensitivity_std = base_score * relative_sensitivity_uncertainty
        
        # Calculate bounds
        z_score = stats.norm.ppf(1 - (1 - config.confidence_level) / 2)
        lower = base_score - z_score * sensitivity_std
        upper = base_score + z_score * sensitivity_std
        
        return {
            'lower': max(0, lower),  # Sensitivity can't be negative
            'upper': upper,
            'std': sensitivity_std,
            'mean': base_score
        }
    
    def _sample_parameters(self,
                         X: pd.DataFrame,
                         distributions: Optional[Dict[str, Dict[str, Any]]]) -> pd.DataFrame:
        """Sample parameters from specified distributions"""
        X_sampled = X.copy()
        
        if not distributions:
            # Default: Add Gaussian noise
            for col in X_sampled.select_dtypes(include=[np.number]).columns:
                noise = np.random.normal(0, 0.05 * X_sampled[col].std(), len(X_sampled))
                X_sampled[col] = X_sampled[col] + noise
        else:
            # Sample from specified distributions
            for param, dist_info in distributions.items():
                if param in X_sampled.columns:
                    dist_type = dist_info.get('type', 'normal')
                    
                    if dist_type == 'normal':
                        mean = dist_info.get('mean', X_sampled[param].mean())
                        std = dist_info.get('std', X_sampled[param].std())
                        X_sampled[param] = np.random.normal(mean, std, len(X_sampled))
                    elif dist_type == 'uniform':
                        low = dist_info.get('low', X_sampled[param].min())
                        high = dist_info.get('high', X_sampled[param].max())
                        X_sampled[param] = np.random.uniform(low, high, len(X_sampled))
                    elif dist_type == 'lognormal':
                        mean = dist_info.get('mean', np.log(X_sampled[param].mean()))
                        std = dist_info.get('std', 0.1)
                        X_sampled[param] = np.random.lognormal(mean, std, len(X_sampled))
        
        return X_sampled
    
    def _add_output_noise(self, y: pd.DataFrame, output: str) -> pd.DataFrame:
        """Add realistic noise to output variables"""
        y_noisy = y.copy()
        
        if output in y_noisy.columns:
            # Add 5% Gaussian noise
            noise_level = 0.05 * y_noisy[output].std()
            noise = np.random.normal(0, noise_level, len(y_noisy))
            y_noisy[output] = y_noisy[output] + noise
        
        return y_noisy
    
    def _scenario_analysis(self,
                         X: pd.DataFrame,
                         y: pd.DataFrame,
                         param: str,
                         output: str,
                         config: UncertaintyConfig) -> Dict[str, float]:
        """Analyze sensitivity under different scenarios"""
        
        scenario_sensitivities = []
        
        for scenario, weight in config.scenario_weights.items():
            # Apply scenario-specific transformations
            X_scenario = self._apply_scenario(X, scenario)
            y_scenario = self._apply_scenario(y, scenario)
            
            # Calculate sensitivity for this scenario
            if param in X_scenario.columns and output in y_scenario.columns:
                corr = X_scenario[param].corr(y_scenario[output])
                if not np.isnan(corr):
                    scenario_sensitivities.append({
                        'scenario': scenario,
                        'sensitivity': abs(corr),
                        'weight': weight
                    })
        
        if scenario_sensitivities:
            # Weighted average
            weighted_mean = sum(
                s['sensitivity'] * s['weight'] for s in scenario_sensitivities
            ) / sum(s['weight'] for s in scenario_sensitivities)
            
            # Weighted standard deviation
            weighted_var = sum(
                s['weight'] * (s['sensitivity'] - weighted_mean)**2 
                for s in scenario_sensitivities
            ) / sum(s['weight'] for s in scenario_sensitivities)
            
            weighted_std = np.sqrt(weighted_var)
        else:
            weighted_mean = 0
            weighted_std = 0
        
        return {
            'mean': weighted_mean,
            'std': weighted_std,
            'scenarios': scenario_sensitivities
        }
    
    def _apply_scenario(self, df: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """Apply scenario-specific transformations to data"""
        df_scenario = df.copy()
        
        # Example scenario transformations
        if scenario == 'high_efficiency':
            # Reduce energy consumption by 20%
            energy_cols = [col for col in df_scenario.columns if 'Energy' in col]
            for col in energy_cols:
                df_scenario[col] = df_scenario[col] * 0.8
        elif scenario == 'climate_change':
            # Increase cooling, decrease heating
            cooling_cols = [col for col in df_scenario.columns if 'Cooling' in col]
            heating_cols = [col for col in df_scenario.columns if 'Heating' in col]
            for col in cooling_cols:
                df_scenario[col] = df_scenario[col] * 1.2
            for col in heating_cols:
                df_scenario[col] = df_scenario[col] * 0.9
        elif scenario == 'extreme_weather':
            # Increase variability
            for col in df_scenario.select_dtypes(include=[np.number]).columns:
                noise = np.random.normal(0, 0.2 * df_scenario[col].std(), len(df_scenario))
                df_scenario[col] = df_scenario[col] + noise
        
        return df_scenario
    
    def bayesian_uncertainty(self,
                           X: pd.DataFrame,
                           y: pd.DataFrame,
                           prior_sensitivity: pd.DataFrame,
                           config: UncertaintyConfig) -> pd.DataFrame:
        """
        Bayesian approach to uncertainty quantification.
        Updates prior beliefs about sensitivity with observed data.
        """
        results = []
        
        for (param, output), prior_group in prior_sensitivity.groupby(['parameter', 'output_variable']):
            # Prior parameters
            prior_mean = prior_group['sensitivity_score'].mean()
            prior_std = prior_group['sensitivity_score'].std() if len(prior_group) > 1 else prior_mean * 0.2
            
            # Calculate likelihood from data
            if param in X.columns and output in y.columns:
                observed_corr = abs(X[param].corr(y[output]))
                likelihood_std = 0.1  # Assumed measurement error
                
                # Bayesian update (conjugate prior for normal distribution)
                posterior_precision = 1/prior_std**2 + 1/likelihood_std**2
                posterior_mean = (prior_mean/prior_std**2 + observed_corr/likelihood_std**2) / posterior_precision
                posterior_std = np.sqrt(1/posterior_precision)
                
                # Credible interval
                z_score = stats.norm.ppf(1 - (1 - config.confidence_level) / 2)
                lower = posterior_mean - z_score * posterior_std
                upper = posterior_mean + z_score * posterior_std
            else:
                posterior_mean = prior_mean
                posterior_std = prior_std
                lower = prior_mean - 2 * prior_std
                upper = prior_mean + 2 * prior_std
            
            results.append({
                'parameter': param,
                'output_variable': output,
                'sensitivity_score': posterior_mean,
                'method': 'bayesian_uncertainty',
                'prior_mean': prior_mean,
                'posterior_mean': posterior_mean,
                'posterior_std': posterior_std,
                'credible_lower': max(0, lower),
                'credible_upper': upper,
                'confidence_level': config.confidence_level
            })
        
        return pd.DataFrame(results)