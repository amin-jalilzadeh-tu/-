"""
c_sensitivity/unified_sensitivity.py

Enhanced unified sensitivity analysis with modification support.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from .sensitivity_data_manager import SensitivityDataManager
from .modification_sensitivity_analyzer import ModificationSensitivityAnalyzer


def run_enhanced_sensitivity_analysis(
    manager: SensitivityDataManager,
    config: Dict[str, Any],
    logger: logging.Logger
) -> Optional[str]:
    """
    Run enhanced sensitivity analysis with multiple methods.
    
    This can handle both traditional scenario-based and modification-based analysis.
    """
    output_dir = Path(config.get("output_base_dir", manager.project_root / "sensitivity_results"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if this is modification-based analysis
    if config.get("analysis_type") == "modification_based":
        # Route to modification analyzer
        analyzer = ModificationSensitivityAnalyzer(
            job_output_dir=manager.project_root,
            logger=logger
        )
        
        # Run modification-based analysis
        return run_modification_based_analysis(analyzer, config, output_dir, logger)
    
    # Otherwise, run traditional analysis
    return run_traditional_analysis(manager, config, output_dir, logger)


def run_modification_based_analysis(
    analyzer: ModificationSensitivityAnalyzer,
    config: Dict[str, Any],
    output_dir: Path,
    logger: logging.Logger
) -> Optional[str]:
    """Run modification-based sensitivity analysis."""
    logger.info("Running modification-based sensitivity analysis...")
    
    try:
        # Load modification data
        modifications = analyzer.load_modification_tracking()
        if modifications.empty:
            logger.error("No modifications found")
            return None
        
        # Load results
        mod_config = config.get("modification_analysis", {})
        base_results, modified_results = analyzer.load_simulation_results(
            result_type=mod_config.get("aggregation", "daily")
        )
        
        # Calculate deltas
        output_vars = mod_config.get("output_variables", [
            "Heating:EnergyTransfer",
            "Cooling:EnergyTransfer",
            "Electricity:Facility"
        ])
        
        # Clean variable names
        output_vars_clean = [var.split('[')[0].strip() for var in output_vars]
        
        output_deltas = analyzer.calculate_output_deltas(
            output_vars_clean,
            aggregation=mod_config.get("output_aggregation", "sum")
        )
        
        # Calculate parameter aggregates
        param_aggregates = analyzer.calculate_parameter_aggregates()
        
        # Calculate sensitivity
        parameter_groups = mod_config.get("parameter_groups")
        sensitivity_results = analyzer.calculate_sensitivity_scores(
            parameter_groups=parameter_groups,
            output_variables=[col for col in output_deltas.columns if col.endswith('_delta')]
        )
        
        # Weight by validation if requested
        if mod_config.get("analysis_options", {}).get("weight_by_validation_accuracy", False):
            sensitivity_results = analyzer.weight_by_validation(sensitivity_results)
        
        # Analyze groups
        group_analysis = analyzer.analyze_parameter_groups(sensitivity_results)
        
        # Generate report
        report = analyzer.generate_report(
            sensitivity_results,
            group_analysis,
            output_dir
        )
        
        return str(output_dir / "modification_sensitivity_report.json")
        
    except Exception as e:
        logger.error(f"Modification-based analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_traditional_analysis(
    manager: SensitivityDataManager,
    config: Dict[str, Any],
    output_dir: Path,
    logger: logging.Logger
) -> Optional[str]:
    """Run traditional sensitivity analysis using parsed data."""
    logger.info("Running traditional sensitivity analysis...")
    
    try:
        # Load data based on configuration
        categories = config.get("categories")
        if not categories and config.get("file_patterns"):
            # Extract categories from file patterns
            categories = extract_categories_from_patterns(config["file_patterns"])
        
        # Load parameters
        param_df = manager.load_idf_parameters(categories=categories)
        if param_df.empty:
            logger.error("No parameter data loaded")
            return None
        
        # Load simulation results
        target_vars = config.get("target_variable", [])
        if isinstance(target_vars, str):
            target_vars = [target_vars]
        
        results = manager.load_simulation_results(
            result_type='daily',
            variables=target_vars,
            load_modified=False  # Traditional uses base only
        )
        
        if not results or 'base' not in results:
            logger.error("No simulation results found")
            return None
        
        # Create analysis dataset
        X, y = manager.create_analysis_dataset(
            output_variables=target_vars,
            use_modifications=False
        )
        
        if X.empty or y.empty:
            logger.error("Failed to create analysis dataset")
            return None
        
        # Perform sensitivity analysis based on method
        method = config.get("method", "correlation")
        
        if method == "correlation":
            sensitivity_results = calculate_correlation_sensitivity(X, y)
        elif method == "regression":
            sensitivity_results = calculate_regression_sensitivity(X, y)
        elif method == "sobol":
            sensitivity_results = calculate_sobol_indices(X, y)
        else:
            logger.error(f"Unknown sensitivity method: {method}")
            return None
        
        # Apply additional analyses if requested
        if config.get("perform_building_specific"):
            building_results = perform_building_specific_analysis(
                X, y, manager.building_metadata
            )
            sensitivity_results['building_specific'] = building_results
        
        if config.get("perform_multi_objective"):
            multi_obj_results = perform_multi_objective_analysis(
                X, y, config.get("objective_weights", {})
            )
            sensitivity_results['multi_objective'] = multi_obj_results
        
        if config.get("perform_hierarchical"):
            hierarchy_results = perform_hierarchical_analysis(
                X, y, config.get("parameter_groups", {})
            )
            sensitivity_results['hierarchical'] = hierarchy_results
        
        # Generate report
        report = generate_sensitivity_report(
            sensitivity_results,
            config,
            output_dir
        )
        
        # Save results
        report_path = output_dir / "enhanced_sensitivity_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save detailed results
        if 'dataframe' in sensitivity_results:
            sensitivity_results['dataframe'].to_parquet(
                output_dir / "sensitivity_results.parquet"
            )
        
        # Export for downstream use
        if config.get("export_for_surrogate"):
            export_top_parameters(
                sensitivity_results,
                output_dir,
                config.get("export_top_n_parameters", 20)
            )
        
        logger.info(f"Traditional sensitivity analysis complete: {report_path}")
        return str(report_path)
        
    except Exception as e:
        logger.error(f"Traditional analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def calculate_correlation_sensitivity(X: pd.DataFrame, y: pd.DataFrame) -> Dict[str, Any]:
    """Calculate correlation-based sensitivity."""
    # Remove non-numeric columns
    X_numeric = X.select_dtypes(include=[np.number])
    y_numeric = y.select_dtypes(include=[np.number])
    
    results = []
    
    for y_col in y_numeric.columns:
        for x_col in X_numeric.columns:
            if x_col in ['building_id', 'variant_id']:
                continue
                
            # Calculate correlation
            corr = X_numeric[x_col].corr(y_numeric[y_col])
            
            if not np.isnan(corr):
                results.append({
                    'parameter': x_col,
                    'output': y_col,
                    'correlation': corr,
                    'abs_correlation': abs(corr),
                    'method': 'pearson'
                })
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('abs_correlation', ascending=False)
    
    return {
        'method': 'correlation',
        'dataframe': df_results,
        'top_parameters': df_results.head(20).to_dict('records')
    }


def calculate_regression_sensitivity(X: pd.DataFrame, y: pd.DataFrame) -> Dict[str, Any]:
    """Calculate regression-based sensitivity."""
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LinearRegression
    
    # Prepare data
    X_numeric = X.select_dtypes(include=[np.number]).drop(columns=['building_id', 'variant_id'], errors='ignore')
    y_numeric = y.select_dtypes(include=[np.number])
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_numeric)
    
    results = []
    
    for y_col in y_numeric.columns:
        # Fit regression
        model = LinearRegression()
        model.fit(X_scaled, y_numeric[y_col])
        
        # Get standardized coefficients
        for i, (col, coef) in enumerate(zip(X_numeric.columns, model.coef_)):
            results.append({
                'parameter': col,
                'output': y_col,
                'coefficient': coef,
                'abs_coefficient': abs(coef),
                'method': 'regression'
            })
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('abs_coefficient', ascending=False)
    
    return {
        'method': 'regression',
        'dataframe': df_results,
        'top_parameters': df_results.head(20).to_dict('records')
    }


def calculate_sobol_indices(X: pd.DataFrame, y: pd.DataFrame, n_samples: int = 1000) -> Dict[str, Any]:
    """Calculate Sobol sensitivity indices (simplified version)."""
    # This is a placeholder for actual Sobol analysis
    # Real implementation would use SALib or similar
    logger = logging.getLogger(__name__)
    logger.warning("Sobol indices calculation not fully implemented - using approximation")
    
    # Fall back to correlation for now
    return calculate_correlation_sensitivity(X, y)


def perform_building_specific_analysis(
    X: pd.DataFrame, 
    y: pd.DataFrame,
    building_metadata: pd.DataFrame
) -> Dict[str, Any]:
    """Perform building-specific sensitivity analysis."""
    results = {}
    
    if 'building_id' not in X.columns:
        return results
    
    # Group by building type if metadata available
    if not building_metadata.empty:
        merged = X.merge(building_metadata, on='building_id', how='left')
        
        for building_type in merged['building_type'].dropna().unique():
            type_data = merged[merged['building_type'] == building_type]
            type_X = type_data.drop(columns=['building_type', 'building_function', 'age_range'], errors='ignore')
            type_y = y[y.index.isin(type_X.index)]
            
            if len(type_X) > 10:  # Need enough samples
                type_sensitivity = calculate_correlation_sensitivity(type_X, type_y)
                results[building_type] = type_sensitivity
    
    return results


def perform_multi_objective_analysis(
    X: pd.DataFrame,
    y: pd.DataFrame,
    weights: Dict[str, float]
) -> Dict[str, Any]:
    """Perform multi-objective sensitivity analysis."""
    # Create weighted composite output
    y_numeric = y.select_dtypes(include=[np.number])
    
    # Normalize outputs
    y_norm = (y_numeric - y_numeric.mean()) / y_numeric.std()
    
    # Apply weights
    composite_output = pd.Series(0, index=y_norm.index)
    
    for col in y_norm.columns:
        weight = weights.get(col, 1.0 / len(y_norm.columns))
        composite_output += y_norm[col] * weight
    
    # Calculate sensitivity for composite
    y_composite = pd.DataFrame({'composite_output': composite_output})
    
    return calculate_correlation_sensitivity(X, y_composite)


def perform_hierarchical_analysis(
    X: pd.DataFrame,
    y: pd.DataFrame,
    parameter_groups: Dict[str, List[str]]
) -> Dict[str, Any]:
    """Perform hierarchical sensitivity analysis by parameter groups."""
    results = {}
    
    for group_name, params in parameter_groups.items():
        # Find columns matching this group
        group_cols = []
        for param in params:
            matching_cols = [col for col in X.columns if param in col]
            group_cols.extend(matching_cols)
        
        if group_cols:
            # Calculate group sensitivity
            group_X = X[group_cols]
            group_sensitivity = calculate_correlation_sensitivity(group_X, y)
            
            # Aggregate to group level
            avg_sensitivity = np.mean([
                abs(r['correlation']) 
                for r in group_sensitivity['top_parameters']
            ])
            
            results[group_name] = {
                'average_sensitivity': avg_sensitivity,
                'n_parameters': len(group_cols),
                'parameters': group_cols
            }
    
    return results


def generate_sensitivity_report(
    results: Dict[str, Any],
    config: Dict[str, Any],
    output_dir: Path
) -> Dict[str, Any]:
    """Generate comprehensive sensitivity report."""
    report = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'method': results.get('method', 'unknown'),
            'config': config
        },
        'summary': {
            'top_parameters': results.get('top_parameters', []),
            'method': results.get('method', 'unknown')
        }
    }
    
    # Add additional analysis results
    if 'building_specific' in results:
        report['building_specific'] = results['building_specific']
    
    if 'multi_objective' in results:
        report['multi_objective'] = results['multi_objective']
    
    if 'hierarchical' in results:
        report['hierarchical'] = results['hierarchical']
    
    return report


def export_top_parameters(
    results: Dict[str, Any],
    output_dir: Path,
    top_n: int = 20
) -> None:
    """Export top sensitive parameters for downstream use."""
    if 'dataframe' in results:
        df = results['dataframe']
        
        # Get top parameters
        top_params = df.head(top_n)
        
        # Save for surrogate/calibration
        top_params.to_csv(output_dir / "top_sensitive_parameters.csv", index=False)
        
        # Create parameter list
        param_list = top_params['parameter'].unique().tolist()
        
        with open(output_dir / "sensitive_parameters.json", 'w') as f:
            json.dump({
                'parameters': param_list,
                'selection_method': results['method'],
                'top_n': top_n
            }, f, indent=2)


def extract_categories_from_patterns(patterns: List[str]) -> List[str]:
    """Extract category names from file patterns."""
    categories = []
    
    for pattern in patterns:
        # Extract category from pattern like "*hvac*.csv"
        if '*' in pattern:
            parts = pattern.replace('*', '').replace('.csv', '').strip()
            if parts:
                categories.append(parts)
    
    return categories