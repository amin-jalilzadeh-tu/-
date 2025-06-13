# Standard ML vs AutoML - Quick Decision Guide

## Overview

Your enhanced surrogate modeling system now supports three levels of automation:

### 1. **Basic Mode** (Original)
- Single model (Random Forest)
- Manual hyperparameter tuning
- Fast and simple

### 2. **Standard Automated ML**
- Multiple traditional ML models
- Automated hyperparameter tuning
- Good balance of speed and accuracy

### 3. **Advanced AutoML**
- State-of-the-art AutoML frameworks
- Automatic feature engineering
- Neural networks and deep learning
- Best possible accuracy

## Configuration Comparison

### Option 1: Basic Random Forest (Fastest)
```json
{
  "surrogate": {
    "perform_surrogate": true,
    "automated_ml": false,
    "use_automl": false
  }
}
```
- **Time**: < 1 minute
- **Use when**: Quick testing, small datasets

### Option 2: Standard Automated ML (Recommended for Most Cases)
```json
{
  "surrogate": {
    "perform_surrogate": true,
    "automated_ml": true,
    "use_automl": false,
    "model_types": ["random_forest", "xgboost", "gradient_boosting"]
  }
}
```
- **Time**: 2-10 minutes
- **Use when**: Good balance needed, regular production use

### Option 3: Advanced AutoML (Best Accuracy)
```json
{
  "surrogate": {
    "perform_surrogate": true,
    "use_automl": true,
    "automl_framework": "autogluon",
    "automl_time_limit": 600
  }
}
```
- **Time**: 5-60 minutes
- **Use when**: Maximum accuracy needed, final models

## Feature Comparison Table

| Feature | Basic | Standard ML | AutoML |
|---------|-------|-------------|---------|
| **Setup Complexity** | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Training Speed** | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Accuracy** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Models Available** | 1 | 6 | 20+ |
| **Feature Engineering** | ❌ | Limited | ✅ Automatic |
| **Neural Networks** | ❌ | Simple | ✅ Advanced |
| **Ensemble Methods** | ❌ | Basic | ✅ Advanced |
| **Memory Usage** | Low | Medium | High |
| **Interpretability** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Dependencies** | Minimal | Moderate | Heavy |

## Decision Tree

```
Start Here
    │
    ├─ Need results in < 1 minute?
    │   └─ YES → Use Basic Mode
    │
    ├─ Is this for quick experimentation?
    │   └─ YES → Use Standard ML with ["random_forest", "xgboost"]
    │
    ├─ Do you have > 10 minutes for training?
    │   └─ YES → Do you need maximum possible accuracy?
    │       ├─ YES → Use AutoML (AutoGluon)
    │       └─ NO → Use Standard ML (all models)
    │
    └─ Is this for production deployment?
        ├─ Need model interpretability?
        │   └─ YES → Use Standard ML
        └─ NO → Use AutoML with "optimize_for_deployment"
```

## Quick Start Commands

### Install for Standard ML
```bash
pip install scikit-learn xgboost lightgbm
```

### Install for AutoML (choose one)
```bash
# Best accuracy
pip install autogluon

# Lightweight & fast
pip install flaml[automl]

# Both
pip install autogluon flaml[automl]
```

## Example Configurations

### Fast Experiment (2 minutes)
```json
{
  "surrogate": {
    "automated_ml": true,
    "model_types": ["random_forest", "xgboost"],
    "cv_strategy": "kfold",
    "test_size": 0.2
  }
}
```

### Balanced Approach (10 minutes)
```json
{
  "surrogate": {
    "automated_ml": true,
    "model_types": ["random_forest", "xgboost", "gradient_boosting", "lightgbm"],
    "scale_features": true,
    "cv_strategy": "kfold"
  }
}
```

### Maximum Accuracy (30 minutes)
```json
{
  "surrogate": {
    "use_automl": true,
    "automl_framework": "autogluon",
    "automl_time_limit": 1800,
    "automl_config": {
      "presets": "best_quality"
    }
  }
}
```

### Compare Everything (1 hour)
```json
{
  "surrogate": {
    "use_automl": true,
    "automl_framework": null,
    "automl_time_limit": 600,
    "sensitivity_results_path": "sensitivity.csv",
    "feature_selection": {
      "method": "correlation",
      "top_n": 20
    }
  }
}
```

## Performance Expectations

### Standard ML Performance
- Random Forest: R² = 0.85-0.92
- XGBoost: R² = 0.88-0.94
- LightGBM: R² = 0.87-0.93

### AutoML Performance
- AutoGluon: R² = 0.90-0.97
- FLAML: R² = 0.88-0.95
- H2O: R² = 0.89-0.95

*Note: Actual performance depends on data quality and problem complexity*

## Migration Path

1. **Start with**: Standard ML for initial development
2. **Optimize with**: AutoML for specific high-value models
3. **Deploy with**: The best performing model from comparison

## Common Issues and Solutions

### "AutoML taking too long"
- Reduce `automl_time_limit`
- Use FLAML instead of AutoGluon
- Apply feature selection first

### "Out of memory with AutoML"
- Use standard ML instead
- Reduce dataset size
- Use FLAML (most memory efficient)

### "Need interpretable models"
- Use standard ML with ["random_forest", "gradient_boosting"]
- Use H2O AutoML with interpretability focus
- Extract feature importance from any model

## Summary

- **For most users**: Standard Automated ML is the sweet spot
- **For maximum accuracy**: AutoML with AutoGluon
- **For quick tests**: Basic mode or FLAML
- **For production**: Test both and choose based on accuracy/speed tradeoff