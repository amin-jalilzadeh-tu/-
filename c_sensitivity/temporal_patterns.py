"""
c_sensitivity/temporal_patterns.py

Advanced temporal pattern analysis for time-varying sensitivity.
Includes Fourier analysis, time-lag detection, and dynamic tracking.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from scipy import signal, stats, fft
from scipy.interpolate import interp1d
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class TemporalPatternsAnalyzer:
    """
    Analyzes temporal patterns in sensitivity over time.
    
    Features:
    - Fourier analysis of sensitivity patterns
    - Time-lagged sensitivity effects
    - Dynamic sensitivity evolution tracking
    - Seasonal pattern detection
    - Trend analysis
    
    Example usage:
        analyzer = TemporalPatternsAnalyzer(data_manager, logger)
        config = {
            'time_column': 'DateTime',
            'frequency_analysis': True,
            'max_lag': 24,  # hours
            'window_size': 168,  # 1 week in hours
            'detect_seasonality': True
        }
        results = analyzer.analyze(X, y, base_sensitivity_df, config)
    """
    
    def __init__(self, data_manager, logger: Optional[logging.Logger] = None):
        self.data_manager = data_manager
        self.logger = logger or logging.getLogger(__name__)
        
    def analyze(self,
                X: pd.DataFrame,
                y: pd.DataFrame,
                base_sensitivity_df: pd.DataFrame,
                config: Dict[str, Any]) -> pd.DataFrame:
        """
        Perform temporal pattern analysis on sensitivity results.
        
        Args:
            X: Input parameters DataFrame with time column
            y: Output variables DataFrame with time column
            base_sensitivity_df: Time-resolved sensitivity results
            config: Analysis configuration
            
        Returns:
            DataFrame with temporal pattern analysis results
        """
        self.logger.info("Starting temporal pattern analysis...")
        
        if config is None:
            config = {}
        if config is None:
            config = {}
        if config is None:
            config = {}
        if config is None:
            config = {}
        time_column = config.get('time_column', 'DateTime')
        frequency_analysis = config.get('frequency_analysis', True)
        max_lag = config.get('max_lag', 24)
        window_size = config.get('window_size', 168)
        detect_seasonality = config.get('detect_seasonality', True)
        
        results = []
        
        # Ensure time column exists
        if time_column not in X.columns:
            self.logger.error(f"Time column '{time_column}' not found in data.")
            raise ValueError(f"Time column '{time_column}' not found in data. Cannot perform temporal pattern analysis.")
        
        # Sort by time
        X = X.sort_values(time_column)
        y = y.sort_values(time_column) if time_column in y.columns else y
        
        # Analyze each parameter-output pair
        unique_pairs = base_sensitivity_df[['parameter', 'output_variable']].drop_duplicates()
        
        for _, pair in unique_pairs.iterrows():
            param = pair['parameter']
            output = pair['output_variable']
            
            self.logger.debug(f"Analyzing temporal patterns for {param} -> {output}")
            
            # Calculate time-varying sensitivity
            time_sensitivity = self._calculate_time_varying_sensitivity(
                X, y, param, output, time_column, window_size
            )
            
            if len(time_sensitivity) < 10:
                continue
            
            # Frequency analysis
            if frequency_analysis:
                freq_results = self._fourier_analysis(time_sensitivity)
                
                results.append({
                    'parameter': param,
                    'output_variable': output,
                    'method': 'fourier_analysis',
                    'dominant_frequency': freq_results['dominant_freq'],
                    'dominant_period': freq_results['dominant_period'],
                    'frequency_power': freq_results['power'],
                    'frequency_components': freq_results['top_frequencies'],
                    'temporal_variance': np.var(time_sensitivity['sensitivity'])
                })
            
            # Time-lag analysis
            lag_results = self._time_lag_analysis(
                X, y, param, output, time_column, max_lag
            )
            
            if lag_results:
                results.append({
                    'parameter': param,
                    'output_variable': output,
                    'method': 'time_lag_analysis',
                    'optimal_lag': lag_results['optimal_lag'],
                    'lag_correlation': lag_results['max_correlation'],
                    'lag_profile': lag_results['lag_profile'],
                    'lag_significance': lag_results['significance']
                })
            
            # Trend analysis
            trend_results = self._trend_analysis(time_sensitivity)
            
            results.append({
                'parameter': param,
                'output_variable': output,
                'method': 'trend_analysis',
                'trend_slope': trend_results['slope'],
                'trend_significance': trend_results['p_value'],
                'trend_r_squared': trend_results['r_squared'],
                'is_stationary': trend_results['is_stationary']
            })
            
            # Seasonality detection
            if detect_seasonality:
                seasonal_results = self._detect_seasonality(time_sensitivity)
                
                if seasonal_results['has_seasonality']:
                    results.append({
                        'parameter': param,
                        'output_variable': output,
                        'method': 'seasonality_detection',
                        'has_seasonality': True,
                        'seasonal_period': seasonal_results['period'],
                        'seasonal_strength': seasonal_results['strength'],
                        'seasonal_pattern': seasonal_results['pattern']
                    })
            
            # Dynamic sensitivity tracking
            dynamic_results = self._track_dynamic_sensitivity(
                time_sensitivity, config.get('change_threshold', 0.1)
            )
            
            results.append({
                'parameter': param,
                'output_variable': output,
                'method': 'dynamic_tracking',
                'n_regime_changes': dynamic_results['n_changes'],
                'change_points': dynamic_results['change_points'],
                'stability_periods': dynamic_results['stability_periods'],
                'volatility': dynamic_results['volatility']
            })
        
        return pd.DataFrame(results)
    
    def _calculate_time_varying_sensitivity(self,
                                          X: pd.DataFrame,
                                          y: pd.DataFrame,
                                          param: str,
                                          output: str,
                                          time_column: str,
                                          window_size: int) -> pd.DataFrame:
        """Calculate sensitivity in sliding time windows"""
        
        if param not in X.columns or output not in y.columns:
            return pd.DataFrame()
        
        times = []
        sensitivities = []
        
        # Sliding window analysis
        for i in range(window_size, len(X), window_size // 4):  # 25% overlap
            window_end = min(i, len(X))
            window_start = window_end - window_size
            
            if window_start < 0:
                continue
            
            # Get window data
            X_window = X.iloc[window_start:window_end]
            y_window = y.iloc[window_start:window_end] if len(y) == len(X) else y
            
            # Calculate sensitivity for this window
            if len(X_window) > 10:
                corr = X_window[param].corr(y_window[output])
                
                if not np.isnan(corr):
                    # Window center time
                    center_idx = (window_start + window_end) // 2
                    times.append(X.iloc[center_idx][time_column])
                    sensitivities.append(abs(corr))
        
        return pd.DataFrame({
            'time': times,
            'sensitivity': sensitivities
        })
    
    def _fourier_analysis(self, time_sensitivity: pd.DataFrame) -> Dict[str, Any]:
        """Perform Fourier analysis on time-varying sensitivity"""
        
        if len(time_sensitivity) < 10:
            return {
                'dominant_freq': 0,
                'dominant_period': np.inf,
                'power': 0,
                'top_frequencies': []
            }
        
        # Interpolate to regular time grid
        sensitivity_values = time_sensitivity['sensitivity'].values
        
        # Remove mean
        sensitivity_centered = sensitivity_values - np.mean(sensitivity_values)
        
        # Apply window to reduce spectral leakage
        window = signal.hann(len(sensitivity_centered))
        sensitivity_windowed = sensitivity_centered * window
        
        # Compute FFT
        fft_values = fft.fft(sensitivity_windowed)
        frequencies = fft.fftfreq(len(sensitivity_windowed))
        
        # Get power spectrum (positive frequencies only)
        power = np.abs(fft_values[:len(fft_values)//2])**2
        pos_frequencies = frequencies[:len(frequencies)//2]
        
        # Find dominant frequency
        if len(power) > 0 and np.max(power) > 0:
            dominant_idx = np.argmax(power[1:]) + 1  # Skip DC component
            dominant_freq = pos_frequencies[dominant_idx]
            dominant_period = 1 / dominant_freq if dominant_freq > 0 else np.inf
            
            # Get top 3 frequencies
            top_indices = np.argsort(power[1:])[-3:] + 1
            top_frequencies = [
                {
                    'frequency': pos_frequencies[idx],
                    'period': 1 / pos_frequencies[idx] if pos_frequencies[idx] > 0 else np.inf,
                    'power': power[idx]
                }
                for idx in reversed(top_indices)
            ]
        else:
            dominant_freq = 0
            dominant_period = np.inf
            top_frequencies = []
        
        return {
            'dominant_freq': dominant_freq,
            'dominant_period': dominant_period,
            'power': np.max(power) if len(power) > 0 else 0,
            'top_frequencies': top_frequencies
        }
    
    def _time_lag_analysis(self,
                         X: pd.DataFrame,
                         y: pd.DataFrame,
                         param: str,
                         output: str,
                         time_column: str,
                         max_lag: int) -> Optional[Dict[str, Any]]:
        """Analyze time-lagged effects between parameters and outputs"""
        
        if param not in X.columns or output not in y.columns:
            return None
        
        # Ensure same length
        min_len = min(len(X), len(y))
        X_param = X[param].iloc[:min_len].values
        y_output = y[output].iloc[:min_len].values
        
        lag_correlations = []
        
        # Test different lags
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                # Parameter leads output
                x_lagged = X_param[:lag]
                y_lagged = y_output[-lag:]
            elif lag > 0:
                # Output leads parameter
                x_lagged = X_param[lag:]
                y_lagged = y_output[:-lag]
            else:
                # No lag
                x_lagged = X_param
                y_lagged = y_output
            
            if len(x_lagged) > 10:
                corr, p_value = stats.pearsonr(x_lagged, y_lagged)
                lag_correlations.append({
                    'lag': lag,
                    'correlation': corr,
                    'p_value': p_value
                })
        
        if not lag_correlations:
            return None
        
        # Find optimal lag
        lag_df = pd.DataFrame(lag_correlations)
        optimal_idx = lag_df['correlation'].abs().idxmax()
        optimal_lag = lag_df.iloc[optimal_idx]['lag']
        max_correlation = lag_df.iloc[optimal_idx]['correlation']
        significance = lag_df.iloc[optimal_idx]['p_value']
        
        return {
            'optimal_lag': optimal_lag,
            'max_correlation': max_correlation,
            'lag_profile': lag_correlations,
            'significance': significance
        }
    
    def _trend_analysis(self, time_sensitivity: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trends in time-varying sensitivity"""
        
        if len(time_sensitivity) < 3:
            return {
                'slope': 0,
                'p_value': 1,
                'r_squared': 0,
                'is_stationary': True
            }
        
        # Create time index
        time_index = np.arange(len(time_sensitivity))
        sensitivity_values = time_sensitivity['sensitivity'].values
        
        # Linear trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            time_index, sensitivity_values
        )
        
        # Test for stationarity (simplified Dickey-Fuller test)
        # Check if detrended series has unit root
        detrended = sensitivity_values - (slope * time_index + intercept)
        
        # Simple stationarity check: compare variance of first and second half
        mid_point = len(detrended) // 2
        var_first_half = np.var(detrended[:mid_point])
        var_second_half = np.var(detrended[mid_point:])
        
        # F-test for equal variances
        f_stat = var_first_half / var_second_half if var_second_half > 0 else 1
        p_value_stationarity = 2 * min(
            stats.f.cdf(f_stat, mid_point - 1, len(detrended) - mid_point - 1),
            1 - stats.f.cdf(f_stat, mid_point - 1, len(detrended) - mid_point - 1)
        )
        
        is_stationary = p_value_stationarity > 0.05
        
        return {
            'slope': slope,
            'p_value': p_value,
            'r_squared': r_value**2,
            'is_stationary': is_stationary
        }
    
    def _detect_seasonality(self, time_sensitivity: pd.DataFrame) -> Dict[str, Any]:
        """Detect seasonal patterns in sensitivity"""
        
        if len(time_sensitivity) < 24:  # Need at least 24 points
            return {'has_seasonality': False}
        
        sensitivity_values = time_sensitivity['sensitivity'].values
        
        # Try different seasonal periods
        potential_periods = [24, 168, 720]  # Daily, weekly, monthly (in hours)
        best_period = None
        best_strength = 0
        
        for period in potential_periods:
            if len(sensitivity_values) >= 2 * period:
                # Compute autocorrelation at this lag
                acf_value = np.corrcoef(
                    sensitivity_values[:-period],
                    sensitivity_values[period:]
                )[0, 1]
                
                if abs(acf_value) > best_strength:
                    best_strength = abs(acf_value)
                    best_period = period
        
        # Significant seasonality threshold
        if best_strength > 0.3 and best_period is not None:
            # Extract seasonal pattern
            n_cycles = len(sensitivity_values) // best_period
            seasonal_pattern = []
            
            for i in range(best_period):
                values_at_phase = [
                    sensitivity_values[j * best_period + i]
                    for j in range(n_cycles)
                    if j * best_period + i < len(sensitivity_values)
                ]
                seasonal_pattern.append(np.mean(values_at_phase))
            
            return {
                'has_seasonality': True,
                'period': best_period,
                'strength': best_strength,
                'pattern': seasonal_pattern
            }
        
        return {'has_seasonality': False}
    
    def _track_dynamic_sensitivity(self,
                                 time_sensitivity: pd.DataFrame,
                                 change_threshold: float) -> Dict[str, Any]:
        """Track dynamic changes in sensitivity over time"""
        
        if len(time_sensitivity) < 10:
            return {
                'n_changes': 0,
                'change_points': [],
                'stability_periods': [],
                'volatility': 0
            }
        
        sensitivity_values = time_sensitivity['sensitivity'].values
        
        # Calculate rolling statistics
        window = min(10, len(sensitivity_values) // 4)
        rolling_mean = pd.Series(sensitivity_values).rolling(window, center=True).mean()
        rolling_std = pd.Series(sensitivity_values).rolling(window, center=True).std()
        
        # Detect change points (simplified CUSUM)
        mean_sensitivity = np.mean(sensitivity_values)
        cusum = np.cumsum(sensitivity_values - mean_sensitivity)
        
        # Find peaks in CUSUM
        peaks, _ = signal.find_peaks(np.abs(cusum), prominence=change_threshold)
        
        # Identify stability periods
        stability_periods = []
        change_points = list(peaks)
        
        if len(change_points) > 0:
            # Add start and end
            boundaries = [0] + change_points.tolist() + [len(sensitivity_values) - 1]
            
            for i in range(len(boundaries) - 1):
                start = boundaries[i]
                end = boundaries[i + 1]
                
                if end - start > window:
                    period_std = np.std(sensitivity_values[start:end])
                    stability_periods.append({
                        'start': start,
                        'end': end,
                        'duration': end - start,
                        'mean_sensitivity': np.mean(sensitivity_values[start:end]),
                        'stability': 1 / (1 + period_std)
                    })
        
        # Calculate overall volatility
        volatility = np.mean(rolling_std.dropna()) if len(rolling_std.dropna()) > 0 else 0
        
        return {
            'n_changes': len(change_points),
            'change_points': change_points,
            'stability_periods': stability_periods,
            'volatility': volatility
        }
    
    def analyze_sensitivity_dynamics(self,
                                   X: pd.DataFrame,
                                   y: pd.DataFrame,
                                   time_column: str,
                                   config: Dict[str, Any]) -> pd.DataFrame:
        """
        Analyze how sensitivity evolves dynamically over time.
        """
        window_type = config.get('window_type', 'sliding')  # 'sliding' or 'expanding'
        window_size = config.get('window_size', 168)
        step_size = config.get('step_size', 24)
        
        results = []
        
        # Sort by time
        X_sorted = X.sort_values(time_column)
        y_sorted = y.sort_values(time_column) if time_column in y.columns else y
        
        # Analyze each parameter-output pair
        for param in X.select_dtypes(include=[np.number]).columns:
            for output in y.select_dtypes(include=[np.number]).columns:
                
                sensitivity_evolution = []
                
                if window_type == 'sliding':
                    # Sliding window
                    for start in range(0, len(X_sorted) - window_size, step_size):
                        end = start + window_size
                        
                        X_window = X_sorted.iloc[start:end]
                        y_window = y_sorted.iloc[start:end] if len(y_sorted) == len(X_sorted) else y_sorted
                        
                        # Calculate sensitivity
                        corr = X_window[param].corr(y_window[output])
                        
                        if not np.isnan(corr):
                            sensitivity_evolution.append({
                                'time': X_window.iloc[window_size//2][time_column],
                                'window_start': X_window.iloc[0][time_column],
                                'window_end': X_window.iloc[-1][time_column],
                                'sensitivity': abs(corr),
                                'sample_size': len(X_window)
                            })
                
                elif window_type == 'expanding':
                    # Expanding window
                    for end in range(window_size, len(X_sorted), step_size):
                        X_window = X_sorted.iloc[:end]
                        y_window = y_sorted.iloc[:end] if len(y_sorted) == len(X_sorted) else y_sorted
                        
                        # Calculate sensitivity
                        corr = X_window[param].corr(y_window[output])
                        
                        if not np.isnan(corr):
                            sensitivity_evolution.append({
                                'time': X_window.iloc[-1][time_column],
                                'window_start': X_window.iloc[0][time_column],
                                'window_end': X_window.iloc[-1][time_column],
                                'sensitivity': abs(corr),
                                'sample_size': len(X_window)
                            })
                
                if sensitivity_evolution:
                    evolution_df = pd.DataFrame(sensitivity_evolution)
                    
                    results.append({
                        'parameter': param,
                        'output_variable': output,
                        'method': 'sensitivity_dynamics',
                        'window_type': window_type,
                        'evolution_mean': evolution_df['sensitivity'].mean(),
                        'evolution_std': evolution_df['sensitivity'].std(),
                        'evolution_trend': stats.linregress(
                            range(len(evolution_df)), 
                            evolution_df['sensitivity']
                        ).slope,
                        'evolution_data': sensitivity_evolution
                    })
        
        return pd.DataFrame(results)