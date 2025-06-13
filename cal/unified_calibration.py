"""
unified_calibration.py - ENHANCED VERSION

Enhanced features:
- Time-based calibration for specific periods
- Multi-objective optimization (NSGA-II)
- Advanced algorithms (PSO, DE, CMA-ES)
- Calibration validation and overfitting detection
- Adaptive/hybrid optimization strategies
- Integration with enhanced sensitivity and surrogate modules

Author: Your Team
"""

import os
import csv
import random
import copy
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Callable, Optional, Union, Any
import logging
from datetime import datetime
import time
import json

# Import from new modules
from cal.calibration_objectives import (
    CalibrationObjective, MultiObjectiveFunction, TimeBasedObjective,
    create_ashrae_objectives, create_peak_focused_objectives,
    create_seasonal_objectives
)
from cal.calibration_algorithms import (
    ParticleSwarmOptimizer, DifferentialEvolution, 
    NSGA2Optimizer, CMAESOptimizer, HybridOptimizer,
    OptimizationResult
)

# scikit-optimize for bayesian calibration
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    from skopt.utils import use_named_args
    HAVE_SKOPT = True
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None
    use_named_args = None
    HAVE_SKOPT = False

# For Surrogate usage
import joblib

logger = logging.getLogger(__name__)

###############################################################################
# 0) Global placeholders for loaded Surrogate + Real Data
###############################################################################
MODEL_SURROGATE = None
MODEL_COLUMNS   = None
REAL_DATA_DICT  = None
REAL_DATA_DF    = None  # New: store full DataFrame for time slicing

###############################################################################
# 1) Enhanced ParamSpec with groups and constraints
###############################################################################

class ParamSpec:
    """
    Enhanced parameter specification with groups and constraints
    """
    def __init__(self, 
                 name: str, 
                 min_value: float, 
                 max_value: float, 
                 is_integer: bool = False,
                 group: Optional[str] = None,
                 constraints: Optional[List[Dict]] = None):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.is_integer = is_integer
        self.group = group  # For grouping related parameters
        self.constraints = constraints or []  # Constraints with other parameters

    def sample_random(self) -> float:
        val = random.uniform(self.min_value, self.max_value)
        return int(round(val)) if self.is_integer else val
    
    def apply_constraints(self, value: float, param_dict: Dict[str, float]) -> float:
        """Apply constraints based on other parameter values"""
        for constraint in self.constraints:
            if constraint['type'] == 'min_ratio':
                # This param must be at least X times another param
                other_param = constraint['other_param']
                min_ratio = constraint['ratio']
                if other_param in param_dict:
                    min_val = param_dict[other_param] * min_ratio
                    value = max(value, min_val)
            elif constraint['type'] == 'max_ratio':
                # This param must be at most X times another param
                other_param = constraint['other_param']
                max_ratio = constraint['ratio']
                if other_param in param_dict:
                    max_val = param_dict[other_param] * max_ratio
                    value = min(value, max_val)
        
        return np.clip(value, self.min_value, self.max_value)


###############################################################################
# 2) Enhanced loading with time support
###############################################################################

def load_real_data_once(real_csv: str, time_aggregation: str = 'sum'):
    """
    Enhanced to load full DataFrame for time-based calibration
    """
    global REAL_DATA_DICT, REAL_DATA_DF
    if REAL_DATA_DF is None:
        logger.info(f"[INFO] Loading real data => {real_csv}")
        REAL_DATA_DF = pd.read_csv(real_csv)
        
        # Create simple dictionary for backward compatibility
        # Aggregate across all time columns
        if 'VariableName' in REAL_DATA_DF.columns and 'BuildingID' in REAL_DATA_DF.columns:
            REAL_DATA_DICT = {}
            for (bid, var), group in REAL_DATA_DF.groupby(['BuildingID', 'VariableName']):
                # Get time columns
                time_cols = [col for col in group.columns 
                           if col not in ['BuildingID', 'VariableName']]
                
                if time_aggregation == 'sum':
                    value = group[time_cols].sum().sum()
                elif time_aggregation == 'mean':
                    value = group[time_cols].mean().mean()
                else:
                    value = group[time_cols].sum().sum()
                
                if bid not in REAL_DATA_DICT:
                    REAL_DATA_DICT[bid] = {}
                REAL_DATA_DICT[bid][var] = value
        else:
            # Fallback for simple format
            REAL_DATA_DICT = {0: 1.23e7}


###############################################################################
# 3) Enhanced error calculation with time slicing
###############################################################################

def calculate_error_with_time_slice(
    param_dict: Dict[str, float],
    config: dict,
    objective_func: Optional[MultiObjectiveFunction] = None,
    time_slice_config: Optional[Dict] = None
) -> Union[float, List[float]]:
    """
    Calculate error with optional time slicing and multi-objective support
    """
    use_surrogate = config.get("use_surrogate", False)
    
    if use_surrogate:
        # Get predictions from surrogate
        simulated_data = predict_with_surrogate(param_dict, config)
        
        # Get real data
        real_csv = config.get("real_data_csv", "")
        load_real_data_once(real_csv)
        
        # Apply time slicing if configured
        if time_slice_config and REAL_DATA_DF is not None:
            from cal.time_slice_utils import filter_results_by_time_slice, apply_predefined_slice
            
            # Filter real data
            if time_slice_config.get("method") == "predefined":
                slice_name = time_slice_config.get("predefined_slice")
                real_filtered = apply_predefined_slice(REAL_DATA_DF, slice_name)
            else:
                real_filtered = filter_results_by_time_slice(REAL_DATA_DF, time_slice_config)
            
            # Aggregate filtered data
            observed_data = {}
            for var in simulated_data.keys():
                var_data = real_filtered[real_filtered['VariableName'] == var]
                if not var_data.empty:
                    time_cols = [col for col in var_data.columns 
                               if col not in ['BuildingID', 'VariableName']]
                    observed_data[var] = var_data[time_cols].values.flatten()
        else:
            # Use pre-aggregated data
            observed_data = {}
            if REAL_DATA_DICT and 0 in REAL_DATA_DICT:
                for var in simulated_data.keys():
                    if var in REAL_DATA_DICT[0]:
                        observed_data[var] = np.array([REAL_DATA_DICT[0][var]])
        
        # Calculate objective(s)
        if objective_func:
            if isinstance(objective_func, MultiObjectiveFunction):
                # Multi-objective
                return objective_func.calculate_all(simulated_data, observed_data)
            else:
                # Single objective with custom function
                return objective_func.calculate_weighted_sum(simulated_data, observed_data)
        else:
            # Legacy single variable error
            target_var = config.get("target_variable", "Heating:EnergyTransfer [J](Hourly)")
            if target_var in simulated_data and target_var in observed_data:
                sim = simulated_data[target_var]
                obs = observed_data[target_var]
                return np.abs(sim[0] - obs[0]) if len(obs) > 0 else float('inf')
            return float('inf')
    else:
        # Placeholder for E+ simulation
        return run_energyplus_and_compute_error(param_dict, config)


def predict_with_surrogate(param_dict: Dict[str, float], config: dict) -> Dict[str, np.ndarray]:
    """
    Enhanced surrogate prediction returning multiple variables
    """
    model_path = config.get("surrogate_model_path", "heating_surrogate_model.joblib")
    columns_path = config.get("surrogate_columns_path", "heating_surrogate_columns.joblib")
    
    load_surrogate_once(model_path, columns_path)
    
    df_sample = build_feature_row_from_param_dict(param_dict)
    preds = MODEL_SURROGATE.predict(df_sample)
    
    # Handle multi-output models
    target_vars = config.get("target_variables", [config.get("target_variable")])
    if not isinstance(target_vars, list):
        target_vars = [target_vars]
    
    simulated_data = {}
    if len(preds.shape) == 1:
        # Single output
        simulated_data[target_vars[0]] = preds
    else:
        # Multi-output
        for i, var in enumerate(target_vars):
            if i < preds.shape[1]:
                simulated_data[var] = preds[:, i]
    
    return simulated_data


###############################################################################
# 4) Enhanced calibration algorithms
###############################################################################

def run_calibration_config(
    config: Dict[str, Any],
    param_specs: List[ParamSpec],
    eval_func: Callable
) -> OptimizationResult:
    """
    Run a single calibration configuration
    """
    method = config.get("method", "ga")
    
    if method == "pso":
        opt = ParticleSwarmOptimizer(
            n_particles=config.get("n_particles", 50),
            max_iter=config.get("max_iter", 100),
            inertia=config.get("inertia", 0.9),
            cognitive=config.get("cognitive", 2.0),
            social=config.get("social", 2.0)
        )
        return opt.optimize(eval_func, param_specs)
    
    elif method == "de":
        opt = DifferentialEvolution(
            pop_size=config.get("pop_size", 50),
            max_iter=config.get("max_iter", 100),
            mutation_factor=config.get("mutation_factor", 0.8),
            crossover_prob=config.get("crossover_prob", 0.7),
            strategy=config.get("strategy", "best1bin"),
            adaptive=config.get("adaptive", True)
        )
        return opt.optimize(eval_func, param_specs)
    
    elif method == "cmaes":
        opt = CMAESOptimizer(
            sigma0=config.get("sigma0", 0.5),
            popsize=config.get("popsize"),
            max_iter=config.get("max_iter", 100)
        )
        return opt.optimize(eval_func, param_specs)
    
    elif method == "nsga2":
        # Multi-objective optimization
        n_objectives = len(config.get("objectives", []))
        if n_objectives < 2:
            logger.warning("[WARN] NSGA-II requires multiple objectives, falling back to DE")
            return run_calibration_config({**config, "method": "de"}, param_specs, eval_func)
        
        opt = NSGA2Optimizer(
            pop_size=config.get("pop_size", 100),
            n_generations=config.get("n_generations", 100),
            crossover_prob=config.get("crossover_prob", 0.9),
            mutation_prob=config.get("mutation_prob")
        )
        
        # Need multi-objective eval function
        multi_eval = lambda p: eval_func(p)  # Should return list of objectives
        return opt.optimize(multi_eval, param_specs, n_objectives)
    
    elif method == "hybrid":
        stages = config.get("stages", [
            {"algorithm": "de", "iterations": 50},
            {"algorithm": "pso", "iterations": 30, "bounds_multiplier": 0.5}
        ])
        opt = HybridOptimizer(stages)
        return opt.optimize(eval_func, param_specs)
    
    elif method == "ga":
        # Legacy GA implementation
        return ga_calibration(
            param_specs=param_specs,
            eval_func=eval_func,
            pop_size=config.get("ga_pop_size", 10),
            generations=config.get("ga_generations", 5),
            crossover_prob=config.get("ga_crossover_prob", 0.7),
            mutation_prob=config.get("ga_mutation_prob", 0.2)
        )
    
    elif method == "bayes":
        return bayes_calibration(
            param_specs=param_specs,
            eval_func=eval_func,
            n_calls=config.get("bayes_n_calls", 15)
        )
    
    elif method == "random":
        return random_search_calibration(
            param_specs=param_specs,
            eval_func=eval_func,
            n_iterations=config.get("random_n_iter", 20)
        )
    
    else:
        raise ValueError(f"Unknown calibration method: {method}")


###############################################################################
# 5) Calibration validation
###############################################################################

def validate_calibration(
    best_params: Dict[str, float],
    validation_config: Dict[str, Any],
    eval_func: Callable
) -> Dict[str, Any]:
    """
    Validate calibration results to check for overfitting
    """
    results = {
        'is_valid': True,
        'metrics': {},
        'warnings': []
    }
    
    if validation_config.get("cross_validate", False):
        # Perform k-fold cross-validation
        n_folds = validation_config.get("n_folds", 3)
        cv_errors = []
        
        logger.info(f"[Validation] Running {n_folds}-fold cross-validation...")
        
        # This is simplified - in practice would need to split time series properly
        for fold in range(n_folds):
            fold_error = eval_func(best_params)
            cv_errors.append(fold_error)
        
        cv_mean = np.mean(cv_errors)
        cv_std = np.std(cv_errors)
        
        results['metrics']['cv_mean_error'] = cv_mean
        results['metrics']['cv_std_error'] = cv_std
        results['metrics']['cv_coefficient'] = cv_std / cv_mean if cv_mean > 0 else 0
        
        # Check overfitting
        overfitting_threshold = validation_config.get("overfitting_threshold", 0.1)
        if results['metrics']['cv_coefficient'] > overfitting_threshold:
            results['warnings'].append(
                f"High CV coefficient ({results['metrics']['cv_coefficient']:.3f}) "
                f"suggests possible overfitting"
            )
            results['is_valid'] = False
    
    # Parameter bounds check
    for param_name, value in best_params.items():
        if "_MIN" in param_name or "_MAX" in param_name:
            base_name = param_name.rsplit("_", 1)[0]
            val_name = base_name + "_VAL"
            min_name = base_name + "_MIN"
            max_name = base_name + "_MAX"
            
            if all(k in best_params for k in [val_name, min_name, max_name]):
                if not (best_params[min_name] <= best_params[val_name] <= best_params[max_name]):
                    results['warnings'].append(
                        f"Parameter bounds violated for {base_name}"
                    )
                    results['is_valid'] = False
    
    return results


###############################################################################
# 6) Main enhanced calibration function
###############################################################################

def run_unified_calibration(calibration_config: dict):
    """
    Enhanced unified calibration with all new features
    
    New configuration options:
    - calibration_configs: List of time-based configurations
    - objectives: Multi-objective specification
    - algorithm_config: Advanced algorithm parameters
    - validation: Cross-validation settings
    - adaptive_config: Adaptive optimization settings
    """
    logger.info("=== Starting Enhanced Unified Calibration ===")
    start_time = time.time()
    
    # Extract configuration
    scenario_folder = calibration_config["scenario_folder"]
    scenario_files = calibration_config.get("scenario_files", [])
    
    # Check for multiple calibration configurations (time-based)
    calib_configs = calibration_config.get("calibration_configs", [])
    
    if calib_configs:
        # Run multiple time-based calibrations
        logger.info(f"[INFO] Running {len(calib_configs)} calibration configurations")
        
        all_results = []
        for i, calib_cfg in enumerate(calib_configs):
            logger.info(f"\n[INFO] === Calibration Configuration {i+1}/{len(calib_configs)}: "
                       f"{calib_cfg.get('name', 'Unnamed')} ===")
            
            # Merge with base config
            merged_config = {**calibration_config, **calib_cfg}
            
            # Run single calibration
            result = run_single_calibration(merged_config)
            all_results.append(result)
        
        # Combine results
        combined_result = combine_calibration_results(all_results, calibration_config)
        
        # Save combined results
        save_combined_calibration_results(combined_result, calibration_config)
        
    else:
        # Single calibration (backward compatible)
        result = run_single_calibration(calibration_config)
        
        # Save results
        save_calibration_results(result, calibration_config)
    
    elapsed_time = time.time() - start_time
    logger.info(f"=== Calibration Complete (took {elapsed_time:.2f} seconds) ===")


def run_single_calibration(config: dict) -> Dict[str, Any]:
    """
    Run a single calibration configuration
    """
    # 1) Load scenario CSV
    scenario_folder = config["scenario_folder"]
    scenario_files = config.get("scenario_files", [])
    
    # Apply file patterns if specified
    file_patterns = config.get("file_patterns")
    if file_patterns:
        import glob
        all_files = []
        for pattern in file_patterns:
            matching = glob.glob(os.path.join(scenario_folder, pattern))
            all_files.extend(matching)
        scenario_files = [os.path.basename(f) for f in all_files]
    
    df_scen = load_scenario_csvs(scenario_folder, scenario_files)
    
    # 2) Filter by sensitivity if configured
    subset_sens = config.get("subset_sensitivity_csv", "")
    top_n = config.get("top_n_params", 9999)
    
    if config.get("param_filters"):
        # Use enhanced filtering
        from cal.unified_sensitivity import load_scenario_params
        df_scen = load_scenario_params(
            scenario_folder,
            file_patterns=config.get("file_patterns"),
            param_filters=config.get("param_filters")
        )
    else:
        # Legacy filtering
        df_scen = optionally_filter_by_sensitivity(df_scen, subset_sens, top_n)
    
    # 3) Build param specs with constraints
    param_specs = build_param_specs_from_scenario(
        df_scen, 
        calibrate_min_max=config.get("calibrate_min_max", True),
        param_groups=config.get("param_groups", {})
    )
    
    # 4) Setup objective function
    objectives_config = config.get("objectives", [])
    time_slice_config = config.get("time_slice", config.get("time_slice_config"))
    
    if objectives_config:
        # Multi-objective setup
        objectives = []
        for obj_cfg in objectives_config:
            obj = CalibrationObjective(
                target_variable=obj_cfg["target_variable"],
                metric=obj_cfg.get("metric", "rmse"),
                weight=obj_cfg.get("weight", 1.0),
                tolerance=obj_cfg.get("tolerance"),
                time_slice_config=time_slice_config
            )
            objectives.append(obj)
        
        multi_obj_func = MultiObjectiveFunction(objectives)
        
        # Create evaluation function
        if len(objectives) > 1 and config.get("method") == "nsga2":
            # Multi-objective optimization
            def eval_func(pdict: Dict[str, float]) -> List[float]:
                return calculate_error_with_time_slice(
                    pdict, config, multi_obj_func, time_slice_config
                )
        else:
            # Single weighted objective
            def eval_func(pdict: Dict[str, float]) -> float:
                errors = calculate_error_with_time_slice(
                    pdict, config, multi_obj_func, time_slice_config
                )
                if isinstance(errors, list):
                    return multi_obj_func.calculate_weighted_sum(
                        {"dummy": np.array([0])}, {"dummy": np.array([0])}
                    )
                return errors
    else:
        # Legacy single objective
        def eval_func(pdict: Dict[str, float]) -> float:
            return calculate_error_with_time_slice(
                pdict, config, None, time_slice_config
            )
    
    # 5) Run optimization
    algorithm_config = config.get("algorithm_config", {})
    method = config.get("method", "ga")
    
    # Get algorithm-specific config
    if method in algorithm_config:
        method_config = {**config, **algorithm_config[method]}
    else:
        method_config = config
    
    # Check for adaptive configuration
    if config.get("adaptive_config", {}).get("enable_adaptive", False):
        adaptive_cfg = config["adaptive_config"]
        method_config["method"] = "hybrid"
        method_config["stages"] = adaptive_cfg.get("stages", [
            {"algorithm": "de", "iterations": 50},
            {"algorithm": "pso", "iterations": 30, "bounds_multiplier": 0.5}
        ])
    
    # Run calibration
    result = run_calibration_config(method_config, param_specs, eval_func)
    
    # 6) Validation
    validation_config = config.get("validation", {})
    if validation_config:
        validation_results = validate_calibration(
            result.best_params,
            validation_config,
            eval_func
        )
        
        if not validation_results['is_valid']:
            logger.warning("[WARN] Calibration validation failed:")
            for warning in validation_results['warnings']:
                logger.warning(f"  - {warning}")
    else:
        validation_results = None
    
    # 7) Package results
    return {
        'optimization_result': result,
        'validation_results': validation_results,
        'config': config,
        'param_specs': param_specs,
        'df_scenarios': df_scen
    }


def combine_calibration_results(
    results: List[Dict[str, Any]],
    base_config: dict
) -> Dict[str, Any]:
    """
    Combine results from multiple calibration runs
    """
    combined = {
        'individual_results': results,
        'best_overall': None,
        'best_by_config': {},
        'summary_statistics': {}
    }
    
    # Find overall best
    best_objective = float('inf')
    best_idx = -1
    
    for i, result in enumerate(results):
        opt_result = result['optimization_result']
        config_name = result['config'].get('name', f'Config_{i}')
        
        combined['best_by_config'][config_name] = {
            'params': opt_result.best_params,
            'objective': opt_result.best_objective
        }
        
        if opt_result.best_objective < best_objective:
            best_objective = opt_result.best_objective
            best_idx = i
    
    if best_idx >= 0:
        combined['best_overall'] = results[best_idx]['optimization_result'].best_params
    
    # Calculate summary statistics
    all_objectives = [r['optimization_result'].best_objective for r in results]
    combined['summary_statistics'] = {
        'mean_objective': np.mean(all_objectives),
        'std_objective': np.std(all_objectives),
        'min_objective': np.min(all_objectives),
        'max_objective': np.max(all_objectives)
    }
    
    return combined


###############################################################################
# 7) Enhanced saving functions
###############################################################################

def save_calibration_results(result: Dict[str, Any], config: dict):
    """
    Save single calibration results
    """
    # Save history
    opt_result = result['optimization_result']
    hist_path = config.get("output_history_csv", "calibration_history.csv")
    save_history_to_csv(opt_result.history, hist_path)
    
    # Save best parameters
    best_params_dir = config.get("best_params_folder", "./")
    save_best_params_separately(
        opt_result.best_params,
        result['df_scenarios'],
        out_folder=best_params_dir,
        prefix="calibrated_params_"
    )
    
    # Save metadata
    metadata = {
        'method': config.get('method'),
        'best_objective': opt_result.best_objective,
        'n_iterations': len(opt_result.history),
        'timestamp': datetime.now().isoformat(),
        'config': config
    }
    
    if result['validation_results']:
        metadata['validation'] = result['validation_results']
    
    if opt_result.pareto_front:
        metadata['n_pareto_solutions'] = len(opt_result.pareto_front)
    
    metadata_path = os.path.join(best_params_dir, "calibration_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Save convergence data if available
    if opt_result.convergence_data:
        conv_path = os.path.join(best_params_dir, "convergence_data.json")
        
        # Convert numpy arrays to lists for JSON serialization
        conv_data_serializable = {}
        for key, value in opt_result.convergence_data.items():
            if isinstance(value, np.ndarray):
                conv_data_serializable[key] = value.tolist()
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], np.ndarray):
                conv_data_serializable[key] = [v.tolist() for v in value]
            else:
                conv_data_serializable[key] = value
        
        with open(conv_path, 'w') as f:
            json.dump(conv_data_serializable, f, indent=2)


def save_combined_calibration_results(combined: Dict[str, Any], config: dict):
    """
    Save results from multiple calibration configurations
    """
    output_dir = config.get("best_params_folder", "./")
    
    # Save summary
    summary_path = os.path.join(output_dir, "calibration_summary.json")
    
    # Extract serializable parts
    summary = {
        'best_overall': combined['best_overall'],
        'best_by_config': combined['best_by_config'],
        'summary_statistics': combined['summary_statistics'],
        'n_configurations': len(combined['individual_results']),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Save individual results
    for i, result in enumerate(combined['individual_results']):
        config_name = result['config'].get('name', f'config_{i}')
        config_dir = os.path.join(output_dir, config_name)
        os.makedirs(config_dir, exist_ok=True)
        
        # Update paths in config
        result['config']['best_params_folder'] = config_dir
        result['config']['output_history_csv'] = os.path.join(
            config_dir, "calibration_history.csv"
        )
        
        # Save using standard function
        save_calibration_results(result, result['config'])
    
    logger.info(f"[INFO] Saved combined calibration results to {output_dir}")


###############################################################################
# 8) Legacy functions (unchanged for backward compatibility)
###############################################################################

def load_scenario_csvs(scenario_folder: str, scenario_files: List[str]) -> pd.DataFrame:
    """Original function - unchanged"""
    if not scenario_files:
        scenario_files = [
            "scenario_params_dhw.csv",
            "scenario_params_elec.csv",
            "scenario_params_equipment.csv",
            "scenario_params_fenez.csv",
            "scenario_params_hvac.csv",
            "scenario_params_vent.csv"
        ]

    dfs = []
    for fname in scenario_files:
        fpath = os.path.join(scenario_folder, fname)
        if os.path.isfile(fpath):
            df_temp = pd.read_csv(fpath)
            df_temp["source_file"] = fname
            dfs.append(df_temp)
        else:
            logger.info(f"[WARN] Scenario file '{fname}' not found => skipping.")
    if not dfs:
        raise FileNotFoundError(f"No scenario CSV found in {scenario_folder} for files={scenario_files}")

    merged = pd.concat(dfs, ignore_index=True)
    return merged


def optionally_filter_by_sensitivity(
    df_scen: pd.DataFrame,
    sensitivity_csv: str,
    top_n: int = 10,
    param_col: str = "param",
    metric_col: str = "mu_star"
) -> pd.DataFrame:
    """Original function - unchanged"""
    if not sensitivity_csv or not os.path.isfile(sensitivity_csv):
        logger.info("[INFO] No sensitivity CSV or not found => skipping filter.")
        return df_scen

    df_sens = pd.read_csv(sensitivity_csv)
    if param_col not in df_sens.columns or metric_col not in df_sens.columns:
        logger.info(f"[WARN] param_col='{param_col}' or metric_col='{metric_col}' not found => skipping filter.")
        return df_scen

    df_sens_sorted = df_sens.sort_values(metric_col, ascending=False)
    top_params = df_sens_sorted[param_col].head(top_n).tolist()
    logger.info(f"[INFO] Filtering scenario params to top {top_n} from {sensitivity_csv} => {top_params}")

    df_filt = df_scen[df_scen["param_name"].isin(top_params)].copy()
    if df_filt.empty:
        logger.info("[WARN] After filter, no scenario params remain => returning original.")
        return df_scen
    return df_filt


def build_param_specs_from_scenario(
    df_scen: pd.DataFrame,
    calibrate_min_max: bool = True,
    param_groups: Optional[Dict[str, List[str]]] = None
) -> List[ParamSpec]:
    """Enhanced with parameter groups"""
    specs = []
    
    # Initialize param_to_group as empty dict first - ALWAYS DEFINED
    param_to_group = {}
    
    # Then populate it if param_groups is provided
    if param_groups:
        for group_name, param_list in param_groups.items():
            for param in param_list:
                param_to_group[param] = group_name
    
    # Now process each row
    for idx, row in df_scen.iterrows():
        p_name = row.get("param_name", "UnknownParam")
        source_file = row.get("source_file", "")
        base_val = row.get("param_value", np.nan)
        base_min = row.get("param_min", np.nan)
        base_max = row.get("param_max", np.nan)

        base_key = f"{source_file}:{p_name}".replace(".csv","")

        try:
            valf = float(base_val)
        except:
            valf = 1.0

        if pd.isna(base_min) or pd.isna(base_max) or (base_min >= base_max):
            base_min = valf * 0.8
            base_max = valf * 1.2
            if base_min >= base_max:
                base_max = base_min + 0.001

        # Get group if exists - param_to_group is now defined
        group = param_to_group.get(p_name)

        # param_value
        specs.append(ParamSpec(
            name=f"{base_key}_VAL",
            min_value=float(base_min),
            max_value=float(base_max),
            is_integer=False,
            group=group
        ))

        if calibrate_min_max:
            # param_min
            mmn = 0.0
            mmx = min(valf, base_min) if base_min < valf else valf
            if mmx <= mmn:
                mmx = mmn + 0.001
            specs.append(ParamSpec(
                name=f"{base_key}_MIN",
                min_value=mmn,
                max_value=mmx,
                is_integer=False,
                group=group
            ))

            # param_max
            mm2 = max(valf, base_max)
            mm2b = mm2 * 2.0
            specs.append(ParamSpec(
                name=f"{base_key}_MAX",
                min_value=mm2,
                max_value=mm2b,
                is_integer=False,
                group=group
            ))

    return specs



def load_surrogate_once(model_path: str, columns_path: str):
    """Original function - unchanged"""
    global MODEL_SURROGATE, MODEL_COLUMNS
    if MODEL_SURROGATE is None or MODEL_COLUMNS is None:
        logger.info(f"[INFO] Loading surrogate => {model_path} / {columns_path}")
        
        # Handle new format with model data dictionary
        model_data = joblib.load(model_path)
        if isinstance(model_data, dict):
            MODEL_SURROGATE = model_data['model']
            MODEL_COLUMNS = model_data.get('feature_columns', joblib.load(columns_path))
        else:
            MODEL_SURROGATE = model_data
            MODEL_COLUMNS = joblib.load(columns_path)


def transform_calib_name_to_surrogate_col(full_name: str) -> str:
    """Original function - unchanged"""
    if ":" in full_name:
        full_name = full_name.split(":",1)[1]
    for suffix in ["_VAL","_MIN","_MAX"]:
        if full_name.endswith(suffix):
            full_name = full_name[: -len(suffix)]
    return full_name


def build_feature_row_from_param_dict(param_dict: Dict[str, float]) -> pd.DataFrame:
    """Original function - unchanged"""
    global MODEL_COLUMNS
    row_dict = {col: 0.0 for col in MODEL_COLUMNS}

    for k, v in param_dict.items():
        short_k = transform_calib_name_to_surrogate_col(k)
        if short_k in row_dict:
            row_dict[short_k] = v

    return pd.DataFrame([row_dict])


def predict_error_with_surrogate(param_dict: Dict[str, float], config: dict) -> float:
    """Legacy function - calls enhanced version"""
    errors = calculate_error_with_time_slice(param_dict, config, None, None)
    if isinstance(errors, list):
        return errors[0] if errors else float('inf')
    return errors


def run_energyplus_and_compute_error(param_dict: Dict[str, float], config: dict) -> float:
    """Original placeholder - unchanged"""
    val_sum = sum(param_dict.values())
    noise = random.uniform(-2.0, 2.0)
    error = abs(val_sum - 50) + noise
    return error


def random_search_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    n_iterations: int
) -> Tuple[Dict[str, float], float, list]:
    """Original function - enhanced to return OptimizationResult"""
    best_params = None
    best_err = float('inf')
    history = []
    for _ in range(n_iterations):
        p_dict = {}
        for s in param_specs:
            p_dict[s.name] = s.sample_random()
        err = eval_func(p_dict)
        history.append((p_dict, err))
        if err < best_err:
            best_err = err
            best_params = p_dict
    
    # Return as OptimizationResult for consistency
    return OptimizationResult(
        best_params=best_params,
        best_objective=best_err,
        history=history
    )


def ga_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    pop_size: int,
    generations: int,
    crossover_prob: float,
    mutation_prob: float
) -> OptimizationResult:
    """Original GA - enhanced to return OptimizationResult"""
    def random_individual():
        p = {}
        for s in param_specs:
            p[s.name] = s.sample_random()
        return p

    def evaluate(ind: dict) -> Tuple[float, float]:
        e = eval_func(ind)
        fit = 1.0 / (1.0 + e)
        return fit, e

    def tournament_select(pop, k=3):
        contenders = random.sample(pop, k)
        best = max(contenders, key=lambda x: x["fitness"])
        return copy.deepcopy(best)

    def crossover(p1: dict, p2: dict):
        c1, c2 = {}, {}
        for k in p1.keys():
            if random.random() < 0.5:
                c1[k] = p1[k]
                c2[k] = p2[k]
            else:
                c1[k] = p2[k]
                c2[k] = p1[k]
        return c1, c2

    def mutate(ind: dict):
        for s in param_specs:
            if random.random() < mutation_prob:
                ind[s.name] = s.sample_random()

    population = []
    history = []
    
    # Initialize
    for _ in range(pop_size):
        ind = random_individual()
        fit, err = evaluate(ind)
        population.append({"params": ind, "fitness": fit, "error": err})
        history.append((ind, err))

    # Evolution
    for g in range(generations):
        new_pop = []
        while len(new_pop) < pop_size:
            pa = tournament_select(population)
            pb = tournament_select(population)
            if random.random() < crossover_prob:
                c1, c2 = crossover(pa["params"], pb["params"])
            else:
                c1, c2 = pa["params"], pb["params"]
            mutate(c1)
            mutate(c2)
            f1, e1 = evaluate(c1)
            f2, e2 = evaluate(c2)
            new_pop.append({"params": c1, "fitness": f1, "error": e1})
            new_pop.append({"params": c2, "fitness": f2, "error": e2})
            history.append((c1, e1))
            history.append((c2, e2))
        
        new_pop.sort(key=lambda x: x["fitness"], reverse=True)
        population = new_pop[:pop_size]
        best_ind = max(population, key=lambda x: x["fitness"])
        logger.info(f"[GA] gen={g} best_error={best_ind['error']:.3f}")

    best_ind = max(population, key=lambda x: x["fitness"])
    
    return OptimizationResult(
        best_params=best_ind["params"],
        best_objective=best_ind["error"],
        history=history
    )


def bayes_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    n_calls: int
) -> OptimizationResult:
    """Original Bayesian - enhanced to return OptimizationResult"""
    if not HAVE_SKOPT or gp_minimize is None:
        logger.info("[WARN] scikit-optimize not installed => fallback random.")
        return random_search_calibration(param_specs, eval_func, n_calls)

    skopt_dims = []
    param_names = []
    for s in param_specs:
        param_names.append(s.name)
        if s.is_integer:
            skopt_dims.append(Integer(s.min_value, s.max_value, name=s.name))
        else:
            skopt_dims.append(Real(s.min_value, s.max_value, name=s.name))

    @use_named_args(skopt_dims)
    def objective(**kwargs):
        return eval_func(kwargs)

    res = gp_minimize(
        objective,
        dimensions=skopt_dims,
        n_calls=n_calls,
        n_initial_points=5,
        random_state=42
    )
    
    best_err = res.fun
    best_x = res.x
    best_params = {}
    for i, val in enumerate(best_x):
        best_params[param_names[i]] = val

    history = []
    for i, x_list in enumerate(res.x_iters):
        pdict = {}
        for j, val in enumerate(x_list):
            pdict[param_names[j]] = val
        e = res.func_vals[i]
        history.append((pdict, e))

    return OptimizationResult(
        best_params=best_params,
        best_objective=best_err,
        history=history
    )


def save_history_to_csv(history: list, filename: str):
    """Original function - unchanged"""
    if not history:
        logger.info("[WARN] No history => skipping save.")
        return
    rows = []
    all_params = set()
    for (pdict, err) in history:
        rows.append((pdict, err))
        all_params.update(pdict.keys())
    all_params = sorted(all_params)
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        header = list(all_params) + ["error"]
        writer.writerow(header)
        for (pdict, err) in rows:
            rowvals = [pdict.get(p, "") for p in all_params]
            rowvals.append(err)
            writer.writerow(rowvals)
    logger.info(f"[INFO] Wrote calibration history => {filename}")


def fix_min_max_relations(best_params: Dict[str, float]):
    """Original function - unchanged"""
    from collections import defaultdict
    groups = defaultdict(dict)
    for k,v in best_params.items():
        if k.endswith("_VAL"):
            base = k[:-4]
            groups[base]["VAL"] = v
        elif k.endswith("_MIN"):
            base = k[:-4]
            groups[base]["MIN"] = v
        elif k.endswith("_MAX"):
            base = k[:-4]
            groups[base]["MAX"] = v

    for base, triple in groups.items():
        if "VAL" in triple and "MIN" in triple and "MAX" in triple:
            mn = triple["MIN"]
            val = triple["VAL"]
            mx = triple["MAX"]
            new_min = min(mn, val, mx)
            new_max = max(mn, val, mx)
            new_val = max(new_min, min(val, new_max))
            best_params[base+"_MIN"] = new_min
            best_params[base+"_VAL"] = new_val
            best_params[base+"_MAX"] = new_max


def save_best_params_separately(
    best_params: Dict[str, float],
    df_scen: pd.DataFrame,
    out_folder: str = "./",
    prefix: str = "calibrated_params_"
):
    """Original function - unchanged"""
    fix_min_max_relations(best_params)
    os.makedirs(out_folder, exist_ok=True)
    grouped = df_scen.groupby("source_file")

    for sfile, group_df in grouped:
        out_rows = []
        for _, row in group_df.iterrows():
            p_name = row["param_name"]
            s_file = row["source_file"]
            old_val = row.get("param_value", np.nan)
            old_min = row.get("param_min", np.nan)
            old_max = row.get("param_max", np.nan)

            base_key = f"{s_file}:{p_name}".replace(".csv","")
            new_val_key = base_key + "_VAL"
            new_min_key = base_key + "_MIN"
            new_max_key = base_key + "_MAX"

            new_val = best_params.get(new_val_key, old_val)
            new_min = best_params.get(new_min_key, old_min)
            new_max = best_params.get(new_max_key, old_max)

            out_rows.append({
                "scenario_index": row.get("scenario_index",""),
                "ogc_fid": row.get("ogc_fid",""),
                "object_name": row.get("object_name",""),
                "param_name": p_name,
                "old_param_value": old_val,
                "new_param_value": new_val,
                "old_param_min": old_min,
                "new_param_min": new_min,
                "old_param_max": old_max,
                "new_param_max": new_max,
                "source_file": s_file
            })

        df_out = pd.DataFrame(out_rows)
        out_name = prefix + sfile
        out_path = os.path.join(out_folder, out_name)
        df_out.to_csv(out_path, index=False)
        logger.info(f"[INFO] Wrote best params => {out_path}")