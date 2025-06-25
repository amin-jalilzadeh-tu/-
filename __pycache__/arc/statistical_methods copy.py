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
from typing import Dict, List, Tuple, Optional, Any
import logging

warnings.filterwarnings('ignore', category=FutureWarning)


class StatisticalMethods:
    """Collection of statistical methods for sensitivity analysis"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.scaler = StandardScaler()
    
    def correlation_analysis(self, 
                           X: pd.DataFrame, 
                           y: pd.DataFrame,
                           method: str = 'pearson',
                           min_samples: int = 5) -> pd.DataFrame:
        """
        Calculate correlation-based sensitivity
        
        Args:
            X: Input parameters
            y: Output variables
            method: 'pearson', 'spearman', or 'kendall'
            min_samples: Minimum samples required
            
        Returns:
            DataFrame with sensitivity results
        """
        results = []
        
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
                        'ci_lower': corr_result['confidence_interval'][0],
                        'ci_upper': corr_result['confidence_interval'][1],
                        'method': method,
                        'n_samples': corr_result['n_samples']
                    })
        
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results = df_results.sort_values('sensitivity_score', ascending=False)
        
        return df_results
    
    def calculate_correlation(self,
                            x: pd.Series,
                            y: pd.Series,
                            method: str = 'pearson',
                            confidence_level: float = 0.95) -> Dict[str, Any]:
        """Calculate correlation with confidence interval"""
        # Remove NaN values
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask]
        y_clean = y[mask]
        
        n_samples = len(x_clean)
        
        if n_samples < 3:
            return {
                'correlation': None,
                'p_value': 1.0,
                'confidence_interval': (0, 0),
                'n_samples': n_samples
            }
        
        # Calculate correlation
        if method == 'pearson':
            corr, p_value = stats.pearsonr(x_clean, y_clean)
        elif method == 'spearman':
            corr, p_value = stats.spearmanr(x_clean, y_clean)
        elif method == 'kendall':
            corr, p_value = stats.kendalltau(x_clean, y_clean)
        else:
            raise ValueError(f"Unknown correlation method: {method}")
        
        # Calculate confidence interval using Fisher's z-transformation
        if method == 'pearson' and not np.isnan(corr):
            ci_lower, ci_upper = self._correlation_confidence_interval(
                corr, n_samples, confidence_level
            )
        else:
            ci_lower, ci_upper = corr - 0.1, corr + 0.1  # Rough estimate
        
        return {
            'correlation': corr,
            'p_value': p_value,
            'confidence_interval': (ci_lower, ci_upper),
            'n_samples': n_samples
        }
    
    def _correlation_confidence_interval(self,
                                       r: float,
                                       n: int,
                                       confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for correlation using Fisher's z"""
        # Fisher's z transformation
        z = 0.5 * np.log((1 + r) / (1 - r))
        
        # Standard error
        se = 1 / np.sqrt(n - 3)
        
        # Critical value
        alpha = 1 - confidence_level
        z_crit = stats.norm.ppf(1 - alpha/2)
        
        # Confidence interval in z space
        z_lower = z - z_crit * se
        z_upper = z + z_crit * se
        
        # Transform back to correlation space
        ci_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
        ci_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)
        
        return ci_lower, ci_upper
    
    def regression_analysis(self,
                          X: pd.DataFrame,
                          y: pd.DataFrame,
                          method: str = 'linear',
                          standardize: bool = True,
                          **kwargs) -> pd.DataFrame:
        """
        Regression-based sensitivity analysis
        
        Args:
            X: Input parameters
            y: Output variables
            method: 'linear', 'ridge', 'lasso', or 'random_forest'
            standardize: Whether to standardize inputs
            **kwargs: Additional method-specific parameters
            
        Returns:
            DataFrame with sensitivity results
        """
        results = []
        
        # Prepare data
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        # Remove columns with zero variance
        X_numeric = X_numeric.loc[:, X_numeric.std() > 0]
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        # Standardize if requested
        if standardize:
            X_scaled = self.scaler.fit_transform(X_numeric)
            X_df = pd.DataFrame(X_scaled, columns=X_numeric.columns, index=X_numeric.index)
        else:
            X_df = X_numeric
        
        # Fit model for each output
        for y_col in y_numeric.columns:
            y_series = y_numeric[y_col]
            
            # Skip if insufficient variation
            if y_series.std() == 0:
                continue
            
            # Select model
            if method == 'linear':
                model = LinearRegression()
            elif method == 'ridge':
                alpha = kwargs.get('alpha', 1.0)
                model = Ridge(alpha=alpha)
            elif method == 'lasso':
                alpha = kwargs.get('alpha', 1.0)
                model = Lasso(alpha=alpha)
            elif method == 'random_forest':
                model = RandomForestRegressor(
                    n_estimators=kwargs.get('n_estimators', 100),
                    random_state=42
                )
            else:
                raise ValueError(f"Unknown regression method: {method}")
            
            # Fit model
            try:
                model.fit(X_df, y_series)
                
                # Get feature importance
                if method == 'random_forest':
                    importances = model.feature_importances_
                else:
                    # Use standardized coefficients
                    importances = np.abs(model.coef_)
                
                # Calculate R-squared
                y_pred = model.predict(X_df)
                r2 = r2_score(y_series, y_pred)
                
                # Calculate p-values for linear models
                if method in ['linear', 'ridge', 'lasso']:
                    p_values = self._calculate_regression_pvalues(X_df, y_series, model)
                else:
                    p_values = [np.nan] * len(importances)
                
                # Store results
                for i, (col, importance) in enumerate(zip(X_numeric.columns, importances)):
                    results.append({
                        'parameter': col,
                        'output_variable': y_col,
                        'sensitivity_score': importance,
                        'coefficient': model.coef_[i] if hasattr(model, 'coef_') else importance,
                        'p_value': p_values[i] if i < len(p_values) else np.nan,
                        'r_squared': r2,
                        'method': f"{method}_regression",
                        'n_samples': len(X_df)
                    })
                    
            except Exception as e:
                self.logger.warning(f"Regression failed for {y_col}: {e}")
                continue
        
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            # Normalize sensitivity scores within each output variable
            for y_col in df_results['output_variable'].unique():
                mask = df_results['output_variable'] == y_col
                scores = df_results.loc[mask, 'sensitivity_score']
                if scores.max() > 0:
                    df_results.loc[mask, 'sensitivity_score'] = scores / scores.max()
            
            df_results = df_results.sort_values('sensitivity_score', ascending=False)
        
        return df_results
    
    def _calculate_regression_pvalues(self,
                                    X: pd.DataFrame,
                                    y: pd.Series,
                                    model) -> List[float]:
        """Calculate p-values for regression coefficients"""
        n = len(X)
        p = X.shape[1]
        
        # Predictions and residuals
        y_pred = model.predict(X)
        residuals = y - y_pred
        
        # Mean squared error
        mse = np.sum(residuals**2) / (n - p - 1)
        
        # Variance-covariance matrix
        try:
            var_coef = mse * np.linalg.inv(X.T @ X)
            sd_coef = np.sqrt(np.diag(var_coef))
            
            # T-statistics
            t_stats = model.coef_ / sd_coef
            
            # P-values
            p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - p - 1))
            
            return p_values.tolist()
        except:
            return [np.nan] * p
    
    # Add this method to the StatisticalMethods class in statistical_methods.py
    # This provides the calculate_elasticity method that was referenced but missing

    def calculate_elasticity(self, x: pd.Series, y: pd.Series) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate elasticity between two variables
        
        Args:
            x: Input parameter series (independent variable)
            y: Output variable series (dependent variable)
            
        Returns:
            Tuple of (elasticity, stats_info)
        """
        # Remove NaN values
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask]
        y_clean = y[mask]
        
        stats_info = {
            'p_value': 1.0,
            'confidence_interval': (0, 0),
            'r_squared': 0.0
        }
        
        if len(x_clean) < 2:
            return None, stats_info
        
        try:
            # For direct elasticity calculation when we have percentage changes
            if all(col in str(x.name) + str(y.name) for col in ['pct_change']):
                # Direct elasticity from percentage changes
                if x_clean.iloc[0] != 0:
                    elasticity = y_clean.iloc[0] / x_clean.iloc[0]
                else:
                    elasticity = 0.0
            else:
                # Calculate elasticity from raw values
                x_mean = x_clean.mean()
                y_mean = y_clean.mean()
                
                if x_mean == 0 or y_mean == 0:
                    return 0.0, stats_info
                
                # Fit linear model for local elasticity
                if x_clean.std() > 0:
                    # Simple linear regression
                    n = len(x_clean)
                    x_values = x_clean.values
                    y_values = y_clean.values
                    
                    # Calculate slope
                    xy_mean = (x_values * y_values).mean()
                    x_sq_mean = (x_values ** 2).mean()
                    slope = (xy_mean - x_mean * y_mean) / (x_sq_mean - x_mean ** 2) if x_sq_mean != x_mean ** 2 else 0
                    
                    # Calculate elasticity at mean
                    elasticity = (slope * x_mean) / y_mean
                    
                    # Calculate R-squared
                    y_pred = slope * x_values + (y_mean - slope * x_mean)
                    ss_res = ((y_values - y_pred) ** 2).sum()
                    ss_tot = ((y_values - y_mean) ** 2).sum()
                    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    
                    # Simple p-value calculation
                    if n > 2:
                        t_stat = abs(slope) * np.sqrt(n - 2) / np.sqrt(ss_res / (n - 2)) if ss_res > 0 else 0
                        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
                    else:
                        p_value = 1.0
                    
                    stats_info = {
                        'p_value': p_value,
                        'confidence_interval': (elasticity - 0.1, elasticity + 0.1),  # Simplified
                        'r_squared': r_squared
                    }
                else:
                    elasticity = 0.0
            
            return elasticity, stats_info
            
        except Exception as e:
            self.logger.warning(f"Elasticity calculation failed: {e}")
            return 0.0, stats_info
    
    def sobol_analysis(self,
                     X: pd.DataFrame,
                     y: pd.DataFrame,
                     n_samples: int = 1000,
                     calc_second_order: bool = False,
                     **kwargs) -> pd.DataFrame:
        """
        Simplified Sobol sensitivity analysis
        
        Note: This is a simplified implementation. For production use,
        consider using SALib or similar specialized libraries.
        """
        self.logger.info("Performing simplified Sobol analysis...")
        
        results = []
        
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        # For each output variable
        for y_col in y_numeric.columns:
            # Calculate variance-based sensitivity using random forest
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            
            try:
                rf.fit(X_numeric, y_numeric[y_col])
                
                # Use feature importances as proxy for Sobol indices
                importances = rf.feature_importances_
                
                # Normalize to sum to 1 (like Sobol indices)
                total_var = np.sum(importances)
                if total_var > 0:
                    sobol_indices = importances / total_var
                else:
                    sobol_indices = importances
                
                # Store results
                for param, s_index in zip(X_numeric.columns, sobol_indices):
                    results.append({
                        'parameter': param,
                        'output_variable': y_col,
                        'sensitivity_score': s_index,
                        'sobol_index': s_index,
                        'sobol_type': 'first_order',
                        'method': 'sobol_approx',
                        'n_samples': len(X_numeric)
                    })
                    
            except Exception as e:
                self.logger.warning(f"Sobol analysis failed for {y_col}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def morris_analysis(self,
                      X: pd.DataFrame,
                      y: pd.DataFrame,
                      n_trajectories: int = 10,
                      **kwargs) -> pd.DataFrame:
        """
        Simplified Morris method for screening
        
        Note: This is a simplified implementation focusing on elementary effects.
        """
        self.logger.info("Performing simplified Morris analysis...")
        
        results = []
        
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        # For each parameter, calculate elementary effects
        for param_col in X_numeric.columns:
            for y_col in y_numeric.columns:
                # Calculate correlation as proxy for elementary effect
                corr_result = self.calculate_correlation(
                    X_numeric[param_col],
                    y_numeric[y_col]
                )
                
                if corr_result['correlation'] is not None:
                    # Use absolute correlation as sensitivity measure
                    sensitivity = abs(corr_result['correlation'])
                    
                    # Estimate mean and std of effects (simplified)
                    results.append({
                        'parameter': param_col,
                        'output_variable': y_col,
                        'sensitivity_score': sensitivity,
                        'morris_mean': sensitivity,
                        'morris_std': sensitivity * 0.1,  # Rough estimate
                        'p_value': corr_result['p_value'],
                        'method': 'morris_screening',
                        'n_samples': corr_result['n_samples']
                    })
        
        return pd.DataFrame(results)
    
    def mutual_information_analysis(self,
                                  X: pd.DataFrame,
                                  y: pd.DataFrame,
                                  n_neighbors: int = 3,
                                  **kwargs) -> pd.DataFrame:
        """
        Calculate mutual information for non-linear relationships
        """
        results = []
        
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.empty or y_numeric.empty:
            return pd.DataFrame()
        
        # Calculate MI for each output
        for y_col in y_numeric.columns:
            y_series = y_numeric[y_col]
            
            # Skip if no variation
            if y_series.std() == 0:
                continue
            
            # Calculate mutual information
            try:
                mi_scores = mutual_info_regression(
                    X_numeric, 
                    y_series,
                    n_neighbors=n_neighbors,
                    random_state=42
                )
                
                # Normalize scores
                max_mi = np.max(mi_scores) if np.max(mi_scores) > 0 else 1
                mi_normalized = mi_scores / max_mi
                
                for param, mi_score, mi_norm in zip(X_numeric.columns, mi_scores, mi_normalized):
                    results.append({
                        'parameter': param,
                        'output_variable': y_col,
                        'sensitivity_score': mi_norm,
                        'mutual_information': mi_score,
                        'method': 'mutual_information',
                        'n_samples': len(X_numeric)
                    })
                    
            except Exception as e:
                self.logger.warning(f"MI calculation failed for {y_col}: {e}")
                continue
        
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results = df_results.sort_values('sensitivity_score', ascending=False)
        
        return df_results
    
    def bootstrap_sensitivity(self,
                            X: pd.DataFrame,
                            y: pd.DataFrame,
                            method: str = 'correlation',
                            n_bootstrap: int = 1000,
                            confidence_level: float = 0.95,
                            **kwargs) -> pd.DataFrame:
        """
        Bootstrap confidence intervals for sensitivity measures
        """
        self.logger.info(f"Performing bootstrap analysis with {n_bootstrap} iterations...")
        
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
                    'ci_lower_bootstrap': ci_lower,
                    'ci_upper_bootstrap': ci_upper,
                    'n_bootstrap': n_bootstrap
                })
        
        # Merge with original results
        bootstrap_df = pd.DataFrame(bootstrap_results)
        
        if not bootstrap_df.empty:
            final_results = base_results.merge(
                bootstrap_df[['parameter', 'output_variable', 'ci_lower_bootstrap', 'ci_upper_bootstrap']],
                on=['parameter', 'output_variable'],
                how='left'
            )
            return final_results
        
        return base_results
    
    def calculate_interactions(self,
                             X: pd.DataFrame,
                             y: pd.DataFrame,
                             max_interactions: int = 10,
                             min_interaction_strength: float = 0.1) -> pd.DataFrame:
        """
        Calculate interaction effects between parameters
        """
        results = []
        
        X_numeric = X.select_dtypes(include=[np.number])
        y_numeric = y.select_dtypes(include=[np.number])
        
        if X_numeric.shape[1] < 2:
            return pd.DataFrame()
        
        # Limit number of parameters to avoid combinatorial explosion
        if X_numeric.shape[1] > 20:
            # Select top variables based on individual correlations
            corr_results = self.correlation_analysis(X_numeric, y_numeric)
            if not corr_results.empty:
                top_params = corr_results.groupby('parameter')['sensitivity_score'].mean().nlargest(10).index
                X_numeric = X_numeric[top_params]
        
        # Calculate interactions for each output
        for y_col in y_numeric.columns:
            y_series = y_numeric[y_col]
            
            # Create interaction terms
            param_cols = list(X_numeric.columns)
            interaction_scores = []
            
            for i in range(len(param_cols)):
                for j in range(i + 1, len(param_cols)):
                    param1 = param_cols[i]
                    param2 = param_cols[j]
                    
                    # Create interaction term
                    interaction = X_numeric[param1] * X_numeric[param2]
                    
                    # Calculate correlation of interaction with output
                    corr_result = self.calculate_correlation(interaction, y_series)
                    
                    if corr_result['correlation'] is not None:
                        # Calculate interaction strength
                        # Compare to individual effects
                        corr1 = self.calculate_correlation(X_numeric[param1], y_series)['correlation'] or 0
                        corr2 = self.calculate_correlation(X_numeric[param2], y_series)['correlation'] or 0
                        
                        interaction_strength = abs(corr_result['correlation']) - max(abs(corr1), abs(corr2))
                        
                        if interaction_strength > min_interaction_strength:
                            interaction_scores.append({
                                'param1': param1,
                                'param2': param2,
                                'output_variable': y_col,
                                'interaction_correlation': corr_result['correlation'],
                                'interaction_strength': interaction_strength,
                                'p_value': corr_result['p_value']
                            })
            
            # Keep top interactions
            interaction_scores.sort(key=lambda x: abs(x['interaction_strength']), reverse=True)
            results.extend(interaction_scores[:max_interactions])
        
        return pd.DataFrame(results)