"""
c_sensitivity/statistical_methods.py

Advanced statistical methods for sensitivity analysis.
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.feature_selection import mutual_info_regression
import warnings
from typing import Dict, List, Tuple, Optional, Any, Union
import logging

warnings.filterwarnings('ignore', category=FutureWarning)


class StatisticalMethods:
    """Collection of statistical methods for sensitivity analysis"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.scaler = StandardScaler()
        
        # Import advanced analyzers for routing
        self._advanced_analyzers = None
    
    def _get_advanced_analyzers(self):
        """Lazy load advanced analyzers to avoid circular imports"""
        if self._advanced_analyzers is None:
            self._advanced_analyzers = {
                'uncertainty': None,
                'threshold': None,
                'regional': None,
                'sobol': None,
                'temporal': None
            }
        return self._advanced_analyzers
    
    def calculate_sensitivity(self, 
                            X: pd.DataFrame, 
                            y: pd.DataFrame,
                            method: str = 'correlation',
                            config: Optional[Dict[str, Any]] = None,
                            **kwargs) -> pd.DataFrame:
        """
        Main entry point for sensitivity calculation with routing to advanced methods
        
        Args:
            X: Input parameters
            y: Output variables
            method: Method name (existing or advanced)
            config: Configuration dictionary
            **kwargs: Additional method-specific arguments
            
        Returns:
            DataFrame with sensitivity results
        """
        # Check if this is an advanced method
        if method in ['uncertainty', 'threshold', 'regional', 'sobol', 'temporal']:
            return self._route_to_advanced_analyzer(X, y, method, config, **kwargs)
        
        # Otherwise use existing methods
        if method == 'correlation':
            return self.correlation_analysis(X, y, **kwargs)
        elif method == 'regression':
            return self.regression_analysis(X, y, **kwargs)
        elif method == 'mutual_info':
            return self.mutual_information_analysis(X, y, **kwargs)
        elif method == 'random_forest':
            return self.random_forest_importance(X, y, **kwargs)
        elif method == 'elasticity':
            return self.elasticity_analysis(X, y, **kwargs)
        elif method == 'bootstrap':
            return self.bootstrap_analysis(X, y, **kwargs)
        else:
            self.logger.warning(f"Unknown method: {method}, defaulting to correlation")
            return self.correlation_analysis(X, y, **kwargs)
    
    def _route_to_advanced_analyzer(self,
                                   X: pd.DataFrame,
                                   y: pd.DataFrame,
                                   method: str,
                                   config: Optional[Dict[str, Any]] = None,
                                   **kwargs) -> pd.DataFrame:
        """Route to advanced analyzer modules"""
        try:
            if method == 'uncertainty':
                from .advanced_uncertainty import UncertaintyAnalyzer, UncertaintyConfig
                analyzer = UncertaintyAnalyzer(None, self.logger)
                
                # Get base results if available
                base_results = kwargs.get('base_results', pd.DataFrame())
                
                # Create config
                if isinstance(config, dict):
                    unc_config = UncertaintyConfig(**config)
                else:
                    unc_config = config or UncertaintyConfig()
                
                return analyzer.analyze(X, y, base_results, unc_config)
            
            elif method == 'threshold':
                from .threshold_analysis import ThresholdAnalyzer
                analyzer = ThresholdAnalyzer(None, self.logger)
                return analyzer.analyze(X, y, config or {})
            
            elif method == 'regional':
                from .regional_sensitivity import RegionalSensitivityAnalyzer
                analyzer = RegionalSensitivityAnalyzer(None, self.logger)
                return analyzer.analyze(X, y, config or {})
            
            elif method == 'sobol':
                from .sobol_analyzer import SobolAnalyzer
                analyzer = SobolAnalyzer(None, self.logger)
                return analyzer.analyze(X, y, config or {})
            
            elif method == 'temporal':
                from .temporal_patterns import TemporalPatternAnalyzer
                analyzer = TemporalPatternAnalyzer(None, self.logger)
                return analyzer.analyze(X, y, config or {})
            
            else:
                self.logger.error(f"Unknown advanced method: {method}")
                return pd.DataFrame()
                
        except ImportError as e:
            self.logger.error(f"Could not import advanced analyzer for {method}: {e}")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error in advanced analysis {method}: {e}")
            return pd.DataFrame()
    
    # Keep all existing methods unchanged below
    
    def correlation_analysis(self, 
                           X: pd.DataFrame, 
                           y: Union[pd.DataFrame, pd.Series],
                           method: str = 'pearson',
                           min_samples: int = 5) -> pd.DataFrame:
        """
        Calculate correlation-based sensitivity
        
        Args:
            X: Input parameters
            y: Output variables (DataFrame or Series)
            method: 'pearson', 'spearman', or 'kendall'
            min_samples: Minimum samples required
            
        Returns:
            DataFrame with sensitivity results
        """
        results = []
        
        # Convert Series to DataFrame if needed
        if isinstance(y, pd.Series):
            y = pd.DataFrame({y.name if y.name else 'output': y})
        
        # Remove non-numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if len(X_numeric) < min_samples or len(y_numeric) < min_samples:
            self.logger.warning(f"Insufficient samples for correlation analysis: {len(X_numeric)}")
            return pd.DataFrame()
        
        for y_col in y_numeric.columns:
            for x_col in X_numeric.columns:
                # Skip constant columns
                if X_numeric[x_col].std() == 0 or y_numeric[y_col].std() == 0:
                    continue
                
                # Calculate correlation with confidence interval
                corr_result = self.calculate_correlation(
                    X_numeric[x_col], 
                    y_numeric[y_col],
                    method=method
                )
                
                if corr_result['correlation'] is not None:
                    results.append({
                        'parameter': x_col,
                        'output_variable': y_col,
                        'sensitivity_score': abs(corr_result['correlation']),
                        'correlation': corr_result['correlation'],
                        'p_value': corr_result['p_value'],
                        'confidence_lower': corr_result['ci_lower'],
                        'confidence_upper': corr_result['ci_upper'],
                        'method': f'correlation_{method}',
                        'n_samples': len(X_numeric)
                    })
        
        return pd.DataFrame(results)
    
    def calculate_correlation(self, x: pd.Series, y: pd.Series, 
                            method: str = 'pearson',
                            confidence_level: float = 0.95) -> Dict[str, float]:
        """Calculate correlation with confidence intervals"""
        # Remove NaN values
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            return {
                'correlation': None,
                'p_value': None,
                'ci_lower': None,
                'ci_upper': None
            }
        
        try:
            if method == 'pearson':
                corr, p_value = stats.pearsonr(x_clean, y_clean)
            elif method == 'spearman':
                corr, p_value = stats.spearmanr(x_clean, y_clean)
            elif method == 'kendall':
                corr, p_value = stats.kendalltau(x_clean, y_clean)
            else:
                raise ValueError(f"Unknown correlation method: {method}")
            
            # Calculate confidence interval using Fisher's z transformation
            if method == 'pearson' and len(x_clean) > 3:
                z = np.arctanh(corr)
                se = 1 / np.sqrt(len(x_clean) - 3)
                z_crit = stats.norm.ppf((1 + confidence_level) / 2)
                
                ci_lower = np.tanh(z - z_crit * se)
                ci_upper = np.tanh(z + z_crit * se)
            else:
                ci_lower, ci_upper = None, None
            
            return {
                'correlation': corr,
                'p_value': p_value,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper
            }
            
        except Exception as e:
            self.logger.warning(f"Correlation calculation failed: {e}")
            return {
                'correlation': None,
                'p_value': None,
                'ci_lower': None,
                'ci_upper': None
            }
    
    def regression_analysis(self,
                          X: pd.DataFrame,
                          y: Union[pd.DataFrame, pd.Series],
                          model_type: str = 'linear',
                          normalize: bool = True) -> pd.DataFrame:
        """
        Regression-based sensitivity analysis
        
        Args:
            X: Input parameters
            y: Output variables
            model_type: 'linear', 'ridge', or 'lasso'
            normalize: Whether to normalize inputs
            
        Returns:
            DataFrame with regression coefficients as sensitivity
        """
        results = []
        
        # Convert Series to DataFrame if needed
        if isinstance(y, pd.Series):
            y = pd.DataFrame({y.name if y.name else 'output': y})
        
        # Select numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        # Remove NaN values
        mask = ~(X_numeric.isna().any(axis=1) | y_numeric.isna().any(axis=1))
        X_clean = X_numeric[mask]
        y_clean = y_numeric[mask]
        
        if len(X_clean) < len(X_clean.columns) + 1:
            self.logger.warning("Insufficient samples for regression")
            return pd.DataFrame()
        
        # Normalize if requested
        if normalize:
            X_scaled = self.scaler.fit_transform(X_clean)
            X_clean = pd.DataFrame(X_scaled, columns=X_clean.columns, index=X_clean.index)
        
        # Fit regression for each output
        for y_col in y_clean.columns:
            y_values = y_clean[y_col]
            
            # Skip constant outputs
            if y_values.std() == 0:
                continue
            
            try:
                # Select model
                if model_type == 'linear':
                    model = LinearRegression()
                elif model_type == 'ridge':
                    model = Ridge(alpha=1.0)
                elif model_type == 'lasso':
                    model = Lasso(alpha=0.1)
                else:
                    raise ValueError(f"Unknown model type: {model_type}")
                
                # Fit model
                model.fit(X_clean, y_values)
                
                # Get coefficients
                coefficients = model.coef_
                r2 = model.score(X_clean, y_values)
                
                # Calculate standardized coefficients if not normalized
                if not normalize:
                    std_coef = coefficients * (X_clean.std() / y_values.std())
                else:
                    std_coef = coefficients
                
                # Store results
                for i, x_col in enumerate(X_clean.columns):
                    results.append({
                        'parameter': x_col,
                        'output_variable': y_col,
                        'sensitivity_score': abs(std_coef[i]),
                        'coefficient': coefficients[i],
                        'standardized_coefficient': std_coef[i],
                        'r2_score': r2,
                        'method': f'regression_{model_type}',
                        'n_samples': len(X_clean)
                    })
                    
            except Exception as e:
                self.logger.warning(f"Regression failed for {y_col}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def mutual_information_analysis(self,
                                  X: pd.DataFrame,
                                  y: pd.DataFrame,
                                  n_neighbors: int = 3) -> pd.DataFrame:
        """
        Mutual information based sensitivity
        
        Args:
            X: Input parameters
            y: Output variables
            n_neighbors: Number of neighbors for MI estimation
            
        Returns:
            DataFrame with mutual information scores
        """
        results = []
        
        # Select numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        for y_col in y_numeric.columns:
            y_values = y_numeric[y_col]
            
            # Skip constant outputs
            if y_values.std() == 0:
                continue
            
            # Remove NaN values
            mask = ~(X_numeric.isna().any(axis=1) | y_values.isna())
            X_clean = X_numeric[mask]
            y_clean = y_values[mask]
            
            if len(X_clean) < n_neighbors + 1:
                continue
            
            try:
                # Calculate MI for all features
                mi_scores = mutual_info_regression(
                    X_clean, y_clean,
                    n_neighbors=min(n_neighbors, len(X_clean) - 1)
                )
                
                # Normalize MI scores
                max_mi = mi_scores.max()
                if max_mi > 0:
                    mi_scores_normalized = mi_scores / max_mi
                else:
                    mi_scores_normalized = mi_scores
                
                # Store results
                for i, x_col in enumerate(X_clean.columns):
                    results.append({
                        'parameter': x_col,
                        'output_variable': y_col,
                        'sensitivity_score': mi_scores_normalized[i],
                        'mutual_information': mi_scores[i],
                        'method': 'mutual_information',
                        'n_samples': len(X_clean)
                    })
                    
            except Exception as e:
                self.logger.warning(f"MI calculation failed for {y_col}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def mutual_information(self, X: pd.DataFrame, y: Union[pd.DataFrame, pd.Series], **kwargs) -> pd.DataFrame:
        """Alias for mutual_information_analysis for compatibility"""
        return self.mutual_information_analysis(X, y, **kwargs)
    
    def random_forest_importance(self,
                               X: pd.DataFrame,
                               y: pd.DataFrame,
                               n_estimators: int = 100,
                               max_depth: Optional[int] = None) -> pd.DataFrame:
        """
        Random Forest feature importance as sensitivity
        
        Args:
            X: Input parameters
            y: Output variables
            n_estimators: Number of trees
            max_depth: Maximum tree depth
            
        Returns:
            DataFrame with feature importance scores
        """
        results = []
        
        # Select numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        for y_col in y_numeric.columns:
            y_values = y_numeric[y_col]
            
            # Skip constant outputs
            if y_values.std() == 0:
                continue
            
            # Remove NaN values
            mask = ~(X_numeric.isna().any(axis=1) | y_values.isna())
            X_clean = X_numeric[mask]
            y_clean = y_values[mask]
            
            if len(X_clean) < 10:  # Minimum samples for RF
                continue
            
            try:
                # Fit Random Forest
                rf = RandomForestRegressor(
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    random_state=42
                )
                rf.fit(X_clean, y_clean)
                
                # Get feature importances
                importances = rf.feature_importances_
                r2 = rf.score(X_clean, y_clean)
                
                # Calculate permutation importance for comparison
                baseline_score = r2
                perm_importances = []
                
                for i, col in enumerate(X_clean.columns):
                    X_perm = X_clean.copy()
                    X_perm[col] = np.random.permutation(X_perm[col])
                    perm_score = rf.score(X_perm, y_clean)
                    perm_importance = baseline_score - perm_score
                    perm_importances.append(max(0, perm_importance))
                
                # Store results
                for i, x_col in enumerate(X_clean.columns):
                    results.append({
                        'parameter': x_col,
                        'output_variable': y_col,
                        'sensitivity_score': importances[i],
                        'feature_importance': importances[i],
                        'permutation_importance': perm_importances[i],
                        'r2_score': r2,
                        'method': 'random_forest',
                        'n_samples': len(X_clean)
                    })
                    
            except Exception as e:
                self.logger.warning(f"Random Forest failed for {y_col}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def elasticity_analysis(self,
                          X: pd.DataFrame,
                          y: pd.DataFrame,
                          delta_fraction: float = 0.01) -> pd.DataFrame:
        """
        Calculate elasticity (percentage change sensitivity)
        
        Args:
            X: Input parameters
            y: Output variables
            delta_fraction: Fraction change in parameters
            
        Returns:
            DataFrame with elasticity scores
        """
        results = []
        
        # Select numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        for y_col in y_numeric.columns:
            for x_col in X_numeric.columns:
                # Get clean data
                mask = ~(X_numeric[x_col].isna() | y_numeric[y_col].isna())
                x_values = X_numeric[x_col][mask]
                y_values = y_numeric[y_col][mask]
                
                if len(x_values) < 2:
                    continue
                
                # Skip constant columns
                if x_values.std() == 0 or y_values.std() == 0:
                    continue
                
                try:
                    # Calculate local elasticity at mean
                    x_mean = x_values.mean()
                    y_mean = y_values.mean()
                    
                    # Fit local linear model around mean
                    x_range = x_values.std()
                    mask_local = (x_values >= x_mean - x_range) & (x_values <= x_mean + x_range)
                    
                    if mask_local.sum() < 3:
                        continue
                    
                    x_local = x_values[mask_local]
                    y_local = y_values[mask_local]
                    
                    # Calculate slope
                    slope, intercept = np.polyfit(x_local, y_local, 1)
                    
                    # Calculate elasticity
                    elasticity = (slope * x_mean) / y_mean if y_mean != 0 else 0
                    
                    results.append({
                        'parameter': x_col,
                        'output_variable': y_col,
                        'sensitivity_score': abs(elasticity),
                        'elasticity': elasticity,
                        'slope': slope,
                        'x_mean': x_mean,
                        'y_mean': y_mean,
                        'method': 'elasticity',
                        'n_samples': len(x_values)
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Elasticity calculation failed for {x_col}-{y_col}: {e}")
                    continue
        
        return pd.DataFrame(results)
    
    def bootstrap_analysis(self,
                         X: pd.DataFrame,
                         y: pd.DataFrame,
                         method: str = 'correlation',
                         n_bootstrap: int = 100,
                         confidence_level: float = 0.95,
                         **kwargs) -> pd.DataFrame:
        """
        Bootstrap confidence intervals for sensitivity scores
        
        Args:
            X: Input parameters
            y: Output variables
            method: Base method to bootstrap
            n_bootstrap: Number of bootstrap samples
            confidence_level: Confidence level for intervals
            **kwargs: Additional arguments for base method
            
        Returns:
            DataFrame with bootstrapped confidence intervals
        """
        # Get base sensitivity results
        if method == 'correlation':
            base_results = self.correlation_analysis(X, y, **kwargs)
        elif method == 'regression':
            base_results = self.regression_analysis(X, y, **kwargs)
        else:
            raise ValueError(f"Bootstrap not implemented for method: {method}")
        
        if base_results.empty:
            return base_results
        
        # Bootstrap for each parameter-output pair
        bootstrap_results = []
        
        unique_pairs = base_results[['parameter', 'output_variable']].drop_duplicates()
        
        for _, pair in unique_pairs.iterrows():
            param = pair['parameter']
            output = pair['output_variable']
            
            # Get data for this pair
            if param not in X.columns or output not in y.columns:
                continue
            
            x_data = X[param]
            y_data = y[output]
            
            # Bootstrap samples
            bootstrap_scores = []
            
            for _ in range(n_bootstrap):
                # Resample with replacement
                indices = np.random.choice(len(x_data), size=len(x_data), replace=True)
                x_boot = x_data.iloc[indices]
                y_boot = y_data.iloc[indices]
                
                # Calculate sensitivity
                if method == 'correlation':
                    corr_result = self.calculate_correlation(x_boot, y_boot)
                    if corr_result['correlation'] is not None:
                        bootstrap_scores.append(abs(corr_result['correlation']))
            
            if bootstrap_scores:
                # Calculate confidence intervals
                alpha = 1 - confidence_level
                ci_lower = np.percentile(bootstrap_scores, 100 * alpha / 2)
                ci_upper = np.percentile(bootstrap_scores, 100 * (1 - alpha / 2))
                
                # Get original score
                orig_score = base_results[
                    (base_results['parameter'] == param) & 
                    (base_results['output_variable'] == output)
                ]['sensitivity_score'].iloc[0]
                
                bootstrap_results.append({
                    'parameter': param,
                    'output_variable': output,
                    'sensitivity_score': orig_score,
                    'bootstrap_mean': np.mean(bootstrap_scores),
                    'bootstrap_std': np.std(bootstrap_scores),
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper,
                    'method': f'bootstrap_{method}',
                    'n_bootstrap': n_bootstrap
                })
        
        return pd.DataFrame(bootstrap_results)
    
    def aggregate_methods(self,
                        results_list: List[pd.DataFrame],
                        aggregation: str = 'mean',
                        weights: Optional[List[float]] = None) -> pd.DataFrame:
        """
        Aggregate results from multiple methods
        
        Args:
            results_list: List of DataFrames from different methods
            aggregation: 'mean', 'median', 'max', or 'weighted'
            weights: Weights for weighted aggregation
            
        Returns:
            Aggregated sensitivity results
        """
        if not results_list:
            return pd.DataFrame()
        
        # Combine all results
        all_results = pd.concat(results_list, ignore_index=True)
        
        if all_results.empty:
            return pd.DataFrame()
        
        # Group by parameter and output
        grouped = all_results.groupby(['parameter', 'output_variable'])
        
        if aggregation == 'mean':
            aggregated = grouped['sensitivity_score'].mean()
        elif aggregation == 'median':
            aggregated = grouped['sensitivity_score'].median()
        elif aggregation == 'max':
            aggregated = grouped['sensitivity_score'].max()
        elif aggregation == 'weighted' and weights is not None:
            # Weighted aggregation
            def weighted_mean(group):
                methods = group['method'].unique()
                method_weights = {m: w for m, w in zip(methods[:len(weights)], weights)}
                group['weight'] = group['method'].map(method_weights).fillna(1.0)
                return (group['sensitivity_score'] * group['weight']).sum() / group['weight'].sum()
            
            aggregated = grouped.apply(weighted_mean)
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation}")
        
        # Create result DataFrame
        result = aggregated.reset_index()
        result.columns = ['parameter', 'output_variable', 'sensitivity_score']
        
        # Add additional statistics
        result['n_methods'] = grouped.size().values
        result['score_std'] = grouped['sensitivity_score'].std().values
        result['methods_used'] = grouped['method'].apply(lambda x: list(x.unique())).values
        result['method'] = f'aggregated_{aggregation}'
        
        return result
    
    def calculate_interaction_effects(self,
                                    X: pd.DataFrame,
                                    y: pd.DataFrame,
                                    max_interactions: int = 10) -> pd.DataFrame:
        """
        Calculate interaction effects between parameters
        
        Args:
            X: Input parameters
            y: Output variables
            max_interactions: Maximum number of interactions to test
            
        Returns:
            DataFrame with interaction effects
        """
        results = []
        
        # Select numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.shape[1] < 2 or y_numeric.empty:
            return pd.DataFrame()
        
        # Get parameter pairs
        from itertools import combinations
        param_pairs = list(combinations(X_numeric.columns, 2))[:max_interactions]
        
        for y_col in y_numeric.columns:
            y_values = y_numeric[y_col]
            
            for param1, param2 in param_pairs:
                # Create interaction term
                interaction = X_numeric[param1] * X_numeric[param2]
                
                # Remove NaN values
                mask = ~(X_numeric[[param1, param2]].isna().any(axis=1) | 
                        y_values.isna() | interaction.isna())
                
                if mask.sum() < 10:
                    continue
                
                try:
                    # Fit model with interaction
                    X_with_interaction = pd.DataFrame({
                        param1: X_numeric[param1][mask],
                        param2: X_numeric[param2][mask],
                        'interaction': interaction[mask]
                    })
                    
                    model = LinearRegression()
                    model.fit(X_with_interaction, y_values[mask])
                    
                    # Get interaction coefficient
                    interaction_coef = model.coef_[2]
                    r2 = model.score(X_with_interaction, y_values[mask])
                    
                    # Test significance
                    # Simple approach - could be improved with proper statistical test
                    interaction_importance = abs(interaction_coef) * interaction[mask].std()
                    
                    results.append({
                        'parameter': f'{param1}*{param2}',
                        'parameter_1': param1,
                        'parameter_2': param2,
                        'output_variable': y_col,
                        'sensitivity_score': interaction_importance,
                        'interaction_coefficient': interaction_coef,
                        'r2_score': r2,
                        'method': 'interaction',
                        'n_samples': mask.sum()
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Interaction calculation failed for {param1}*{param2}: {e}")
                    continue
        
        return pd.DataFrame(results)