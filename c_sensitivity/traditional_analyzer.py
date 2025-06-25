"""
c_sensitivity/traditional_analyzer.py

Traditional scenario-based sensitivity analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, Tuple

from .base_analyzer import BaseSensitivityAnalyzer
from .data_manager import SensitivityDataManager
from .statistical_methods import StatisticalMethods


class TraditionalSensitivityAnalyzer(BaseSensitivityAnalyzer):
    """Traditional sensitivity analysis using scenario/parameter variations"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        super().__init__(job_output_dir, logger)
        self.data_manager = SensitivityDataManager(job_output_dir)
        self.stats = StatisticalMethods()
        
        # Traditional analysis specific attributes
        self.parameter_matrix = None
        self.scenario_results = None
        
    def get_analysis_type(self) -> str:
        return "traditional"
    
    def load_parameter_data(self, categories: Optional[List[str]] = None) -> pd.DataFrame:
        """Load parameter variations from IDF data"""
        self.logger.info("Loading parameter data for traditional analysis...")
        
        # Use data manager to load parameters
        param_df = self.data_manager.load_idf_parameters(categories=categories)
        
        if param_df.empty:
            raise ValueError("No parameter data found")
        
        self.parameter_data = param_df
        return param_df
    
    def load_scenario_results(self, 
                            scenario_folder: Optional[Path] = None,
                            result_type: str = 'daily') -> pd.DataFrame:
        """Load results from multiple scenario runs"""
        self.logger.info("Loading scenario results...")
        
        if scenario_folder is None:
            scenario_folder = self.job_output_dir / "scenarios"
        
        scenario_results = []
        
        # Load results from each scenario
        for scenario_dir in scenario_folder.iterdir():
            if not scenario_dir.is_dir():
                continue
                
            scenario_name = scenario_dir.name
            
            # Load parsed results for this scenario
            parsed_dir = scenario_dir / "parsed_data"
            if not parsed_dir.exists():
                self.logger.warning(f"No parsed data for scenario {scenario_name}")
                continue
            
            # Load aggregated results
            for category in ['hvac', 'energy', 'electricity']:
                result_path = parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
                
                if result_path.exists():
                    df = pd.read_parquet(result_path)
                    df['scenario'] = scenario_name
                    scenario_results.append(df)
        
        if scenario_results:
            self.scenario_results = pd.concat(scenario_results, ignore_index=True)
            return self.scenario_results
        else:
            raise ValueError("No scenario results found")
    
    def calculate_sensitivity(self, 
                            method: str = 'correlation',
                            output_variables: Optional[List[str]] = None,
                            parameter_groups: Optional[Dict[str, List[str]]] = None,
                            **kwargs) -> pd.DataFrame:
        """
        Calculate sensitivity using traditional methods
        
        Args:
            method: 'correlation', 'regression', 'sobol', 'morris'
            output_variables: List of output variables to analyze
            parameter_groups: Grouping of parameters for hierarchical analysis
            **kwargs: Additional method-specific parameters
            
        Returns:
            DataFrame with sensitivity results
        """
        self.logger.info(f"Calculating traditional sensitivity using {method} method...")
        
        # Create analysis dataset
        X, y = self._create_analysis_dataset(output_variables)
        
        if X.empty or y.empty:
            raise ValueError("Failed to create analysis dataset")
        
        # Apply selected method
        if method == 'correlation':
            results = self.stats.correlation_analysis(X, y, **kwargs)
        elif method == 'regression':
            results = self.stats.regression_analysis(X, y, **kwargs)
        elif method == 'sobol':
            results = self.stats.sobol_analysis(X, y, **kwargs)
        elif method == 'morris':
            results = self.stats.morris_analysis(X, y, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Add parameter groups if provided
        if parameter_groups:
            results = self._add_parameter_groups(results, parameter_groups)
        
        # Apply hierarchical analysis if requested
        if kwargs.get('hierarchical', False):
            hierarchy_results = self._perform_hierarchical_analysis(X, y, parameter_groups)
            results = self._merge_hierarchical_results(results, hierarchy_results)
        
        return results
    
    def _create_analysis_dataset(self, 
                               output_variables: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create X (parameters) and y (outputs) datasets for analysis"""
        # Use data manager's method if available
        if hasattr(self.data_manager, 'create_analysis_dataset'):
            return self.data_manager.create_analysis_dataset(
                output_variables=output_variables,
                use_modifications=False
            )
        
        # Otherwise, create manually
        if self.parameter_data is None:
            self.load_parameter_data()
            
        if self.scenario_results is None:
            self.load_scenario_results()
        
        # Pivot parameters to wide format
        X = self._pivot_parameters_wide()
        
        # Extract output variables
        y = self._extract_output_variables(output_variables)
        
        # Align indices
        common_index = X.index.intersection(y.index)
        X = X.loc[common_index]
        y = y.loc[common_index]
        
        return X, y
    
    def _pivot_parameters_wide(self) -> pd.DataFrame:
        """Convert parameter data to wide format for analysis"""
        # Select numeric parameters
        numeric_params = self.parameter_data.select_dtypes(include=[np.number])
        
        # Create parameter names
        if 'category' in self.parameter_data.columns and 'field' in self.parameter_data.columns:
            self.parameter_data['param_name'] = (
                self.parameter_data['category'] + '_' + 
                self.parameter_data['field']
            )
        
        # Pivot to wide format
        if 'param_name' in self.parameter_data.columns:
            # Group by building/scenario and pivot
            pivot_cols = ['building_id'] if 'building_id' in self.parameter_data.columns else []
            if 'scenario' in self.parameter_data.columns:
                pivot_cols.append('scenario')
            
            if pivot_cols and 'param_name' in self.parameter_data.columns:
                # Get numeric value column
                value_col = None
                for col in ['value', 'numeric_value', 'value_numeric']:
                    if col in self.parameter_data.columns:
                        value_col = col
                        break
                
                if value_col:
                    X = self.parameter_data.pivot_table(
                        index=pivot_cols,
                        columns='param_name',
                        values=value_col,
                        aggfunc='first'
                    )
                    return X
        
        # Fallback: return numeric columns
        return numeric_params
    
    def _extract_output_variables(self, 
                                output_variables: Optional[List[str]] = None) -> pd.DataFrame:
        """Extract output variables from scenario results"""
        if self.scenario_results is None:
            return pd.DataFrame()
        
        if output_variables is None:
            # Default output variables
            output_variables = [
                'Heating:EnergyTransfer',
                'Cooling:EnergyTransfer', 
                'Electricity:Facility'
            ]
        
        # Find matching columns
        output_cols = []
        for var in output_variables:
            matching = [col for col in self.scenario_results.columns 
                       if var in col and col not in ['Date', 'scenario', 'building_id']]
            output_cols.extend(matching)
        
        if not output_cols:
            self.logger.warning("No matching output variables found")
            return pd.DataFrame()
        
        # Aggregate by scenario/building
        groupby_cols = []
        if 'scenario' in self.scenario_results.columns:
            groupby_cols.append('scenario')
        if 'building_id' in self.scenario_results.columns:
            groupby_cols.append('building_id')
        
        if groupby_cols:
            y = self.scenario_results.groupby(groupby_cols)[output_cols].sum()
        else:
            y = self.scenario_results[output_cols]
        
        return y
    
    def _add_parameter_groups(self, 
                            results: pd.DataFrame,
                            parameter_groups: Dict[str, List[str]]) -> pd.DataFrame:
        """Add parameter group information to results"""
        if 'parameter' not in results.columns:
            return results
        
        # Create parameter to group mapping
        param_to_group = {}
        for group, params in parameter_groups.items():
            for param in params:
                param_to_group[param] = group
        
        # Add group column
        results['parameter_group'] = results['parameter'].map(
            lambda p: next((g for param, g in param_to_group.items() if param in p), 'other')
        )
        
        return results
    
    def _perform_hierarchical_analysis(self,
                                     X: pd.DataFrame,
                                     y: pd.DataFrame,
                                     parameter_groups: Dict[str, List[str]]) -> pd.DataFrame:
        """Perform analysis at parameter group level"""
        if not parameter_groups:
            return pd.DataFrame()
        
        group_results = []
        
        for group_name, params in parameter_groups.items():
            # Find columns for this group
            group_cols = [col for col in X.columns if any(param in col for param in params)]
            
            if not group_cols:
                continue
            
            # Calculate group-level sensitivity
            group_X = X[group_cols]
            group_sensitivity = self.stats.correlation_analysis(group_X, y)
            
            # Aggregate to group level
            if not group_sensitivity.empty:
                avg_sensitivity = group_sensitivity.groupby('output_variable')['sensitivity_score'].mean()
                
                for output_var, score in avg_sensitivity.items():
                    group_results.append({
                        'parameter_group': group_name,
                        'output_variable': output_var,
                        'group_sensitivity_score': score,
                        'n_parameters': len(group_cols)
                    })
        
        return pd.DataFrame(group_results)
    
    def _merge_hierarchical_results(self,
                                  results: pd.DataFrame,
                                  hierarchy_results: pd.DataFrame) -> pd.DataFrame:
        """Merge parameter-level and group-level results"""
        if hierarchy_results.empty:
            return results
        
        # Add hierarchy information to main results
        if 'parameter_group' in results.columns:
            results = results.merge(
                hierarchy_results,
                on=['parameter_group', 'output_variable'],
                how='left'
            )
        
        return results
    
    def perform_building_specific_analysis(self,
                                         building_metadata: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
        """Analyze sensitivity by building type"""
        if self.parameter_data is None or self.scenario_results is None:
            raise ValueError("Data not loaded")
        
        results = {}
        
        if building_metadata is not None and 'building_type' in building_metadata.columns:
            # Group by building type
            for building_type in building_metadata['building_type'].unique():
                type_buildings = building_metadata[
                    building_metadata['building_type'] == building_type
                ]['building_id'].tolist()
                
                # Filter data for this building type
                type_X, type_y = self._create_analysis_dataset()
                
                if 'building_id' in type_X.index.names:
                    type_X = type_X[type_X.index.get_level_values('building_id').isin(type_buildings)]
                    type_y = type_y[type_y.index.isin(type_X.index)]
                
                if len(type_X) > 5:  # Need enough samples
                    type_sensitivity = self.stats.correlation_analysis(type_X, type_y)
                    results[building_type] = type_sensitivity
        
        return results
    
    def export_for_downstream(self, 
                            sensitivity_df: pd.DataFrame,
                            output_dir: Path,
                            top_n: int = 20) -> None:
        """Export top parameters for surrogate modeling and calibration"""
        output_dir = Path(output_dir)
        
        # Get top parameters
        if 'sensitivity_score' in sensitivity_df.columns:
            top_params = sensitivity_df.nlargest(top_n, 'sensitivity_score')
            
            # Save parameter list
            param_list = top_params['parameter'].unique().tolist()
            
            with open(output_dir / 'top_sensitive_parameters.json', 'w') as f:
                json.dump({
                    'parameters': param_list,
                    'method': 'traditional',
                    'top_n': top_n
                }, f, indent=2)
            
            # Save detailed results
            top_params.to_csv(output_dir / 'top_parameters_detailed.csv', index=False)
        
        self.logger.info(f"Exported top {top_n} parameters for downstream use")
