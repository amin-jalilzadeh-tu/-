"""
c_sensitivity/modification_sensitivity_analyzer.py

Analyzes sensitivity based on actual modifications and their impacts.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
from datetime import datetime
from scipy import stats
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

@dataclass
class ModificationSensitivityResult:
    """Container for modification-based sensitivity results"""
    parameter: str
    category: str
    output_variable: str
    sensitivity_score: float
    correlation: float
    p_value: float
    n_samples: int
    mean_param_change: float
    mean_output_change: float
    elasticity: float
    confidence_level: str

class ModificationSensitivityAnalyzer:
    """Analyzes sensitivity based on modification tracking and results"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger or logging.getLogger(__name__)
        
        # Define paths
        self.base_parsed_dir = self.job_output_dir / "parsed_data"
        self.modified_parsed_dir = self.job_output_dir / "parsed_modified_results"
        self.modifications_dir = self.job_output_dir / "modified_idfs"
        self.validation_dir = self.job_output_dir / "validation_results"
        
        # Data containers
        self.modification_tracking = None
        self.base_results = {}
        self.modified_results = {}
        self.parameter_deltas = {}
        self.output_deltas = {}
        self.validation_scores = {}
        
    def load_modification_tracking(self) -> pd.DataFrame:
        """Load modification tracking data"""
        self.logger.info("Loading modification tracking data...")
        
        # Find latest modification detail file
        mod_files = list(self.modifications_dir.glob("modifications_detail_*.parquet"))
        if not mod_files:
            raise FileNotFoundError("No modification tracking files found")
            
        latest_file = max(mod_files, key=lambda x: x.stat().st_mtime)
        self.logger.info(f"Loading modifications from: {latest_file}")
        
        # Load and process
        df = pd.read_parquet(latest_file)
        
        # Parse numeric values where possible
        df['original_value_numeric'] = pd.to_numeric(df['original_value'], errors='coerce')
        df['new_value_numeric'] = pd.to_numeric(df['new_value'], errors='coerce')
        
        # Calculate change
        df['param_delta'] = df['new_value_numeric'] - df['original_value_numeric']
        df['param_pct_change'] = (df['param_delta'] / df['original_value_numeric'].replace(0, np.nan)) * 100
        
        # Create parameter key
        df['param_key'] = df['category'] + '_' + df['object_type'] + '_' + df['field_name']
        
        self.modification_tracking = df
        self.logger.info(f"Loaded {len(df)} modifications across {df['building_id'].nunique()} buildings")
        
        return df
    
    def load_simulation_results(self, result_type: str = 'daily') -> Tuple[Dict, Dict]:
        """Load base and modified simulation results"""
        self.logger.info(f"Loading {result_type} simulation results...")
        
        # Define paths for different result categories
        result_categories = ['hvac', 'energy', 'temperature', 'electricity']
        
        for category in result_categories:
            # Base results
            base_path = self.base_parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
            if base_path.exists():
                self.base_results[category] = pd.read_parquet(base_path)
                self.logger.debug(f"Loaded base {category}: {len(self.base_results[category])} records")
            
            # Modified results
            mod_path = self.modified_parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
            if mod_path.exists():
                self.modified_results[category] = pd.read_parquet(mod_path)
                self.logger.debug(f"Loaded modified {category}: {len(self.modified_results[category])} records")
        
        # Also load summary metrics if available
        base_summary_path = self.base_parsed_dir / "sql_results/summary_metrics/annual_summary.parquet"
        if base_summary_path.exists():
            self.base_results['summary'] = pd.read_parquet(base_summary_path)
            
        mod_summary_path = self.modified_parsed_dir / "sql_results/summary_metrics/annual_summary.parquet"
        if mod_summary_path.exists():
            self.modified_results['summary'] = pd.read_parquet(mod_summary_path)
            
        return self.base_results, self.modified_results
    
    def calculate_output_deltas(self, output_variables: List[str], aggregation: str = 'sum') -> pd.DataFrame:
        """Calculate changes in outputs between base and modified"""
        self.logger.info("Calculating output deltas...")
        
        delta_records = []
        
        # Get unique buildings from modifications
        buildings = self.modification_tracking['building_id'].unique()
        
        for building_id in buildings:
            building_deltas = {}
            building_deltas['building_id'] = building_id
            
            # For each output variable
            for var_name in output_variables:
                # Find the variable in results
                var_found = False
                
                for category, base_df in self.base_results.items():
                    if category == 'summary':
                        continue
                        
                    if var_name in base_df.columns or 'Variable' in base_df.columns:
                        # Get base value
                        if 'Variable' in base_df.columns:
                            base_data = base_df[
                                (base_df['building_id'] == building_id) & 
                                (base_df['Variable'] == var_name)
                            ]
                        else:
                            base_data = base_df[base_df['building_id'] == building_id]
                            
                        # Get modified value
                        if category in self.modified_results:
                            mod_df = self.modified_results[category]
                            if 'Variable' in mod_df.columns:
                                mod_data = mod_df[
                                    (mod_df['building_id'] == building_id) & 
                                    (mod_df['Variable'] == var_name)
                                ]
                            else:
                                mod_data = mod_df[mod_df['building_id'] == building_id]
                                
                            # Calculate aggregated values
                            if aggregation == 'sum':
                                base_val = base_data.get('Value', base_data.get(var_name, pd.Series())).sum()
                                mod_val = mod_data.get('Value', mod_data.get(var_name, pd.Series())).sum()
                            elif aggregation == 'mean':
                                base_val = base_data.get('Value', base_data.get(var_name, pd.Series())).mean()
                                mod_val = mod_data.get('Value', mod_data.get(var_name, pd.Series())).mean()
                            else:
                                base_val = base_data.get('Value', base_data.get(var_name, pd.Series())).iloc[-1] if len(base_data) > 0 else 0
                                mod_val = mod_data.get('Value', mod_data.get(var_name, pd.Series())).iloc[-1] if len(mod_data) > 0 else 0
                            
                            # Store delta
                            building_deltas[f"{var_name}_base"] = base_val
                            building_deltas[f"{var_name}_modified"] = mod_val
                            building_deltas[f"{var_name}_delta"] = mod_val - base_val
                            building_deltas[f"{var_name}_pct_change"] = ((mod_val - base_val) / base_val * 100) if base_val != 0 else 0
                            
                            var_found = True
                            break
                
                if not var_found:
                    self.logger.warning(f"Variable {var_name} not found for building {building_id}")
                    
            delta_records.append(building_deltas)
        
        df_deltas = pd.DataFrame(delta_records)
        self.output_deltas = df_deltas
        
        return df_deltas
    
    def calculate_parameter_aggregates(self) -> pd.DataFrame:
        """Aggregate parameter changes by building and category"""
        self.logger.info("Aggregating parameter changes...")
        
        # Group by building and parameter
        param_agg = self.modification_tracking.groupby(['building_id', 'category', 'param_key']).agg({
            'param_delta': 'mean',
            'param_pct_change': 'mean',
            'variant_id': 'count'  # Number of variants with this change
        }).reset_index()
        
        param_agg.columns = ['building_id', 'category', 'param_key', 'avg_delta', 'avg_pct_change', 'n_variants']
        
        self.parameter_deltas = param_agg
        return param_agg
    
    def calculate_sensitivity_scores(self, 
                                   parameter_groups: Optional[Dict[str, List[str]]] = None,
                                   output_variables: Optional[List[str]] = None) -> pd.DataFrame:
        """Calculate sensitivity scores for parameter-output pairs"""
        self.logger.info("Calculating sensitivity scores...")
        
        if output_variables is None:
            # Use all available output variables
            output_variables = [col for col in self.output_deltas.columns 
                              if col.endswith('_delta') and not col.startswith('building')]
        
        results = []
        
        # Get parameter categories
        if parameter_groups:
            categories = list(parameter_groups.keys())
        else:
            categories = self.parameter_deltas['category'].unique()
        
        # For each category
        for category in categories:
            cat_params = self.parameter_deltas[self.parameter_deltas['category'] == category]
            
            # Get unique parameters in this category
            if parameter_groups and category in parameter_groups:
                param_list = parameter_groups[category]
            else:
                param_list = cat_params['param_key'].unique()
            
            # For each parameter
            for param in param_list:
                param_data = cat_params[cat_params['param_key'].str.contains(param, na=False)]
                
                if len(param_data) == 0:
                    continue
                
                # For each output variable
                for output_var in output_variables:
                    if output_var not in self.output_deltas.columns:
                        continue
                    
                    # Merge parameter and output data
                    merged = pd.merge(
                        param_data[['building_id', 'avg_pct_change', 'avg_delta']],
                        self.output_deltas[['building_id', output_var]],
                        on='building_id'
                    )
                    
                    if len(merged) < 3:  # Need at least 3 points for correlation
                        continue
                    
                    # Calculate correlation and sensitivity
                    corr, p_value = stats.pearsonr(merged['avg_pct_change'], merged[output_var])
                    
                    # Calculate elasticity (% change in output / % change in input)
                    if output_var.replace('_delta', '_pct_change') in self.output_deltas.columns:
                        output_pct_col = output_var.replace('_delta', '_pct_change')
                        merged_pct = pd.merge(
                            param_data[['building_id', 'avg_pct_change']],
                            self.output_deltas[['building_id', output_pct_col]],
                            on='building_id'
                        )
                        
                        # Elasticity = mean(output % change) / mean(input % change)
                        mean_param_change = merged_pct['avg_pct_change'].mean()
                        mean_output_change = merged_pct[output_pct_col].mean()
                        
                        if mean_param_change != 0:
                            elasticity = mean_output_change / mean_param_change
                        else:
                            elasticity = 0
                    else:
                        elasticity = 0
                        mean_output_change = merged[output_var].mean()
                    
                    # Sensitivity score (combination of correlation and elasticity)
                    sensitivity_score = abs(corr) * (1 + abs(elasticity))
                    
                    # Confidence level based on p-value
                    if p_value < 0.01:
                        confidence = 'high'
                    elif p_value < 0.05:
                        confidence = 'medium'
                    elif p_value < 0.1:
                        confidence = 'low'
                    else:
                        confidence = 'very_low'
                    
                    result = ModificationSensitivityResult(
                        parameter=param,
                        category=category,
                        output_variable=output_var,
                        sensitivity_score=sensitivity_score,
                        correlation=corr,
                        p_value=p_value,
                        n_samples=len(merged),
                        mean_param_change=merged['avg_pct_change'].mean(),
                        mean_output_change=mean_output_change,
                        elasticity=elasticity,
                        confidence_level=confidence
                    )
                    
                    results.append(result)
        
        # Convert to DataFrame
        df_results = pd.DataFrame([vars(r) for r in results])
        
        # Sort by sensitivity score
        df_results = df_results.sort_values('sensitivity_score', ascending=False)
        
        return df_results
    
    def weight_by_validation(self, sensitivity_df: pd.DataFrame) -> pd.DataFrame:
        """Weight sensitivity scores by validation accuracy"""
        self.logger.info("Weighting by validation results...")
        
        # Load validation results if available
        baseline_val_path = self.validation_dir / "baseline/validation_results.parquet"
        modified_val_path = self.validation_dir / "modified/validation_results.parquet"
        
        if baseline_val_path.exists() and modified_val_path.exists():
            baseline_val = pd.read_parquet(baseline_val_path)
            modified_val = pd.read_parquet(modified_val_path)
            
            # Calculate improvement in validation metrics
            val_improvements = {}
            
            for building_id in baseline_val['building_id'].unique():
                base_data = baseline_val[baseline_val['building_id'] == building_id]
                mod_data = modified_val[modified_val['building_id'] == building_id]
                
                if len(mod_data) > 0:
                    # Average CVRMSE improvement
                    base_cvrmse = base_data['cvrmse'].mean()
                    mod_cvrmse = mod_data['cvrmse'].mean()
                    
                    improvement = (base_cvrmse - mod_cvrmse) / base_cvrmse if base_cvrmse > 0 else 0
                    val_improvements[building_id] = max(0, improvement)  # Only positive improvements
            
            # Apply weights
            sensitivity_df['validation_weight'] = 1.0
            
            for idx, row in sensitivity_df.iterrows():
                # Get buildings that had this parameter modified
                param_buildings = self.modification_tracking[
                    self.modification_tracking['param_key'].str.contains(row['parameter'], na=False)
                ]['building_id'].unique()
                
                # Average validation improvement for these buildings
                avg_improvement = np.mean([val_improvements.get(b, 0) for b in param_buildings])
                
                # Weight: 1 + improvement (so 20% improvement = 1.2x weight)
                weight = 1 + avg_improvement
                sensitivity_df.at[idx, 'validation_weight'] = weight
                sensitivity_df.at[idx, 'weighted_sensitivity'] = row['sensitivity_score'] * weight
        
        return sensitivity_df
    
    def analyze_parameter_groups(self, sensitivity_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze sensitivity by parameter groups/categories"""
        self.logger.info("Analyzing parameter groups...")
        
        # Group by category and output variable
        group_analysis = sensitivity_df.groupby(['category', 'output_variable']).agg({
            'sensitivity_score': ['mean', 'max', 'std'],
            'correlation': 'mean',
            'elasticity': 'mean',
            'n_samples': 'sum',
            'parameter': 'count'
        }).reset_index()
        
        # Flatten column names
        group_analysis.columns = ['_'.join(col).strip('_') for col in group_analysis.columns]
        
        # Rank categories by impact
        group_analysis['impact_rank'] = group_analysis.groupby('output_variable')['sensitivity_score_mean'].rank(ascending=False)
        
        return group_analysis
    
    def generate_report(self, 
                       sensitivity_df: pd.DataFrame,
                       group_analysis: pd.DataFrame,
                       output_path: Path) -> Dict[str, Any]:
        """Generate comprehensive sensitivity report"""
        self.logger.info("Generating sensitivity report...")
        
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'job_id': self.job_output_dir.name,
                'analysis_type': 'modification_based',
                'n_buildings': self.modification_tracking['building_id'].nunique(),
                'n_modifications': len(self.modification_tracking),
                'n_parameters': len(sensitivity_df['parameter'].unique()),
                'n_outputs': len(sensitivity_df['output_variable'].unique())
            },
            'top_sensitive_parameters': sensitivity_df.head(20).to_dict('records'),
            'category_impact': group_analysis.to_dict('records'),
            'summary': {
                'most_sensitive_category': group_analysis.loc[group_analysis['sensitivity_score_mean'].idxmax(), 'category'],
                'highest_correlation': {
                    'parameter': sensitivity_df.loc[sensitivity_df['correlation'].abs().idxmax(), 'parameter'],
                    'output': sensitivity_df.loc[sensitivity_df['correlation'].abs().idxmax(), 'output_variable'],
                    'correlation': sensitivity_df['correlation'].abs().max()
                },
                'highest_elasticity': {
                    'parameter': sensitivity_df.loc[sensitivity_df['elasticity'].abs().idxmax(), 'parameter'],
                    'output': sensitivity_df.loc[sensitivity_df['elasticity'].abs().idxmax(), 'output_variable'],
                    'elasticity': sensitivity_df['elasticity'].abs().max()
                }
            }
        }
        
        # Save report
        report_file = output_path / 'modification_sensitivity_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save detailed results
        sensitivity_df.to_parquet(output_path / 'modification_sensitivity_detailed.parquet')
        group_analysis.to_parquet(output_path / 'modification_sensitivity_groups.parquet')
        
        # Save for downstream use (surrogate, calibration)
        if len(sensitivity_df) > 0:
            # Top parameters for calibration
            top_params = sensitivity_df.groupby('parameter')['sensitivity_score'].mean().nlargest(20)
            top_params.to_csv(output_path / 'top_sensitive_parameters.csv')
        
        self.logger.info(f"Report saved to: {report_file}")
        
        return report