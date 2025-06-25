"""
c_sensitivity/regional_sensitivity.py

Regional sensitivity analysis to understand how sensitivity changes
across different parameter ranges and operating conditions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from scipy import interpolate, stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class RegionalSensitivityAnalyzer:
    """
    Analyzes how sensitivity varies across different regions of parameter space.
    
    Features:
    - Local sensitivity at different operating points
    - Parameter range-dependent sensitivity indices
    - Sensitivity maps across parameter space
    - Operating region identification
    
    Example usage:
        analyzer = RegionalSensitivityAnalyzer(data_manager, logger)
        config = {
            'n_regions': 5,
            'region_method': 'kmeans',  # or 'grid', 'quantile'
            'local_window_size': 0.1,   # fraction of data range
            'create_sensitivity_map': True
        }
        results = analyzer.analyze(X, y, config)
    """
    
    def __init__(self, data_manager, logger: Optional[logging.Logger] = None):
        self.data_manager = data_manager
        self.logger = logger or logging.getLogger(__name__)
        self.scaler = StandardScaler()
        
    def analyze(self,
                X: pd.DataFrame,
                y: pd.DataFrame,
                config: Dict[str, Any]) -> pd.DataFrame:
        """
        Perform regional sensitivity analysis.
        
        Args:
            X: Input parameters DataFrame
            y: Output variables DataFrame
            config: Analysis configuration
            
        Returns:
            DataFrame with regional sensitivity results
        """
        self.logger.info("Starting regional sensitivity analysis...")
        
        n_regions = config.get('n_regions', 5)
        region_method = config.get('region_method', 'kmeans')
        local_window_size = config.get('local_window_size', 0.1)
        
        results = []
        
        # Define regions based on method
        if region_method == 'kmeans':
            regions = self._define_kmeans_regions(X, n_regions)
        elif region_method == 'grid':
            regions = self._define_grid_regions(X, n_regions)
        elif region_method == 'quantile':
            regions = self._define_quantile_regions(X, n_regions)
        else:
            regions = self._define_kmeans_regions(X, n_regions)
        
        # Calculate sensitivity in each region
        for region_id, region_data in regions.items():
            region_mask = region_data['mask']
            
            if region_mask.sum() < 5:  # Need minimum samples
                continue
            
            # Calculate sensitivity for each parameter-output pair in this region
            for param in X.select_dtypes(include=[np.number]).columns:
                for output in y.select_dtypes(include=[np.number]).columns:
                    # Regional data
                    X_region = X.loc[region_mask, param]
                    y_region = y.loc[region_mask, output]
                    
                    # Calculate regional sensitivity
                    sensitivity = self._calculate_regional_sensitivity(
                        X_region, y_region, local_window_size
                    )
                    
                    # Add region characteristics
                    region_chars = self._characterize_region(X.loc[region_mask], param)
                    
                    results.append({
                        'parameter': param,
                        'output_variable': output,
                        'sensitivity_score': sensitivity['score'],
                        'method': 'regional_sensitivity',
                        'region_id': region_id,
                        'region_center': region_data.get('center', {}).get(param, np.nan),
                        'region_size': region_mask.sum(),
                        'parameter_mean': region_chars['mean'],
                        'parameter_std': region_chars['std'],
                        'parameter_min': region_chars['min'],
                        'parameter_max': region_chars['max'],
                        'local_correlation': sensitivity['correlation'],
                        'local_slope': sensitivity['slope'],
                        'local_nonlinearity': sensitivity['nonlinearity']
                    })
        
        df_results = pd.DataFrame(results)
        
        # Create sensitivity maps if requested
        if config.get('create_sensitivity_map', False) and not df_results.empty:
            self._create_sensitivity_maps(df_results, X, y, output_dir=config.get('output_dir'))
        
        # Add global context
        if not df_results.empty:
            df_results = self._add_global_context(df_results, X, y)
        
        return df_results
    
    def _define_kmeans_regions(self, X: pd.DataFrame, n_regions: int) -> Dict[int, Dict]:
        """Define regions using K-means clustering"""
        
        # Use only numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        
        # Scale data
        X_scaled = self.scaler.fit_transform(X_numeric)
        
        # K-means clustering
        kmeans = KMeans(n_clusters=n_regions, random_state=42)
        cluster_labels = kmeans.fit_predict(X_scaled)
        
        # Create region dictionary
        regions = {}
        for i in range(n_regions):
            mask = cluster_labels == i
            
            # Calculate cluster center in original space
            center = {}
            for j, col in enumerate(X_numeric.columns):
                center_scaled = kmeans.cluster_centers_[i, j]
                center[col] = self.scaler.inverse_transform(
                    [[center_scaled]]
                )[0][0]
            
            regions[i] = {
                'mask': mask,
                'center': center,
                'method': 'kmeans'
            }
        
        return regions
    
    def _define_grid_regions(self, X: pd.DataFrame, n_regions_per_dim: int) -> Dict[int, Dict]:
        """Define regions using grid partitioning"""
        
        X_numeric = X.select_dtypes(include=[np.number])
        n_dims = len(X_numeric.columns)
        
        if n_dims > 3:
            # For high dimensions, use only top 3 most variable parameters
            variances = X_numeric.var()
            top_params = variances.nlargest(3).index
            X_numeric = X_numeric[top_params]
            n_dims = 3
        
        # Create grid boundaries
        boundaries = {}
        for col in X_numeric.columns:
            boundaries[col] = np.linspace(
                X_numeric[col].min(),
                X_numeric[col].max(),
                n_regions_per_dim + 1
            )
        
        # Create regions
        regions = {}
        region_id = 0
        
        # Generate all combinations of grid cells
        import itertools
        indices = list(itertools.product(*[range(n_regions_per_dim) for _ in range(n_dims)]))
        
        for idx_tuple in indices:
            # Create mask for this grid cell
            mask = pd.Series(True, index=X.index)
            center = {}
            
            for dim, (col, idx) in enumerate(zip(X_numeric.columns, idx_tuple)):
                lower = boundaries[col][idx]
                upper = boundaries[col][idx + 1]
                
                mask &= (X[col] >= lower) & (X[col] <= upper)
                center[col] = (lower + upper) / 2
            
            if mask.sum() > 0:  # Only add non-empty regions
                regions[region_id] = {
                    'mask': mask,
                    'center': center,
                    'method': 'grid',
                    'grid_indices': idx_tuple
                }
                region_id += 1
        
        return regions
    
    def _define_quantile_regions(self, X: pd.DataFrame, n_quantiles: int) -> Dict[int, Dict]:
        """Define regions using quantile-based partitioning"""
        
        # For simplicity, partition based on first principal component
        X_numeric = X.select_dtypes(include=[np.number])
        
        # Calculate first PC
        X_scaled = self.scaler.fit_transform(X_numeric)
        U, s, Vt = np.linalg.svd(X_scaled, full_matrices=False)
        pc1 = U[:, 0] * s[0]
        
        # Define quantile boundaries
        quantiles = np.linspace(0, 1, n_quantiles + 1)
        boundaries = np.quantile(pc1, quantiles)
        
        # Create regions
        regions = {}
        for i in range(n_quantiles):
            mask = (pc1 >= boundaries[i]) & (pc1 < boundaries[i + 1])
            if i == n_quantiles - 1:  # Include upper boundary in last region
                mask = (pc1 >= boundaries[i]) & (pc1 <= boundaries[i + 1])
            
            # Calculate region center
            center = {}
            for col in X_numeric.columns:
                center[col] = X_numeric.loc[mask, col].mean()
            
            regions[i] = {
                'mask': mask,
                'center': center,
                'method': 'quantile',
                'pc1_range': (boundaries[i], boundaries[i + 1])
            }
        
        return regions
    
    def _calculate_regional_sensitivity(self,
                                      x: pd.Series,
                                      y: pd.Series,
                                      window_size: float) -> Dict[str, float]:
        """Calculate sensitivity measures for a region"""
        
        if len(x) < 3:
            return {'score': 0, 'correlation': 0, 'slope': 0, 'nonlinearity': 0}
        
        # Remove NaN values
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            return {'score': 0, 'correlation': 0, 'slope': 0, 'nonlinearity': 0}
        
        # Calculate correlation
        correlation = x_clean.corr(y_clean)
        if np.isnan(correlation):
            correlation = 0
        
        # Calculate local slope using weighted regression
        if x_clean.std() > 0:
            # Fit linear model
            coeffs_linear = np.polyfit(x_clean, y_clean, 1)
            slope = coeffs_linear[0]
            y_pred_linear = np.polyval(coeffs_linear, x_clean)
            
            # Fit quadratic model to detect nonlinearity
            try:
                coeffs_quad = np.polyfit(x_clean, y_clean, 2)
                y_pred_quad = np.polyval(coeffs_quad, x_clean)
                
                # Measure nonlinearity as improvement in fit
                ss_linear = np.sum((y_clean - y_pred_linear)**2)
                ss_quad = np.sum((y_clean - y_pred_quad)**2)
                
                if ss_linear > 0:
                    nonlinearity = 1 - ss_quad / ss_linear
                else:
                    nonlinearity = 0
            except:
                nonlinearity = 0
        else:
            slope = 0
            nonlinearity = 0
        
        # Normalize slope
        if y_clean.std() > 0:
            normalized_slope = slope * x_clean.std() / y_clean.std()
        else:
            normalized_slope = 0
        
        # Combined sensitivity score
        # Weight correlation more for linear relationships
        # Weight slope more for nonlinear relationships
        linear_weight = 1 - nonlinearity
        score = (linear_weight * abs(correlation) + 
                (1 - linear_weight) * abs(normalized_slope))
        
        return {
            'score': score,
            'correlation': correlation,
            'slope': slope,
            'nonlinearity': nonlinearity
        }
    
    def _characterize_region(self, X_region: pd.DataFrame, param: str) -> Dict[str, float]:
        """Characterize a region's parameter statistics"""
        
        if param not in X_region.columns:
            return {'mean': np.nan, 'std': np.nan, 'min': np.nan, 'max': np.nan}
        
        param_data = X_region[param]
        
        return {
            'mean': param_data.mean(),
            'std': param_data.std(),
            'min': param_data.min(),
            'max': param_data.max()
        }
    
    def _create_sensitivity_maps(self,
                               df_results: pd.DataFrame,
                               X: pd.DataFrame,
                               y: pd.DataFrame,
                               output_dir: Optional[Path] = None):
        """Create sensitivity maps showing how sensitivity varies across parameter space"""
        
        # This would create visualizations - placeholder for now
        self.logger.info("Sensitivity map creation not implemented in base module")
        # In practice, this would create heatmaps or contour plots
        
    def _add_global_context(self,
                          df_results: pd.DataFrame,
                          X: pd.DataFrame,
                          y: pd.DataFrame) -> pd.DataFrame:
        """Add global sensitivity context to regional results"""
        
        # Calculate global sensitivity for comparison
        global_sensitivities = {}
        
        for param in df_results['parameter'].unique():
            for output in df_results['output_variable'].unique():
                if param in X.columns and output in y.columns:
                    corr = X[param].corr(y[output])
                    global_sensitivities[(param, output)] = abs(corr) if not np.isnan(corr) else 0
        
        # Add global sensitivity and relative regional sensitivity
        df_results['global_sensitivity'] = df_results.apply(
            lambda row: global_sensitivities.get(
                (row['parameter'], row['output_variable']), 0
            ),
            axis=1
        )
        
        df_results['relative_sensitivity'] = (
            df_results['sensitivity_score'] / 
            (df_results['global_sensitivity'] + 1e-10)
        )
        
        return df_results
    
    def calculate_local_derivatives(self,
                                  X: pd.DataFrame,
                                  y: pd.DataFrame,
                                  config: Dict[str, Any]) -> pd.DataFrame:
        """
        Calculate local derivatives at specific operating points.
        """
        operating_points = config.get('operating_points', [])
        derivative_order = config.get('derivative_order', 1)
        neighborhood_size = config.get('neighborhood_size', 0.05)  # 5% of range
        
        results = []
        
        for op_idx, operating_point in enumerate(operating_points):
            # Find samples near this operating point
            distances = np.zeros(len(X))
            
            for param, value in operating_point.items():
                if param in X.columns:
                    param_range = X[param].max() - X[param].min()
                    normalized_dist = (X[param] - value) / (param_range + 1e-10)
                    distances += normalized_dist**2
            
            distances = np.sqrt(distances)
            neighborhood_mask = distances < neighborhood_size
            
            if neighborhood_mask.sum() < 10:
                self.logger.warning(f"Too few samples near operating point {op_idx}")
                continue
            
            # Calculate local derivatives
            for param in X.select_dtypes(include=[np.number]).columns:
                for output in y.select_dtypes(include=[np.number]).columns:
                    x_local = X.loc[neighborhood_mask, param].values
                    y_local = y.loc[neighborhood_mask, output].values
                    
                    # Fit polynomial locally
                    try:
                        coeffs = np.polyfit(x_local, y_local, derivative_order + 1)
                        poly = np.poly1d(coeffs)
                        
                        # Calculate derivatives at operating point
                        derivatives = []
                        for order in range(1, derivative_order + 1):
                            deriv_poly = np.polyder(poly, order)
                            deriv_value = deriv_poly(operating_point.get(param, X[param].mean()))
                            derivatives.append(deriv_value)
                        
                        results.append({
                            'parameter': param,
                            'output_variable': output,
                            'method': 'local_derivative',
                            'operating_point_id': op_idx,
                            'operating_point_value': operating_point.get(param, np.nan),
                            'first_derivative': derivatives[0] if len(derivatives) > 0 else np.nan,
                            'second_derivative': derivatives[1] if len(derivatives) > 1 else np.nan,
                            'neighborhood_size': neighborhood_mask.sum(),
                            'distance_from_op': distances[neighborhood_mask].mean()
                        })
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to calculate derivatives: {e}")
        
        return pd.DataFrame(results)