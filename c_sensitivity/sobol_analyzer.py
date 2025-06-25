"""
c_sensitivity/sobol_analyzer.py

Proper Sobol variance-based sensitivity analysis implementation.
Includes first-order, higher-order, and total effect indices.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from scipy import stats
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class SobolAnalyzer:
    """
    Performs variance-based Sobol sensitivity analysis.
    
    Features:
    - First-order Sobol indices
    - Second and higher-order interaction indices
    - Total effect indices
    - Multiple sampling strategies (Saltelli, Latin Hypercube)
    - Confidence intervals via bootstrap
    
    Example usage:
        analyzer = SobolAnalyzer(data_manager, logger)
        config = {
            'calc_second_order': True,
            'n_samples': 1024,  # Should be power of 2 for Sobol
            'sampling_method': 'saltelli',
            'confidence_level': 0.95,
            'bootstrap_samples': 100
        }
        results = analyzer.analyze(X, y, parameter_bounds, config)
    """
    
    def __init__(self, data_manager, logger: Optional[logging.Logger] = None):
        self.data_manager = data_manager
        self.logger = logger or logging.getLogger(__name__)
        
    def analyze(self,
                X: pd.DataFrame,
                y: pd.DataFrame,
                parameter_bounds: Dict[str, Tuple[float, float]],
                config: Dict[str, Any]) -> pd.DataFrame:
        """
        Perform Sobol sensitivity analysis.
        
        Args:
            X: Input parameters DataFrame (can be used for bounds estimation)
            y: Output variables DataFrame
            parameter_bounds: Dictionary of (min, max) bounds for each parameter
            config: Analysis configuration
            
        Returns:
            DataFrame with Sobol indices
        """
        self.logger.info("Starting Sobol sensitivity analysis...")
        
        n_samples = config.get('n_samples', 1024)
        calc_second_order = config.get('calc_second_order', False)
        sampling_method = config.get('sampling_method', 'saltelli')
        confidence_level = config.get('confidence_level', 0.95)
        bootstrap_samples = config.get('bootstrap_samples', 100)
        
        # Get parameter names and bounds
        param_names = list(parameter_bounds.keys())
        n_params = len(param_names)
        
        # Generate samples
        self.logger.info(f"Generating {sampling_method} samples...")
        if sampling_method == 'saltelli':
            samples = self._saltelli_sampling(parameter_bounds, n_samples, calc_second_order)
        elif sampling_method == 'latin_hypercube':
            samples = self._latin_hypercube_sampling(parameter_bounds, n_samples)
        else:
            samples = self._saltelli_sampling(parameter_bounds, n_samples, calc_second_order)
        
        # Evaluate model at sample points
        self.logger.info("Evaluating model at sample points...")
        model_outputs = self._evaluate_model(samples, param_names, X, y)
        
        results = []
        
        # Calculate Sobol indices for each output
        for output_name, output_values in model_outputs.items():
            self.logger.debug(f"Calculating Sobol indices for {output_name}")
            
            # First-order indices
            first_order = self._calculate_first_order_indices(
                output_values, n_params, calc_second_order
            )
            
            # Total effect indices
            total_effects = self._calculate_total_effect_indices(
                output_values, n_params, calc_second_order
            )
            
            # Bootstrap confidence intervals
            if bootstrap_samples > 0:
                first_ci = self._bootstrap_confidence_intervals(
                    output_values, n_params, 'first', 
                    bootstrap_samples, confidence_level, calc_second_order
                )
                total_ci = self._bootstrap_confidence_intervals(
                    output_values, n_params, 'total', 
                    bootstrap_samples, confidence_level, calc_second_order
                )
            else:
                first_ci = {i: (0, 0) for i in range(n_params)}
                total_ci = {i: (0, 0) for i in range(n_params)}
            
            # Store first-order results
            for i, param in enumerate(param_names):
                results.append({
                    'parameter': param,
                    'output_variable': output_name,
                    'sensitivity_score': first_order[i],
                    'method': 'sobol_first_order',
                    'sobol_index': first_order[i],
                    'sobol_type': 'first_order',
                    'total_effect': total_effects[i],
                    'confidence_lower': first_ci[i][0],
                    'confidence_upper': first_ci[i][1],
                    'confidence_level': confidence_level,
                    'n_samples': n_samples
                })
            
            # Second-order indices if requested
            if calc_second_order:
                second_order = self._calculate_second_order_indices(
                    output_values, n_params
                )
                
                for i in range(n_params):
                    for j in range(i + 1, n_params):
                        results.append({
                            'parameter': f"{param_names[i]}*{param_names[j]}",
                            'output_variable': output_name,
                            'sensitivity_score': second_order[i, j],
                            'method': 'sobol_second_order',
                            'sobol_index': second_order[i, j],
                            'sobol_type': 'second_order',
                            'param1': param_names[i],
                            'param2': param_names[j],
                            'n_samples': n_samples
                        })
        
        df_results = pd.DataFrame(results)
        
        # Add variance decomposition summary
        if not df_results.empty:
            df_results = self._add_variance_decomposition(df_results)
        
        return df_results
    
    def _saltelli_sampling(self,
                         parameter_bounds: Dict[str, Tuple[float, float]],
                         n_samples: int,
                         calc_second_order: bool) -> np.ndarray:
        """Generate samples using Saltelli's extension of Sobol sequence"""
        
        n_params = len(parameter_bounds)
        
        # Total samples needed
        if calc_second_order:
            n_total = n_samples * (2 * n_params + 2)
        else:
            n_total = n_samples * (n_params + 2)
        
        # Generate base samples using Sobol sequence (simplified)
        # In practice, use proper Sobol sequence generator
        base_samples = self._generate_sobol_sequence(n_samples, 2 * n_params)
        
        # Create sample matrices
        A = base_samples[:, :n_params]
        B = base_samples[:, n_params:]
        
        # Create additional matrices for sensitivity calculation
        samples = []
        samples.append(A)  # Base matrix A
        samples.append(B)  # Base matrix B
        
        # Create matrices where one column comes from B, rest from A
        for i in range(n_params):
            AB_i = A.copy()
            AB_i[:, i] = B[:, i]
            samples.append(AB_i)
        
        if calc_second_order:
            # Create matrices where two columns come from B
            for i in range(n_params):
                BA_i = B.copy()
                BA_i[:, i] = A[:, i]
                samples.append(BA_i)
        
        # Combine all samples
        all_samples = np.vstack(samples)
        
        # Scale to parameter bounds
        param_names = list(parameter_bounds.keys())
        for i, param in enumerate(param_names):
            min_val, max_val = parameter_bounds[param]
            all_samples[:, i] = all_samples[:, i] * (max_val - min_val) + min_val
        
        return all_samples
    
    def _latin_hypercube_sampling(self,
                                parameter_bounds: Dict[str, Tuple[float, float]],
                                n_samples: int) -> np.ndarray:
        """Generate samples using Latin Hypercube Sampling"""
        
        n_params = len(parameter_bounds)
        
        # Create Latin Hypercube samples
        samples = np.zeros((n_samples, n_params))
        
        for i in range(n_params):
            # Create stratified samples
            cuts = np.linspace(0, 1, n_samples + 1)
            u = np.random.uniform(cuts[:-1], cuts[1:])
            np.random.shuffle(u)
            samples[:, i] = u
        
        # Scale to parameter bounds
        param_names = list(parameter_bounds.keys())
        for i, param in enumerate(param_names):
            min_val, max_val = parameter_bounds[param]
            samples[:, i] = samples[:, i] * (max_val - min_val) + min_val
        
        return samples
    
    def _generate_sobol_sequence(self, n_samples: int, n_dims: int) -> np.ndarray:
        """
        Generate Sobol sequence (simplified implementation).
        In practice, use a proper Sobol sequence generator.
        """
        # Simplified: use quasi-random uniform samples
        samples = np.zeros((n_samples, n_dims))
        
        # Simple Halton sequence as approximation
        for dim in range(n_dims):
            base = self._get_prime(dim + 1)
            samples[:, dim] = self._halton_sequence(n_samples, base)
        
        return samples
    
    def _get_prime(self, n: int) -> int:
        """Get nth prime number"""
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        return primes[min(n - 1, len(primes) - 1)]
    
    def _halton_sequence(self, n: int, base: int) -> np.ndarray:
        """Generate Halton sequence"""
        sequence = np.zeros(n)
        for i in range(n):
            f = 1
            r = 0
            idx = i + 1
            while idx > 0:
                f = f / base
                r = r + f * (idx % base)
                idx = idx // base
            sequence[i] = r
        return sequence
    
    def _evaluate_model(self,
                       samples: np.ndarray,
                       param_names: List[str],
                       X_data: pd.DataFrame,
                       y_data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Evaluate model at sample points.
        This is a simplified surrogate evaluation.
        """
        model_outputs = {}
        
        # For each output variable
        for output_col in y_data.select_dtypes(include=[np.number]).columns:
            output_values = np.zeros(len(samples))
            
            # Simple linear interpolation as surrogate
            # In practice, use actual model or trained surrogate
            for i, sample in enumerate(samples):
                # Find nearest neighbors in original data
                distances = np.zeros(len(X_data))
                
                for j, param in enumerate(param_names):
                    if param in X_data.columns:
                        param_std = X_data[param].std()
                        if param_std > 0:
                            distances += ((X_data[param] - sample[j]) / param_std) ** 2
                
                # Use weighted average of k nearest neighbors
                k = min(5, len(X_data))
                nearest_idx = np.argsort(distances)[:k]
                weights = 1 / (distances[nearest_idx] + 1e-10)
                weights /= weights.sum()
                
                output_values[i] = np.average(y_data.iloc[nearest_idx][output_col], weights=weights)
            
            model_outputs[output_col] = output_values
        
        return model_outputs
    
    def _calculate_first_order_indices(self,
                                     y: np.ndarray,
                                     n_params: int,
                                     calc_second_order: bool) -> np.ndarray:
        """Calculate first-order Sobol indices"""
        
        if calc_second_order:
            n_samples = len(y) // (2 * n_params + 2)
        else:
            n_samples = len(y) // (n_params + 2)
        
        # Extract matrices
        f_A = y[:n_samples]
        f_B = y[n_samples:2*n_samples]
        
        # Variance of output
        var_y = np.var(np.concatenate([f_A, f_B]))
        
        # First-order indices
        S = np.zeros(n_params)
        
        for i in range(n_params):
            f_AB_i = y[(2 + i) * n_samples:(3 + i) * n_samples]
            
            # Estimate first-order effect
            S[i] = np.mean(f_B * (f_AB_i - f_A)) / var_y
            
            # Ensure non-negative
            S[i] = max(0, S[i])
        
        return S
    
    def _calculate_total_effect_indices(self,
                                      y: np.ndarray,
                                      n_params: int,
                                      calc_second_order: bool) -> np.ndarray:
        """Calculate total effect Sobol indices"""
        
        if calc_second_order:
            n_samples = len(y) // (2 * n_params + 2)
        else:
            n_samples = len(y) // (n_params + 2)
        
        # Extract matrices
        f_A = y[:n_samples]
        f_B = y[n_samples:2*n_samples]
        
        # Variance of output
        var_y = np.var(np.concatenate([f_A, f_B]))
        
        # Total effect indices
        S_T = np.zeros(n_params)
        
        for i in range(n_params):
            if calc_second_order:
                # Use BA_i matrix
                f_BA_i = y[(2 + n_params + i) * n_samples:(3 + n_params + i) * n_samples]
                
                # Total effect calculation
                S_T[i] = 1 - np.mean(f_B * (f_BA_i - f_A)) / var_y
            else:
                # Use AB_i matrix for approximation
                f_AB_i = y[(2 + i) * n_samples:(3 + i) * n_samples]
                
                # Approximate total effect
                S_T[i] = np.mean((f_A - f_AB_i) ** 2) / (2 * var_y)
            
            # Ensure valid range
            S_T[i] = np.clip(S_T[i], 0, 1)
        
        return S_T
    
    def _calculate_second_order_indices(self,
                                      y: np.ndarray,
                                      n_params: int) -> np.ndarray:
        """Calculate second-order interaction Sobol indices"""
        
        n_samples = len(y) // (2 * n_params + 2)
        
        # Extract matrices
        f_A = y[:n_samples]
        f_B = y[n_samples:2*n_samples]
        
        # Variance of output
        var_y = np.var(np.concatenate([f_A, f_B]))
        
        # Get first-order indices
        S_first = self._calculate_first_order_indices(y, n_params, True)
        
        # Second-order indices
        S_ij = np.zeros((n_params, n_params))
        
        for i in range(n_params):
            for j in range(i + 1, n_params):
                # Get relevant matrices
                f_AB_i = y[(2 + i) * n_samples:(3 + i) * n_samples]
                f_AB_j = y[(2 + j) * n_samples:(3 + j) * n_samples]
                
                # Second-order effect
                V_ij = np.mean(f_AB_i * f_AB_j) - np.mean(f_A) * np.mean(f_B)
                S_ij_total = V_ij / var_y
                
                # Remove first-order effects
                S_ij[i, j] = S_ij_total - S_first[i] - S_first[j]
                S_ij[i, j] = max(0, S_ij[i, j])
                S_ij[j, i] = S_ij[i, j]  # Symmetric
        
        return S_ij
    
    def _bootstrap_confidence_intervals(self,
                                      y: np.ndarray,
                                      n_params: int,
                                      index_type: str,
                                      n_bootstrap: int,
                                      confidence_level: float,
                                      calc_second_order: bool) -> Dict[int, Tuple[float, float]]:
        """Calculate bootstrap confidence intervals for Sobol indices"""
        
        bootstrap_indices = []
        
        if calc_second_order:
            n_samples = len(y) // (2 * n_params + 2)
        else:
            n_samples = len(y) // (n_params + 2)
        
        for _ in range(n_bootstrap):
            # Resample with replacement
            idx = np.random.choice(n_samples, n_samples, replace=True)
            
            # Reconstruct y with bootstrap samples
            y_boot = []
            
            # Add resampled matrices
            for matrix_idx in range(2 + n_params + (n_params if calc_second_order else 0)):
                start_idx = matrix_idx * n_samples
                y_boot.extend(y[start_idx + idx])
            
            y_boot = np.array(y_boot)
            
            # Calculate indices
            if index_type == 'first':
                indices = self._calculate_first_order_indices(
                    y_boot, n_params, calc_second_order
                )
            else:  # total
                indices = self._calculate_total_effect_indices(
                    y_boot, n_params, calc_second_order
                )
            
            bootstrap_indices.append(indices)
        
        # Calculate confidence intervals
        bootstrap_indices = np.array(bootstrap_indices)
        alpha = 1 - confidence_level
        
        ci = {}
        for i in range(n_params):
            ci[i] = (
                np.percentile(bootstrap_indices[:, i], 100 * alpha / 2),
                np.percentile(bootstrap_indices[:, i], 100 * (1 - alpha / 2))
            )
        
        return ci
    
    def _add_variance_decomposition(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add variance decomposition summary to results"""
        
        # Calculate total variance explained
        for output in df['output_variable'].unique():
            output_mask = df['output_variable'] == output
            
            # Sum of first-order indices
            first_order_mask = output_mask & (df['sobol_type'] == 'first_order')
            first_order_sum = df.loc[first_order_mask, 'sobol_index'].sum()
            
            # Add to dataframe
            df.loc[output_mask, 'first_order_sum'] = first_order_sum
            
            # Calculate interaction effects
            if 'second_order' in df['sobol_type'].values:
                second_order_mask = output_mask & (df['sobol_type'] == 'second_order')
                second_order_sum = df.loc[second_order_mask, 'sobol_index'].sum()
                df.loc[output_mask, 'interaction_effects'] = second_order_sum
            else:
                df.loc[output_mask, 'interaction_effects'] = 0
            
            # Higher-order effects (unexplained variance)
            df.loc[output_mask, 'higher_order_effects'] = max(
                0, 1 - first_order_sum - df.loc[output_mask, 'interaction_effects'].iloc[0]
            )
        
        return df