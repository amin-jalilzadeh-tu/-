"""
c_surrogate/unified_surrogate.py - ENHANCED VERSION WITH NEW DATA PIPELINE

Enhanced features:
- Integration with new data extraction and preprocessing pipeline
- Direct support for preprocessed data from surrogate_data_preprocessor
- Backward compatibility with original scenario-based approach
- Enhanced AutoML and time slicing support
- Integration with surrogate_output_manager

Author: Your Team
"""

import os
import pandas as pd
import numpy as np
import joblib
from typing import Optional, List, Union, Dict, Any, Tuple
from sklearn.model_selection import train_test_split, RandomizedSearchCV, GridSearchCV
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error
import logging
from datetime import datetime

# Import ML pipeline utilities
from c_surrogate.ml_pipeline_utils import (
    get_available_models,
    create_model_instance,
    get_cv_strategy,
    aggregate_time_series_data,
    extract_time_features,
    create_interaction_features,
    evaluate_model,
    select_features_from_sensitivity,
    save_model_metadata,
    load_model_metadata,
    # AutoML imports
    AutoMLWrapper,
    get_available_automl_frameworks,
    run_automl_comparison,
    HAVE_XGBOOST,
    HAVE_LIGHTGBM
)

# Import new data pipeline components
from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor
from c_surrogate.surrogate_output_manager import SurrogateOutputManager

logger = logging.getLogger(__name__)


###############################################################################
# NEW INTEGRATED FUNCTIONS
###############################################################################

def build_surrogate_from_job(
    job_output_dir: str,
    sur_cfg: Dict[str, Any],
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Build surrogate model using the new integrated pipeline.
    
    This is the main entry point when using the new data extraction/preprocessing.
    
    Args:
        job_output_dir: Job output directory containing all parquet files
        sur_cfg: Surrogate configuration from main config
        output_dir: Directory to save surrogate outputs
        
    Returns:
        Dictionary containing model, output manager, and results
    """
    logger.info("[Surrogate] Starting integrated surrogate modeling pipeline")
    
    # Step 1: Extract data
    logger.info("[Surrogate] Step 1: Extracting data from job outputs")
    extraction_config = sur_cfg.get('data_extraction', {})
    
    extractor = SurrogateDataExtractor(job_output_dir, extraction_config)
    extracted_data = extractor.extract_all()
    
    # Log extraction summary
    summary = extractor.get_summary_statistics()
    logger.info(f"[Surrogate] Extracted data summary: {summary['data_sources'].keys()}")
    
    # Step 2: Preprocess data
    logger.info("[Surrogate] Step 2: Preprocessing data")
    preprocessing_config = sur_cfg.get('preprocessing', {})
    
    # Override target variables from main config
    if 'target_variable' in sur_cfg:
        target_vars = sur_cfg['target_variable']
        if isinstance(target_vars, str):
            target_vars = [target_vars]
        preprocessing_config['target_variables'] = target_vars
    
    preprocessor = SurrogateDataPreprocessor(extracted_data, preprocessing_config)
    processed_data = preprocessor.preprocess_all()
    
    # Step 3: Build surrogate model
    logger.info("[Surrogate] Step 3: Building surrogate model")
    
    # Get features and targets
    features = processed_data['features']
    targets = processed_data['targets']
    metadata = processed_data['metadata']
    
    # Get feature and target columns
    feature_cols = metadata['feature_columns']
    target_cols = metadata['target_columns']
    
    # Build model using enhanced function
    model_result = build_and_save_surrogate_from_preprocessed(
        features=features,
        targets=targets,
        feature_cols=feature_cols,
        target_cols=target_cols,
        model_out_path=sur_cfg.get('model_out', 'surrogate_model.joblib'),
        columns_out_path=sur_cfg.get('cols_out', 'surrogate_columns.joblib'),
        test_size=sur_cfg.get('test_size', 0.2),
        # Enhanced parameters
        model_types=sur_cfg.get('model_types'),
        automated_ml=sur_cfg.get('automated_ml', True),
        scale_features=sur_cfg.get('scale_features', True),
        cv_strategy=sur_cfg.get('cv_strategy', 'kfold'),
        save_metadata=sur_cfg.get('save_metadata', True),
        # AutoML parameters
        use_automl=sur_cfg.get('use_automl', False),
        automl_framework=sur_cfg.get('automl_framework'),
        automl_time_limit=sur_cfg.get('automl_time_limit', 300),
        automl_config=sur_cfg.get('automl_config', {})
    )
    
    # Step 4: Create output manager
    logger.info("[Surrogate] Step 4: Setting up output management")
    
    output_config = sur_cfg.get('output_management', {})
    model_artifacts = {
        'model': model_result['model'],
        'feature_columns': feature_cols,
        'target_columns': target_cols,
        'metadata': {**metadata, **model_result['metadata']},
        'scaler': model_result.get('scaler'),
        'model_path': sur_cfg.get('model_out')
    }
    
    # Create test data for validation if requested
    test_data = None
    if output_config.get('create_validation_reports', True):
        # Generate test scenarios
        scenarios = preprocessor.generate_training_scenarios(split_ratio=0.8)
        test_data = {
            'features': scenarios['test']['features'],
            'targets': scenarios['test']['targets']
        }
    
    # Create output manager
    output_manager = SurrogateOutputManager(model_artifacts, output_config)
    
    # Save artifacts and create reports
    if output_dir:
        output_manager.save_surrogate_artifacts(output_dir)
        
        if test_data:
            validation_results = output_manager.create_validation_reports(test_data, output_dir)
            # Build validation scores string outside the f-string to avoid syntax error
            validation_scores = [f"{k}: {v['r2']:.3f}" for k, v in validation_results['target_metrics'].items()]
            logger.info(f"[Surrogate] Validation R² scores: {validation_scores}")
    
    # Generate prediction interface
    predict_func = output_manager.generate_prediction_interface('function')
    
    return {
        'model': model_result['model'],
        'output_manager': output_manager,
        'predict_function': predict_func,
        'metadata': model_artifacts['metadata'],
        'validation_results': validation_results if test_data else None,
        'extraction_summary': summary,
        'preprocessing_summary': {
            'n_features': len(feature_cols),
            'n_targets': len(target_cols),
            'n_samples': len(features)
        }
    }


def build_and_save_surrogate_from_preprocessed(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    feature_cols: List[str],
    target_cols: List[str],
    model_out_path: str = "surrogate_model.joblib",
    columns_out_path: str = "surrogate_columns.joblib",
    test_size: float = 0.3,
    random_state: int = 42,
    **kwargs
) -> Dict[str, Any]:
    """
    Build surrogate from preprocessed data.
    
    This function replaces the data loading and preparation steps of the original
    build_and_save_surrogate function.
    
    Args:
        features: Preprocessed feature DataFrame
        targets: Preprocessed target DataFrame
        feature_cols: List of feature column names
        target_cols: List of target column names
        Other args same as build_and_save_surrogate
        
    Returns:
        Dictionary with model and metadata
    """
    logger.info("[Surrogate] Building model from preprocessed data")
    
    # Extract ID columns
    id_cols = [col for col in features.columns if col not in feature_cols]
    
    # Get feature and target data
    X_data = features[feature_cols]
    Y_data = targets[target_cols]
    
    # Check for sufficient data
    if len(X_data) < 10:
        logger.error(f"[ERROR] Not enough data => only {len(X_data)} row(s).")
        return None
    
    # Multi-output check
    multi_output = len(target_cols) > 1
    
    # Train/test split
    X_train, X_test, Y_train, Y_test = train_test_split(
        X_data, Y_data, test_size=test_size, random_state=random_state
    )
    
    # Feature scaling
    scaler = None
    scale_features = kwargs.get('scale_features', True)
    
    if scale_features:
        scaler_type = kwargs.get('scaler_type', 'standard')
        if scaler_type == "standard":
            scaler = StandardScaler()
        elif scaler_type == "minmax":
            scaler = MinMaxScaler()
        
        if scaler:
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Convert back to DataFrame
            X_train = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
            X_test = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)
    
    # Model training (same as original)
    use_automl = kwargs.get('use_automl', False)
    
    if use_automl:
        # AutoML path
        logger.info("[Surrogate] Using AutoML framework")
        model, metrics, model_info = _train_with_automl(
            X_train, Y_train, X_test, Y_test, 
            kwargs.get('automl_framework'),
            kwargs.get('automl_time_limit', 300),
            kwargs.get('automl_config', {}),
            random_state
        )
    else:
        # Standard ML path
        if kwargs.get('automated_ml', True):
            model, model_info, metrics = build_automated_ml_model(
                X_train, Y_train, X_test, Y_test,
                model_types=kwargs.get('model_types'),
                cv_strategy=kwargs.get('cv_strategy', 'kfold'),
                n_jobs=-1,
                random_state=random_state
            )
        else:
            # Original RandomForest approach
            model, metrics = _train_random_forest(
                X_train, Y_train, X_test, Y_test,
                multi_output, random_state
            )
            model_info = {'model_type': 'random_forest'}
    
    # Print summary
    logger.info("\n[Surrogate Training Summary]")
    logger.info(f"Model Type: {model_info.get('model_type', 'unknown')}")
    logger.info(f"Features: {len(feature_cols)}")
    logger.info(f"Targets: {len(target_cols)}")
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Test samples: {len(X_test)}")
    
    for metric, value in metrics.items():
        if isinstance(value, (int, float)):
            logger.info(f"{metric}: {value:.4f}")
    
    # Save model and metadata
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_cols,
        'target_columns': target_cols,
        'model_info': model_info
    }

    # Create directories if they don't exist
    import os
    os.makedirs(os.path.dirname(model_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(columns_out_path), exist_ok=True)

    joblib.dump(model_data, model_out_path)
    joblib.dump(feature_cols, columns_out_path)
    
    logger.info(f"[INFO] Saved surrogate model => {model_out_path}")
    logger.info(f"[INFO] Saved columns => {columns_out_path}")
    
    # Save extended metadata if requested
    if kwargs.get('save_metadata', True):
        metadata = {
            'model_info': model_info,
            'metrics': metrics,
            'features': {
                'count': len(feature_cols),
                'names': feature_cols
            },
            'targets': {
                'count': len(target_cols),
                'names': target_cols
            },
            'data_info': {
                'total_samples': len(features),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            },
            'configuration': {
                'test_size': test_size,
                'scale_features': scale_features,
                'scaler_type': kwargs.get('scaler_type') if scale_features else None,
                'cv_strategy': kwargs.get('cv_strategy'),
                'automated_ml': kwargs.get('automated_ml')
            },
            'training_date': datetime.now().isoformat()
        }
        save_model_metadata(model_out_path, metadata)
    
    return {
        'model': model,
        'metadata': metadata if kwargs.get('save_metadata') else model_info,
        'metrics': metrics,
        'scaler': scaler
    }


###############################################################################
# HELPER FUNCTIONS
###############################################################################

def _train_with_automl(X_train, Y_train, X_test, Y_test, 
                      framework, time_limit, config, random_state):
    """Train using AutoML framework."""
    if framework:
        frameworks = [framework]
    else:
        frameworks = get_available_automl_frameworks()
        if not frameworks:
            raise ValueError("No AutoML frameworks available")
    
    if len(frameworks) == 1:
        # Single framework
        automl = AutoMLWrapper(
            framework=frameworks[0],
            time_limit=time_limit,
            seed=random_state,
            **config
        )
        
        automl.fit(X_train, Y_train, X_test, Y_test)
        
        # Get predictions for metrics
        Y_pred_test = automl.predict(X_test)
        if len(Y_pred_test.shape) == 1:
            Y_pred_test = Y_pred_test.reshape(-1, 1)
        
        # Calculate metrics
        metrics = evaluate_model_automl(Y_test, Y_pred_test)
        
        model_info = {
            'model_type': f'automl_{frameworks[0]}',
            'framework': frameworks[0],
            'time_limit': time_limit
        }
        
        return automl, metrics, model_info
    else:
        # Compare multiple frameworks
        results = run_automl_comparison(
            X_train, Y_train, X_test, Y_test,
            frameworks=frameworks,
            time_limit=time_limit,
            **config
        )
        
        # Select best
        best_framework = max(results.items(), 
                           key=lambda x: x[1].get('metrics', {}).get('r2', -np.inf))[0]
        
        model = results[best_framework]['model']
        metrics = results[best_framework]['metrics']
        model_info = {
            'model_type': f'automl_{best_framework}',
            'framework': best_framework,
            'comparison_results': {k: v.get('metrics', {}) for k, v in results.items() if 'error' not in v}
        }
        
        return model, metrics, model_info


def _train_random_forest(X_train, Y_train, X_test, Y_test, multi_output, random_state):
    """Train RandomForest model (original approach)."""
    from sklearn.ensemble import RandomForestRegressor
    
    param_dist = {
        "n_estimators": [50, 100, 200],
        "max_depth": [None, 5, 10, 20],
        "max_features": ["auto", "sqrt", 0.5]
    }
    
    base_rf = RandomForestRegressor(random_state=random_state)
    search = RandomizedSearchCV(
        base_rf,
        param_distributions=param_dist,
        n_iter=10,
        cv=3,
        random_state=random_state,
        n_jobs=-1
    )
    
    if multi_output:
        first_col = Y_train.columns[0]
        search.fit(X_train, Y_train[first_col].values.ravel())
        best_params = search.best_params_
        best_rf = RandomForestRegressor(random_state=random_state, **best_params)
        model = MultiOutputRegressor(best_rf)
        model.fit(X_train, Y_train)
    else:
        search.fit(X_train, Y_train.values.ravel())
        best_params = search.best_params_
        model = RandomForestRegressor(random_state=random_state, **best_params)
        model.fit(X_train, Y_train.values.ravel())
    
    # Evaluate
    metrics = evaluate_model(model, X_test, Y_test)
    
    return model, metrics


def evaluate_model_automl(Y_test, Y_pred):
    """Evaluate AutoML model predictions."""
    metrics = {}
    
    for i in range(Y_pred.shape[1] if len(Y_pred.shape) > 1 else 1):
        y_true = Y_test.iloc[:, i] if Y_test.shape[1] > 1 else Y_test.values.ravel()
        y_pred = Y_pred[:, i] if Y_pred.shape[1] > 1 else Y_pred.ravel()
        
        prefix = f'output_{i}_' if Y_pred.shape[1] > 1 else ''
        
        metrics[f'{prefix}r2'] = r2_score(y_true, y_pred)
        metrics[f'{prefix}mae'] = mean_absolute_error(y_true, y_pred)
        metrics[f'{prefix}rmse'] = np.sqrt(np.mean((y_true - y_pred)**2))
    
    return metrics


###############################################################################
# ORIGINAL FUNCTIONS WITH MINOR UPDATES (Backward Compatibility)
###############################################################################

# Include all the original helper functions
def encode_categorical_if_known(param_name: str, param_value) -> Optional[float]:
    """
    1) Attempt float conversion
    2) If fails, check known label encodings
    3) If still unknown => return None => skip row
    """
    if param_value is None or pd.isna(param_value):
        return None

    # (A) Direct float conversion
    try:
        return float(param_value)
    except (ValueError, TypeError):
        pass

    # (B) Known label encodings
    if param_value == "Electricity":
        return 0.0
    elif param_value == "Gas":
        return 1.0

    # Roughness
    rough_map = {
        "Smooth": 0.0,
        "MediumSmooth": 1.0,
        "MediumRough": 2.0,
        "Rough": 3.0
    }
    if param_value in rough_map:
        return rough_map[param_value]

    # Yes/No
    if param_value in ["Yes", "No"]:
        return 1.0 if param_value == "Yes" else 0.0
    
    # Design flow methods
    if param_value in ["Flow/Zone", "DesignDay", "DesignDayWithLimit"]:
        flow_map = {"Flow/Zone": 0.0, "DesignDay": 1.0, "DesignDayWithLimit": 2.0}
        return flow_map.get(param_value, None)

    # Not recognized => skip
    return None


# Include all original scenario loading functions...
def load_scenario_file(filepath: str, param_filters: Optional[Dict] = None) -> pd.DataFrame:
    """Load scenario file - original function kept for compatibility"""
    df_in = pd.read_csv(filepath)

    # unify to 'assigned_value'
    if "assigned_value" not in df_in.columns and "param_value" in df_in.columns:
        df_in.rename(columns={"param_value": "assigned_value"}, inplace=True)

    # Apply filters if provided
    if param_filters:
        if "include_params" in param_filters:
            df_in = df_in[df_in["param_name"].isin(param_filters["include_params"])]
        
        if "exclude_params" in param_filters:
            df_in = df_in[~df_in["param_name"].isin(param_filters["exclude_params"])]
        
        if "param_name_contains" in param_filters:
            mask = False
            for pattern in param_filters["param_name_contains"]:
                mask |= df_in["param_name"].str.contains(pattern, case=False, na=False)
            df_in = df_in[mask]

    # Keep only numeric rows
    rows_out = []
    for _, row in df_in.iterrows():
        val = row.get("assigned_value", None)
        if val is None or pd.isna(val):
            continue

        param_name = str(row.get("param_name", ""))
        num_val = encode_categorical_if_known(param_name, val)
        if num_val is None:
            continue

        new_row = row.copy()
        new_row["assigned_value"] = num_val
        rows_out.append(new_row)

    if not rows_out:
        return pd.DataFrame()

    return pd.DataFrame(rows_out)


def load_scenario_params(
    scenario_folder: str,
    file_patterns: Optional[List[str]] = None,
    param_filters: Optional[Dict] = None
) -> pd.DataFrame:
    """Load scenario parameters - original function kept for compatibility"""
    # Default files if not specified
    if file_patterns is None:
        scenario_files = [
            "scenario_params_dhw.csv",
            "scenario_params_elec.csv",
            "scenario_params_equipment.csv",
            "scenario_params_fenez.csv",
            "scenario_params_hvac.csv",
            "scenario_params_shading.csv",
            "scenario_params_vent.csv",
            "scenario_params_zone_sizing.csv"
        ]
    else:
        import glob
        scenario_files = []
        for pattern in file_patterns:
            matching = glob.glob(os.path.join(scenario_folder, pattern))
            scenario_files.extend([os.path.basename(f) for f in matching])

    all_dfs = []
    for fname in scenario_files:
        fpath = os.path.join(scenario_folder, fname)
        if not os.path.isfile(fpath):
            logger.info(f"[INFO] Not found => {fpath}")
            continue

        df_scenario = load_scenario_file(fpath, param_filters)
        if df_scenario.empty:
            logger.info(f"[WARN] No numeric row data in => {fpath} (skipped all).")
        else:
            df_scenario["source_file"] = fname
            all_dfs.append(df_scenario)

    if not all_dfs:
        raise FileNotFoundError(f"[ERROR] No scenario CSV with numeric data found in '{scenario_folder}'.")
    
    merged = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"[INFO] Loaded {len(merged)} parameter rows from {len(all_dfs)} files")
    
    return merged


def pivot_scenario_params(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot scenario parameters - original function"""
    if "scenario_index" not in df.columns or "param_name" not in df.columns or "assigned_value" not in df.columns:
        raise ValueError("DataFrame must have columns: scenario_index, param_name, assigned_value")

    if "ogc_fid" not in df.columns:
        df["ogc_fid"] = 0

    pivot_df = df.pivot_table(
        index=["scenario_index", "ogc_fid"],
        columns="param_name",
        values="assigned_value",
        aggfunc="first"
    ).reset_index()

    pivot_df.columns.name = None
    return pivot_df


def load_sim_results(
    results_csv: str,
    target_variables: Optional[List[str]] = None
) -> pd.DataFrame:
    """Load simulation results - original function"""
    df = pd.read_csv(results_csv)
    
    if target_variables and "VariableName" in df.columns:
        df = df[df["VariableName"].isin(target_variables)]
        logger.info(f"[INFO] Filtered results to {len(df)} rows for {len(target_variables)} variables")
    
    return df


def aggregate_results(
    df_sim: pd.DataFrame,
    time_aggregation: str = "sum",
    time_features: bool = False
) -> pd.DataFrame:
    """Aggregate results - original function with enhancements"""
    needed = {"BuildingID", "VariableName"}
    if not needed.issubset(df_sim.columns):
        raise ValueError("df_sim must have columns BuildingID, VariableName plus time columns.")
    
    # Get time columns
    time_columns = [col for col in df_sim.columns if col not in needed]
    
    if time_features:
        # Extract time features before aggregation
        time_feat_dfs = []
        for _, row in df_sim.iterrows():
            feat_df = extract_time_features(row.to_frame().T, time_columns)
            feat_df["BuildingID"] = row["BuildingID"]
            feat_df["VariableName"] = row["VariableName"]
            time_feat_dfs.append(feat_df)
        
        if time_feat_dfs:
            time_features_df = pd.concat(time_feat_dfs, ignore_index=True)
            df_sim = pd.merge(df_sim, time_features_df, on=["BuildingID", "VariableName"], how="left")
    
    # Apply time aggregation
    result_dfs = []
    
    for _, group in df_sim.groupby(["BuildingID", "VariableName"]):
        agg_row = {
            "BuildingID": group.iloc[0]["BuildingID"],
            "VariableName": group.iloc[0]["VariableName"]
        }
        
        # Get time columns for this group
        time_data = group[time_columns]
        
        if time_aggregation == "sum":
            agg_row["TotalEnergy_J"] = time_data.sum(axis=1).iloc[0]
        elif time_aggregation == "mean":
            agg_row["TotalEnergy_J"] = time_data.mean(axis=1).iloc[0]
        elif time_aggregation == "max":
            agg_row["TotalEnergy_J"] = time_data.max(axis=1).iloc[0]
        elif time_aggregation == "min":
            agg_row["TotalEnergy_J"] = time_data.min(axis=1).iloc[0]
        elif time_aggregation == "std":
            agg_row["TotalEnergy_J"] = time_data.std(axis=1).iloc[0]
        elif time_aggregation.startswith("percentile_"):
            pct = float(time_aggregation.split("_")[1])
            agg_row["TotalEnergy_J"] = time_data.quantile(pct/100, axis=1).iloc[0]
        else:
            # Multiple aggregations
            agg_row["sum_value"] = time_data.sum(axis=1).iloc[0]
            agg_row["mean_value"] = time_data.mean(axis=1).iloc[0]
            agg_row["max_value"] = time_data.max(axis=1).iloc[0]
            agg_row["min_value"] = time_data.min(axis=1).iloc[0]
            agg_row["std_value"] = time_data.std(axis=1).iloc[0]
        
        # Add time features if extracted
        if time_features:
            time_feat_cols = [col for col in group.columns if '_hour' in col or '_month' in col or '_is_' in col]
            for col in time_feat_cols:
                agg_row[col] = group[col].iloc[0]
        
        result_dfs.append(agg_row)
    
    return pd.DataFrame(result_dfs)


def merge_params_with_results(
    pivot_df: pd.DataFrame,
    df_agg: pd.DataFrame,
    target_var: Union[str, List[str], None] = None,
    create_interactions: bool = False,
    interaction_features: int = 10
) -> pd.DataFrame:
    """Merge parameters with results - original function"""
    merged = pivot_df.copy()
    merged.rename(columns={"scenario_index": "BuildingID"}, inplace=True)

    if target_var is None:
        merged_final = pd.merge(merged, df_agg, on="BuildingID", how="inner")
    elif isinstance(target_var, str):
        df_sub = df_agg[df_agg["VariableName"] == target_var].copy()
        
        value_cols = [col for col in df_sub.columns if col.endswith('_value') or col == 'TotalEnergy_J']
        if value_cols:
            df_sub.rename(columns={value_cols[0]: target_var}, inplace=True)
        
        df_sub.drop(columns=["VariableName"], inplace=True, errors="ignore")
        merged_final = pd.merge(merged, df_sub, on="BuildingID", how="inner")
    elif isinstance(target_var, list):
        df_sub = df_agg[df_agg["VariableName"].isin(target_var)]
        
        value_cols = [col for col in df_sub.columns if col.endswith('_value') or col == 'TotalEnergy_J']
        if value_cols:
            pivot_vars = df_sub.pivot(
                index="BuildingID",
                columns="VariableName",
                values=value_cols[0]
            ).reset_index()
        else:
            raise ValueError("No value columns found in aggregated results")
        
        merged_final = pd.merge(merged, pivot_vars, on="BuildingID", how="inner")

    # Create interaction features if requested
    if create_interactions:
        feature_cols = [col for col in merged_final.columns 
                       if col not in ["BuildingID", "ogc_fid", "VariableName", "source_file"] 
                       and not col.startswith(tuple(target_var) if isinstance(target_var, list) else [target_var])]
        
        merged_final = create_interaction_features(
            merged_final, 
            feature_cols[:10],
            max_interactions=interaction_features
        )

    return merged_final


# Keep the original build_and_save_surrogate function for backward compatibility
def build_and_save_surrogate(
    df_data: pd.DataFrame,
    target_col: Union[str, List[str]] = "TotalEnergy_J",
    model_out_path: str = "surrogate_model.joblib",
    columns_out_path: str = "surrogate_columns.joblib",
    test_size: float = 0.3,
    random_state: int = 42,
    **kwargs
):
    """
    Original surrogate building function - kept for backward compatibility.
    For new projects, use build_surrogate_from_job() instead.
    """
    # Determine target columns
    if isinstance(target_col, str):
        if target_col not in df_data.columns:
            logger.error(f"[ERROR] target_col '{target_col}' not in df_data.")
            return None, None
        y_data = df_data[[target_col]].copy()
        multi_output = False
    elif isinstance(target_col, list):
        missing = [t for t in target_col if t not in df_data.columns]
        if missing:
            logger.error(f"[ERROR] Some target columns missing: {missing}")
            return None, None
        y_data = df_data[target_col].copy()
        multi_output = (len(target_col) > 1)
    else:
        logger.error("[ERROR] target_col must be str or list[str].")
        return None, None

    # Build features
    exclude_cols = ["BuildingID", "ogc_fid", "VariableName", "source_file"]
    if multi_output:
        exclude_cols.extend(target_col)
    else:
        exclude_cols.append(target_col)

    candidate_cols = [c for c in df_data.columns if c not in exclude_cols]
    numeric_cols = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df_data[c])]

    # Apply feature selection if sensitivity results provided
    sensitivity_results_path = kwargs.get('sensitivity_results_path')
    if sensitivity_results_path and os.path.exists(sensitivity_results_path):
        logger.info(f"[INFO] Loading sensitivity results from {sensitivity_results_path}")
        sensitivity_df = pd.read_csv(sensitivity_results_path)
        
        feature_selection = kwargs.get('feature_selection')
        if feature_selection:
            numeric_cols = select_features_from_sensitivity(
                numeric_cols,
                sensitivity_df,
                top_n=feature_selection.get('top_n'),
                threshold=feature_selection.get('threshold'),
                method=feature_selection.get('method', 'correlation')
            )

    if not numeric_cols:
        logger.error("[ERROR] No numeric feature columns found => can't train surrogate.")
        return None, None

    # Drop rows with any NaN
    full_df = df_data[numeric_cols + list(y_data.columns)].dropna()
    if full_df.empty:
        logger.error("[ERROR] All data is NaN => can't train surrogate.")
        return None, None

    X_data = full_df[numeric_cols]
    Y_data = full_df[y_data.columns]

    # Must have enough rows
    if len(X_data) < 10:
        logger.error(f"[ERROR] Not enough data => only {len(X_data)} row(s).")
        return None, None

    # Create DataFrame format
    features_df = pd.DataFrame(X_data, columns=numeric_cols)
    targets_df = pd.DataFrame(Y_data, columns=y_data.columns)
    
    # Use the new preprocessed function
    result = build_and_save_surrogate_from_preprocessed(
        features=features_df,
        targets=targets_df,
        feature_cols=numeric_cols,
        target_cols=list(y_data.columns),
        model_out_path=model_out_path,
        columns_out_path=columns_out_path,
        test_size=test_size,
        random_state=random_state,
        **kwargs
    )
    
    if result:
        return result['model'], numeric_cols
    else:
        return None, None


# Keep other original helper functions...
def load_surrogate_and_predict(
    model_path: str,
    columns_path: str,
    sample_features: dict,
    return_uncertainty: bool = False
):
    """Load and predict - original function with enhancements"""
    # Load model data
    model_data = joblib.load(model_path)
    
    # Handle both old and new formats
    if isinstance(model_data, dict):
        model = model_data['model']
        scaler = model_data.get('scaler')
        feature_cols = model_data['feature_columns']
    else:
        # Old format - just the model
        model = model_data
        scaler = None
        feature_cols = joblib.load(columns_path)

    # Construct DF
    df_sample = pd.DataFrame([sample_features])
    
    # Insert missing columns
    for col in feature_cols:
        if col not in df_sample.columns:
            df_sample[col] = 0.0

    df_sample = df_sample[feature_cols].fillna(0.0)
    
    # Scale if needed
    if scaler is not None:
        df_sample_scaled = scaler.transform(df_sample)
        df_sample = pd.DataFrame(df_sample_scaled, columns=feature_cols)

    # Predict
    y_pred = model.predict(df_sample)
    
    # Get uncertainty if requested and model supports it
    if return_uncertainty:
        try:
            # For RandomForest, we can get predictions from individual trees
            if hasattr(model, 'estimators_'):
                predictions = np.array([tree.predict(df_sample) for tree in model.estimators_])
                y_std = np.std(predictions, axis=0)
                return y_pred, y_std
        except:
            logger.warning("Uncertainty estimation not available for this model")
    
    return y_pred


def filter_top_parameters(
    df_pivot: pd.DataFrame,
    sensitivity_csv: str,
    top_n: int,
    param_col: str = "param",
    metric_col: str = "mu_star"
) -> pd.DataFrame:
    """Filter by top parameters - original function"""
    if not os.path.isfile(sensitivity_csv):
        print(f"[INFO] Sensitivity file '{sensitivity_csv}' not found => skipping filter.")
        return df_pivot

    sens_df = pd.read_csv(sensitivity_csv)
    if param_col not in sens_df.columns or metric_col not in sens_df.columns:
        print(f"[ERROR] param_col='{param_col}' or metric_col='{metric_col}' not in {sensitivity_csv}.")
        return df_pivot

    top_params = sens_df.sort_values(metric_col, ascending=False)[param_col].head(top_n).tolist()
    keep_cols = ["scenario_index", "ogc_fid"] + [p for p in top_params if p in df_pivot.columns]
    filtered = df_pivot[keep_cols].copy()
    print(f"[INFO] Filtered pivot from {df_pivot.shape} -> {filtered.shape} using top {top_n} params.")
    return filtered


# Add this function to unified_surrogate.py

def build_automated_ml_model(
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    Y_test: pd.DataFrame,
    model_types: List[str] = None,
    cv_strategy: str = 'kfold',
    n_jobs: int = -1,
    random_state: int = 42
) -> Tuple[Any, Dict[str, Any], Dict[str, float]]:
    """
    Build model using automated ML pipeline with multiple model types.
    
    Args:
        X_train, Y_train: Training data
        X_test, Y_test: Test data
        model_types: List of model types to try
        cv_strategy: Cross-validation strategy
        n_jobs: Number of parallel jobs
        random_state: Random seed
        
    Returns:
        (model, model_info, metrics)
    """
    logger.info("[AutoML] Starting automated model selection")
    
    # Default model types if not specified
    if model_types is None:
        model_types = ['random_forest', 'extra_trees', 'gradient_boosting']
        if HAVE_XGBOOST:
            model_types.append('xgboost')
        if HAVE_LIGHTGBM:
            model_types.append('lightgbm')
    
    # Get available models
    available_models = get_available_models()
    
    # Filter to requested and available models
    models_to_test = [m for m in model_types if m in available_models]
    
    if not models_to_test:
        logger.warning("[AutoML] No requested models available, using RandomForest")
        models_to_test = ['random_forest']
    
    logger.info(f"[AutoML] Testing models: {models_to_test}")
    
    # Check if multi-output
    multi_output = Y_train.shape[1] > 1 if len(Y_train.shape) > 1 else False
    
    best_model = None
    best_score = -np.inf
    best_model_type = None
    best_params = {}
    all_results = {}
    
    # Get CV strategy
    cv = get_cv_strategy(cv_strategy, n_splits=3, random_state=random_state)
    
    # Test each model type
    for model_type in models_to_test:
        logger.info(f"[AutoML] Testing {model_type}...")
        
        try:
            model_config = available_models[model_type]
            
            # Create base model with default params
            base_model = create_model_instance(model_type, model_config.default_params)
            
            # Handle multi-output
            if multi_output and model_type in ['svm', 'neural_network']:
                base_model = MultiOutputRegressor(base_model)
            
            # Simplified hyperparameter search for small datasets
            param_grid = model_config.param_grid
            
            # Reduce parameter grid for small datasets
            if len(X_train) < 50:
                # Use smaller parameter grids
                if 'n_estimators' in param_grid:
                    param_grid['n_estimators'] = [50, 100]
                if 'max_depth' in param_grid:
                    param_grid['max_depth'] = [None, 5, 10]
                if 'hidden_layer_sizes' in param_grid:
                    param_grid['hidden_layer_sizes'] = [(50,), (100,)]
            
            # Use RandomizedSearchCV for efficiency
            search = RandomizedSearchCV(
                base_model,
                param_distributions=param_grid,
                n_iter=10,  # Limit iterations for small datasets
                cv=cv,
                scoring='r2',
                n_jobs=n_jobs,
                random_state=random_state,
                verbose=0
            )
            
            # Fit on first target for multi-output
            if multi_output:
                search.fit(X_train, Y_train.iloc[:, 0])
            else:
                search.fit(X_train, Y_train.values.ravel())
            
            # Get best parameters
            best_params_for_model = search.best_params_
            
            # Train final model with best params
            final_params = {**model_config.default_params, **best_params_for_model}
            final_model = create_model_instance(model_type, final_params)
            
            if multi_output and model_type in ['svm', 'neural_network']:
                final_model = MultiOutputRegressor(final_model)
            
            # Fit on all data
            if multi_output:
                final_model.fit(X_train, Y_train)
            else:
                final_model.fit(X_train, Y_train.values.ravel())
            
            # Evaluate
            metrics = evaluate_model(final_model, X_test, Y_test)
            
            # Get primary score
            if 'r2' in metrics:
                score = metrics['r2']
            elif 'overall_r2' in metrics:
                score = metrics['overall_r2']
            else:
                score = -metrics.get('rmse', np.inf)
            
            all_results[model_type] = {
                'model': final_model,
                'params': best_params_for_model,
                'metrics': metrics,
                'score': score
            }
            
            logger.info(f"[AutoML] {model_type} score: {score:.4f}")
            
            if score > best_score:
                best_score = score
                best_model = final_model
                best_model_type = model_type
                best_params = best_params_for_model
                
        except Exception as e:
            logger.warning(f"[AutoML] Failed to train {model_type}: {e}")
            continue
    
    if best_model is None:
        raise ValueError("No models could be trained successfully")
    
    logger.info(f"[AutoML] Best model: {best_model_type} (score: {best_score:.4f})")
    
    # Get final metrics
    final_metrics = all_results[best_model_type]['metrics']
    
    model_info = {
        'model_type': best_model_type,
        'best_params': best_params,
        'all_results': {k: v['metrics'] for k, v in all_results.items()},
        'cv_strategy': cv_strategy,
        'n_models_tested': len(all_results)
    }
    
    return best_model, model_info, final_metrics