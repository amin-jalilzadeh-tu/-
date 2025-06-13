# Surrogate Modeling Quick Reference

## Common Use Cases

### 1. Basic Surrogate (Default)
```json
{
  "surrogate": {
    "perform_surrogate": true,
    "scenario_folder": "scenarios",
    "results_csv": "results/merged_daily_mean.csv",
    "target_variable": "Heating:EnergyTransfer [J](Hourly)",
    "model_out": "surrogate.joblib",
    "cols_out": "columns.joblib"
  }
}
```

### 2. Automated ML (Recommended)
```json
{
  "surrogate": {
    "perform_surrogate": true,
    "automated_ml": true,
    "model_types": ["random_forest", "xgboost", "gradient_boosting"]
  }
}
```

### 3. Use Top 10 Parameters from Sensitivity
```json
{
  "surrogate": {
    "sensitivity_results_path": "sensitivity.csv",
    "feature_selection": {
      "method": "correlation",
      "top_n": 10
    }
  }
}
```

### 4. Multi-Output Model
```json
{
  "surrogate": {
    "target_variable": [
      "Heating:EnergyTransfer [J](Hourly)",
      "Cooling:EnergyTransfer [J](Hourly)",
      "Electricity:Facility [J](Daily)"
    ]
  }
}
```

### 5. Filter to HVAC Parameters Only
```json
{
  "surrogate": {
    "file_patterns": ["*hvac*.csv"],
    "param_filters": {
      "param_name_contains": ["setpoint", "temperature"]
    }
  }
}
```

### 6. Peak Load Analysis
```json
{
  "surrogate": {
    "target_variable": "Cooling:EnergyTransfer [J](Hourly)",
    "time_aggregation": "max"
  }
}
```

## Parameter Reference

### Input Selection
- `file_patterns`: List of file patterns, e.g., `["*hvac*.csv", "*dhw*.csv"]`
- `param_filters`:
  - `include_params`: List of exact parameter names to include
  - `exclude_params`: List of exact parameter names to exclude
  - `param_name_contains`: List of substrings to match

### Time Handling
- `time_aggregation`: `"sum"`, `"mean"`, `"max"`, `"min"`, `"std"`, `"percentile_95"`
- `extract_time_features`: `true/false` - Extract hour, month, day features

### Model Configuration
- `automated_ml`: `true/false` - Use automated model selection
- `model_types`: List from `["random_forest", "xgboost", "lightgbm", "gradient_boosting", "neural_network", "elastic_net"]`
- `cv_strategy`: `"kfold"` or `"time_series"`
- `scale_features`: `true/false` - Scale input features
- `scaler_type`: `"standard"` or `"minmax"`

### Feature Engineering
- `create_interactions`: `true/false` - Create parameter interactions
- `interaction_features`: Number of interactions to create (default: 10)
- `sensitivity_results_path`: Path to sensitivity CSV
- `feature_selection`:
  - `method`: `"correlation"`, `"morris"`, or `"sobol"`
  - `top_n`: Select top N features
  - `threshold`: Select features above threshold

### Output
- `model_out`: Path for model file
- `cols_out`: Path for columns file
- `save_metadata`: `true/false` - Save performance metrics

## Model Types Comparison

| Model | Speed | Accuracy | Interpretability | Best For |
|-------|-------|----------|------------------|----------|
| Random Forest | Fast | High | Good | General use, robust |
| XGBoost | Medium | Very High | Medium | Best accuracy |
| LightGBM | Fast | Very High | Medium | Large datasets |
| Gradient Boosting | Slow | High | Medium | Small datasets |
| Neural Network | Medium | High* | Low | Complex patterns |
| Elastic Net | Very Fast | Medium | High | Linear relationships |

*Neural networks require more data for good performance

## Tips

1. **Start with defaults** - The system works well out of the box
2. **Use automated ML** - Let the system choose the best model
3. **Leverage sensitivity** - Use sensitivity results to reduce features
4. **Match aggregation to use** - Sum for energy, mean for temperature
5. **Scale features** - Usually improves performance
6. **Save metadata** - Track model performance over time