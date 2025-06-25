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


class SensitivityManager:
    """Main manager for all sensitivity analysis types"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger or logging.getLogger(__name__)
        self.data_manager = SensitivityDataManager(job_output_dir)
        self.reporter = SensitivityReporter()
        
        # Analysis results storage
        self.results = {}
        self.reports = {}
        
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
        
        # Create output directory
        output_dir = Path(config.get("output_base_dir", self.job_output_dir / "sensitivity_results"))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if analysis_type == "modification_based":
                report_path = self._run_modification_analysis(config, output_dir)
            elif analysis_type == "traditional":
                report_path = self._run_traditional_analysis(config, output_dir)
            elif analysis_type == "hybrid":
                report_path = self._run_hybrid_analysis(config, output_dir)
            else:
                self.logger.error(f"Unknown analysis type: {analysis_type}")
                return None
            
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
    
    def _run_modification_analysis(self, config: Dict[str, Any], output_dir: Path) -> Optional[str]:
        """Run modification-based sensitivity analysis"""
        self.logger.info("Running modification-based sensitivity analysis...")
        
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
        
        # Load simulation results
        result_type = mod_config.get("aggregation", "daily")
        analyzer.load_simulation_results(result_type=result_type)
        
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
        
        # Save results
        results_path, report_path = analyzer.save_results(
            sensitivity_results,
            report,
            output_dir
        )
        
        # Store for later use
        self.results['modification'] = sensitivity_results
        self.reports['modification'] = report
        
        self.logger.info(f"Modification sensitivity analysis complete: {report_path}")
        return str(report_path)
    
    def _run_traditional_analysis(self, config: Dict[str, Any], output_dir: Path) -> Optional[str]:
        """Run traditional scenario-based sensitivity analysis"""
        self.logger.info("Running traditional sensitivity analysis...")
        
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
        
        # Load scenario results if available
        if config.get("scenario_folder"):
            try:
                scenario_results = analyzer.load_scenario_results(
                    scenario_folder=Path(config["scenario_folder"])
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
            min_samples=config.get("min_samples", 5)
        )
        
        if sensitivity_results.empty:
            self.logger.error("No sensitivity results calculated")
            return None
        
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
                }
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
        self.results['traditional'] = sensitivity_results
        self.reports['traditional'] = report
        
        self.logger.info(f"Traditional sensitivity analysis complete: {report_path}")
        return str(report_path)
    
    def _run_hybrid_analysis(self, config: Dict[str, Any], output_dir: Path) -> Optional[str]:
        """Run both traditional and modification analyses and combine results"""
        self.logger.info("Running hybrid sensitivity analysis...")
        
        # Run both analyses
        trad_report = self._run_traditional_analysis(config, output_dir)
        mod_report = self._run_modification_analysis(config, output_dir)
        
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
            'comparison': self._compare_methods(combined_results)
        }
        
        # Save combined report
        report_path = output_dir / "hybrid_sensitivity_report.json"
        with open(report_path, 'w') as f:
            json.dump(combined_report, f, indent=2)
        
        # Save combined results
        if combined_results is not None:
            combined_results.to_parquet(output_dir / "hybrid_sensitivity_results.parquet")
        
        self.logger.info(f"Hybrid sensitivity analysis complete: {report_path}")
        return str(report_path)
    
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
            'total_parameters_analyzed': combined_results['parameter'].nunique() if 'parameter' in combined_results else 0,
            'total_outputs_analyzed': combined_results['output_variable'].nunique() if 'output_variable' in combined_results else 0,
            'analysis_methods_used': combined_results['analysis_source'].unique().tolist() if 'analysis_source' in combined_results else []
        }
        
        # Top parameters by consensus
        if 'consensus_score' in combined_results.columns:
            top_consensus = combined_results.nlargest(10, 'consensus_score')[
                ['parameter', 'consensus_score', 'n_methods']
            ].to_dict('records')
            summary['top_parameters_consensus'] = top_consensus
        
        return summary
    
    def _compare_methods(self, combined_results: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Compare results across different methods"""
        if combined_results is None or combined_results.empty:
            return {}
        
        comparison = {}
        
        # Method agreement analysis
        if 'parameter' in combined_results.columns and 'analysis_source' in combined_results.columns:
            # Find parameters identified by multiple methods
            param_methods = combined_results.groupby('parameter')['analysis_source'].nunique()
            agreed_params = param_methods[param_methods > 1].index.tolist()
            
            comparison['parameters_agreed_upon'] = agreed_params
            comparison['agreement_rate'] = len(agreed_params) / len(param_methods) if len(param_methods) > 0 else 0
        
        # Method-specific insights
        for method in combined_results['analysis_source'].unique():
            method_df = combined_results[combined_results['analysis_source'] == method]
            comparison[f'{method}_unique_parameters'] = method_df[
                ~method_df['parameter'].isin(agreed_params)
            ]['parameter'].unique().tolist() if 'parameter' in method_df else []
        
        return comparison
    
    def _export_for_surrogate(self, output_dir: Path, config: Dict[str, Any]):
        """Export sensitivity results for surrogate modeling"""
        self.logger.info("Exporting results for surrogate modeling...")
        
        # Get top parameters from all analyses
        all_top_params = set()
        top_n = config.get("export_top_n_parameters", 30)
        
        for analysis_type, results in self.results.items():
            if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                top_params = results.nlargest(top_n, 'sensitivity_score')['parameter'].unique()
                all_top_params.update(top_params)
        
        # Save parameter list
        param_export = {
            'parameters': list(all_top_params),
            'selection_method': 'sensitivity_analysis',
            'top_n_per_method': top_n,
            'total_selected': len(all_top_params),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_dir / 'sensitive_parameters_for_surrogate.json', 'w') as f:
            json.dump(param_export, f, indent=2)
        
        self.logger.info(f"Exported {len(all_top_params)} parameters for surrogate modeling")
    
    def _export_for_calibration(self, output_dir: Path, config: Dict[str, Any]):
        """Export sensitivity results for calibration"""
        self.logger.info("Exporting results for calibration...")
        
        # Similar to surrogate export but with calibration-specific format
        top_n = config.get("export_top_n_parameters", 15)
        
        calibration_params = []
        
        for analysis_type, results in self.results.items():
            if isinstance(results, pd.DataFrame) and 'sensitivity_score' in results.columns:
                top_params = results.nlargest(top_n, 'sensitivity_score')
                
                for _, row in top_params.iterrows():
                    calibration_params.append({
                        'parameter': row['parameter'],
                        'sensitivity_score': float(row['sensitivity_score']),
                        'analysis_method': analysis_type,
                        'output_variable': row.get('output_variable', 'unknown')
                    })
        
        # Remove duplicates, keeping highest sensitivity score
        param_dict = {}
        for param in calibration_params:
            key = param['parameter']
            if key not in param_dict or param['sensitivity_score'] > param_dict[key]['sensitivity_score']:
                param_dict[key] = param
        
        calibration_export = {
            'parameters': list(param_dict.values()),
            'selection_criteria': 'top_sensitivity',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_dir / 'sensitive_parameters_for_calibration.json', 'w') as f:
            json.dump(calibration_export, f, indent=2)
        
        self.logger.info(f"Exported {len(param_dict)} parameters for calibration")
    
    def _generate_visualizations(self, output_dir: Path, config: Dict[str, Any]):
        """Generate sensitivity analysis visualizations"""
        self.logger.info("Generating visualizations...")
        
        viz_dir = output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        viz_types = config.get("visualization_types", [
            "sensitivity_by_level",
            "top_parameters_by_level",
            "parameter_comparison"
        ])
        
        for viz_type in viz_types:
            try:
                if viz_type == "sensitivity_by_level" and 'modification' in self.results:
                    self._plot_sensitivity_by_level(self.results['modification'], viz_dir)
                elif viz_type == "top_parameters_by_level":
                    self._plot_top_parameters(viz_dir)
                elif viz_type == "parameter_comparison" and len(self.results) > 1:
                    self._plot_method_comparison(viz_dir)
                elif viz_type == "zone_sensitivity_heatmap" and 'modification' in self.results:
                    self._plot_zone_heatmap(self.results['modification'], viz_dir)
            except Exception as e:
                self.logger.warning(f"Failed to generate {viz_type} visualization: {e}")
    
    def _plot_sensitivity_by_level(self, results: pd.DataFrame, viz_dir: Path):
        """Plot sensitivity scores by analysis level"""
        if 'level' not in results.columns:
            return
        
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Group by level and calculate statistics
        level_stats = results.groupby('level')['sensitivity_score'].describe()
        
        # Create box plot
        levels = results['level'].unique()
        data_by_level = [results[results['level'] == level]['sensitivity_score'].values for level in levels]
        
        ax.boxplot(data_by_level, labels=levels)
        ax.set_xlabel('Analysis Level')
        ax.set_ylabel('Sensitivity Score')
        ax.set_title('Sensitivity Distribution by Analysis Level')
        
        plt.tight_layout()
        plt.savefig(viz_dir / 'sensitivity_by_level.png', dpi=300)
        plt.close()
    
    def _plot_top_parameters(self, viz_dir: Path):
        """Plot top parameters from each analysis method"""
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
