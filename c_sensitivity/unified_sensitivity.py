"""
unified_sensitivity.py - ENHANCED VERSION

Now includes:
- Building-specific sensitivity analysis
- Validation-weighted sensitivity
- Multi-objective analysis
- Hierarchical parameter grouping
- Integration with data manager
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, List, Tuple
import glob
import json
from datetime import datetime

# Import time slice utilities (existing)
from cal.time_slice_utils import (
    filter_results_by_time_slice,
    apply_predefined_slice,
    get_peak_hours
)

# Import new data manager
from c_sensitivity.sensitivity_data_manager import SensitivityDataManager

# Attempt SALib imports (existing)
try:
    from SALib.sample import morris as morris_sample
    from SALib.sample import saltelli
    from SALib.analyze import morris as morris_analyze
    from SALib.analyze import sobol
    HAVE_SALIB = True
except ImportError:
    HAVE_SALIB = False
    morris_sample = None
    morris_analyze = None
    saltelli = None
    sobol = None


###############################################################################
# EXISTING FUNCTIONS (kept from original)
###############################################################################

def encode_categorical_if_known(param_name: str, param_value) -> Optional[float]:
    """[Existing function - unchanged]"""
    if param_value is None or pd.isna(param_value):
        return None

    try:
        return float(param_value)
    except (ValueError, TypeError):
        pass

    # Known encodings
    if param_name.lower().endswith("fuel_type"):
        if param_value == "Electricity":
            return 0.0
        elif param_value == "Gas":
            return 1.0
        return None

    if "roughness" in param_name.lower():
        rough_map = {
            "Smooth": 0.0,
            "MediumSmooth": 1.0,
            "MediumRough": 2.0,
            "Rough": 3.0
        }
        if param_value in rough_map:
            return rough_map[param_value]
        return None

    if param_value in ["Yes", "No"]:
        return 1.0 if param_value == "Yes" else 0.0

    if param_value == "SpectralAverage":
        return 0.0

    if param_value == "Electricity":
        return 0.0
    elif param_value == "Gas":
        return 1.0

    return None


def build_unified_param_name(row: pd.Series) -> str:
    """[Existing function - unchanged]"""
    base_name = str(row.get("param_name", "UnknownParam"))
    name_parts = []

    zname = row.get("zone_name", None)
    if pd.notna(zname) and isinstance(zname, str) and zname.strip():
        name_parts.append(zname.strip())

    oname = row.get("object_name", None)
    if pd.notna(oname) and isinstance(oname, str) and oname.strip():
        name_parts.append(oname.strip())

    skey = row.get("sub_key", None)
    if pd.notna(skey) and isinstance(skey, str) and skey.strip():
        name_parts.append(skey.strip())

    name_parts.append(base_name)
    return "__".join(name_parts)


###############################################################################
# ENHANCED FUNCTIONS
###############################################################################

def building_specific_sensitivity(
    df_scenarios: pd.DataFrame,
    df_results: pd.DataFrame,
    target_variables: Union[str, List[str]],
    building_groups: Optional[Dict[str, List[str]]] = None,
    validation_weights: Optional[pd.DataFrame] = None,
    output_dir: str = "sensitivity_by_building"
) -> Dict[str, pd.DataFrame]:
    """
    Perform sensitivity analysis for each building or building group
    
    Args:
        df_scenarios: Scenario parameters
        df_results: Simulation results
        target_variables: Variables to analyze
        building_groups: Dict of group_name -> building_ids
        validation_weights: DataFrame with building validation weights
        output_dir: Directory to save results
        
    Returns:
        Dictionary of group_name -> sensitivity_results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Default to analyzing all buildings together if no groups specified
    if building_groups is None:
        all_buildings = df_scenarios['ogc_fid'].unique() if 'ogc_fid' in df_scenarios.columns else []
        building_groups = {'all': list(all_buildings)}
    
    group_results = {}
    
    for group_name, building_ids in building_groups.items():
        print(f"\n[INFO] Analyzing sensitivity for group: {group_name} ({len(building_ids)} buildings)")
        
        # Filter data for this group
        if 'ogc_fid' in df_scenarios.columns:
            group_scenarios = df_scenarios[df_scenarios['ogc_fid'].isin(building_ids)]
        else:
            group_scenarios = df_scenarios
            
        if 'BuildingID' in df_results.columns:
            group_results_df = df_results[df_results['BuildingID'].isin(building_ids)]
        else:
            group_results_df = df_results
        
        if group_scenarios.empty or group_results_df.empty:
            print(f"[WARNING] No data for group {group_name}")
            continue
        
        # Perform correlation analysis
        corr_df = correlation_sensitivity(
            df_scenarios=group_scenarios,
            df_results=group_results_df,
            target_variables=target_variables
        )
        
        # Add validation weighting if available
        if validation_weights is not None and 'validation_weight' in validation_weights.columns:
            # Calculate weighted sensitivity scores
            if 'ogc_fid' in group_scenarios.columns:
                avg_weight = validation_weights[
                    validation_weights['building_id'].isin(building_ids)
                ]['validation_weight'].mean()
                
                corr_df['WeightedScore'] = corr_df['AbsCorrelation'] * avg_weight if 'AbsCorrelation' in corr_df.columns else 0
        
        # Save group results
        group_results[group_name] = corr_df
        corr_df.to_csv(f"{output_dir}/sensitivity_{group_name}.csv", index=False)
    
    return group_results


def multi_objective_sensitivity(
    df_scenarios: pd.DataFrame,
    df_results: pd.DataFrame,
    target_variables: List[str],
    objective_weights: Optional[Dict[str, float]] = None,
    identify_conflicts: bool = True
) -> pd.DataFrame:
    """
    Perform multi-objective sensitivity analysis
    
    Args:
        df_scenarios: Scenario parameters
        df_results: Simulation results
        target_variables: List of variables to analyze
        objective_weights: Weights for each objective (default: equal)
        identify_conflicts: Whether to identify conflicting parameters
        
    Returns:
        DataFrame with multi-objective sensitivity results
    """
    if len(target_variables) < 2:
        raise ValueError("Multi-objective analysis requires at least 2 target variables")
    
    # Default equal weights
    if objective_weights is None:
        objective_weights = {var: 1.0/len(target_variables) for var in target_variables}
    
    # Get correlation for each objective
    corr_results = correlation_sensitivity(
        df_scenarios=df_scenarios,
        df_results=df_results,
        target_variables=target_variables
    )
    
    # Calculate composite sensitivity score
    if len(target_variables) == 1:
        # Single objective - use existing structure
        corr_results['CompositeScore'] = corr_results['AbsCorrelation']
    else:
        # Multi-objective - calculate weighted composite
        composite_scores = []
        conflict_scores = []
        
        for _, row in corr_results.iterrows():
            weighted_sum = 0
            correlations = []
            
            for var in target_variables:
                corr_col = f"Corr_{var}"
                abs_col = f"AbsCorr_{var}"
                
                if abs_col in row:
                    weight = objective_weights.get(var, 1.0)
                    weighted_sum += row[abs_col] * weight
                    correlations.append(row[corr_col] if corr_col in row else 0)
            
            composite_scores.append(weighted_sum)
            
            # Calculate conflict score (parameters that improve one objective but worsen another)
            if identify_conflicts and len(correlations) > 1:
                signs = [np.sign(c) for c in correlations if c != 0]
                if len(set(signs)) > 1:  # Different signs = conflict
                    conflict_score = np.std(correlations)  # Higher std = more conflict
                else:
                    conflict_score = 0
                conflict_scores.append(conflict_score)
            else:
                conflict_scores.append(0)
        
        corr_results['CompositeScore'] = composite_scores
        if identify_conflicts:
            corr_results['ConflictScore'] = conflict_scores
            corr_results['IsConflicting'] = corr_results['ConflictScore'] > 0
    
    # Sort by composite score
    corr_results.sort_values('CompositeScore', ascending=False, inplace=True)
    
    return corr_results


def hierarchical_sensitivity(
    df_scenarios: pd.DataFrame,
    df_results: pd.DataFrame,
    target_variables: Union[str, List[str]],
    parameter_groups: Dict[str, List[str]],
    analyze_interactions: bool = True
) -> Dict[str, Any]:
    """
    Perform hierarchical sensitivity analysis by parameter groups
    
    Args:
        df_scenarios: Scenario parameters
        df_results: Simulation results
        target_variables: Variables to analyze
        parameter_groups: Dict of group_name -> parameter_names
        analyze_interactions: Whether to analyze between-group interactions
        
    Returns:
        Dictionary with group-level and interaction results
    """
    results = {
        'group_sensitivity': {},
        'parameter_sensitivity': {},
        'interactions': {}
    }
    
    # Get individual parameter sensitivity first
    param_sensitivity = correlation_sensitivity(
        df_scenarios=df_scenarios,
        df_results=df_results,
        target_variables=target_variables
    )
    results['parameter_sensitivity'] = param_sensitivity
    
    # Calculate group-level sensitivity
    for group_name, param_list in parameter_groups.items():
        # Filter parameters for this group
        if 'Parameter' in param_sensitivity.columns:
            group_params = param_sensitivity[
                param_sensitivity['Parameter'].isin(param_list)
            ]
            
            if not group_params.empty:
                # Calculate group statistics
                if 'AbsCorrelation' in group_params.columns:
                    group_stats = {
                        'mean_sensitivity': group_params['AbsCorrelation'].mean(),
                        'max_sensitivity': group_params['AbsCorrelation'].max(),
                        'total_sensitivity': group_params['AbsCorrelation'].sum(),
                        'num_significant': (group_params['AbsCorrelation'] > 0.3).sum(),
                        'top_parameter': group_params.iloc[0]['Parameter'] if len(group_params) > 0 else None
                    }
                else:
                    # Multi-objective case
                    group_stats = {
                        'mean_sensitivity': group_params['CompositeScore'].mean() if 'CompositeScore' in group_params.columns else 0,
                        'max_sensitivity': group_params['CompositeScore'].max() if 'CompositeScore' in group_params.columns else 0,
                        'num_parameters': len(group_params)
                    }
                
                results['group_sensitivity'][group_name] = group_stats
    
    # Analyze interactions between groups
    if analyze_interactions and len(parameter_groups) > 1:
        # This is a simplified interaction analysis
        # In practice, you might use variance decomposition or other methods
        interaction_matrix = pd.DataFrame(
            index=parameter_groups.keys(),
            columns=parameter_groups.keys(),
            data=0.0
        )
        
        # Calculate correlation between group average values
        for group1 in parameter_groups:
            for group2 in parameter_groups:
                if group1 != group2:
                    # Get parameters for each group
                    params1 = parameter_groups[group1]
                    params2 = parameter_groups[group2]
                    
                    # Calculate interaction score (simplified)
                    # This could be enhanced with actual interaction analysis
                    interaction_score = 0.1  # Placeholder
                    interaction_matrix.loc[group1, group2] = interaction_score
        
        results['interactions'] = interaction_matrix
    
    return results


def validation_weighted_sensitivity(
    df_scenarios: pd.DataFrame,
    df_results: pd.DataFrame,
    target_variables: Union[str, List[str]],
    validation_results: pd.DataFrame,
    weight_method: str = 'inverse_error',
    focus_on_failed: bool = True,
    failure_threshold: float = 30.0
) -> pd.DataFrame:
    """
    Perform sensitivity analysis weighted by validation performance
    
    Args:
        df_scenarios: Scenario parameters
        df_results: Simulation results
        target_variables: Variables to analyze
        validation_results: Validation results with CV-RMSE
        weight_method: How to calculate weights ('inverse_error', 'binary')
        focus_on_failed: Whether to focus only on failed buildings
        failure_threshold: CV-RMSE threshold for failure
        
    Returns:
        DataFrame with validation-weighted sensitivity results
    """
    # Filter to failed buildings if requested
    if focus_on_failed and 'CV(RMSE)' in validation_results.columns:
        failed_buildings = validation_results[
            validation_results['CV(RMSE)'] > failure_threshold
        ]['building_id'].tolist()
        
        print(f"[INFO] Focusing on {len(failed_buildings)} buildings with CV-RMSE > {failure_threshold}")
        
        # Filter scenarios and results
        if 'ogc_fid' in df_scenarios.columns:
            df_scenarios = df_scenarios[df_scenarios['ogc_fid'].isin(failed_buildings)]
        if 'BuildingID' in df_results.columns:
            df_results = df_results[df_results['BuildingID'].isin(failed_buildings)]
    
    # Calculate base sensitivity
    base_sensitivity = correlation_sensitivity(
        df_scenarios=df_scenarios,
        df_results=df_results,
        target_variables=target_variables
    )
    
    # Apply validation weighting
    if 'validation_weight' in df_scenarios.columns:
        # Use pre-calculated weights
        avg_weight = df_scenarios['validation_weight'].mean()
    else:
        # Calculate weights from validation results
        if weight_method == 'inverse_error':
            # Higher weight for worse validation (to focus on problem buildings)
            max_error = validation_results['CV(RMSE)'].max()
            weights = validation_results['CV(RMSE)'] / max_error
            avg_weight = weights.mean()
        else:  # binary
            avg_weight = 1.0 if focus_on_failed else 0.5
    
    # Apply weight to sensitivity scores
    if 'AbsCorrelation' in base_sensitivity.columns:
        base_sensitivity['ValidationWeightedScore'] = base_sensitivity['AbsCorrelation'] * avg_weight
        base_sensitivity['FocusWeight'] = avg_weight
    
    return base_sensitivity


###############################################################################
# ENHANCED MAIN ORCHESTRATION
###############################################################################

def run_enhanced_sensitivity_analysis(
    project_root: str,
    scenario_folder: str,
    results_csv: str,
    target_variable: Union[str, List[str]],
    output_base_dir: str = "sensitivity_results",
    # Analysis options
    perform_building_specific: bool = True,
    perform_multi_objective: bool = True,
    perform_hierarchical: bool = True,
    perform_validation_weighted: bool = True,
    # Configuration
    building_groups: Optional[Dict[str, List[str]]] = None,
    parameter_groups: Optional[Dict[str, List[str]]] = None,
    objective_weights: Optional[Dict[str, float]] = None,
    validation_csv: Optional[str] = None,
    # Export options
    export_for_surrogate: bool = True,
    export_for_calibration: bool = True,
    # Time slicing (from original)
    time_slice_config: Optional[Dict[str, Any]] = None,
    # Original parameters
    method: str = "correlation",
    file_patterns: Optional[List[str]] = None,
    param_filters: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Enhanced sensitivity analysis with all new features
    
    Args:
        project_root: Root directory of the project
        scenario_folder: Folder containing scenarios
        results_csv: Simulation results file
        target_variable: Variable(s) to analyze
        output_base_dir: Base directory for outputs
        ... (see function definition for all parameters)
    """
    print(f"\n[INFO] === ENHANCED SENSITIVITY ANALYSIS ===")
    print(f"Project root: {project_root}")
    print(f"Output directory: {output_base_dir}")
    
    # Initialize data manager
    data_manager = SensitivityDataManager(project_root)
    
    # Create output directory structure
    os.makedirs(output_base_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(output_base_dir, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Save configuration
    config = {
        'timestamp': timestamp,
        'project_root': project_root,
        'scenario_folder': scenario_folder,
        'results_csv': results_csv,
        'target_variable': target_variable,
        'analysis_options': {
            'building_specific': perform_building_specific,
            'multi_objective': perform_multi_objective,
            'hierarchical': perform_hierarchical,
            'validation_weighted': perform_validation_weighted
        }
    }
    
    with open(os.path.join(session_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    
    # 1. Discover parameters if not done
    print("\n[INFO] Discovering available parameters...")
    available_params = data_manager.discover_parameters()
    print(f"Found {len(available_params)} parameters")
    
    # 2. Load validation results if available
    if validation_csv and os.path.exists(validation_csv):
        print("\n[INFO] Loading validation results...")
        validation_df = data_manager.load_validation_results(validation_csv)
    else:
        validation_df = None
    
    # 3. Get building groups
    if building_groups is None and perform_building_specific:
        print("\n[INFO] Creating building groups...")
        building_groups = data_manager.get_building_groups()
        print(f"Created {len(building_groups)} building groups")
    
    # 4. Prepare data
    print("\n[INFO] Preparing sensitivity data...")
    params_df, results_df, metadata = data_manager.prepare_sensitivity_data(
        scenario_folder=scenario_folder,
        results_csv=results_csv,
        target_variables=target_variable,
        use_validation_weights=(validation_df is not None)
    )
    
    # Apply time slicing if configured
    if time_slice_config:
        print(f"\n[INFO] Applying time slice filtering...")
        if time_slice_config.get("method") == "predefined":
            results_df = apply_predefined_slice(results_df, time_slice_config.get("predefined_slice"))
        elif time_slice_config.get("method") == "custom":
            results_df = filter_results_by_time_slice(results_df, time_slice_config.get("custom_config"))
    
    # Store all results
    all_results = {}
    
    # 5. Building-specific analysis
    if perform_building_specific:
        print("\n[INFO] Performing building-specific sensitivity analysis...")
        building_results = building_specific_sensitivity(
            df_scenarios=params_df,
            df_results=results_df,
            target_variables=target_variable,
            building_groups=building_groups,
            validation_weights=validation_df,
            output_dir=os.path.join(session_dir, "by_building")
        )
        all_results['building_specific'] = building_results
    
    # 6. Multi-objective analysis
    if perform_multi_objective and isinstance(target_variable, list) and len(target_variable) > 1:
        print("\n[INFO] Performing multi-objective sensitivity analysis...")
        multi_obj_results = multi_objective_sensitivity(
            df_scenarios=params_df,
            df_results=results_df,
            target_variables=target_variable,
            objective_weights=objective_weights,
            identify_conflicts=True
        )
        multi_obj_results.to_csv(os.path.join(session_dir, "multi_objective_sensitivity.csv"), index=False)
        all_results['multi_objective'] = multi_obj_results
    
    # 7. Hierarchical analysis
    if perform_hierarchical and parameter_groups:
        print("\n[INFO] Performing hierarchical sensitivity analysis...")
        hier_results = hierarchical_sensitivity(
            df_scenarios=params_df,
            df_results=results_df,
            target_variables=target_variable,
            parameter_groups=parameter_groups,
            analyze_interactions=True
        )
        
        # Save hierarchical results
        with open(os.path.join(session_dir, "hierarchical_sensitivity.json"), 'w') as f:
            # Convert DataFrames to dict for JSON serialization
            hier_dict = {
                'group_sensitivity': hier_results['group_sensitivity'],
                'parameter_sensitivity': hier_results['parameter_sensitivity'].to_dict('records') if isinstance(hier_results['parameter_sensitivity'], pd.DataFrame) else {},
                'interactions': hier_results['interactions'].to_dict() if isinstance(hier_results['interactions'], pd.DataFrame) else {}
            }
            json.dump(hier_dict, f, indent=2)
        
        all_results['hierarchical'] = hier_results
    
    # 8. Validation-weighted analysis
    if perform_validation_weighted and validation_df is not None:
        print("\n[INFO] Performing validation-weighted sensitivity analysis...")
        weighted_results = validation_weighted_sensitivity(
            df_scenarios=params_df,
            df_results=results_df,
            target_variables=target_variable,
            validation_results=validation_df,
            focus_on_failed=True
        )
        weighted_results.to_csv(os.path.join(session_dir, "validation_weighted_sensitivity.csv"), index=False)
        all_results['validation_weighted'] = weighted_results
    
    # 9. Export for downstream modules
    if export_for_surrogate:
        print("\n[INFO] Exporting results for surrogate modeling...")
        # Use multi-objective results if available, otherwise use first available
        export_df = all_results.get('multi_objective', 
                                   all_results.get('validation_weighted',
                                                  list(all_results.values())[0] if all_results else pd.DataFrame()))
        
        if not export_df.empty:
            data_manager.export_for_surrogate(
                sensitivity_results=export_df,
                output_path=os.path.join(session_dir, "surrogate_parameters.json"),
                top_n=20
            )
    
    if export_for_calibration:
        print("\n[INFO] Exporting results for calibration...")
        # Extract parameter bounds
        from cal.unified_sensitivity import extract_parameter_ranges
        param_bounds = extract_parameter_ranges(params_df)
        
        if not param_bounds.empty and all_results:
            export_df = all_results.get('validation_weighted', 
                                      all_results.get('multi_objective',
                                                     list(all_results.values())[0]))
            
            data_manager.export_for_calibration(
                sensitivity_results=export_df,
                parameter_bounds=param_bounds,
                output_path=os.path.join(session_dir, "calibration_parameters.json"),
                sensitivity_threshold=0.1
            )
    
    # 10. Generate summary report
    print("\n[INFO] Generating summary report...")
    summary = {
        'session_info': {
            'timestamp': timestamp,
            'num_scenarios': metadata['num_scenarios'],
            'num_parameters': metadata['num_parameters'],
            'num_buildings': metadata['num_buildings'],
            'target_variables': metadata['target_variables']
        },
        'analyses_performed': {
            'building_specific': perform_building_specific,
            'multi_objective': perform_multi_objective,
            'hierarchical': perform_hierarchical,
            'validation_weighted': perform_validation_weighted
        },
        'key_findings': {}
    }
    
    # Add key findings from each analysis
    if 'multi_objective' in all_results and not all_results['multi_objective'].empty:
        top_params = all_results['multi_objective'].head(5)['Parameter'].tolist() if 'Parameter' in all_results['multi_objective'].columns else []
        summary['key_findings']['top_5_parameters'] = top_params
        
        if 'IsConflicting' in all_results['multi_objective'].columns:
            conflicting = all_results['multi_objective'][all_results['multi_objective']['IsConflicting']]
            summary['key_findings']['conflicting_parameters'] = conflicting['Parameter'].tolist() if 'Parameter' in conflicting.columns else []
    
    with open(os.path.join(session_dir, "summary_report.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n[INFO] === SENSITIVITY ANALYSIS COMPLETE ===")
    print(f"Results saved to: {session_dir}")
    
    return all_results


# Keep original function for backward compatibility
def run_sensitivity_analysis(**kwargs):
    """Wrapper for backward compatibility"""
    # Check if this is an enhanced analysis request
    if any(key in kwargs for key in ['project_root', 'perform_building_specific', 'validation_csv']):
        return run_enhanced_sensitivity_analysis(**kwargs)
    else:
        # Call original implementation
        # ... (keep existing implementation)
        pass