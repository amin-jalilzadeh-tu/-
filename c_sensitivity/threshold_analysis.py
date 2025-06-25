"""
c_sensitivity/threshold_analysis.py

Threshold and breakpoint detection for sensitivity analysis.
Identifies critical parameter values where system behavior changes.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from scipy import stats, signal
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class ThresholdAnalyzer:
    """
    Detects thresholds and breakpoints in parameter-output relationships.
    
    Features:
    - Automatic breakpoint detection
    - Piecewise sensitivity analysis
    - Critical value identification
    - Change point detection in time series
    
    Example usage:
        analyzer = ThresholdAnalyzer(data_manager, logger)
        config = {
            'min_segment_size': 10,
            'max_breakpoints': 3,
            'detection_method': 'tree'  # or 'statistical'
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
        Perform threshold analysis to identify breakpoints in sensitivity.
        
        Args:
            X: Input parameters DataFrame
            y: Output variables DataFrame
            config: Analysis configuration
            
        Returns:
            DataFrame with threshold analysis results
        """
        self.logger.info("Starting threshold analysis...")
        
        method = config.get('detection_method', 'tree')
        min_segment_size = config.get('min_segment_size', 10)
        max_breakpoints = config.get('max_breakpoints', 3)
        
        results = []
        
        # Analyze each parameter-output pair
        for param in X.select_dtypes(include=[np.number]).columns:
            for output in y.select_dtypes(include=[np.number]).columns:
                self.logger.debug(f"Analyzing thresholds for {param} -> {output}")
                
                # Detect breakpoints
                if method == 'tree':
                    breakpoints = self._tree_based_detection(
                        X[param].values, y[output].values,
                        max_breakpoints, min_segment_size
                    )
                elif method == 'statistical':
                    breakpoints = self._statistical_detection(
                        X[param].values, y[output].values,
                        max_breakpoints, min_segment_size
                    )
                elif method == 'pelt':
                    breakpoints = self._pelt_detection(
                        X[param].values, y[output].values,
                        min_segment_size
                    )
                else:
                    breakpoints = []
                
                # Calculate piecewise sensitivity
                if breakpoints:
                    segments = self._create_segments(X[param].values, breakpoints)
                    
                    for i, (start, end) in enumerate(segments):
                        segment_mask = (X[param] >= start) & (X[param] < end)
                        
                        if segment_mask.sum() >= min_segment_size:
                            # Calculate sensitivity for this segment
                            segment_sensitivity = self._calculate_segment_sensitivity(
                                X[param][segment_mask],
                                y[output][segment_mask]
                            )
                            
                            results.append({
                                'parameter': param,
                                'output_variable': output,
                                'sensitivity_score': segment_sensitivity['score'],
                                'method': 'threshold_analysis',
                                'segment_index': i,
                                'segment_start': start,
                                'segment_end': end,
                                'breakpoint_value': breakpoints[i] if i < len(breakpoints) else None,
                                'segment_size': segment_mask.sum(),
                                'segment_correlation': segment_sensitivity['correlation'],
                                'segment_slope': segment_sensitivity['slope'],
                                'is_critical_region': segment_sensitivity['score'] > 0.7
                            })
                else:
                    # No breakpoints found - single segment
                    sensitivity = self._calculate_segment_sensitivity(X[param], y[output])
                    
                    results.append({
                        'parameter': param,
                        'output_variable': output,
                        'sensitivity_score': sensitivity['score'],
                        'method': 'threshold_analysis',
                        'segment_index': 0,
                        'segment_start': X[param].min(),
                        'segment_end': X[param].max(),
                        'breakpoint_value': None,
                        'segment_size': len(X),
                        'segment_correlation': sensitivity['correlation'],
                        'segment_slope': sensitivity['slope'],
                        'is_critical_region': False
                    })
        
        df_results = pd.DataFrame(results)
        
        # Identify critical thresholds
        if not df_results.empty:
            df_results = self._identify_critical_thresholds(df_results)
        
        return df_results
    
    def _tree_based_detection(self,
                            x: np.ndarray,
                            y: np.ndarray,
                            max_breakpoints: int,
                            min_segment_size: int) -> List[float]:
        """Use decision trees to detect breakpoints"""
        
        if len(x) < 2 * min_segment_size:
            return []
        
        # Sort by x values
        sorted_idx = np.argsort(x)
        x_sorted = x[sorted_idx]
        y_sorted = y[sorted_idx]
        
        # Fit decision tree
        tree = DecisionTreeRegressor(
            max_leaf_nodes=max_breakpoints + 1,
            min_samples_leaf=min_segment_size
        )
        
        try:
            tree.fit(x_sorted.reshape(-1, 1), y_sorted)
            
            # Extract split points
            tree_structure = tree.tree_
            breakpoints = []
            
            def extract_splits(node_id):
                if tree_structure.children_left[node_id] != -1:  # Not a leaf
                    breakpoints.append(tree_structure.threshold[node_id])
                    extract_splits(tree_structure.children_left[node_id])
                    extract_splits(tree_structure.children_right[node_id])
            
            extract_splits(0)
            
            # Sort and remove duplicates
            breakpoints = sorted(list(set(breakpoints)))
            
            # Map thresholds back to original x values
            breakpoints = [self._find_nearest_x(x_sorted, bp) for bp in breakpoints]
            
            return breakpoints[:max_breakpoints]
            
        except Exception as e:
            self.logger.warning(f"Tree-based detection failed: {e}")
            return []
    
    def _statistical_detection(self,
                             x: np.ndarray,
                             y: np.ndarray,
                             max_breakpoints: int,
                             min_segment_size: int) -> List[float]:
        """Statistical change point detection using cumulative sums"""
        
        if len(x) < 2 * min_segment_size:
            return []
        
        # Sort by x values
        sorted_idx = np.argsort(x)
        x_sorted = x[sorted_idx]
        y_sorted = y[sorted_idx]
        
        # Calculate residuals from linear fit
        coeffs = np.polyfit(x_sorted, y_sorted, 1)
        y_pred = np.polyval(coeffs, x_sorted)
        residuals = y_sorted - y_pred
        
        # CUSUM test for change detection
        cusum = np.cumsum(residuals - np.mean(residuals))
        
        # Find peaks in CUSUM
        peaks, properties = signal.find_peaks(
            np.abs(cusum),
            distance=min_segment_size,
            prominence=np.std(cusum)
        )
        
        if len(peaks) > 0:
            # Sort by prominence and select top breakpoints
            prominences = properties['prominences']
            top_peaks = peaks[np.argsort(prominences)[-max_breakpoints:]]
            
            # Convert indices to x values
            breakpoints = [x_sorted[idx] for idx in sorted(top_peaks)]
            return breakpoints
        
        return []
    
    def _pelt_detection(self,
                       x: np.ndarray,
                       y: np.ndarray,
                       min_segment_size: int) -> List[float]:
        """
        Pruned Exact Linear Time (PELT) algorithm for change point detection.
        Simplified implementation.
        """
        if len(x) < 2 * min_segment_size:
            return []
        
        # Sort by x values
        sorted_idx = np.argsort(x)
        x_sorted = x[sorted_idx]
        y_sorted = y[sorted_idx]
        
        n = len(y_sorted)
        
        # Cost function (negative log likelihood for normal distribution)
        def segment_cost(start, end):
            if end - start < min_segment_size:
                return np.inf
            segment = y_sorted[start:end]
            if len(segment) == 0:
                return np.inf
            var = np.var(segment)
            if var == 0:
                var = 1e-10
            return len(segment) * (np.log(2 * np.pi * var) + 1)
        
        # Dynamic programming
        penalty = 2 * np.log(n)  # BIC penalty
        F = np.zeros(n + 1)
        changepoints = {0: []}
        
        for t in range(min_segment_size, n + 1):
            candidates = []
            for s in range(t - min_segment_size + 1):
                cost = F[s] + segment_cost(s, t) + penalty
                candidates.append((cost, s))
            
            best_cost, best_s = min(candidates)
            F[t] = best_cost
            changepoints[t] = changepoints[best_s] + [best_s] if best_s > 0 else []
        
        # Get final changepoints
        final_changepoints = changepoints[n]
        
        # Convert to x values
        breakpoints = [x_sorted[cp] for cp in final_changepoints if 0 < cp < n]
        
        return breakpoints
    
    def _create_segments(self, x: np.ndarray, breakpoints: List[float]) -> List[Tuple[float, float]]:
        """Create segments from breakpoints"""
        segments = []
        
        # Sort breakpoints
        breakpoints_sorted = sorted(breakpoints)
        
        # Add min and max as boundaries
        boundaries = [x.min()] + breakpoints_sorted + [x.max() + 1e-10]
        
        # Create segments
        for i in range(len(boundaries) - 1):
            segments.append((boundaries[i], boundaries[i + 1]))
        
        return segments
    
    def _calculate_segment_sensitivity(self,
                                     x: pd.Series,
                                     y: pd.Series) -> Dict[str, float]:
        """Calculate sensitivity measures for a segment"""
        
        if len(x) < 2:
            return {'score': 0, 'correlation': 0, 'slope': 0}
        
        # Remove NaN values
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return {'score': 0, 'correlation': 0, 'slope': 0}
        
        # Calculate correlation
        correlation = x_clean.corr(y_clean)
        if np.isnan(correlation):
            correlation = 0
        
        # Calculate slope (normalized)
        if x_clean.std() > 0:
            slope = np.polyfit(x_clean, y_clean, 1)[0]
            # Normalize by standard deviations
            normalized_slope = slope * x_clean.std() / (y_clean.std() + 1e-10)
        else:
            slope = 0
            normalized_slope = 0
        
        # Combined sensitivity score
        score = np.sqrt(correlation**2 + normalized_slope**2) / np.sqrt(2)
        
        return {
            'score': abs(score),
            'correlation': correlation,
            'slope': slope
        }
    
    def _find_nearest_x(self, x_sorted: np.ndarray, threshold: float) -> float:
        """Find the nearest actual x value to a threshold"""
        idx = np.argmin(np.abs(x_sorted - threshold))
        return x_sorted[idx]
    
    def _identify_critical_thresholds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify which thresholds are critical based on sensitivity changes"""
        
        # Group by parameter and output
        for (param, output), group in df.groupby(['parameter', 'output_variable']):
            if len(group) > 1:
                # Calculate sensitivity change across segments
                sensitivities = group.sort_values('segment_index')['sensitivity_score'].values
                
                # Find maximum change
                max_change_idx = np.argmax(np.abs(np.diff(sensitivities)))
                
                # Mark the breakpoint with maximum change as critical
                critical_breakpoint_idx = group.iloc[max_change_idx]['segment_index']
                
                df.loc[
                    (df['parameter'] == param) & 
                    (df['output_variable'] == output) & 
                    (df['segment_index'] == critical_breakpoint_idx),
                    'is_critical_threshold'
                ] = True
            else:
                df.loc[group.index, 'is_critical_threshold'] = False
        
        return df
    
    def detect_nonlinear_thresholds(self,
                                  X: pd.DataFrame,
                                  y: pd.DataFrame,
                                  config: Dict[str, Any]) -> pd.DataFrame:
        """
        Detect thresholds in nonlinear relationships using polynomial fitting.
        """
        degree = config.get('polynomial_degree', 3)
        threshold_significance = config.get('threshold_significance', 0.1)
        
        results = []
        
        for param in X.select_dtypes(include=[np.number]).columns:
            for output in y.select_dtypes(include=[np.number]).columns:
                # Sort data
                sorted_idx = X[param].argsort()
                x_sorted = X[param].iloc[sorted_idx].values
                y_sorted = y[output].iloc[sorted_idx].values
                
                # Fit polynomial
                try:
                    coeffs = np.polyfit(x_sorted, y_sorted, degree)
                    poly = np.poly1d(coeffs)
                    
                    # Find critical points (where derivative changes sign)
                    poly_derivative = np.polyder(poly)
                    critical_points = np.roots(poly_derivative)
                    
                    # Filter real critical points within data range
                    real_critical = [
                        cp.real for cp in critical_points 
                        if np.isreal(cp) and x_sorted.min() <= cp.real <= x_sorted.max()
                    ]
                    
                    # Evaluate second derivative to classify critical points
                    poly_second_derivative = np.polyder(poly_derivative)
                    
                    for cp in real_critical:
                        second_deriv = poly_second_derivative(cp)
                        
                        # Check if it's a significant threshold
                        y_range = y_sorted.max() - y_sorted.min()
                        threshold_change = abs(poly(cp + 0.01) - poly(cp - 0.01))
                        
                        if threshold_change / y_range > threshold_significance:
                            results.append({
                                'parameter': param,
                                'output_variable': output,
                                'method': 'nonlinear_threshold',
                                'critical_point': cp,
                                'critical_type': 'minimum' if second_deriv > 0 else 'maximum',
                                'second_derivative': second_deriv,
                                'threshold_significance': threshold_change / y_range,
                                'polynomial_degree': degree
                            })
                            
                except Exception as e:
                    self.logger.warning(f"Nonlinear threshold detection failed for {param}->{output}: {e}")
        
        return pd.DataFrame(results)