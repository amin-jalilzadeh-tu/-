"""
c_sensitivity/base_analyzer.py

Base class with common functionality for all sensitivity analyzers.
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
    
    def load_simulation_results(self, 
                              result_type: str = 'daily',
                              categories: Optional[List[str]] = None,
                              use_cache: bool = True) -> Tuple[Dict, Dict]:
        """Load base and modified simulation results with caching"""
        cache_key = f"results_{result_type}_{categories}"
        
        if use_cache and cache_key in self._cache:
            self.logger.debug(f"Using cached results for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Loading {result_type} simulation results...")
        
        if categories is None:
            categories = ['hvac', 'energy', 'temperature', 'electricity', 'zones', 'ventilation']
        
        base_results = {}
        modified_results = {}
        
        for category in categories:
            # Base results
            base_path = self.base_parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
            if base_path.exists():
                base_results[category] = pd.read_parquet(base_path)
                self.logger.debug(f"Loaded base {category}: {len(base_results[category])} records")
            
            # Modified results (only if available)
            mod_path = self.modified_parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
            if mod_path.exists():
                modified_results[category] = pd.read_parquet(mod_path)
                self.logger.debug(f"Loaded modified {category}: {len(modified_results[category])} records")
        
        # Also load summary metrics
        self._load_summary_metrics(base_results, modified_results)
        
        # Cache results
        self._cache[cache_key] = (base_results, modified_results)
        
        self.base_results = base_results
        self.modified_results = modified_results
        
        return base_results, modified_results
    
    def _load_summary_metrics(self, base_results: Dict, modified_results: Dict):
        """Load annual summary metrics if available"""
        base_summary_path = self.base_parsed_dir / "sql_results/summary_metrics/annual_summary.parquet"
        if base_summary_path.exists():
            base_results['summary'] = pd.read_parquet(base_summary_path)
            
        mod_summary_path = self.modified_parsed_dir / "sql_results/summary_metrics/annual_summary.parquet"
        if mod_summary_path.exists():
            modified_results['summary'] = pd.read_parquet(mod_summary_path)
    
    def calculate_output_deltas(self, 
                              output_variables: List[str],
                              aggregation: str = 'sum',
                              groupby: Optional[List[str]] = None) -> pd.DataFrame:
        """Calculate changes in outputs between base and modified runs"""
        self.logger.info("Calculating output deltas...")
        
        if not self.base_results or not self.modified_results:
            raise ValueError("Results not loaded. Call load_simulation_results first.")
        
        delta_records = []
        
        # Determine grouping
        if groupby is None:
            groupby = ['building_id']
        
        # Process each category
        for category, base_df in self.base_results.items():
            if category == 'summary':  # Skip summary for now
                continue
                
            if category not in self.modified_results:
                continue
                
            mod_df = self.modified_results[category]
            
            # Find matching output variables
            for var_name in output_variables:
                matching_cols = [col for col in base_df.columns 
                               if var_name in col and col not in groupby + ['Date']]
                
                for col in matching_cols:
                    if col not in mod_df.columns:
                        continue
                    
                    # Calculate aggregated values
                    if aggregation == 'sum':
                        base_agg = base_df.groupby(groupby)[col].sum()
                        mod_agg = mod_df.groupby(groupby)[col].sum()
                    elif aggregation == 'mean':
                        base_agg = base_df.groupby(groupby)[col].mean()
                        mod_agg = mod_df.groupby(groupby)[col].mean()
                    else:
                        raise ValueError(f"Unknown aggregation method: {aggregation}")
                    
                    # Calculate deltas
                    for idx in base_agg.index:
                        if idx not in mod_agg.index:
                            continue
                            
                        base_val = base_agg[idx]
                        mod_val = mod_agg[idx]
                        
                        delta_record = {
                            'category': category,
                            'variable': col,
                            'variable_clean': var_name,
                            f'{var_name}_base': base_val,
                            f'{var_name}_modified': mod_val,
                            f'{var_name}_delta': mod_val - base_val,
                            f'{var_name}_pct_change': ((mod_val - base_val) / base_val * 100) if base_val != 0 else 0
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
        
        # Save detailed results as parquet
        results_path = output_dir / f"{self.get_analysis_type()}_sensitivity_results.parquet"
        sensitivity_df.to_parquet(results_path, index=False)
        
        # Save report as JSON
        report_path = output_dir / f"{self.get_analysis_type()}_sensitivity_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Saved results to {results_path} and {report_path}")
        
        return results_path, report_path
    
    def clear_cache(self):
        """Clear cached data"""
        self._cache.clear()
        self.logger.debug("Cleared data cache")
