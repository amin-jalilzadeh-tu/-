"""
c_surrogate/ml_pipeline_utils.py

Enhanced utilities for automated machine learning pipeline including:
- Model selection and hyperparameter tuning
- Time aggregation strategies
- Feature engineering
- Model evaluation and selection
- AutoML framework support (AutoGluon, FLAML, H2O, TPOT)
- Integration with new data pipeline

Author: Your Team
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
import logging
from sklearn.model_selection import TimeSeriesSplit, KFold, train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
import json
from datetime import datetime
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Try importing optional ML libraries
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.svm import SVR
    from sklearn.linear_model import ElasticNet, Lasso, Ridge
    SKLEARN_MODELS = True
except ImportError:
    SKLEARN_MODELS = False
    logger.warning("Some sklearn models not available")

try:
    import xgboost as xgb
    HAVE_XGBOOST = True
except ImportError:
    HAVE_XGBOOST = False
    logger.info("XGBoost not available")

try:
    import lightgbm as lgb
    HAVE_LIGHTGBM = True
except ImportError:
    HAVE_LIGHTGBM = False
    logger.info("LightGBM not available")

try:
    import catboost as cb
    HAVE_CATBOOST = True
except ImportError:
    HAVE_CATBOOST = False
    logger.info("CatBoost not available")

# Try importing AutoML frameworks
try:
    from autogluon.tabular import TabularPredictor
    HAVE_AUTOGLUON = True
except ImportError:
    HAVE_AUTOGLUON = False
    logger.info("AutoGluon not available")

try:
    import h2o
    from h2o.automl import H2OAutoML
    HAVE_H2O = True
except ImportError:
    HAVE_H2O = False
    logger.info("H2O AutoML not available")

try:
    from tpot import TPOTRegressor
    HAVE_TPOT = True
except ImportError:
    HAVE_TPOT = False
    logger.info("TPOT not available")

try:
    from flaml import AutoML as FLAMLAutoML
    HAVE_FLAML = True
except ImportError:
    HAVE_FLAML = False
    logger.info("FLAML not available")


class ModelConfig:
    """Configuration for a specific model type"""
    def __init__(self, model_type: str, param_grid: Dict, default_params: Dict):
        self.model_type = model_type
        self.param_grid = param_grid
        self.default_params = default_params


def get_available_models() -> Dict[str, ModelConfig]:
    """Return configurations for all available model types"""
    models = {}
    
    # Random Forest
    models['random_forest'] = ModelConfig(
        'random_forest',
        param_grid={
            'n_estimators': [50, 100, 200, 300],
            'max_depth': [None, 5, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['auto', 'sqrt', 0.5, 0.3]
        },
        default_params={
            'n_estimators': 100,
            'max_depth': None,
            'random_state': 42,
            'n_jobs': -1
        }
    )
    
    # Extra Trees (often performs well for building energy)
    models['extra_trees'] = ModelConfig(
        'extra_trees',
        param_grid={
            'n_estimators': [50, 100, 200, 300],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['auto', 'sqrt', 0.5]
        },
        default_params={
            'n_estimators': 100,
            'max_depth': None,
            'random_state': 42,
            'n_jobs': -1
        }
    )
    
    # Gradient Boosting
    models['gradient_boosting'] = ModelConfig(
        'gradient_boosting',
        param_grid={
            'n_estimators': [50, 100, 200],
            'learning_rate': [0.01, 0.1, 0.3],
            'max_depth': [3, 5, 7, 10],
            'subsample': [0.8, 0.9, 1.0],
            'min_samples_split': [2, 5, 10]
        },
        default_params={
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 3,
            'random_state': 42
        }
    )
    
    # XGBoost
    if HAVE_XGBOOST:
        models['xgboost'] = ModelConfig(
            'xgboost',
            param_grid={
                'n_estimators': [50, 100, 200, 300],
                'learning_rate': [0.01, 0.05, 0.1, 0.3],
                'max_depth': [3, 5, 7, 10],
                'subsample': [0.7, 0.8, 0.9, 1.0],
                'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
                'gamma': [0, 0.1, 0.2]
            },
            default_params={
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 3,
                'random_state': 42,
                'n_jobs': -1,
                'objective': 'reg:squarederror'
            }
        )
    
    # LightGBM
    if HAVE_LIGHTGBM:
        models['lightgbm'] = ModelConfig(
            'lightgbm',
            param_grid={
                'n_estimators': [50, 100, 200, 300],
                'learning_rate': [0.01, 0.05, 0.1, 0.3],
                'num_leaves': [31, 50, 100, 200],
                'feature_fraction': [0.7, 0.8, 0.9, 1.0],
                'bagging_fraction': [0.7, 0.8, 0.9, 1.0],
                'min_data_in_leaf': [10, 20, 30]
            },
            default_params={
                'n_estimators': 100,
                'learning_rate': 0.1,
                'num_leaves': 31,
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1,
                'objective': 'regression'
            }
        )
    
    # CatBoost
    if HAVE_CATBOOST:
        models['catboost'] = ModelConfig(
            'catboost',
            param_grid={
                'iterations': [100, 200, 300],
                'learning_rate': [0.01, 0.05, 0.1],
                'depth': [4, 6, 8, 10],
                'l2_leaf_reg': [1, 3, 5, 7]
            },
            default_params={
                'iterations': 100,
                'learning_rate': 0.1,
                'depth': 6,
                'random_state': 42,
                'verbose': False
            }
        )
    
    # Neural Network
    models['neural_network'] = ModelConfig(
        'neural_network',
        param_grid={
            'hidden_layer_sizes': [(50,), (100,), (50, 50), (100, 50), (100, 100, 50)],
            'learning_rate_init': [0.0001, 0.001, 0.01],
            'alpha': [0.0001, 0.001, 0.01],
            'max_iter': [500, 1000, 2000],
            'activation': ['relu', 'tanh']
        },
        default_params={
            'hidden_layer_sizes': (100, 50),
            'learning_rate_init': 0.001,
            'max_iter': 1000,
            'random_state': 42,
            'early_stopping': True,
            'validation_fraction': 0.1
        }
    )
    
    # Linear Models
    models['elastic_net'] = ModelConfig(
        'elastic_net',
        param_grid={
            'alpha': [0.0001, 0.001, 0.01, 0.1, 1.0],
            'l1_ratio': [0.1, 0.3, 0.5, 0.7, 0.9]
        },
        default_params={
            'alpha': 0.1,
            'l1_ratio': 0.5,
            'random_state': 42,
            'max_iter': 2000
        }
    )
    
    models['lasso'] = ModelConfig(
        'lasso',
        param_grid={
            'alpha': [0.0001, 0.001, 0.01, 0.1, 1.0]
        },
        default_params={
            'alpha': 0.1,
            'random_state': 42,
            'max_iter': 2000
        }
    )
    
    models['ridge'] = ModelConfig(
        'ridge',
        param_grid={
            'alpha': [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0]
        },
        default_params={
            'alpha': 1.0,
            'random_state': 42
        }
    )
    
    return models


def create_model_instance(model_type: str, params: Dict = None):
    """Create a model instance based on type and parameters"""
    if params is None:
        params = {}
    
    if model_type == 'random_forest':
        return RandomForestRegressor(**params)
    elif model_type == 'extra_trees':
        return ExtraTreesRegressor(**params)
    elif model_type == 'gradient_boosting':
        return GradientBoostingRegressor(**params)
    elif model_type == 'xgboost' and HAVE_XGBOOST:
        return xgb.XGBRegressor(**params)
    elif model_type == 'lightgbm' and HAVE_LIGHTGBM:
        return lgb.LGBMRegressor(**params)
    elif model_type == 'catboost' and HAVE_CATBOOST:
        return cb.CatBoostRegressor(**params)
    elif model_type == 'neural_network':
        return MLPRegressor(**params)
    elif model_type == 'elastic_net':
        return ElasticNet(**params)
    elif model_type == 'lasso':
        return Lasso(**params)
    elif model_type == 'ridge':
        return Ridge(**params)
    else:
        raise ValueError(f"Unknown or unavailable model type: {model_type}")


def get_cv_strategy(strategy: str, n_splits: int = 5, **kwargs):
    """Get cross-validation strategy based on configuration"""
    if strategy == 'time_series':
        return TimeSeriesSplit(n_splits=n_splits)
    elif strategy == 'kfold':
        return KFold(n_splits=n_splits, shuffle=True, random_state=kwargs.get('random_state', 42))
    elif strategy == 'stratified_kfold':
        # For regression, we can stratify based on binned target values
        from sklearn.model_selection import StratifiedKFold
        return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=kwargs.get('random_state', 42))
    else:
        raise ValueError(f"Unknown CV strategy: {strategy}")


def get_scaler(scaler_type: str = 'standard', **kwargs):
    """Get scaler based on type"""
    if scaler_type == 'standard':
        return StandardScaler()
    elif scaler_type == 'minmax':
        return MinMaxScaler(feature_range=kwargs.get('feature_range', (0, 1)))
    elif scaler_type == 'robust':
        return RobustScaler(quantile_range=kwargs.get('quantile_range', (25.0, 75.0)))
    else:
        return None


def aggregate_time_series_data(
    df: pd.DataFrame,
    time_aggregation: str = 'mean',
    time_columns: List[str] = None
) -> pd.DataFrame:
    """
    Aggregate time series data based on specified method
    """
    if time_columns is None:
        # Auto-detect time columns
        time_columns = [col for col in df.columns if '/' in str(col) or ':' in str(col)]
    
    if not time_columns:
        return df
    
    # Keep non-time columns
    id_columns = [col for col in df.columns if col not in time_columns]
    
    # Apply aggregation
    aggregations = {}
    
    if time_aggregation == 'mean':
        df_agg = df[time_columns].mean(axis=1)
        aggregations['mean_value'] = df_agg
    elif time_aggregation == 'sum':
        df_agg = df[time_columns].sum(axis=1)
        aggregations['sum_value'] = df_agg
    elif time_aggregation == 'max':
        df_agg = df[time_columns].max(axis=1)
        aggregations['max_value'] = df_agg
    elif time_aggregation == 'min':
        df_agg = df[time_columns].min(axis=1)
        aggregations['min_value'] = df_agg
    elif time_aggregation == 'std':
        df_agg = df[time_columns].std(axis=1)
        aggregations['std_value'] = df_agg
    elif time_aggregation.startswith('percentile_'):
        percentile = float(time_aggregation.split('_')[1])
        df_agg = df[time_columns].quantile(percentile/100, axis=1)
        aggregations[f'p{int(percentile)}_value'] = df_agg
    elif time_aggregation == 'multiple':
        # Calculate multiple aggregations
        aggregations['sum_value'] = df[time_columns].sum(axis=1)
        aggregations['mean_value'] = df[time_columns].mean(axis=1)
        aggregations['max_value'] = df[time_columns].max(axis=1)
        aggregations['min_value'] = df[time_columns].min(axis=1)
        aggregations['std_value'] = df[time_columns].std(axis=1)
        aggregations['p95_value'] = df[time_columns].quantile(0.95, axis=1)
    else:
        raise ValueError(f"Unknown aggregation method: {time_aggregation}")
    
    # Combine with ID columns
    result = df[id_columns].copy()
    for name, values in aggregations.items():
        result[name] = values
    
    return result


def extract_time_features(df: pd.DataFrame, time_columns: List[str]) -> pd.DataFrame:
    """
    Extract time-based features from column names
    """
    features = {}
    
    for i, col in enumerate(time_columns):
        if '/' in col and ':' in col:
            try:
                # Parse E+ format
                parts = col.split()
                if len(parts) >= 2:
                    date_part = parts[0]
                    time_part = parts[1]
                    
                    month, day = date_part.split('/')
                    hour = int(time_part.split(':')[0])
                    
                    # Only store features for first column to avoid duplication
                    if i == 0:
                        features['month'] = int(month)
                        features['day'] = int(day)
                        features['hour'] = hour
                        
                        # Derived features
                        features['is_summer'] = int(month) in [6, 7, 8]
                        features['is_winter'] = int(month) in [12, 1, 2]
                        features['is_peak_hour'] = hour in [14, 15, 16, 17]
                        features['is_night'] = hour < 6 or hour > 20
                        features['is_business_hour'] = 8 <= hour <= 17
                        
                        # Cyclical encoding
                        features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
                        features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
                        features['month_sin'] = np.sin(2 * np.pi * int(month) / 12)
                        features['month_cos'] = np.cos(2 * np.pi * int(month) / 12)
                    
            except Exception as e:
                logger.debug(f"Could not parse time features from {col}: {e}")
    
    return pd.DataFrame([features])


def create_interaction_features(
    df: pd.DataFrame,
    feature_cols: List[str],
    max_interactions: int = 10,
    interaction_type: str = 'multiply'
) -> pd.DataFrame:
    """
    Create interaction features between parameters
    """
    interactions_created = 0
    
    # Sort features by importance if possible (e.g., by variance)
    feature_importance = df[feature_cols].var().sort_values(ascending=False)
    important_features = feature_importance.index.tolist()
    
    # Create pairwise interactions for most important features
    for i, col1 in enumerate(important_features):
        for col2 in important_features[i+1:]:
            if interactions_created >= max_interactions:
                break
            
            if pd.api.types.is_numeric_dtype(df[col1]) and pd.api.types.is_numeric_dtype(df[col2]):
                if interaction_type == 'multiply':
                    # Multiplication interaction
                    df[f'{col1}_X_{col2}'] = df[col1] * df[col2]
                    interactions_created += 1
                
                elif interaction_type == 'divide':
                    # Ratio interaction (avoid division by zero)
                    denominator = df[col2].replace(0, np.nan)
                    if denominator.notna().sum() > len(df) * 0.5:  # At least 50% non-zero
                        df[f'{col1}_div_{col2}'] = df[col1] / denominator
                        interactions_created += 1
                
                elif interaction_type == 'both':
                    # Both multiplication and division
                    df[f'{col1}_X_{col2}'] = df[col1] * df[col2]
                    interactions_created += 1
                    
                    if interactions_created < max_interactions:
                        denominator = df[col2].replace(0, np.nan)
                        if denominator.notna().sum() > len(df) * 0.5:
                            df[f'{col1}_div_{col2}'] = df[col1] / denominator
                            interactions_created += 1
    
    logger.info(f"Created {interactions_created} interaction features")
    return df


def create_polynomial_features(
    df: pd.DataFrame,
    feature_cols: List[str],
    degree: int = 2,
    include_bias: bool = False
) -> pd.DataFrame:
    """
    Create polynomial features
    """
    from sklearn.preprocessing import PolynomialFeatures
    
    poly = PolynomialFeatures(degree=degree, include_bias=include_bias)
    poly_features = poly.fit_transform(df[feature_cols])
    
    # Get feature names
    poly_names = poly.get_feature_names_out(feature_cols)
    
    # Create new DataFrame
    poly_df = pd.DataFrame(poly_features, columns=poly_names, index=df.index)
    
    # Merge with original (excluding original features to avoid duplication)
    new_features = [col for col in poly_names if col not in feature_cols]
    for col in new_features:
        df[col] = poly_df[col]
    
    return df


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    metrics: List[str] = None
) -> Dict[str, float]:
    """
    Evaluate model performance with multiple metrics.
    Fixed to handle DataFrame indexing properly.
    """
    if metrics is None:
        metrics = ['r2', 'rmse', 'mae', 'mape', 'cvrmse', 'nmbe']
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Convert y_test to numpy array immediately to avoid all pandas indexing issues
    if isinstance(y_test, pd.DataFrame):
        y_test_array = y_test.values
    else:
        y_test_array = y_test
    
    # Ensure correct shape
    if len(y_pred.shape) == 1:
        y_pred = y_pred.reshape(-1, 1)
    if len(y_test_array.shape) == 1:
        y_test_array = y_test_array.reshape(-1, 1)
    
    results = {}
    
    # Calculate metrics for each output
    n_outputs = y_pred.shape[1] if len(y_pred.shape) > 1 else 1
    
    for i in range(n_outputs):
        # Extract the i-th output using numpy indexing only
        if n_outputs > 1:
            y_true_i = y_test_array[:, i]
            y_pred_i = y_pred[:, i]
        else:
            y_true_i = y_test_array.flatten()
            y_pred_i = y_pred.flatten()
        
        prefix = f'output_{i}_' if n_outputs > 1 else ''
        
        if 'r2' in metrics:
            results[f'{prefix}r2'] = r2_score(y_true_i, y_pred_i)
        
        if 'rmse' in metrics:
            results[f'{prefix}rmse'] = np.sqrt(mean_squared_error(y_true_i, y_pred_i))
        
        if 'mae' in metrics:
            results[f'{prefix}mae'] = mean_absolute_error(y_true_i, y_pred_i)
        
        if 'mape' in metrics:
            # Mean Absolute Percentage Error
            mask = y_true_i != 0
            if np.any(mask):
                mape = np.mean(np.abs((y_true_i[mask] - y_pred_i[mask]) / y_true_i[mask])) * 100
                results[f'{prefix}mape'] = mape
        
        if 'cvrmse' in metrics:
            # Coefficient of Variation of RMSE
            mean_val = np.mean(y_true_i)
            if mean_val != 0:
                cvrmse = (np.sqrt(mean_squared_error(y_true_i, y_pred_i)) / abs(mean_val)) * 100
                results[f'{prefix}cvrmse'] = cvrmse
        
        if 'nmbe' in metrics:
            # Normalized Mean Bias Error
            mean_val = np.mean(y_true_i)
            if mean_val != 0:
                nmbe = (np.sum(y_pred_i - y_true_i) / (len(y_true_i) * abs(mean_val))) * 100
                results[f'{prefix}nmbe'] = nmbe
    
    # Add overall metrics for multi-output
    if n_outputs > 1:
        r2_values = [v for k, v in results.items() if k.endswith('r2')]
        rmse_values = [v for k, v in results.items() if k.endswith('rmse')]
        mae_values = [v for k, v in results.items() if k.endswith('mae')]
        
        if r2_values:
            results['overall_r2'] = np.mean(r2_values)
        if rmse_values:
            results['overall_rmse'] = np.mean(rmse_values)
        if mae_values:
            results['overall_mae'] = np.mean(mae_values)
    
    return results


def select_features_from_sensitivity(
    feature_cols: List[str],
    sensitivity_results: pd.DataFrame,
    top_n: int = None,
    threshold: float = None,
    method: str = 'correlation'
) -> List[str]:
    """
    Select features based on sensitivity analysis results
    """
    if sensitivity_results is None or sensitivity_results.empty:
        return feature_cols
    
    # Determine which column to use for ranking
    rank_col = None
    
    if method == 'correlation':
        if 'sensitivity_score' in sensitivity_results.columns:
            rank_col = 'sensitivity_score'
        elif 'AbsCorrelation' in sensitivity_results.columns:
            rank_col = 'AbsCorrelation'
        else:
            # Handle multiple correlation columns
            abs_cols = [col for col in sensitivity_results.columns if col.startswith('AbsCorr_')]
            if abs_cols:
                sensitivity_results['mean_abs_corr'] = sensitivity_results[abs_cols].mean(axis=1)
                rank_col = 'mean_abs_corr'
    elif method == 'elasticity':
        rank_col = 'elasticity' if 'elasticity' in sensitivity_results.columns else None
    elif method == 'morris':
        rank_col = 'mu_star' if 'mu_star' in sensitivity_results.columns else None
    elif method == 'sobol':
        rank_col = 'ST' if 'ST' in sensitivity_results.columns else None
    
    if rank_col is None:
        logger.warning(f"Ranking column not found for method {method}")
        return feature_cols
    
    # Get parameter names
    param_col = None
    for col in ['parameter', 'param', 'Parameter', 'feature']:
        if col in sensitivity_results.columns:
            param_col = col
            break
    
    if param_col is None:
        logger.warning("Parameter column not found in sensitivity results")
        return feature_cols
    
    # Clean absolute values
    sensitivity_results[rank_col] = sensitivity_results[rank_col].abs()
    
    # Sort by importance
    sensitivity_results = sensitivity_results.sort_values(rank_col, ascending=False)
    
    # Filter based on criteria
    if threshold is not None:
        important_params = sensitivity_results[sensitivity_results[rank_col] >= threshold][param_col].tolist()
    elif top_n is not None:
        important_params = sensitivity_results.head(top_n)[param_col].tolist()
    else:
        important_params = sensitivity_results[param_col].tolist()
    
    # Match feature columns with sensitivity parameters
    selected_features = []
    for feat in feature_cols:
        # Check exact match
        if feat in important_params:
            selected_features.append(feat)
        else:
            # Check partial match (for cases where parameter names are simplified)
            for param in important_params:
                if param in feat or feat in param:
                    selected_features.append(feat)
                    break
    
    # Remove duplicates while preserving order
    selected_features = list(dict.fromkeys(selected_features))
    
    logger.info(f"Selected {len(selected_features)} features from {len(feature_cols)} based on sensitivity analysis")
    
    return selected_features


def save_model_metadata(
    model_path: str,
    metadata: Dict[str, Any]
):
    """Save model metadata including performance metrics, features, etc."""
    metadata['timestamp'] = datetime.now().isoformat()
    metadata['model_path'] = model_path
    
    # Extract model type if available
    if 'model_info' in metadata:
        metadata['model_type'] = metadata['model_info'].get('model_type', 'unknown')
    
    metadata_path = model_path.replace('.joblib', '_metadata.json')
    
    # Convert numpy types to native Python types
    def convert_numpy(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(item) for item in obj]
        return obj
    
    metadata = convert_numpy(metadata)
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved model metadata to {metadata_path}")


def load_model_metadata(model_path: str) -> Dict[str, Any]:
    """Load model metadata"""
    metadata_path = model_path.replace('.joblib', '_metadata.json')
    
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"No metadata found for {model_path}")
        return {}


def create_model_card(
    model_path: str,
    model_metadata: Dict[str, Any],
    output_path: Optional[str] = None
) -> str:
    """
    Create a model card documenting the model
    """
    card_content = f"""# Model Card

## Model Details
- **Model Type**: {model_metadata.get('model_type', 'Unknown')}
- **Created**: {model_metadata.get('timestamp', 'Unknown')}
- **Framework**: scikit-learn / {model_metadata.get('framework', 'Unknown')}

## Training Data
- **Number of Samples**: {model_metadata.get('data_info', {}).get('total_samples', 'Unknown')}
- **Number of Features**: {model_metadata.get('features', {}).get('count', 'Unknown')}
- **Target Variables**: {model_metadata.get('targets', {}).get('names', [])}

## Performance Metrics
"""
    
    if 'metrics' in model_metadata:
        for metric, value in model_metadata['metrics'].items():
            if isinstance(value, (int, float)):
                card_content += f"- **{metric}**: {value:.4f}\n"
    
    card_content += f"""
## Features
Top features used:
"""
    
    if 'features' in model_metadata and 'names' in model_metadata['features']:
        for i, feat in enumerate(model_metadata['features']['names'][:20]):
            card_content += f"{i+1}. {feat}\n"
    
    card_content += """
## Usage
```python
import joblib
model_data = joblib.load('""" + model_path + """')
model = model_data['model']
scaler = model_data.get('scaler')
features = model_data['feature_columns']
```

## Limitations
- Model trained on specific building configuration
- Performance may degrade for extrapolation beyond training range
- Temporal patterns based on training period only
"""
    
    if output_path:
        output_file = Path(output_path) / 'MODEL_CARD.md'
        with open(output_file, 'w') as f:
            f.write(card_content)
        logger.info(f"Saved model card to {output_file}")
    
    return card_content


###############################################################################
# AUTOML FRAMEWORKS SUPPORT
###############################################################################

class AutoMLWrapper:
    """Unified interface for different AutoML frameworks"""
    
    def __init__(self, framework: str, **kwargs):
        self.framework = framework
        self.model = None
        self.kwargs = kwargs
        self.is_fitted = False
        self.training_history = {}
        
    def fit(self, X_train, y_train, X_val=None, y_val=None, **fit_kwargs):
        """Fit the AutoML model"""
        start_time = time.perf_counter()
        
        if self.framework == 'autogluon' and HAVE_AUTOGLUON:
            self._fit_autogluon(X_train, y_train, X_val, y_val, **fit_kwargs)
        elif self.framework == 'h2o' and HAVE_H2O:
            self._fit_h2o(X_train, y_train, X_val, y_val, **fit_kwargs)
        elif self.framework == 'tpot' and HAVE_TPOT:
            self._fit_tpot(X_train, y_train, X_val, y_val, **fit_kwargs)
        elif self.framework == 'flaml' and HAVE_FLAML:
            self._fit_flaml(X_train, y_train, X_val, y_val, **fit_kwargs)
        else:
            raise ValueError(f"AutoML framework '{self.framework}' not available or not supported")
        
        self.is_fitted = True
        self.training_history['fit_time'] = time.perf_counter() - start_time
        logger.info(f"[AutoML] {self.framework} training completed in {self.training_history['fit_time']:.2f} seconds")
    
    def predict(self, X):
        """Make predictions"""
        if not self.is_fitted:
            raise ValueError("Model not fitted yet")
            
        if self.framework == 'autogluon':
            return self.model.predict(X)
        elif self.framework == 'h2o':
            h2o_frame = h2o.H2OFrame(X)
            predictions = self.model.predict(h2o_frame)
            return predictions.as_data_frame().values.flatten()
        elif self.framework in ['tpot', 'flaml']:
            return self.model.predict(X)
        else:
            raise ValueError(f"Prediction not implemented for {self.framework}")
    
    def _fit_autogluon(self, X_train, y_train, X_val, y_val, **fit_kwargs):
        """Fit AutoGluon model"""
        # Prepare data
        train_data = pd.concat([X_train, y_train], axis=1)
        label = y_train.columns[0] if hasattr(y_train, 'columns') else 'target'
        
        if label not in train_data.columns:
            train_data[label] = y_train
        
        # Configure AutoGluon
        time_limit = self.kwargs.get('time_limit', 300)
        presets = self.kwargs.get('presets', 'medium_quality')
        
        # Handle multi-output
        if isinstance(y_train, pd.DataFrame) and y_train.shape[1] > 1:
            logger.warning("AutoGluon does not natively support multi-output regression. Training on first target only.")
            label = y_train.columns[0]
        
        # Create predictor
        self.model = TabularPredictor(
            label=label,
            eval_metric=self.kwargs.get('eval_metric', 'rmse'),
            path=self.kwargs.get('save_path', 'AutogluonModels'),
            verbosity=self.kwargs.get('verbosity', 2)
        )
        
        # Prepare validation data if provided
        tuning_data = None
        if X_val is not None and y_val is not None:
            tuning_data = pd.concat([X_val, y_val], axis=1)
            if label not in tuning_data.columns:
                tuning_data[label] = y_val
        
        # Fit
        self.model.fit(
            train_data=train_data,
            tuning_data=tuning_data,
            time_limit=time_limit,
            presets=presets,
            **fit_kwargs
        )
        
        # Store best model info
        self.best_model_name = self.model.get_model_best()
        self.leaderboard = self.model.leaderboard()
        self.training_history['best_model'] = self.best_model_name
        self.training_history['leaderboard'] = self.leaderboard
    
    def _fit_h2o(self, X_train, y_train, X_val, y_val, **fit_kwargs):
        """Fit H2O AutoML"""
        # Initialize H2O
        h2o.init(nthreads=-1, max_mem_size='4G')
        
        # Convert to H2O frames
        train_frame = h2o.H2OFrame(pd.concat([X_train, y_train], axis=1))
        
        # Set target column
        y_col = y_train.columns[0] if hasattr(y_train, 'columns') else 'target'
        x_cols = [col for col in train_frame.columns if col != y_col]
        
        # Handle multi-output
        if isinstance(y_train, pd.DataFrame) and y_train.shape[1] > 1:
            logger.warning("H2O AutoML does not support multi-output regression. Training on first target only.")
            y_col = y_train.columns[0]
        
        # Configure H2O AutoML
        aml = H2OAutoML(
            max_models=self.kwargs.get('max_models', 20),
            max_runtime_secs=self.kwargs.get('time_limit', 300),
            seed=self.kwargs.get('seed', 42),
            nfolds=self.kwargs.get('nfolds', 5),
            **fit_kwargs
        )
        
        # Train
        aml.train(x=x_cols, y=y_col, training_frame=train_frame)
        
        self.model = aml.leader
        self.leaderboard = aml.leaderboard
        self.training_history['leaderboard'] = self.leaderboard.as_data_frame()
    
    def _fit_tpot(self, X_train, y_train, X_val, y_val, **fit_kwargs):
        """Fit TPOT AutoML"""
        # TPOT configuration
        self.model = TPOTRegressor(
            generations=self.kwargs.get('generations', 5),
            population_size=self.kwargs.get('population_size', 20),
            cv=self.kwargs.get('cv', 5),
            random_state=self.kwargs.get('seed', 42),
            verbosity=self.kwargs.get('verbosity', 2),
            n_jobs=self.kwargs.get('n_jobs', -1),
            max_time_mins=self.kwargs.get('time_limit', 300) / 60,
            **fit_kwargs
        )
        
        # Fit
        y_train_1d = y_train.values.ravel() if hasattr(y_train, 'values') else y_train
        self.model.fit(X_train, y_train_1d)
        
        # Export pipeline
        if 'export_pipeline' in self.kwargs:
            self.model.export(self.kwargs['export_pipeline'])
            
        self.training_history['pipeline_score'] = self.model.score(X_train, y_train_1d)
    
    def _fit_flaml(self, X_train, y_train, X_val, y_val, **fit_kwargs):
        """Fit FLAML AutoML"""
        # FLAML configuration
        self.model = FLAMLAutoML()
        
        # Settings
        settings = {
            "time_budget": self.kwargs.get('time_limit', 300),
            "metric": self.kwargs.get('metric', 'rmse'),
            "estimator_list": self.kwargs.get('estimator_list', ['lgbm', 'rf', 'xgboost', 'extra_tree']),
            "task": "regression",
            "seed": self.kwargs.get('seed', 42),
            "n_jobs": self.kwargs.get('n_jobs', -1),
            "eval_method": self.kwargs.get('eval_method', 'auto'),
        }
        
        # Fit
        y_train_1d = y_train.values.ravel() if hasattr(y_train, 'values') else y_train
        
        X_val_used = X_val
        y_val_used = y_val.values.ravel() if y_val is not None and hasattr(y_val, 'values') else y_val
        
        self.model.fit(
            X_train, y_train_1d,
            X_val=X_val_used,
            y_val=y_val_used,
            **settings,
            **fit_kwargs
        )
        
        # Store results
        self.best_model_name = self.model.best_estimator
        self.best_config = self.model.best_config
        self.best_loss = self.model.best_loss
        self.training_history.update({
            'best_model': self.best_model_name,
            'best_config': self.best_config,
            'best_loss': self.best_loss,
            'time_to_best': self.model.time_to_find_best_model
        })
    
    def get_feature_importance(self):
        """Get feature importance if available"""
        if self.framework == 'autogluon':
            return self.model.feature_importance()
        elif self.framework == 'h2o':
            return self.model.varimp(use_pandas=True)
        elif self.framework == 'flaml':
            if hasattr(self.model.model.estimator, 'feature_importances_'):
                return pd.DataFrame({
                    'feature': self.model.feature_names_in_,
                    'importance': self.model.model.estimator.feature_importances_
                })
        elif self.framework == 'tpot':
            # TPOT doesn't directly provide feature importance
            return None
        return None
    
    def save(self, path: str):
        """Save the AutoML model"""
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.framework == 'autogluon':
            # AutoGluon saves to its own directory
            logger.info(f"AutoGluon model saved to {self.model.path}")
            # Save path reference
            with open(save_path, 'w') as f:
                json.dump({'autogluon_path': self.model.path}, f)
        elif self.framework == 'h2o':
            h2o.save_model(model=self.model, path=str(save_path.parent), force=True)
        elif self.framework in ['tpot', 'flaml']:
            joblib.dump(self.model, save_path)
            
        # Save training history
        history_path = str(save_path).replace('.joblib', '_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
    
    def load(self, path: str):
        """Load a saved AutoML model"""
        if self.framework == 'autogluon':
            with open(path, 'r') as f:
                info = json.load(f)
            self.model = TabularPredictor.load(info['autogluon_path'])
        elif self.framework == 'h2o':
            self.model = h2o.load_model(path)
        elif self.framework in ['tpot', 'flaml']:
            self.model = joblib.load(path)
        self.is_fitted = True


def get_available_automl_frameworks() -> List[str]:
    """Return list of available AutoML frameworks"""
    available = []
    if HAVE_AUTOGLUON:
        available.append('autogluon')
    if HAVE_H2O:
        available.append('h2o')
    if HAVE_TPOT:
        available.append('tpot')
    if HAVE_FLAML:
        available.append('flaml')
    return available


def run_automl_comparison(
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    frameworks: List[str] = None,
    time_limit: int = 300,
    **kwargs
) -> Dict[str, Any]:
    """
    Run multiple AutoML frameworks and compare results
    """
    if frameworks is None:
        frameworks = get_available_automl_frameworks()
    
    if not frameworks:
        raise ValueError("No AutoML frameworks available. Please install at least one.")
    
    results = {}
    
    for framework in frameworks:
        logger.info(f"[AutoML] Testing {framework}...")
        
        try:
            # Create AutoML instance
            automl = AutoMLWrapper(
                framework=framework,
                time_limit=time_limit,
                **kwargs
            )
            
            # Fit
            start_time = time.perf_counter()
            automl.fit(X_train, y_train)
            fit_time = time.perf_counter() - start_time
            
            # Predict
            y_pred = automl.predict(X_test)
            
            # Evaluate
            metrics = evaluate_model_simple(y_test, y_pred)
            
            # Store results
            results[framework] = {
                'model': automl,
                'metrics': metrics,
                'fit_time': fit_time,
                'feature_importance': automl.get_feature_importance(),
                'training_history': automl.training_history
            }
            
            logger.info(f"[AutoML] {framework} completed - RMSE: {metrics['rmse']:.4f}, R2: {metrics['r2']:.4f}")
            
        except Exception as e:
            logger.error(f"[AutoML] {framework} failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results[framework] = {'error': str(e)}
    
    # Find best framework
    best_framework = None
    best_r2 = -np.inf
    
    for framework, result in results.items():
        if 'error' not in result and result['metrics']['r2'] > best_r2:
            best_r2 = result['metrics']['r2']
            best_framework = framework
    
    if best_framework:
        results['best_framework'] = best_framework
        results['best_metrics'] = results[best_framework]['metrics']
        logger.info(f"[AutoML] Best framework: {best_framework} (R2: {best_r2:.4f})")
    
    return results


def evaluate_model_simple(y_true, y_pred) -> Dict[str, float]:
    """Simple evaluation metrics for AutoML comparison"""
    # Handle multi-dimensional arrays
    if hasattr(y_true, 'values'):
        y_true = y_true.values
    if len(y_true.shape) > 1 and y_true.shape[1] == 1:
        y_true = y_true.ravel()
    if len(y_pred.shape) > 1 and y_pred.shape[1] == 1:
        y_pred = y_pred.ravel()
        
    return {
        'r2': r2_score(y_true, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
        'mae': mean_absolute_error(y_true, y_pred)
    }