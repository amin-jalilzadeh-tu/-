"""
unified_surrogate.py - ENHANCED VERSION

Enhanced features:
- Automated model selection from multiple ML algorithms
- Time series aggregation options
- Integration with sensitivity analysis results
- Feature engineering and selection
- Cross-validation strategies
- Model versioning and metadata
- AutoML framework support (AutoGluon, FLAML, H2O, TPOT)

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
from cal.ml_pipeline_utils import (
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
    run_automl_comparison
)

logger = logging.getLogger(__name__)


###############################################################################
# 1) HELPER: Encode known text -> numeric (unchanged)
###############################################################################

def encode_categorical_if_known(param_name: str, param_value) -> Optional[float]:
    """
    1) Attempt float conversion
    2) If fails, check known label encodings
    3) If still unknown => return None => skip row

    Modify or expand to handle your typical discrete strings.
    """
    if param_value is None or pd.isna(param_value):
        return None

    # (A) Direct float conversion
    try:
        return float(param_value)
    except (ValueError, TypeError):
        pass

    # (B) Known label encodings

    # Example: "Electricity" => 0.0, "Gas" => 1.0
    if param_value == "Electricity":
        return 0.0
    elif param_value == "Gas":
        return 1.0

    # Example: Roughness
    rough_map = {
        "Smooth": 0.0,
        "MediumSmooth": 1.0,
        "MediumRough": 2.0,
        "Rough": 3.0
    }
    if param_value in rough_map:
        return rough_map[param_value]

    # Example: "Yes"/"No" => 1.0 / 0.0
    if param_value in ["Yes", "No"]:
        return 1.0 if param_value == "Yes" else 0.0
    
    # Design flow methods
    if param_value in ["Flow/Zone", "DesignDay", "DesignDayWithLimit"]:
        flow_map = {"Flow/Zone": 0.0, "DesignDay": 1.0, "DesignDayWithLimit": 2.0}
        return flow_map.get(param_value, None)

    # Not recognized => skip
    return None


###############################################################################
# 2) ENHANCED SCENARIO LOADING WITH FILTERING
###############################################################################

def load_scenario_file(filepath: str, param_filters: Optional[Dict] = None) -> pd.DataFrame:
    """
    Enhanced version with parameter filtering
    """
    df_in = pd.read_csv(filepath)

    # unify to 'assigned_value'
    if "assigned_value" not in df_in.columns and "param_value" in df_in.columns:
        df_in.rename(columns={"param_value": "assigned_value"}, inplace=True)

    # Apply filters if provided
    if param_filters:
        # Include only specific parameters
        if "include_params" in param_filters:
            df_in = df_in[df_in["param_name"].isin(param_filters["include_params"])]
        
        # Exclude specific parameters
        if "exclude_params" in param_filters:
            df_in = df_in[~df_in["param_name"].isin(param_filters["exclude_params"])]
        
        # Filter by parameter name patterns
        if "param_name_contains" in param_filters:
            mask = False
            for pattern in param_filters["param_name_contains"]:
                mask |= df_in["param_name"].str.contains(pattern, case=False, na=False)
            df_in = df_in[mask]

    # We'll keep only rows that produce a numeric assigned_value
    rows_out = []
    for _, row in df_in.iterrows():
        val = row.get("assigned_value", None)
        if val is None or pd.isna(val):
            continue

        # Attempt numeric or known label
        param_name = str(row.get("param_name", ""))
        num_val = encode_categorical_if_known(param_name, val)
        if num_val is None:
            # skip
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
    """
    Enhanced with file selection and parameter filtering
    """
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
        # Use glob patterns to find files
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
            # Optionally add a 'source_file' column
            df_scenario["source_file"] = fname
            all_dfs.append(df_scenario)

    if not all_dfs:
        raise FileNotFoundError(f"[ERROR] No scenario CSV with numeric data found in '{scenario_folder}'.")
    
    merged = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"[INFO] Loaded {len(merged)} parameter rows from {len(all_dfs)} files")
    
    return merged


def pivot_scenario_params(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots so each scenario_index is a row, each param_name is a column
    """
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


###############################################################################
# 3) ENHANCED RESULTS LOADING WITH TIME AGGREGATION
###############################################################################

def load_sim_results(
    results_csv: str,
    target_variables: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Enhanced to filter by target variables early
    """
    df = pd.read_csv(results_csv)
    
    # Filter by target variables if specified
    if target_variables and "VariableName" in df.columns:
        df = df[df["VariableName"].isin(target_variables)]
        logger.info(f"[INFO] Filtered results to {len(df)} rows for {len(target_variables)} variables")
    
    return df


def aggregate_results(
    df_sim: pd.DataFrame,
    time_aggregation: str = "sum",
    time_features: bool = False
) -> pd.DataFrame:
    """
    Enhanced aggregation with multiple methods and time feature extraction
    """
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
            # Merge with original data
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


###############################################################################
# 4) ENHANCED MERGING WITH FEATURE ENGINEERING
###############################################################################

def merge_params_with_results(
    pivot_df: pd.DataFrame,
    df_agg: pd.DataFrame,
    target_var: Union[str, List[str], None] = None,
    create_interactions: bool = False,
    interaction_features: int = 10
) -> pd.DataFrame:
    """
    Enhanced merging with feature engineering options
    """
    merged = pivot_df.copy()
    merged.rename(columns={"scenario_index": "BuildingID"}, inplace=True)

    if target_var is None:
        # Just join, no filtering
        merged_final = pd.merge(merged, df_agg, on="BuildingID", how="inner")
    elif isinstance(target_var, str):
        # single var
        df_sub = df_agg[df_agg["VariableName"] == target_var].copy()
        
        # Use the appropriate value column
        value_cols = [col for col in df_sub.columns if col.endswith('_value') or col == 'TotalEnergy_J']
        if value_cols:
            df_sub.rename(columns={value_cols[0]: target_var}, inplace=True)
        
        df_sub.drop(columns=["VariableName"], inplace=True, errors="ignore")
        merged_final = pd.merge(merged, df_sub, on="BuildingID", how="inner")
    elif isinstance(target_var, list):
        # multi-output
        df_sub = df_agg[df_agg["VariableName"].isin(target_var)]
        
        # Handle different value columns
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
            feature_cols[:10],  # Use top 10 features for interactions
            max_interactions=interaction_features
        )

    return merged_final


###############################################################################
# 5) AUTOMATED ML PIPELINE
###############################################################################

def build_automated_ml_model(
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    model_types: List[str] = None,
    search_type: str = "random",
    cv_strategy: str = "kfold",
    n_iter: int = 20,
    scoring: str = "neg_mean_squared_error",
    n_jobs: int = -1,
    random_state: int = 42
) -> Tuple[Any, Dict[str, Any], Dict[str, float]]:
    """
    Automated model selection and hyperparameter tuning
    
    Returns:
        - Best model
        - Best parameters
        - Performance metrics
    """
    if model_types is None:
        model_types = ["random_forest", "xgboost", "gradient_boosting"]
    
    available_models = get_available_models()
    
    best_score = -np.inf
    best_model = None
    best_params = None
    best_model_type = None
    all_results = {}
    
    for model_type in model_types:
        if model_type not in available_models:
            logger.warning(f"Model type {model_type} not available, skipping")
            continue
        
        logger.info(f"[ML Pipeline] Testing {model_type}...")
        
        config = available_models[model_type]
        base_model = create_model_instance(model_type, config.default_params)
        
        # Handle multi-output
        if len(y_train.shape) > 1 and y_train.shape[1] > 1:
            base_model = MultiOutputRegressor(base_model)
        
        # Get CV strategy
        cv = get_cv_strategy(cv_strategy, n_splits=5, random_state=random_state)
        
        # Hyperparameter search
        if search_type == "random":
            search = RandomizedSearchCV(
                base_model,
                config.param_grid if not isinstance(base_model, MultiOutputRegressor) else {
                    f'estimator__{k}': v for k, v in config.param_grid.items()
                },
                n_iter=n_iter,
                cv=cv,
                scoring=scoring,
                n_jobs=n_jobs,
                random_state=random_state,
                verbose=1
            )
        else:  # grid search
            search = GridSearchCV(
                base_model,
                config.param_grid if not isinstance(base_model, MultiOutputRegressor) else {
                    f'estimator__{k}': v for k, v in config.param_grid.items()
                },
                cv=cv,
                scoring=scoring,
                n_jobs=n_jobs,
                verbose=1
            )
        
        # Fit
        search.fit(X_train, y_train)
        
        # Evaluate on test set
        test_score = search.score(X_test, y_test)
        
        logger.info(f"[ML Pipeline] {model_type} best CV score: {search.best_score_:.4f}, test score: {test_score:.4f}")
        
        all_results[model_type] = {
            'cv_score': search.best_score_,
            'test_score': test_score,
            'best_params': search.best_params_
        }
        
        if test_score > best_score:
            best_score = test_score
            best_model = search.best_estimator_
            best_params = search.best_params_
            best_model_type = model_type
    
    # Get detailed metrics for best model
    metrics = evaluate_model(best_model, X_test, y_test)
    
    logger.info(f"[ML Pipeline] Best model: {best_model_type} with test score: {best_score:.4f}")
    
    return best_model, {
        'model_type': best_model_type,
        'params': best_params,
        'all_results': all_results
    }, metrics


def build_and_save_surrogate(
    df_data: pd.DataFrame,
    target_col: Union[str, List[str]] = "TotalEnergy_J",
    model_out_path: str = "surrogate_model.joblib",
    columns_out_path: str = "surrogate_columns.joblib",
    test_size: float = 0.3,
    random_state: int = 42,
    # New parameters for enhanced functionality
    model_types: List[str] = None,
    automated_ml: bool = True,
    scale_features: bool = True,
    scaler_type: str = "standard",
    cv_strategy: str = "kfold",
    sensitivity_results_path: Optional[str] = None,
    feature_selection: Optional[Dict] = None,
    save_metadata: bool = True,
    # AutoML parameters
    use_automl: bool = False,
    automl_framework: str = None,
    automl_time_limit: int = 300,
    automl_config: Dict = None
):
    """
    Enhanced surrogate building with automated ML pipeline and AutoML support
    
    New parameters:
        model_types: List of model types to try
        automated_ml: Use automated model selection
        scale_features: Whether to scale features
        scaler_type: 'standard' or 'minmax'
        cv_strategy: Cross-validation strategy
        sensitivity_results_path: Path to sensitivity analysis results
        feature_selection: Feature selection configuration
        save_metadata: Save model metadata
        use_automl: Use advanced AutoML frameworks
        automl_framework: Specific AutoML framework to use
        automl_time_limit: Time limit for AutoML
        automl_config: AutoML-specific configuration
    """
    # 1) Determine target columns
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

    # 2) Build features
    exclude_cols = ["BuildingID", "ogc_fid", "VariableName", "source_file"]
    if multi_output:
        exclude_cols.extend(target_col)
    else:
        exclude_cols.append(target_col)

    candidate_cols = [c for c in df_data.columns if c not in exclude_cols]
    # Keep only numeric columns
    numeric_cols = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df_data[c])]

    # 3) Apply feature selection based on sensitivity analysis
    if sensitivity_results_path and os.path.exists(sensitivity_results_path):
        logger.info(f"[INFO] Loading sensitivity results from {sensitivity_results_path}")
        sensitivity_df = pd.read_csv(sensitivity_results_path)
        
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

    # Drop rows with any NaN in X or y
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

    # 4) Train/test split
    X_train, X_test, Y_train, Y_test = train_test_split(
        X_data, Y_data, test_size=test_size, random_state=random_state
    )

    # 5) Feature scaling
    scaler = None
    if scale_features:
        if scaler_type == "standard":
            scaler = StandardScaler()
        elif scaler_type == "minmax":
            scaler = MinMaxScaler()
        
        if scaler:
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Convert back to DataFrame to preserve column names
            X_train = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
            X_test = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)

    # 6) Model training
    if use_automl:
        # Use advanced AutoML frameworks
        logger.info("[INFO] Using AutoML framework for model training")
        
        if automl_framework:
            # Use specific framework
            frameworks = [automl_framework]
        else:
            # Try all available frameworks
            frameworks = get_available_automl_frameworks()
            if not frameworks:
                logger.warning("[WARN] No AutoML frameworks available, falling back to standard automated ML")
                use_automl = False
            else:
                logger.info(f"[INFO] Available AutoML frameworks: {frameworks}")
        
        if use_automl:
            # Run AutoML
            if automl_config is None:
                automl_config = {}
            
            # For single framework
            if len(frameworks) == 1:
                automl = AutoMLWrapper(
                    framework=frameworks[0],
                    time_limit=automl_time_limit,
                    seed=random_state,
                    **automl_config
                )
                
                logger.info(f"[INFO] Training with {frameworks[0]} AutoML...")
                automl.fit(X_train, Y_train, X_test, Y_test)
                
                # Get predictions for metrics
                Y_pred_test = automl.predict(X_test)
                if len(Y_pred_test.shape) == 1:
                    Y_pred_test = Y_pred_test.reshape(-1, 1)
                
                # Calculate metrics
                metrics = {}
                for i in range(Y_pred_test.shape[1]):
                    y_true = Y_test.iloc[:, i] if Y_test.shape[1] > 1 else Y_test.values.ravel()
                    y_pred = Y_pred_test[:, i] if Y_pred_test.shape[1] > 1 else Y_pred_test.ravel()
                    
                    metrics[f'r2_{i}'] = r2_score(y_true, y_pred)
                    metrics[f'mae_{i}'] = mean_absolute_error(y_true, y_pred)
                    metrics[f'rmse_{i}'] = np.sqrt(np.mean((y_true - y_pred)**2))
                
                model = automl
                model_info = {
                    'model_type': f'automl_{frameworks[0]}',
                    'framework': frameworks[0],
                    'time_limit': automl_time_limit
                }
                
            else:
                # Compare multiple frameworks
                logger.info(f"[INFO] Comparing {len(frameworks)} AutoML frameworks...")
                results = run_automl_comparison(
                    X_train, Y_train, X_test, Y_test,
                    frameworks=frameworks,
                    time_limit=automl_time_limit,
                    **automl_config
                )
                
                # Select best framework based on R2
                best_framework = None
                best_r2 = -np.inf
                
                for framework, result in results.items():
                    if 'error' not in result:
                        r2 = result['metrics']['r2']
                        if r2 > best_r2:
                            best_r2 = r2
                            best_framework = framework
                
                if best_framework:
                    logger.info(f"[INFO] Best AutoML framework: {best_framework} (R2: {best_r2:.4f})")
                    model = results[best_framework]['model']
                    metrics = results[best_framework]['metrics']
                    model_info = {
                        'model_type': f'automl_{best_framework}',
                        'framework': best_framework,
                        'comparison_results': {k: v.get('metrics', {}) for k, v in results.items() if 'error' not in v}
                    }
                else:
                    raise ValueError("All AutoML frameworks failed")
            
            # Set flag for later use
            is_automl = True
        else:
            # Fall through to standard automated ML
            is_automl = False
    else:
        is_automl = False
    
    if not use_automl or not is_automl:
        if automated_ml:
            # Use standard automated ML pipeline
            model, model_info, metrics = build_automated_ml_model(
                X_train, Y_train, X_test, Y_test,
                model_types=model_types,
                cv_strategy=cv_strategy,
                n_jobs=-1,
                random_state=random_state
            )
        else:
            # Use original RandomForest approach
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
            model_info = {
                'model_type': 'random_forest',
                'params': best_params
            }

    # 7) Print summary
    logger.info("\n[Surrogate Training Summary]")
    logger.info(f"Model Type: {model_info['model_type']}")
    logger.info(f"Features: {len(numeric_cols)}")
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Test samples: {len(X_test)}")
    
    for metric, value in metrics.items():
        logger.info(f"{metric}: {value:.4f}")

    # 8) Save model, scaler, and columns
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': numeric_cols,
        'target_columns': list(y_data.columns),
        'model_info': model_info
    }
    
    joblib.dump(model_data, model_out_path)
    joblib.dump(numeric_cols, columns_out_path)  # Keep for backward compatibility
    
    logger.info(f"[INFO] Saved surrogate model => {model_out_path}")
    logger.info(f"[INFO] Saved columns => {columns_out_path}")

    # 9) Save metadata if requested
    if save_metadata:
        metadata = {
            'model_info': model_info,
            'metrics': metrics,
            'features': {
                'count': len(numeric_cols),
                'names': numeric_cols[:20]  # Save first 20 feature names
            },
            'data_info': {
                'total_samples': len(full_df),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            },
            'configuration': {
                'test_size': test_size,
                'scale_features': scale_features,
                'scaler_type': scaler_type if scale_features else None,
                'cv_strategy': cv_strategy,
                'automated_ml': automated_ml
            }
        }
        save_model_metadata(model_out_path, metadata)

    return model, numeric_cols


###############################################################################
# 6) ENHANCED LOADING AND PREDICTION
###############################################################################

def load_surrogate_and_predict(
    model_path: str,
    columns_path: str,
    sample_features: dict,
    return_uncertainty: bool = False
):
    """
    Enhanced prediction with uncertainty estimation
    """
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
            # For RandomForest, we can get predictions from all trees
            if hasattr(model, 'estimators_'):
                predictions = np.array([tree.predict(df_sample) for tree in model.estimators_])
                y_std = np.std(predictions, axis=0)
                return y_pred, y_std
        except:
            logger.warning("Uncertainty estimation not available for this model")
    
    return y_pred


###############################################################################
# 7) LEGACY FUNCTIONS FOR COMPATIBILITY
###############################################################################

def filter_top_parameters(
    df_pivot: pd.DataFrame,
    sensitivity_csv: str,
    top_n: int,
    param_col: str = "param",
    metric_col: str = "mu_star"
) -> pd.DataFrame:
    """
    Reads a Morris sensitivity CSV, picks top_n 'param' by mu_star, 
    filters df_pivot to only those columns plus scenario_index, ogc_fid.
    """
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