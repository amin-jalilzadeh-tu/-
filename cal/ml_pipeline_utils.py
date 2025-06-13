"""
ml_pipeline_utils.py

Utilities for automated machine learning pipeline including:
- Model selection and hyperparameter tuning
- Time aggregation strategies
- Feature engineering
- Model evaluation and selection
- AutoML framework support (AutoGluon, FLAML, H2O, TPOT)

Author: Your Team
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from sklearn.model_selection import TimeSeriesSplit, KFold, train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
import json
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Try importing optional ML libraries
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.svm import SVR
    from sklearn.linear_model import ElasticNet
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
            'n_estimators': [50, 100, 200],
            'max_depth': [None, 5, 10, 20],
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
            'max_depth': [3, 5, 7],
            'subsample': [0.8, 1.0]
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
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'max_depth': [3, 5, 7],
                'subsample': [0.8, 1.0],
                'colsample_bytree': [0.8, 1.0]
            },
            default_params={
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 3,
                'random_state': 42,
                'n_jobs': -1
            }
        )
    
    # LightGBM
    if HAVE_LIGHTGBM:
        models['lightgbm'] = ModelConfig(
            'lightgbm',
            param_grid={
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'num_leaves': [31, 50, 100],
                'feature_fraction': [0.8, 1.0],
                'bagging_fraction': [0.8, 1.0]
            },
            default_params={
                'n_estimators': 100,
                'learning_rate': 0.1,
                'num_leaves': 31,
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            }
        )
    
    # Neural Network
    models['neural_network'] = ModelConfig(
        'neural_network',
        param_grid={
            'hidden_layer_sizes': [(50,), (100,), (50, 50), (100, 50)],
            'learning_rate_init': [0.001, 0.01, 0.1],
            'alpha': [0.0001, 0.001, 0.01],
            'max_iter': [200, 500, 1000]
        },
        default_params={
            'hidden_layer_sizes': (100, 50),
            'learning_rate_init': 0.001,
            'max_iter': 500,
            'random_state': 42,
            'early_stopping': True
        }
    )
    
    # Elastic Net (Linear)
    models['elastic_net'] = ModelConfig(
        'elastic_net',
        param_grid={
            'alpha': [0.001, 0.01, 0.1, 1.0],
            'l1_ratio': [0.1, 0.5, 0.7, 0.9]
        },
        default_params={
            'alpha': 0.1,
            'l1_ratio': 0.5,
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
    elif model_type == 'gradient_boosting':
        return GradientBoostingRegressor(**params)
    elif model_type == 'xgboost' and HAVE_XGBOOST:
        return xgb.XGBRegressor(**params)
    elif model_type == 'lightgbm' and HAVE_LIGHTGBM:
        return lgb.LGBMRegressor(**params)
    elif model_type == 'neural_network':
        return MLPRegressor(**params)
    elif model_type == 'elastic_net':
        return ElasticNet(**params)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def get_cv_strategy(strategy: str, n_splits: int = 5, **kwargs):
    """Get cross-validation strategy based on configuration"""
    if strategy == 'time_series':
        return TimeSeriesSplit(n_splits=n_splits)
    elif strategy == 'kfold':
        return KFold(n_splits=n_splits, shuffle=True, random_state=kwargs.get('random_state', 42))
    else:
        raise ValueError(f"Unknown CV strategy: {strategy}")


def aggregate_time_series_data(
    df: pd.DataFrame,
    time_aggregation: str = 'mean',
    time_columns: List[str] = None
) -> pd.DataFrame:
    """
    Aggregate time series data based on specified method
    
    Args:
        df: DataFrame with time columns
        time_aggregation: 'mean', 'sum', 'max', 'min', 'std', 'percentile_X'
        time_columns: List of columns to aggregate (auto-detect if None)
    """
    if time_columns is None:
        # Auto-detect time columns (those with dates/times in header)
        time_columns = [col for col in df.columns if '/' in str(col) or ':' in str(col)]
    
    if not time_columns:
        return df
    
    # Keep non-time columns
    id_columns = [col for col in df.columns if col not in time_columns]
    
    # Apply aggregation
    if time_aggregation == 'mean':
        df_agg = df[time_columns].mean(axis=1)
    elif time_aggregation == 'sum':
        df_agg = df[time_columns].sum(axis=1)
    elif time_aggregation == 'max':
        df_agg = df[time_columns].max(axis=1)
    elif time_aggregation == 'min':
        df_agg = df[time_columns].min(axis=1)
    elif time_aggregation == 'std':
        df_agg = df[time_columns].std(axis=1)
    elif time_aggregation.startswith('percentile_'):
        percentile = float(time_aggregation.split('_')[1])
        df_agg = df[time_columns].quantile(percentile/100, axis=1)
    else:
        raise ValueError(f"Unknown aggregation method: {time_aggregation}")
    
    # Combine with ID columns
    result = df[id_columns].copy()
    result[f'{time_aggregation}_value'] = df_agg
    
    return result


def extract_time_features(df: pd.DataFrame, time_columns: List[str]) -> pd.DataFrame:
    """
    Extract time-based features from column names
    
    Creates features like:
    - Hour of day
    - Day of week
    - Month
    - Is weekend
    """
    features = {}
    
    for col in time_columns:
        if '/' in col and ':' in col:
            try:
                # Parse "MM/DD HH:MM:SS" format
                parts = col.split()
                if len(parts) >= 2:
                    date_part = parts[0]
                    time_part = parts[1]
                    
                    month, day = date_part.split('/')
                    hour = int(time_part.split(':')[0])
                    
                    # Create feature names
                    features[f'{col}_hour'] = hour
                    features[f'{col}_month'] = int(month)
                    features[f'{col}_day'] = int(day)
                    
                    # Derived features
                    features[f'{col}_is_night'] = 1 if hour < 6 or hour > 20 else 0
                    features[f'{col}_is_business_hours'] = 1 if 8 <= hour <= 17 else 0
                    
            except Exception as e:
                logger.debug(f"Could not parse time features from {col}: {e}")
    
    return pd.DataFrame([features])


def create_interaction_features(
    df: pd.DataFrame,
    feature_cols: List[str],
    max_interactions: int = 10
) -> pd.DataFrame:
    """
    Create interaction features between parameters
    
    Args:
        df: Input DataFrame
        feature_cols: Columns to create interactions for
        max_interactions: Maximum number of interactions to create
    """
    interactions = []
    interaction_count = 0
    
    # Create pairwise interactions for most important features
    for i, col1 in enumerate(feature_cols):
        for col2 in feature_cols[i+1:]:
            if interaction_count >= max_interactions:
                break
            
            if pd.api.types.is_numeric_dtype(df[col1]) and pd.api.types.is_numeric_dtype(df[col2]):
                # Multiplication interaction
                df[f'{col1}_X_{col2}'] = df[col1] * df[col2]
                
                # Ratio interaction (avoid division by zero)
                denominator = df[col2].replace(0, np.nan)
                df[f'{col1}_div_{col2}'] = df[col1] / denominator
                
                interaction_count += 2
    
    return df


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    metrics: List[str] = None
) -> Dict[str, float]:
    """
    Evaluate model performance with multiple metrics
    
    Args:
        model: Trained model
        X_test: Test features
        y_test: Test targets
        metrics: List of metrics to calculate
    
    Returns:
        Dictionary of metric values
    """
    if metrics is None:
        metrics = ['r2', 'rmse', 'mae', 'mape', 'cvrmse']
    
    y_pred = model.predict(X_test)
    
    # Ensure correct shape
    if len(y_pred.shape) == 1:
        y_pred = y_pred.reshape(-1, 1)
    if len(y_test.shape) == 1:
        y_test = y_test.values.reshape(-1, 1)
    
    results = {}
    
    # Calculate metrics for each output
    n_outputs = y_pred.shape[1] if len(y_pred.shape) > 1 else 1
    
    for i in range(n_outputs):
        y_true_i = y_test[:, i] if n_outputs > 1 else y_test.flatten()
        y_pred_i = y_pred[:, i] if n_outputs > 1 else y_pred.flatten()
        
        prefix = f'output_{i}_' if n_outputs > 1 else ''
        
        if 'r2' in metrics:
            results[f'{prefix}r2'] = r2_score(y_true_i, y_pred_i)
        
        if 'rmse' in metrics:
            results[f'{prefix}rmse'] = np.sqrt(mean_squared_error(y_true_i, y_pred_i))
        
        if 'mae' in metrics:
            results[f'{prefix}mae'] = mean_absolute_error(y_true_i, y_pred_i)
        
        if 'mape' in metrics:
            # Mean Absolute Percentage Error (avoid division by zero)
            mask = y_true_i != 0
            if np.any(mask):
                mape = np.mean(np.abs((y_true_i[mask] - y_pred_i[mask]) / y_true_i[mask])) * 100
                results[f'{prefix}mape'] = mape
        
        if 'cvrmse' in metrics:
            # Coefficient of Variation of RMSE
            mean_val = np.mean(y_true_i)
            if mean_val != 0:
                cvrmse = (np.sqrt(mean_squared_error(y_true_i, y_pred_i)) / mean_val) * 100
                results[f'{prefix}cvrmse'] = cvrmse
    
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
    
    Args:
        feature_cols: Available feature columns
        sensitivity_results: DataFrame with sensitivity results
        top_n: Select top N features
        threshold: Select features above threshold
        method: 'correlation', 'morris', 'sobol'
    """
    if sensitivity_results is None or sensitivity_results.empty:
        return feature_cols
    
    # Determine which column to use for ranking
    if method == 'correlation':
        if 'AbsCorrelation' in sensitivity_results.columns:
            rank_col = 'AbsCorrelation'
        else:
            # Handle multiple correlation columns
            abs_cols = [col for col in sensitivity_results.columns if col.startswith('AbsCorr_')]
            if abs_cols:
                # Take mean of all absolute correlations
                sensitivity_results['mean_abs_corr'] = sensitivity_results[abs_cols].mean(axis=1)
                rank_col = 'mean_abs_corr'
            else:
                logger.warning("No correlation columns found in sensitivity results")
                return feature_cols
    elif method == 'morris':
        rank_col = 'mu_star' if 'mu_star' in sensitivity_results.columns else None
    elif method == 'sobol':
        rank_col = 'ST' if 'ST' in sensitivity_results.columns else None
    else:
        logger.warning(f"Unknown sensitivity method: {method}")
        return feature_cols
    
    if rank_col is None:
        logger.warning(f"Ranking column not found for method {method}")
        return feature_cols
    
    # Get parameter names from sensitivity results
    param_col = 'Parameter' if 'Parameter' in sensitivity_results.columns else 'param'
    if param_col not in sensitivity_results.columns:
        logger.warning("Parameter column not found in sensitivity results")
        return feature_cols
    
    # Sort by importance
    sensitivity_results = sensitivity_results.sort_values(rank_col, ascending=False)
    
    # Filter based on criteria
    if threshold is not None:
        important_params = sensitivity_results[sensitivity_results[rank_col] >= threshold][param_col].tolist()
    elif top_n is not None:
        important_params = sensitivity_results.head(top_n)[param_col].tolist()
    else:
        important_params = sensitivity_results[param_col].tolist()
    
    # Return features that are in the important params list
    selected_features = [col for col in feature_cols if col in important_params]
    
    logger.info(f"Selected {len(selected_features)} features from {len(feature_cols)} based on sensitivity analysis")
    
    return selected_features


def save_model_metadata(
    model_path: str,
    metadata: Dict[str, Any]
):
    """Save model metadata including performance metrics, features, etc."""
    metadata['timestamp'] = datetime.now().isoformat()
    metadata_path = model_path.replace('.joblib', '_metadata.json')
    
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
        
    def fit(self, X_train, y_train, X_val=None, y_val=None, **fit_kwargs):
        """Fit the AutoML model"""
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
        time_limit = self.kwargs.get('time_limit', 300)  # 5 minutes default
        presets = self.kwargs.get('presets', 'medium_quality')
        
        # Create predictor
        self.model = TabularPredictor(
            label=label,
            eval_metric=self.kwargs.get('eval_metric', 'rmse'),
            path=self.kwargs.get('save_path', 'AutogluonModels'),
            verbosity=self.kwargs.get('verbosity', 2)
        )
        
        # Fit
        self.model.fit(
            train_data=train_data,
            time_limit=time_limit,
            presets=presets,
            **fit_kwargs
        )
        
        # Store best model info
        self.best_model_name = self.model.get_model_best()
        self.leaderboard = self.model.leaderboard()
    
    def _fit_h2o(self, X_train, y_train, X_val, y_val, **fit_kwargs):
        """Fit H2O AutoML"""
        # Initialize H2O
        h2o.init()
        
        # Convert to H2O frames
        train_frame = h2o.H2OFrame(pd.concat([X_train, y_train], axis=1))
        
        # Set target column
        y_col = y_train.columns[0] if hasattr(y_train, 'columns') else 'target'
        x_cols = [col for col in train_frame.columns if col != y_col]
        
        # Configure H2O AutoML
        aml = H2OAutoML(
            max_models=self.kwargs.get('max_models', 20),
            max_runtime_secs=self.kwargs.get('time_limit', 300),
            seed=self.kwargs.get('seed', 42),
            **fit_kwargs
        )
        
        # Train
        aml.train(x=x_cols, y=y_col, training_frame=train_frame)
        
        self.model = aml.leader
        self.leaderboard = aml.leaderboard
    
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
            **fit_kwargs
        )
        
        # Fit
        y_train_1d = y_train.values.ravel() if hasattr(y_train, 'values') else y_train
        self.model.fit(X_train, y_train_1d)
        
        # Export pipeline
        if 'export_pipeline' in self.kwargs:
            self.model.export(self.kwargs['export_pipeline'])
    
    def _fit_flaml(self, X_train, y_train, X_val, y_val, **fit_kwargs):
        """Fit FLAML AutoML"""
        # FLAML configuration
        self.model = FLAMLAutoML()
        
        # Settings
        settings = {
            "time_budget": self.kwargs.get('time_limit', 300),
            "metric": self.kwargs.get('metric', 'rmse'),
            "estimator_list": self.kwargs.get('estimator_list', ['lgbm', 'rf', 'xgboost']),
            "task": "regression",
            "seed": self.kwargs.get('seed', 42),
            "n_jobs": self.kwargs.get('n_jobs', -1),
        }
        
        # Fit
        y_train_1d = y_train.values.ravel() if hasattr(y_train, 'values') else y_train
        self.model.fit(X_train, y_train_1d, **settings, **fit_kwargs)
        
        # Store results
        self.best_model_name = self.model.best_estimator
        self.best_config = self.model.best_config
        self.best_loss = self.model.best_loss
    
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
        return None
    
    def save(self, path: str):
        """Save the AutoML model"""
        if self.framework == 'autogluon':
            # AutoGluon saves to its own directory
            logger.info(f"AutoGluon model saved to {self.model.path}")
        elif self.framework == 'h2o':
            h2o.save_model(model=self.model, path=path, force=True)
        elif self.framework in ['tpot', 'flaml']:
            joblib.dump(self.model, path)
    
    def load(self, path: str):
        """Load a saved AutoML model"""
        if self.framework == 'autogluon':
            self.model = TabularPredictor.load(path)
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
    
    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data
        frameworks: List of frameworks to test
        time_limit: Time budget in seconds
        
    Returns:
        Dictionary with results from each framework
    """
    if frameworks is None:
        frameworks = get_available_automl_frameworks()
    
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
                'feature_importance': automl.get_feature_importance()
            }
            
            # Framework-specific info
            if framework == 'autogluon':
                results[framework]['leaderboard'] = automl.leaderboard
                results[framework]['best_model'] = automl.best_model_name
            elif framework == 'flaml':
                results[framework]['best_model'] = automl.best_model_name
                results[framework]['best_config'] = automl.best_config
            
            logger.info(f"[AutoML] {framework} completed - RMSE: {metrics['rmse']:.4f}, R2: {metrics['r2']:.4f}")
            
        except Exception as e:
            logger.error(f"[AutoML] {framework} failed: {str(e)}")
            results[framework] = {'error': str(e)}
    
    return results


def evaluate_model_simple(y_true, y_pred) -> Dict[str, float]:
    """Simple evaluation metrics for AutoML comparison"""
    return {
        'r2': r2_score(y_true, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
        'mae': mean_absolute_error(y_true, y_pred)
    }
