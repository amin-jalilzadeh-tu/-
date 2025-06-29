"""
c_sensitivity/base_analyzer.py

Base class with common functionality for all sensitivity analyzers.
Updated to include optional methods for advanced analysis features.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from abc import ABC, abstractmethod
import json
from datetime import datetime
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class BaseSensitivityAnalyzer(ABC):
    """Base class for all sensitivity analyzers"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger or logging.getLogger(__name__)
        
        # Define common paths
        self.base_parsed_dir = self.job_output_dir / "parsed_data"
        self.modified_parsed_dir = self.job_output_dir / "parsed_modified_results"
        self.modifications_dir = self.job_output_dir / "modified_idfs"
        self.validation_dir = self.job_output_dir / "validation_results"
        
        # Data containers
        self.base_results = {}
        self.modified_results = {}
        self.parameter_data = None
        self.output_deltas = None
        self.validation_scores = {}
        self.time_slice_config = None
        self.config = {}  # Configuration dictionary
        
        # Cache for loaded data
        self._cache = {}
        
    @abstractmethod
    def calculate_sensitivity(self, **kwargs) -> pd.DataFrame:
        """Calculate sensitivity scores - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_analysis_type(self) -> str:
        """Return the type of analysis performed"""
        pass
    
    # ===== OPTIONAL METHODS FOR ADVANCED FEATURES =====
    # These methods provide default implementations that can be overridden
    # by subclasses that support advanced analysis features
    
    def calculate_uncertainty(self, 
                            base_results: pd.DataFrame,
                            config: Dict[str, Any],
                            **kwargs) -> pd.DataFrame:
        """
        Calculate uncertainty bounds on sensitivity indices.
        
        This is an optional method that can be overridden by analyzers
        that support uncertainty quantification.
        
        Args:
            base_results: Base sensitivity results
            config: Uncertainty configuration
            **kwargs: Additional arguments
            
        Returns:
            DataFrame with uncertainty bounds
        """
        self.logger.warning(f"{self.get_analysis_type()} analyzer does not implement uncertainty calculation")
        return pd.DataFrame()
    
    def detect_thresholds(self,
                         X: pd.DataFrame,
                         y: pd.DataFrame,
                         config: Dict[str, Any],
                         **kwargs) -> pd.DataFrame:
        """
        Detect parameter thresholds where behavior changes.
        
        This is an optional method for analyzers that support
        threshold/breakpoint detection.
        
        Args:
            X: Input parameters
            y: Output variables
            config: Threshold detection configuration
            **kwargs: Additional arguments
            
        Returns:
            DataFrame with detected thresholds
        """
        self.logger.warning(f"{self.get_analysis_type()} analyzer does not implement threshold detection")
        return pd.DataFrame()
    
    def calculate_regional_sensitivity(self,
                                     X: pd.DataFrame,
                                     y: pd.DataFrame,
                                     config: Dict[str, Any],
                                     **kwargs) -> pd.DataFrame:
        """
        Calculate sensitivity in different regions of parameter space.
        
        This is an optional method for analyzers that support
        regional sensitivity analysis.
        
        Args:
            X: Input parameters
            y: Output variables
            config: Regional analysis configuration
            **kwargs: Additional arguments
            
        Returns:
            DataFrame with regional sensitivity results
        """
        self.logger.warning(f"{self.get_analysis_type()} analyzer does not implement regional sensitivity")
        return pd.DataFrame()
    
    def analyze_temporal_patterns(self,
                                time_series_results: pd.DataFrame,
                                config: Dict[str, Any],
                                **kwargs) -> pd.DataFrame:
        """
        Analyze temporal patterns in sensitivity over time.
        
        This is an optional method for analyzers that support
        temporal pattern analysis.
        
        Args:
            time_series_results: Time-resolved sensitivity results
            config: Temporal analysis configuration
            **kwargs: Additional arguments
            
        Returns:
            DataFrame with temporal pattern results
        """
        self.logger.warning(f"{self.get_analysis_type()} analyzer does not implement temporal pattern analysis")
        return pd.DataFrame()
    
    def perform_variance_decomposition(self,
                                     X: pd.DataFrame,
                                     y: pd.DataFrame,
                                     config: Dict[str, Any],
                                     **kwargs) -> pd.DataFrame:
        """
        Perform variance-based sensitivity decomposition (e.g., Sobol).
        
        This is an optional method for analyzers that support
        variance decomposition methods.
        
        Args:
            X: Input parameters
            y: Output variables
            config: Variance decomposition configuration
            **kwargs: Additional arguments
            
        Returns:
            DataFrame with variance decomposition results
        """
        self.logger.warning(f"{self.get_analysis_type()} analyzer does not implement variance decomposition")
        return pd.DataFrame()
    
    # ===== HELPER METHODS FOR ADVANCED ANALYSIS =====
    
    def prepare_data_for_advanced_analysis(self,
                                         result_type: str = 'daily') -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare X and y data matrices for advanced analysis methods.
        
        Returns:
            Tuple of (X, y) DataFrames
        """
        # Try to load parameter data
        X = pd.DataFrame()
        param_files = list(self.base_parsed_dir.glob("parameters/*.parquet"))
        if param_files:
            try:
                X = pd.concat([pd.read_parquet(f) for f in param_files], axis=1)
            except Exception as e:
                self.logger.warning(f"Could not load parameter data: {e}")
        
        # Try to load output data
        y = pd.DataFrame()
        output_files = list(self.base_parsed_dir.glob(f"outputs/{result_type}/*.parquet"))
        if output_files:
            try:
                y = pd.concat([pd.read_parquet(f) for f in output_files], axis=1)
            except Exception as e:
                self.logger.warning(f"Could not load output data: {e}")
        
        return X, y
    
    def get_parameter_bounds(self, X: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
        """
        Extract parameter bounds from data.
        
        Args:
            X: Parameter DataFrame
            
        Returns:
            Dictionary mapping parameter names to (min, max) tuples
        """
        bounds = {}
        for col in X.select_dtypes(include=[np.number]).columns:
            bounds[col] = (X[col].min(), X[col].max())
        return bounds
    
    def validate_advanced_config(self, config: Dict[str, Any], method: str) -> bool:
        """
        Validate configuration for advanced analysis methods.
        
        Args:
            config: Configuration dictionary
            method: Analysis method name
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = {
            'uncertainty': ['n_samples', 'confidence_level'],
            'threshold': ['min_segment_size', 'max_breakpoints'],
            'regional': ['n_regions', 'region_method'],
            'sobol': ['n_samples', 'sampling_method'],
            'temporal': ['time_column', 'window_size']
        }
        
        if method not in required_keys:
            self.logger.warning(f"Unknown advanced method: {method}")
            return False
        
        missing_keys = [k for k in required_keys[method] if k not in config]
        if missing_keys:
            self.logger.error(f"Missing required keys for {method}: {missing_keys}")
            return False
        
        return True
    
    # ===== EXISTING METHODS (keep all of these unchanged) =====
    
    def load_simulation_results(self, 
                              result_type: str = 'daily',
                              categories: Optional[List[str]] = None,
                              use_cache: bool = True,
                              time_slice_config: Optional[Dict[str, any]] = None) -> Tuple[Dict, Dict]:
        """Load base and modified simulation results using new data format"""
        # Import required modules
        from .time_slicer import TimeSlicer
        from .data_manager import SensitivityDataManager
        
        time_slicer = TimeSlicer(self.logger)
        data_manager = SensitivityDataManager(self.job_output_dir, self.logger)
        
        # Store time slice config for later use
        self.time_slice_config = time_slice_config
        
        # Validate time slice config if provided
        if time_slice_config and time_slice_config.get('enabled', False):
            valid, errors = time_slicer.validate_time_slice_config(time_slice_config)
            if not valid:
                self.logger.error(f"Invalid time slice configuration: {errors}")
                time_slice_config = None
        
        # Create cache key including time slice info
        cache_key = f"results_{result_type}_{categories}"
        if time_slice_config and time_slice_config.get('enabled', False):
            slice_type = time_slice_config.get('slice_type', 'none')
            cache_key += f"_{slice_type}"
        
        if use_cache and cache_key in self._cache:
            self.logger.debug(f"Using cached results for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Loading {result_type} simulation results using new format...")
        
        # Use data manager to load results
        results = data_manager.load_simulation_results(
            result_type=result_type,
            variables=None,  # Load all variables
            load_modified=True,
            time_slice_config=time_slice_config
        )
        
        # Extract base and modified results
        base_results = results.get('base', {})
        modified_results = results.get('modified', {})
        
        # If we have comparison data, use it for modified results
        if 'comparison_data' in results and results['comparison_data']:
            # For backward compatibility, create modified results from comparison data
            if not modified_results:
                modified_results = self._create_modified_from_comparison(results['comparison_data'])
        
        self.logger.info(f"Loaded {len(base_results)} base categories and {len(modified_results)} modified categories")
        
        # Log time slice summary if applied
        if time_slice_config and time_slice_config.get('enabled', False) and base_results:
            # Get summary from first available dataset
            for category, df in base_results.items():
                if not df.empty and 'timestamp' in df.columns:
                    summary = time_slicer.get_time_slice_summary(df, 'timestamp')
                    self.logger.info(f"Time slice summary: {summary['total_records']} records")
                    break
        
        # Cache results
        self._cache[cache_key] = (base_results, modified_results)
        
        self.base_results = base_results
        self.modified_results = modified_results
        
        return base_results, modified_results
    
    def _create_modified_from_comparison(self, comparison_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Create modified results from comparison data for backward compatibility"""
        modified_results = {}
        
        for var_name, df in comparison_data.items():
            # Get first variant as modified
            variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
            if variant_cols:
                # Create modified dataframe
                mod_df = df[['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units']].copy()
                mod_df['Value'] = df[variant_cols[0]]  # Use first variant
                mod_df.rename(columns={'variable_name': 'Variable'}, inplace=True)
                
                # Group by category
                category = df['category'].iloc[0] if 'category' in df.columns else 'unknown'
                if category not in modified_results:
                    modified_results[category] = mod_df
                else:
                    modified_results[category] = pd.concat([modified_results[category], mod_df])
        
        return modified_results
    
    
    def calculate_output_deltas(self, 
                              output_variables: List[str],
                              aggregation: str = 'sum',
                              groupby: Optional[List[str]] = None) -> pd.DataFrame:
        """Calculate changes in outputs between base and modified runs"""
        self.logger.info("Calculating output deltas...")
        
        # Use data manager for delta calculation
        from .data_manager import SensitivityDataManager
        data_manager = SensitivityDataManager(self.job_output_dir, self.logger)
        
        # Load simulation results if not already loaded
        if not hasattr(self, 'simulation_results') or not self.simulation_results:
            results = data_manager.load_simulation_results(
                result_type=self.config.get('result_frequency', 'daily'),
                variables=output_variables,
                load_modified=True,
                time_slice_config=self.time_slice_config
            )
            self.simulation_results = results
        else:
            results = self.simulation_results
        
        # Use comparison data if available
        if 'comparison_data' in results and results['comparison_data']:
            self.logger.info("Using comparison data for delta calculation")
            data_manager.simulation_results = results
            return data_manager._extract_output_deltas(output_variables)
        
        # Otherwise, calculate from base and modified
        if not self.base_results or not self.modified_results:
            raise ValueError("No comparison data or base/modified results available")
        
        # Determine grouping
        if groupby is None:
            groupby = ['building_id']
        
        # Simplified delta calculation using new format
        delta_records = []
        
        for category, base_df in self.base_results.items():
            if category not in self.modified_results:
                continue
                
            mod_df = self.modified_results[category]
            
            # Process each requested variable
            for var_name in output_variables:
                var_clean = var_name.split('[')[0].strip()
                
                # Filter data for this variable
                base_var_data = base_df[base_df['Variable'].str.contains(var_clean, case=False, na=False)]
                mod_var_data = mod_df[mod_df['Variable'].str.contains(var_clean, case=False, na=False)]
                
                if not base_var_data.empty and not mod_var_data.empty:
                    # Group by building_id
                    base_grouped = base_var_data.groupby(groupby)['Value'].agg(aggregation)
                    mod_grouped = mod_var_data.groupby(groupby)['Value'].agg(aggregation)
                    
                    # Calculate deltas
                    for idx in base_grouped.index:
                        if idx in mod_grouped.index:
                            base_val = base_grouped[idx]
                            mod_val = mod_grouped[idx]
                            
                            delta_record = {
                                'category': category,
                                'variable': var_clean,
                                'variable_clean': var_clean,
                                f'{var_clean}_base': base_val,
                                f'{var_clean}_modified': mod_val,
                                f'{var_clean}_delta': mod_val - base_val,
                                f'{var_clean}_pct_change': ((mod_val - base_val) / base_val * 100) if base_val != 0 else 0
                            }
                            
                            # Add groupby values
                            if isinstance(idx, tuple):
                                for i, gb_col in enumerate(groupby):
                                    delta_record[gb_col] = idx[i]
                            else:
                                delta_record[groupby[0]] = idx
                            
                            delta_records.append(delta_record)
        
        df_deltas = pd.DataFrame(delta_records)
        self.output_deltas = df_deltas
        
        # Log summary of deltas with time slice info
        if not df_deltas.empty:
            self.logger.info(f"Calculated {len(df_deltas)} output deltas")
            if self.time_slice_config and self.time_slice_config.get('enabled', False):
                self.logger.info(f"Time slice applied: {self.time_slice_config.get('slice_type')}")
        
        return df_deltas
    
    def load_validation_scores(self) -> Dict[str, pd.DataFrame]:
        """Load validation results for weighting sensitivity"""
        self.logger.info("Loading validation scores...")
        
        validation_scores = {}
        
        # Load baseline validation
        baseline_path = self.validation_dir / "validation_summary_baseline.parquet"
        if baseline_path.exists():
            validation_scores['baseline'] = pd.read_parquet(baseline_path)
        
        # Load modified validation
        modified_path = self.validation_dir / "validation_summary_modified.parquet"
        if modified_path.exists():
            validation_scores['modified'] = pd.read_parquet(modified_path)
        
        self.validation_scores = validation_scores
        return validation_scores
    
    def weight_by_validation(self, 
                           sensitivity_df: pd.DataFrame,
                           weight_column: str = 'sensitivity_score') -> pd.DataFrame:
        """Apply validation-based weighting to sensitivity scores"""
        if not self.validation_scores:
            self.logger.warning("No validation scores available for weighting")
            return sensitivity_df
        
        # Get modified validation scores (or baseline if modified not available)
        val_df = self.validation_scores.get('modified', self.validation_scores.get('baseline'))
        
        if val_df is None:
            return sensitivity_df
        
        # Calculate accuracy weight (inverse of error)
        val_df['accuracy_weight'] = 1 / (1 + val_df['cvrmse'] / 100)
        
        # Merge with sensitivity results
        if 'building_id' in sensitivity_df.columns and 'building_id' in val_df.columns:
            merged = sensitivity_df.merge(
                val_df[['building_id', 'accuracy_weight']], 
                on='building_id', 
                how='left'
            )
            
            # Apply weighting
            merged[weight_column] = merged[weight_column] * merged['accuracy_weight'].fillna(1.0)
            
            return merged.drop(columns=['accuracy_weight'])
        
        return sensitivity_df
    
    def generate_base_report(self, 
                           sensitivity_results: pd.DataFrame,
                           additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate base report structure"""
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': self.get_analysis_type(),
                'job_output_dir': str(self.job_output_dir),
                'n_parameters': len(sensitivity_results['parameter'].unique()) if 'parameter' in sensitivity_results.columns else 0,
                'n_outputs': len(sensitivity_results['output_variable'].unique()) if 'output_variable' in sensitivity_results.columns else 0
            },
            'summary': {
                'top_parameters': self._get_top_parameters(sensitivity_results, n=10),
                'analysis_method': self.get_analysis_type()
            },
            'detailed_results': sensitivity_results.to_dict('records') if len(sensitivity_results) < 1000 else "Results too large - see parquet file"
        }
        
        # Add time slice information if present
        if self.time_slice_config and self.time_slice_config.get('enabled', False):
            report['time_slice'] = {
                'enabled': True,
                'type': self.time_slice_config.get('slice_type'),
                'config': self.time_slice_config
            }
            
            # Add time-specific summary if available
            if 'time_slice_type' in sensitivity_results.columns:
                report['summary']['time_slice_applied'] = sensitivity_results['time_slice_type'].iloc[0] if len(sensitivity_results) > 0 else 'unknown'
        
        if additional_info:
            report.update(additional_info)
        
        return report
    
    def _get_top_parameters(self, df: pd.DataFrame, n: int = 10) -> List[Dict]:
        """Extract top n parameters by sensitivity score"""
        if 'sensitivity_score' not in df.columns:
            return []
        
        # Average across output variables if needed
        if 'parameter' in df.columns:
            top_params = df.groupby('parameter')['sensitivity_score'].mean().nlargest(n)
            
            return [
                {
                    'parameter': param,  # Keep full parameter name
                    'parameter_display': self._format_parameter_name(param) if hasattr(self, '_format_parameter_name') else param,
                    'avg_sensitivity_score': float(score),
                    'rank': i + 1
                }
                for i, (param, score) in enumerate(top_params.items())
            ]
        
        return []
    

    def _format_parameter_name(self, param_name: str, max_length: int = 50) -> str:
        """Format long parameter names for display"""
        if '*' in param_name:
            parts = param_name.split('*')
            if len(parts) >= 4:
                # Show category, object_name, and field_name
                formatted = f"{parts[0]}.{parts[2]}.{parts[3]}"
                if len(formatted) > max_length:
                    # Truncate object_name if needed
                    object_name = parts[2]
                    if len(object_name) > 20:
                        object_name = object_name[:17] + "..."
                    formatted = f"{parts[0]}.{object_name}.{parts[3]}"
                return formatted
        return param_name if len(param_name) <= max_length else param_name[:max_length-3] + "..."
    
    def save_results(self, 
                    sensitivity_df: pd.DataFrame,
                    report: Dict[str, Any],
                    output_dir: Path) -> Tuple[Path, Path]:
        """Save sensitivity results and report"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add time slice suffix to filename if applicable
        filename_suffix = ""
        if self.time_slice_config and self.time_slice_config.get('enabled', False):
            slice_type = self.time_slice_config.get('slice_type', 'custom')
            filename_suffix = f"_{slice_type}"
            if slice_type == 'peak_months':
                filename_suffix += f"_{self.time_slice_config.get('season', 'all')}"
        
        # Save detailed results as parquet
        results_path = output_dir / f"{self.get_analysis_type()}_sensitivity_results{filename_suffix}.parquet"
        sensitivity_df.to_parquet(results_path, index=False)
        
        # Save report as JSON
        report_path = output_dir / f"{self.get_analysis_type()}_sensitivity_report{filename_suffix}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Saved results to {results_path} and {report_path}")
        
        return results_path, report_path
    
    def clear_cache(self):
        """Clear cached data"""
        self._cache.clear()
        self.logger.debug("Cleared data cache")