"""
c_sensitivity/sensitivity_manager.py

Main entry point for sensitivity analysis, replacing unified_sensitivity.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime

from .data_manager import SensitivityDataManager
from .traditional_analyzer import TraditionalSensitivityAnalyzer
from .modification_analyzer import ModificationSensitivityAnalyzer
from .reporter import SensitivityReporter
from .time_slicer import TimeSlicer

# Import new advanced analyzers
from .advanced_uncertainty import UncertaintyAnalyzer, UncertaintyConfig
from .threshold_analysis import ThresholdAnalyzer
from .regional_sensitivity import RegionalSensitivityAnalyzer
from .sobol_analyzer import SobolAnalyzer
from .temporal_patterns import TemporalPatternsAnalyzer


class SensitivityManager:
    """Main manager for all sensitivity analysis types"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger or logging.getLogger(__name__)
        self.data_manager = SensitivityDataManager(job_output_dir)
        self.reporter = SensitivityReporter()
        self.time_slicer = TimeSlicer(logger)
        
        # Analysis results storage
        self.results = {}
        self.reports = {}
        self.time_slice_configs = {}
        
        # Advanced analysis results
        self.advanced_results = {}
        
    def run_analysis(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Main entry point for sensitivity analysis
        
        Args:
            config: Sensitivity configuration from combined.json
            
        Returns:
            Path to the main sensitivity report or None if failed
        """
        self.logger.info("Starting sensitivity analysis...")
        
        # Determine analysis type
        analysis_type = config.get("analysis_type", "traditional")
        
        # Extract time slicing configuration
        time_slice_config = config.get("time_slicing", {})
        if time_slice_config.get("enabled", False):
            self.logger.info(f"Time slicing enabled: {time_slice_config.get('slice_type', 'custom')}")
            
            # Validate time slice config
            valid, errors = self.time_slicer.validate_time_slice_config(time_slice_config)
            if not valid:
                self.logger.error(f"Invalid time slice configuration: {errors}")
                time_slice_config = {"enabled": False}
        
        # Create output directory
        output_dir = Path(config.get("output_base_dir", self.job_output_dir / "sensitivity_results"))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Check if we should run multiple time slices
            if time_slice_config.get("enabled", False) and time_slice_config.get("compare_time_slices", False):
                report_path = self._run_comparative_time_analysis(config, output_dir, analysis_type)
            else:
                # Single analysis (with or without time slice)
                if analysis_type == "modification_based":
                    report_path = self._run_modification_analysis(config, output_dir, time_slice_config)
                elif analysis_type == "traditional":
                    report_path = self._run_traditional_analysis(config, output_dir, time_slice_config)
                elif analysis_type == "hybrid":
                    report_path = self._run_hybrid_analysis(config, output_dir, time_slice_config)
                else:
                    self.logger.error(f"Unknown analysis type: {analysis_type}")
                    return None
            
            # Run advanced analyses if configured
            if config.get("advanced_analysis", {}).get("enabled", False):
                try:
                    self._run_advanced_analyses(config, output_dir, time_slice_config)
                except Exception as e:
                    self.logger.warning(f"Advanced analysis failed but core sensitivity completed: {e}")
                    # Continue with the rest of the analysis
            
            # Export for downstream use if configured
            if report_path and config.get("export_for_surrogate", False):
                self._export_for_surrogate(output_dir, config)
            
            if report_path and config.get("export_for_calibration", False):
                self._export_for_calibration(output_dir, config)
            
            # Generate visualizations if requested
            if report_path and config.get("generate_visualizations", False):
                self._generate_visualizations(output_dir, config)
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"Sensitivity analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_advanced_analyses(self, config: Dict[str, Any], output_dir: Path, 
                             time_slice_config: Optional[Dict[str, Any]] = None) -> None:
        """Run advanced sensitivity analyses based on configuration"""
        self.logger.info("Running advanced sensitivity analyses...")
        
        advanced_config = config.get("advanced_analysis", {})
        
        # Get base results for advanced analysis
        base_results = self._get_base_results_for_advanced_analysis()
        if base_results is None or base_results.empty:
            self.logger.warning("No base results available for advanced analysis")
            return
        
        # Prepare data for analysis
        X, y = self._prepare_data_for_advanced_analysis(base_results)
        
        # 1. Uncertainty Quantification
        if advanced_config.get("uncertainty_propagation", False):
            self.logger.info("Running uncertainty quantification...")
            try:
                uncertainty_analyzer = UncertaintyAnalyzer(self.data_manager, self.logger)
                uncertainty_config = UncertaintyConfig(
                    n_samples=advanced_config.get("uncertainty_samples", 1000),
                    confidence_level=advanced_config.get("confidence_level", 0.95),
                    parameter_distributions=advanced_config.get("parameter_distributions"),
                    bootstrap_iterations=advanced_config.get("bootstrap_iterations", 100)
                )
                
                uncertainty_results = uncertainty_analyzer.analyze(
                    X, y, base_results, uncertainty_config
                )
                
                if not uncertainty_results.empty:
                    self.advanced_results['uncertainty'] = uncertainty_results
                    uncertainty_results.to_parquet(output_dir / "uncertainty_analysis_results.parquet")
                    self.logger.info(f"Uncertainty analysis complete: {len(uncertainty_results)} results")
                    
            except Exception as e:
                self.logger.error(f"Uncertainty analysis failed: {e}")
        
        # 2. Threshold Analysis
        if advanced_config.get("threshold_analysis", False):
            self.logger.info("Running threshold/breakpoint analysis...")
            try:
                threshold_analyzer = ThresholdAnalyzer(self.data_manager, self.logger)
                threshold_config = {
                    'min_segment_size': advanced_config.get("min_segment_size", 10),
                    'max_breakpoints': advanced_config.get("max_breakpoints", 3),
                    'detection_method': advanced_config.get("threshold_detection_method", 'tree'),
                    'significance_level': advanced_config.get("threshold_significance", 0.05)
                }
                
                threshold_results = threshold_analyzer.analyze(X, y, threshold_config)
                
                if not threshold_results.empty:
                    self.advanced_results['threshold'] = threshold_results
                    threshold_results.to_parquet(output_dir / "threshold_analysis_results.parquet")
                    self.logger.info(f"Threshold analysis complete: {len(threshold_results)} breakpoints found")
                    
            except Exception as e:
                self.logger.error(f"Threshold analysis failed: {e}")
        
        # 3. Regional Sensitivity
        if advanced_config.get("regional_sensitivity", False):
            self.logger.info("Running regional sensitivity analysis...")
            try:
                regional_analyzer = RegionalSensitivityAnalyzer(self.data_manager, self.logger)
                regional_config = {
                    'n_regions': advanced_config.get("n_regions", 5),
                    'region_method': advanced_config.get("region_method", 'clustering'),
                    'overlap_fraction': advanced_config.get("region_overlap", 0.1),
                    'min_samples_per_region': advanced_config.get("min_region_samples", 20)
                }
                
                regional_results = regional_analyzer.analyze(X, y, regional_config)
                
                if not regional_results.empty:
                    self.advanced_results['regional'] = regional_results
                    regional_results.to_parquet(output_dir / "regional_sensitivity_results.parquet")
                    self.logger.info(f"Regional sensitivity complete: {len(regional_results)} regional results")
                    
            except Exception as e:
                self.logger.error(f"Regional sensitivity failed: {e}")
        
        # 4. Sobol Analysis
        # In sensitivity_manager.py, update the Sobol analysis section:

        # 4. Sobol Analysis
        if advanced_config.get("sobol_analysis", False):
            self.logger.info("Running Sobol variance decomposition...")
            try:
                sobol_analyzer = SobolAnalyzer(self.data_manager, self.logger)
                
                # Extract parameter bounds from X data
                parameter_bounds = {}
                for col in X.select_dtypes(include=[np.number]).columns:
                    parameter_bounds[col] = (X[col].min(), X[col].max())
                
                sobol_config = {
                    'n_samples': advanced_config.get("sobol_samples", 1024),
                    'calc_second_order': advanced_config.get("sobol_second_order", True),
                    'sampling_method': advanced_config.get("sobol_sampling", 'saltelli'),
                    'conf_level': advanced_config.get("sobol_confidence", 0.95)
                }
                
                # Pass parameter_bounds to analyze method
                sobol_results = sobol_analyzer.analyze(X, y, parameter_bounds, sobol_config)
                
                if not sobol_results.empty:
                    self.advanced_results['sobol'] = sobol_results
                    sobol_results.to_parquet(output_dir / "sobol_analysis_results.parquet")
                    self.logger.info(f"Sobol analysis complete: {len(sobol_results)} indices calculated")
                    
            except Exception as e:
                self.logger.error(f"Sobol analysis failed: {e}")
        
        # 5. Temporal Pattern Analysis
        if advanced_config.get("temporal_patterns", False):
            self.logger.info("Running temporal pattern analysis...")
            try:
                temporal_analyzer = TemporalPatternsAnalyzer(self.data_manager, self.logger)
                temporal_config = {
                    'time_column': advanced_config.get("time_column", 'DateTime'),
                    'frequency_analysis': advanced_config.get("frequency_analysis", True),
                    'lag_analysis': advanced_config.get("lag_analysis", True),
                    'max_lag': advanced_config.get("max_lag", 24),
                    'window_size': advanced_config.get("window_size", 168),
                    'detect_seasonality': advanced_config.get("detect_seasonality", True)
                }
                
                # Need base sensitivity results for temporal analysis
                if base_results is not None and not base_results.empty:
                    temporal_results = temporal_analyzer.analyze(X, y, base_results, temporal_config)
                else:
                    # If no base results, create simple sensitivity results
                    from .statistical_methods import StatisticalMethods
                    stats = StatisticalMethods(self.logger)
                    base_results = stats.correlation_analysis(X, y)
                    temporal_results = temporal_analyzer.analyze(X, y, base_results, temporal_config)
                
                if not temporal_results.empty:
                    self.advanced_results['temporal'] = temporal_results
                    temporal_results.to_parquet(output_dir / "temporal_pattern_results.parquet")
                    self.logger.info(f"Temporal pattern analysis complete: {len(temporal_results)} patterns found")
                    
            except Exception as e:
                self.logger.error(f"Temporal pattern analysis failed: {e}")
        
        # Generate advanced analysis report
        if self.advanced_results:
            self._generate_advanced_analysis_report(output_dir)
    
    def _get_base_results_for_advanced_analysis(self) -> Optional[pd.DataFrame]:
        """Get base sensitivity results for advanced analysis"""
        # Priority: modification > traditional > any available
        if 'modification' in self.results:
            return self.results['modification']
        elif 'traditional' in self.results:
            return self.results['traditional']
        elif self.results:
            # Return first available results
            return next(iter(self.results.values()))
        return None
    
    # Replace the _prepare_data_for_advanced_analysis method in sensitivity_manager.py:

    def _prepare_data_for_advanced_analysis(self, base_results: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Prepare X and y data for advanced analysis"""
        self.logger.info("Preparing data for advanced analysis...")
        
        # Get unique parameters and outputs from base results
        parameters = base_results['parameter'].unique() if 'parameter' in base_results.columns else []
        output_variables = base_results['output_variable'].unique() if 'output_variable' in base_results.columns else []
        
        # Try to load the actual parameter and output data
        try:
            # Method 1: Load from data manager
            X = self.data_manager.load_idf_parameters(categories=None)
            
            # Method 2: Load from simulation results if X is empty
            if X.empty or len(X.columns) == 0:
                self.logger.info("Loading parameter data from simulation results...")
                # Get parameter columns from the base results
                param_data = {}
                for param in parameters:
                    # Extract parameter values from the name or metadata
                    if '*' in param:  # Formatted parameter name
                        parts = param.split('*')
                        category = parts[0] if len(parts) > 0 else 'unknown'
                        # Try to load from parsed data
                        category_data = self.data_manager.load_simulation_results(
                            result_type='parameters',
                            categories=[category]
                        )
                        if not category_data.empty and param in category_data.columns:
                            param_data[param] = category_data[param]
                
                if param_data:
                    X = pd.DataFrame(param_data)
            
            # Load output data (y)
            # Use the data manager's create_analysis_dataset method
            try:
                X_full, y_full = self.data_manager.create_analysis_dataset(
                    output_variables=output_variables,
                    use_modifications=True
                )
                
                # Use only the requested output variables
                if output_variables:
                    available_outputs = [col for col in y_full.columns if any(var.lower() in col.lower() for var in output_variables)]
                    if available_outputs:
                        y = y_full[available_outputs]
                    else:
                        y = y_full
                else:
                    y = y_full
                    
                # Use parameter data
                if not X.empty:
                    # Align X and y indices
                    common_idx = X.index.intersection(y.index)
                    X = X.loc[common_idx]
                    y = y.loc[common_idx]
                else:
                    X = X_full
                    # Align indices
                    common_idx = X.index.intersection(y.index)
                    X = X.loc[common_idx]
                    y = y.loc[common_idx]
                    
            except Exception as e:
                self.logger.warning(f"Could not use create_analysis_dataset: {e}")
                # Fallback: Create minimal dataset
                y = pd.DataFrame(index=[0])  # Single row
                for output_var in output_variables:
                    y[output_var] = [0.0]  # Dummy value
                    
            if y.empty:
                self.logger.error("Could not load output data for advanced analysis")
                raise ValueError("No output data available for advanced analysis")
                
        except Exception as e:
            self.logger.error(f"Could not load full data for advanced analysis: {e}")
            raise
        
        # Ensure X and y have the same number of rows
        if not X.empty and not y.empty:
            min_rows = min(len(X), len(y))
            X = X.iloc[:min_rows]
            y = y.iloc[:min_rows]
        
        self.logger.info(f"Prepared data: X shape = {X.shape}, y shape = {y.shape}")
        
        return X, y

    
    def _generate_advanced_analysis_report(self, output_dir: Path) -> None:
        """Generate comprehensive report for advanced analyses"""
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'advanced_sensitivity',
                'methods_performed': list(self.advanced_results.keys())
            },
            'summary': {},
            'detailed_results': {}
        }
        
        # Add summaries for each advanced analysis
        for method, results in self.advanced_results.items():
            if isinstance(results, pd.DataFrame) and not results.empty:
                summary = {
                    'n_results': len(results),
                    'columns': list(results.columns)
                }
                
                # Method-specific summaries
                if method == 'uncertainty':
                    if 'uncertainty_lower' in results.columns and 'uncertainty_upper' in results.columns:
                        summary['avg_confidence_interval_width'] = float(
                            (results['uncertainty_upper'] - results['uncertainty_lower']).mean()
                        )
                
                elif method == 'threshold':
                    if 'breakpoint_value' in results.columns:
                        summary['n_breakpoints'] = int(results['breakpoint_value'].notna().sum())
                        summary['parameters_with_breakpoints'] = int(results[
                            results['breakpoint_value'].notna()
                        ]['parameter'].nunique())
                
                elif method == 'regional':
                    if 'parameter_region' in results.columns:
                        summary['n_regions_analyzed'] = int(results['parameter_region'].nunique())
                
                elif method == 'sobol':
                    if 'sobol_first_order' in results.columns:
                        summary['total_variance_explained'] = {
                            k: float(v) for k, v in results.groupby('output_variable')['sobol_first_order'].sum().to_dict().items()
                        }
                
                elif method == 'temporal':
                    if 'pattern_type' in results.columns:
                        summary['patterns_found'] = {
                            k: int(v) for k, v in results['pattern_type'].value_counts().to_dict().items()
                        }
                
                report['summary'][method] = summary
                
                # Add top results
                if 'sensitivity_score' in results.columns:
                    top_results = results.nlargest(10, 'sensitivity_score')[
                        ['parameter', 'output_variable', 'sensitivity_score']
                    ].to_dict('records')
                    report['detailed_results'][f'{method}_top_parameters'] = top_results
        
        # Save report
        # Convert numpy types before saving
        # Convert numpy types before saving
        report_converted = self._convert_numpy_types(report)

        # Save report
        report_path = output_dir / "advanced_sensitivity_report.json"
        with open(report_path, 'w') as f:
            json.dump(report_converted, f, indent=2)
        
        self.logger.info(f"Advanced analysis report saved: {report_path}")
    
    # [Keep all existing methods unchanged below this point]
    
    def _run_comparative_time_analysis(self, config: Dict[str, Any], output_dir: Path, analysis_type: str) -> Optional[str]:
        """Run analysis across multiple time slices for comparison"""
        self.logger.info("Running comparative time slice analysis...")
        
        # Define time slices to compare
        time_slices = [
            {"name": "full_year", "enabled": False},  # No slicing
            {"name": "peak_cooling", "enabled": True, "slice_type": "peak_months", "season": "cooling"},
            {"name": "peak_heating", "enabled": True, "slice_type": "peak_months", "season": "heating"},
            {"name": "peak_hours", "enabled": True, "slice_type": "time_of_day", "peak_hours": [14, 15, 16, 17]},
            {"name": "weekdays", "enabled": True, "slice_type": "day_of_week", "analyze_weekends": False},
            {"name": "weekends", "enabled": True, "slice_type": "day_of_week", "analyze_weekends": True}
        ]
        
        # Override with custom slices if provided
        if "time_slice_comparisons" in config.get("time_slicing", {}):
            time_slices = config["time_slicing"]["time_slice_comparisons"]
        
        comparison_results = {}
        
        for time_slice in time_slices:
            slice_name = time_slice.get("name", "unnamed")
            self.logger.info(f"Running analysis for time slice: {slice_name}")
            
            # Run the appropriate analysis type
            if analysis_type == "modification_based":
                report_path = self._run_modification_analysis(config, output_dir, time_slice)
            elif analysis_type == "traditional":
                report_path = self._run_traditional_analysis(config, output_dir, time_slice)
            else:
                continue
            
            if report_path and slice_name in self.results:
                comparison_results[slice_name] = {
                    "results": self.results[slice_name],
                    "report": self.reports.get(slice_name, {}),
                    "config": time_slice
                }
        
        # Generate comparative report
        if comparison_results:
            return self._generate_comparative_report(comparison_results, output_dir)
        
        return None
    
    def _run_modification_analysis(self, config: Dict[str, Any], output_dir: Path, 
                                 time_slice_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Run modification-based sensitivity analysis"""
        self.logger.info("Running modification-based sensitivity analysis...")
        if time_slice_config and time_slice_config.get('enabled', False):
            self.logger.info(f"With time slice: {time_slice_config.get('slice_type', 'custom')}")
        
        # Initialize analyzer
        analyzer = ModificationSensitivityAnalyzer(self.job_output_dir, self.logger)
        
        # Get modification analysis config
        mod_config = config.get("modification_analysis", {})
        
        # Load modification tracking
        try:
            modifications = analyzer.load_modification_tracking(
                detect_scope=mod_config.get("multi_level_analysis", True)
            )
            if modifications.empty:
                self.logger.error("No modifications found")
                return None
        except FileNotFoundError as e:
            self.logger.error(f"Modification tracking not found: {e}")
            return None
        
        # Load simulation results with time slicing
        result_type = mod_config.get("aggregation", "daily")
        analyzer.load_simulation_results(
            result_type=result_type,
            time_slice_config=time_slice_config
        )
        
        # Determine analysis parameters
        output_variables = mod_config.get("output_variables", [
            "Heating:EnergyTransfer",
            "Cooling:EnergyTransfer",
            "Electricity:Facility"
        ])
        
        # Clean variable names
        output_vars_clean = [var.split('[')[0].strip() for var in output_variables]
        
        # Determine analysis levels
        if mod_config.get("multi_level_analysis", True):
            levels = []
            if mod_config.get("aggregation_levels", {}).get("analyze_by_building", True):
                levels.append("building")
            if mod_config.get("aggregation_levels", {}).get("analyze_by_zone", True):
                levels.append("zone")
            if mod_config.get("analyze_equipment", False):
                levels.append("equipment")
        else:
            levels = ["building"]
        
        # Run sensitivity calculation
        sensitivity_results = analyzer.calculate_sensitivity(
            output_variables=output_vars_clean,
            analysis_levels=levels,
            parameter_groups=mod_config.get("parameter_groups", config.get("categories_to_modify")),
            aggregation=mod_config.get("output_aggregation", "sum"),
            method=mod_config.get("method", "elasticity"),
            calculate_interactions=mod_config.get("aggregation_levels", {}).get("cross_level_analysis", False),
            test_significance=mod_config.get("test_significance", True),
            weight_by_validation=mod_config.get("analysis_options", {}).get("weight_by_validation_accuracy", False)
        )
        
        if sensitivity_results.empty:
            self.logger.error("No sensitivity results calculated")
            return None
        
        # Add time slice info to results
        if time_slice_config and time_slice_config.get('enabled', False):
            sensitivity_results['time_slice'] = time_slice_config.get('name', time_slice_config.get('slice_type', 'custom'))
        
        # Analyze parameter groups
        group_analysis = analyzer.analyze_parameter_groups(
            sensitivity_results,
            mod_config.get("parameter_groups")
        )
        
        # Generate report
        report = analyzer.generate_report(
            sensitivity_results,
            group_analysis,
            output_dir
        )
        
        # Add time slice info to report
        if time_slice_config and time_slice_config.get('enabled', False):
            report['time_slice_config'] = time_slice_config
        
        # Save results
        results_path, report_path = analyzer.save_results(
            sensitivity_results,
            report,
            output_dir
        )
        
        # Store for later use
        result_key = time_slice_config.get('name', 'modification') if time_slice_config else 'modification'
        self.results[result_key] = sensitivity_results
        self.reports[result_key] = report
        self.time_slice_configs[result_key] = time_slice_config
        
        self.logger.info(f"Modification sensitivity analysis complete: {report_path}")
        return str(report_path)
    
    def _run_traditional_analysis(self, config: Dict[str, Any], output_dir: Path,
                                time_slice_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Run traditional scenario-based sensitivity analysis"""
        self.logger.info("Running traditional sensitivity analysis...")
        if time_slice_config and time_slice_config.get('enabled', False):
            self.logger.info(f"With time slice: {time_slice_config.get('slice_type', 'custom')}")
        
        # Initialize analyzer
        analyzer = TraditionalSensitivityAnalyzer(self.job_output_dir, self.logger)
        
        # Load parameter data
        categories = config.get("categories")
        if not categories and config.get("file_patterns"):
            categories = self._extract_categories_from_patterns(config["file_patterns"])
        
        try:
            param_data = analyzer.load_parameter_data(categories=categories)
            if param_data.empty:
                self.logger.error("No parameter data loaded")
                return None
        except Exception as e:
            self.logger.error(f"Failed to load parameter data: {e}")
            return None
        
        # Load scenario results if available with time slicing
        if config.get("scenario_folder"):
            try:
                scenario_results = analyzer.load_scenario_results(
                    scenario_folder=Path(config["scenario_folder"]),
                    time_slice_config=time_slice_config
                )
            except Exception as e:
                self.logger.warning(f"Could not load scenario results: {e}")
        
        # Calculate sensitivity
        method = config.get("method", "correlation")
        output_variables = config.get("target_variable", [])
        if isinstance(output_variables, str):
            output_variables = [output_variables]
        
        sensitivity_results = analyzer.calculate_sensitivity(
            method=method,
            output_variables=output_variables,
            parameter_groups=config.get("parameter_groups"),
            hierarchical=config.get("perform_hierarchical", False),
            min_samples=config.get("min_samples", 5),
            time_slice_config=time_slice_config
        )
        
        if sensitivity_results.empty:
            self.logger.error("No sensitivity results calculated")
            return None
        
        # Add time slice info to results
        if time_slice_config and time_slice_config.get('enabled', False):
            sensitivity_results['time_slice'] = time_slice_config.get('name', time_slice_config.get('slice_type', 'custom'))
        
        # Perform additional analyses if requested
        if config.get("perform_building_specific", False):
            building_results = analyzer.perform_building_specific_analysis(
                self.data_manager.building_metadata
            )
            if building_results:
                # Merge or store separately
                self.results['building_specific'] = building_results
        
        # Generate report
        report = analyzer.generate_base_report(
            sensitivity_results,
            additional_info={
                'analysis_config': config,
                'method_details': {
                    'method': method,
                    'categories_analyzed': categories or 'all'
                },
                'time_slice_config': time_slice_config if time_slice_config else None
            }
        )
        
        # Save results
        results_path, report_path = analyzer.save_results(
            sensitivity_results,
            report,
            output_dir
        )
        
        # Export for downstream use
        if config.get("export_top_n_parameters", 0) > 0:
            analyzer.export_for_downstream(
                sensitivity_results,
                output_dir,
                top_n=config["export_top_n_parameters"]
            )
        
        # Store for later use
        result_key = time_slice_config.get('name', 'traditional') if time_slice_config else 'traditional'
        self.results[result_key] = sensitivity_results
        self.reports[result_key] = report
        self.time_slice_configs[result_key] = time_slice_config
        
        self.logger.info(f"Traditional sensitivity analysis complete: {report_path}")
        return str(report_path)
    
    def _run_hybrid_analysis(self, config: Dict[str, Any], output_dir: Path,
                           time_slice_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Run both traditional and modification analyses and combine results"""
        self.logger.info("Running hybrid sensitivity analysis...")
        
        # Run both analyses
        trad_report = self._run_traditional_analysis(config, output_dir, time_slice_config)
        mod_report = self._run_modification_analysis(config, output_dir, time_slice_config)
        
        if not trad_report and not mod_report:
            self.logger.error("Both analyses failed")
            return None
        
        # Combine results
        combined_results = self._combine_analysis_results()
        
        # Generate combined report
        combined_report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'hybrid',
                'job_output_dir': str(self.job_output_dir)
            },
            'traditional_analysis': self.reports.get('traditional', {}),
            'modification_analysis': self.reports.get('modification', {}),
            'combined_summary': self._generate_combined_summary(combined_results),
            'comparison': self._compare_methods(combined_results),
            'time_slice_config': time_slice_config if time_slice_config else None
        }
        
        # Save combined report
        filename_suffix = ""
        if time_slice_config and time_slice_config.get('enabled', False):
            filename_suffix = f"_{time_slice_config.get('name', time_slice_config.get('slice_type', 'custom'))}"
        
        report_path = output_dir / f"hybrid_sensitivity_report{filename_suffix}.json"
        with open(report_path, 'w') as f:
            json.dump(combined_report, f, indent=2)
        
        # Save combined results
        if combined_results is not None:
            combined_results.to_parquet(output_dir / f"hybrid_sensitivity_results{filename_suffix}.parquet")
        
        self.logger.info(f"Hybrid sensitivity analysis complete: {report_path}")
        return str(report_path)
    
    # [Include all other existing methods unchanged...]
    def _generate_comparative_report(self, comparison_results: Dict[str, Any], output_dir: Path) -> str:
        """Generate report comparing results across time slices"""
        self.logger.info("Generating comparative time slice report...")
        
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'time_slice_comparison',
                'job_output_dir': str(self.job_output_dir),
                'n_time_slices': len(comparison_results)
            },
            'time_slices_analyzed': list(comparison_results.keys()),
            'comparative_summary': {},
            'time_slice_details': {}
        }
        
        # Analyze parameter rankings across time slices
        parameter_rankings = {}
        
        for slice_name, slice_data in comparison_results.items():
            results_df = slice_data['results']
            if 'parameter' in results_df.columns and 'sensitivity_score' in results_df.columns:
                # Get top parameters for this slice
                top_params = results_df.nlargest(20, 'sensitivity_score')[['parameter', 'sensitivity_score']]
                
                for idx, row in top_params.iterrows():
                    param = row['parameter']
                    if param not in parameter_rankings:
                        parameter_rankings[param] = {}
                    parameter_rankings[param][slice_name] = {
                        'rank': idx + 1,
                        'score': row['sensitivity_score']
                    }
            
            # Store detailed results
            report['time_slice_details'][slice_name] = {
                'config': slice_data['config'],
                'n_results': len(results_df),
                'summary_stats': {
                    'mean_sensitivity': results_df['sensitivity_score'].mean() if 'sensitivity_score' in results_df else None,
                    'std_sensitivity': results_df['sensitivity_score'].std() if 'sensitivity_score' in results_df else None,
                    'n_parameters': results_df['parameter'].nunique() if 'parameter' in results_df else 0
                }
            }
        
        # Analyze stability of parameters across time slices
        stability_analysis = []
        for param, rankings in parameter_rankings.items():
            scores = [data['score'] for data in rankings.values()]
            ranks = [data['rank'] for data in rankings.values()]
            
            stability_analysis.append({
                'parameter': param,
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'cv': np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else float('inf'),
                'rank_variance': np.var(ranks),
                'n_appearances': len(rankings),
                'time_slices': list(rankings.keys())
            })
        
        # Sort by stability (lower CV = more stable)
        stability_df = pd.DataFrame(stability_analysis)
        stability_df = stability_df.sort_values('cv')
        
        # Create comparative summary
        report['comparative_summary'] = {
            'most_stable_parameters': stability_df.head(10)[['parameter', 'cv', 'mean_score']].to_dict('records'),
            'most_variable_parameters': stability_df.tail(10)[['parameter', 'cv', 'mean_score']].to_dict('records'),
            'consistently_important': stability_df[
                (stability_df['n_appearances'] == len(comparison_results)) & 
                (stability_df['mean_score'] > stability_df['mean_score'].quantile(0.75))
            ][['parameter', 'mean_score']].to_dict('records')
        }
        
        # Save comparative results
        stability_df.to_parquet(output_dir / 'parameter_stability_across_time_slices.parquet')
        
        # Save report
        report_path = output_dir / 'time_slice_comparison_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Store results
        self.results['time_slice_comparison'] = stability_df
        self.reports['comparative_summary'] = report['comparative_summary']
        
        # Generate visualizations
        self._generate_time_slice_visualizations(stability_df, comparison_results, output_dir)
        
        self.logger.info(f"Comparative time slice analysis complete: {report_path}")
        return str(report_path)
    
    def _generate_time_slice_visualizations(self, stability_df: pd.DataFrame, 
                                          comparison_results: Dict[str, Any], 
                                          output_dir: Path) -> None:
        """Generate visualizations for time slice comparison"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # 1. Parameter stability plot
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Most stable parameters
            stable_params = stability_df.head(10)
            ax1.barh(range(len(stable_params)), stable_params['cv'])
            ax1.set_yticks(range(len(stable_params)))
            ax1.set_yticklabels([p.split('*')[-1] if '*' in p else p for p in stable_params['parameter']])
            ax1.set_xlabel('Coefficient of Variation')
            ax1.set_title('Most Stable Parameters Across Time Slices')
            ax1.invert_yaxis()
            
            # Most variable parameters
            variable_params = stability_df.tail(10)
            ax2.barh(range(len(variable_params)), variable_params['cv'])
            ax2.set_yticks(range(len(variable_params)))
            ax2.set_yticklabels([p.split('*')[-1] if '*' in p else p for p in variable_params['parameter']])
            ax2.set_xlabel('Coefficient of Variation')
            ax2.set_title('Most Variable Parameters Across Time Slices')
            ax2.invert_yaxis()
            
            plt.tight_layout()
            plt.savefig(output_dir / 'parameter_stability.png', dpi=300)
            plt.close()
            
            # 2. Time slice comparison heatmap
            # Create matrix of top parameters across time slices
            top_params = stability_df.head(20)['parameter'].tolist()
            time_slices = list(comparison_results.keys())
            
            heatmap_data = np.zeros((len(top_params), len(time_slices)))
            
            for i, param in enumerate(top_params):
                for j, slice_name in enumerate(time_slices):
                    results_df = comparison_results[slice_name]['results']
                    if 'parameter' in results_df.columns and 'sensitivity_score' in results_df.columns:
                        param_data = results_df[results_df['parameter'] == param]
                        if not param_data.empty:
                            heatmap_data[i, j] = param_data['sensitivity_score'].iloc[0]
            
            # Create heatmap
            plt.figure(figsize=(10, 12))
            sns.heatmap(heatmap_data, 
                       xticklabels=time_slices,
                       yticklabels=[p.split('*')[-1] if '*' in p else p for p in top_params],
                       cmap='YlOrRd',
                       annot=True,
                       fmt='.3f')
            plt.title('Sensitivity Scores Across Time Slices')
            plt.xlabel('Time Slice')
            plt.ylabel('Parameter')
            plt.tight_layout()
            plt.savefig(output_dir / 'time_slice_sensitivity_heatmap.png', dpi=300)
            plt.close()
            
        except ImportError:
            self.logger.warning("Matplotlib/seaborn not available - skipping visualizations")
        except Exception as e:
            self.logger.error(f"Failed to generate time slice visualizations: {e}")
    
    def _export_for_surrogate(self, output_dir: Path, config: Dict[str, Any]) -> None:
        """Export sensitivity results for surrogate modeling"""
        self.logger.info("Exporting results for surrogate modeling...")
        
        # Combine all results
        all_results = []
        for analysis_type, results in self.results.items():
            if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                # Get top parameters
                top_n = config.get("export_top_n_parameters", 20)
                top_params = results.nlargest(top_n, 'sensitivity_score')
                all_results.append(top_params)
        
        if all_results:
            combined = pd.concat(all_results, ignore_index=True)
            
            # Remove duplicates, keeping highest sensitivity score
            combined = combined.sort_values('sensitivity_score', ascending=False)
            combined = combined.drop_duplicates(subset=['parameter', 'output_variable'], keep='first')
            
            # Export
            export_path = output_dir / "sensitivity_for_surrogate.parquet"
            combined.to_parquet(export_path)
            
            # Also export parameter list
            param_list = combined['parameter'].unique().tolist()
            with open(output_dir / "important_parameters.json", 'w') as f:
                json.dump({
                    'important_parameters': param_list,
                    'n_parameters': len(param_list),
                    'export_config': config
                }, f, indent=2)
            
            self.logger.info(f"Exported {len(param_list)} important parameters for surrogate modeling")
    
    def _export_for_calibration(self, output_dir: Path, config: Dict[str, Any]) -> None:
        """Export sensitivity results for calibration"""
        self.logger.info("Exporting results for calibration...")
        
        # Similar to surrogate export but with calibration-specific formatting
        calibration_params = {}
        
        for analysis_type, results in self.results.items():
            if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                # Group by output variable
                for output_var in results['output_variable'].unique():
                    var_results = results[results['output_variable'] == output_var]
                    top_params = var_results.nlargest(10, 'sensitivity_score')
                    
                    if output_var not in calibration_params:
                        calibration_params[output_var] = []
                    
                    calibration_params[output_var].extend(
                        top_params[['parameter', 'sensitivity_score']].to_dict('records')
                    )
        
        # Remove duplicates and sort
        for output_var in calibration_params:
            params = calibration_params[output_var]
            # Remove duplicates
            seen = set()
            unique_params = []
            for p in params:
                if p['parameter'] not in seen:
                    seen.add(p['parameter'])
                    unique_params.append(p)
            calibration_params[output_var] = sorted(
                unique_params, key=lambda x: x['sensitivity_score'], reverse=True
            )[:15]  # Top 15 per output
        
        # Export
        with open(output_dir / "calibration_parameters.json", 'w') as f:
            json.dump(calibration_params, f, indent=2)
        
        self.logger.info(f"Exported calibration parameters for {len(calibration_params)} output variables")
    
    def _generate_visualizations(self, output_dir: Path, config: Dict[str, Any]) -> None:
        """Generate comprehensive visualizations"""
        self.logger.info("Generating sensitivity visualizations...")
        
        viz_dir = output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # Generate basic visualizations
        if self.results:
            self._plot_top_parameters(viz_dir)
            
            # Check for multi-level results
            for results in self.results.values():
                if isinstance(results, pd.DataFrame) and 'level' in results.columns:
                    self._plot_zone_heatmap(results, viz_dir)
                    break
            
            # Method comparison if hybrid
            if len(self.results) > 1:
                self._plot_method_comparison(viz_dir)
    
    def _plot_top_parameters(self, viz_dir: Path):
        """Plot top parameters from each analysis method"""
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(1, len(self.results), figsize=(6 * len(self.results), 8))
            
            if len(self.results) == 1:
                axes = [axes]
            
            for i, (method, results) in enumerate(self.results.items()):
                if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                    top_params = results.nlargest(15, 'sensitivity_score')
                    
                    axes[i].barh(range(len(top_params)), top_params['sensitivity_score'])
                    axes[i].set_yticks(range(len(top_params)))
                    axes[i].set_yticklabels(top_params['parameter'])
                    axes[i].set_xlabel('Sensitivity Score')
                    axes[i].set_title(f'Top Parameters - {method.title()}')
                    axes[i].invert_yaxis()
            
            plt.tight_layout()
            plt.savefig(viz_dir / 'top_parameters_comparison.png', dpi=300)
            plt.close()
        except ImportError:
            self.logger.warning("Matplotlib not available - skipping parameter plots")
    
    def _plot_method_comparison(self, viz_dir: Path):
        """Compare sensitivity scores across methods"""
        # Implementation for method comparison visualization
        pass
    
    def _plot_zone_heatmap(self, results: pd.DataFrame, viz_dir: Path):
        """Create heatmap of zone-level sensitivities"""
        if 'level' not in results.columns or 'zone' not in results['level'].values:
            return
        
        # Use reporter's heatmap generation if available
        zone_results = results[results['level'] == 'zone']
        if not zone_results.empty:
            self.reporter.create_sensitivity_heatmap(
                zone_results,
                save_path=str(viz_dir / 'zone_sensitivity_heatmap.png')
            )
    
    def _extract_categories_from_patterns(self, patterns: List[str]) -> List[str]:
        """Extract category names from file patterns"""
        categories = []
        
        for pattern in patterns:
            if '*' in pattern:
                parts = pattern.replace('*', '').replace('.csv', '').strip()
                if parts:
                    categories.append(parts)
        
        return categories
    
    def _combine_analysis_results(self) -> Optional[pd.DataFrame]:
        """Combine results from different analysis methods"""
        if not self.results:
            return None
        
        combined_dfs = []
        
        # Add source column to each result set
        for analysis_type, df in self.results.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df_copy = df.copy()
                df_copy['analysis_source'] = analysis_type
                combined_dfs.append(df_copy)
        
        if not combined_dfs:
            return None
        
        # Combine all results
        combined = pd.concat(combined_dfs, ignore_index=True)
        
        # Calculate consensus sensitivity scores
        if 'parameter' in combined.columns and 'output_variable' in combined.columns:
            # Average sensitivity scores across methods
            consensus = combined.groupby(['parameter', 'output_variable']).agg({
                'sensitivity_score': ['mean', 'std', 'count']
            }).reset_index()
            
            consensus.columns = ['parameter', 'output_variable', 'consensus_score', 'score_std', 'n_methods']
            
            # Merge back
            combined = combined.merge(consensus, on=['parameter', 'output_variable'], how='left')
        
        return combined
    
    def _generate_combined_summary(self, combined_results: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Generate summary of combined analysis results"""
        if combined_results is None or combined_results.empty:
            return {}
        
        summary = {
            'total_parameters_analyzed': combined_results['parameter'].nunique() if 'parameter' in combined_results.columns else 0,
            'total_output_variables': combined_results['output_variable'].nunique() if 'output_variable' in combined_results.columns else 0,
            'methods_used': combined_results['analysis_source'].unique().tolist() if 'analysis_source' in combined_results.columns else []
        }
        
        # Top consensus parameters
        if 'consensus_score' in combined_results.columns:
            top_consensus = combined_results.nlargest(10, 'consensus_score')[
                ['parameter', 'consensus_score', 'score_std', 'n_methods']
            ].to_dict('records')
            summary['top_consensus_parameters'] = top_consensus
        
        return summary
    
    def _compare_methods(self, combined_results: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Compare results between different methods"""
        if combined_results is None or combined_results.empty:
            return {}
        
        comparison = {}
        
        if 'analysis_source' in combined_results.columns:
            # Method agreement analysis
            if 'parameter' in combined_results.columns:
                # Find parameters that appear in multiple methods
                param_methods = combined_results.groupby('parameter')['analysis_source'].nunique()
                params_in_multiple = param_methods[param_methods > 1].index.tolist()
                
                comparison['parameters_in_multiple_methods'] = len(params_in_multiple)
                comparison['total_unique_parameters'] = combined_results['parameter'].nunique()
                comparison['method_overlap_percentage'] = (
                    len(params_in_multiple) / combined_results['parameter'].nunique() * 100
                    if combined_results['parameter'].nunique() > 0 else 0
                )
        
        return comparison


    # Backward compatibility function
    def run_enhanced_sensitivity_analysis(
        manager: SensitivityDataManager,
        config: Dict[str, Any],
        logger: logging.Logger
    ) -> Optional[str]:
        """
        Backward compatibility wrapper for the old function name
        """
        sensitivity_manager = SensitivityManager(manager.project_root, logger)
        return sensitivity_manager.run_analysis(config)
    
    def _convert_numpy_types(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Series):
            return obj.to_list()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_types(item) for item in obj)
        elif hasattr(obj, 'to_dict'):  # Handle pandas objects
            return obj.to_dict()
        return obj