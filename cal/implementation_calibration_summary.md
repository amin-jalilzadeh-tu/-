# Enhanced Calibration System - Implementation Summary

## Overview

The calibration system has been significantly enhanced to support advanced optimization techniques, time-based calibration, multi-objective optimization, and better integration with the enhanced sensitivity and surrogate modules.

## New Files Added

### 1. **`cal/calibration_objectives.py`**
Advanced objective functions for calibration:
- Multi-metric support (RMSE, MAE, CVRMSE, R², MAPE, peak errors)
- Time-based error calculation
- Multi-objective optimization support
- ASHRAE Guideline 14 compliance checking
- Custom weighted objectives

### 2. **`cal/calibration_algorithms.py`**
State-of-the-art optimization algorithms:
- **Particle Swarm Optimization (PSO)** - Good for continuous parameters
- **Differential Evolution (DE)** - Robust global optimization
- **NSGA-II** - Multi-objective genetic algorithm
- **CMA-ES** - Advanced evolution strategy
- **Hybrid/Adaptive** algorithms - Combines multiple methods

### 3. **`cal/unified_calibration.py`** (UPDATED)
Major enhancements:
- Time-based calibration support
- Multi-objective optimization
- Advanced algorithm integration
- Calibration validation
- Parameter constraints and groups
- Enhanced results saving

## Key Features

### 1. Time-Based Calibration

Calibrate parameters for specific time periods:

```json
{
  "calibration_configs": [
    {
      "name": "Summer Peak Cooling",
      "time_slice": {
        "method": "custom",
        "custom_config": {
          "months": [6, 7, 8],
          "hours": [14, 15, 16, 17],
          "weekdays_only": true
        }
      },
      "target_variables": ["Cooling:EnergyTransfer [J](Hourly)"],
      "param_filters": {
        "param_name_contains": ["cooling", "ventilation"]
      }
    }
  ]
}
```

### 2. Multi-Objective Optimization

Optimize multiple metrics simultaneously:

```json
{
  "objectives": [
    {
      "target_variable": "Electricity:Facility [J](Hourly)",
      "metric": "cvrmse",
      "weight": 0.4,
      "tolerance": 15.0  // ASHRAE target
    },
    {
      "target_variable": "Cooling:EnergyTransfer [J](Hourly)",
      "metric": "peak_relative_error",
      "weight": 0.6
    }
  ]
}
```

### 3. Advanced Algorithms

Choose from multiple optimization algorithms:

```json
{
  "method": "pso",  // or "de", "nsga2", "cmaes", "hybrid"
  "algorithm_config": {
    "pso": {
      "n_particles": 50,
      "max_iter": 100,
      "inertia": 0.9,
      "cognitive": 2.0,
      "social": 2.0
    }
  }
}
```

### 4. Calibration Validation

Prevent overfitting with cross-validation:

```json
{
  "validation": {
    "cross_validate": true,
    "n_folds": 3,
    "holdout_percentage": 0.2,
    "overfitting_threshold": 0.1
  }
}
```

### 5. Adaptive Optimization

Multi-stage optimization that adapts based on convergence:

```json
{
  "adaptive_config": {
    "enable_adaptive": true,
    "stages": [
      {
        "name": "Global Search",
        "algorithm": "de",
        "iterations": 50
      },
      {
        "name": "Local Refinement",
        "algorithm": "pso",
        "iterations": 30,
        "bounds_multiplier": 0.5
      }
    ]
  }
}
```

## Usage Examples

### Example 1: Basic Enhanced Calibration
```json
{
  "calibration": {
    "perform_calibration": true,
    "scenario_folder": "scenarios",
    "method": "pso",
    "use_surrogate": true,
    "target_variables": ["Heating:EnergyTransfer [J](Hourly)"],
    "real_data_csv": "data/real_measurements.csv",
    "algorithm_config": {
      "pso": {
        "n_particles": 30,
        "max_iter": 100
      }
    }
  }
}
```

### Example 2: Multi-Objective ASHRAE Calibration
```json
{
  "calibration": {
    "perform_calibration": true,
    "method": "nsga2",
    "objectives": [
      {
        "target_variable": "Electricity:Facility [J](Hourly)",
        "metric": "cvrmse",
        "weight": 0.5,
        "tolerance": 30.0
      },
      {
        "target_variable": "Electricity:Facility [J](Hourly)",
        "metric": "nmbe",
        "weight": 0.5,
        "tolerance": 10.0
      }
    ],
    "algorithm_config": {
      "nsga2": {
        "pop_size": 100,
        "n_generations": 100
      }
    }
  }
}
```

### Example 3: Seasonal Calibration
```json
{
  "calibration": {
    "perform_calibration": true,
    "calibration_configs": [
      {
        "name": "Winter Heating",
        "time_slice": {
          "method": "predefined",
          "predefined_slice": "peak_heating_months"
        },
        "target_variables": ["Heating:EnergyTransfer [J](Hourly)"],
        "param_filters": {
          "param_name_contains": ["heating", "infiltration"]
        },
        "method": "de"
      },
      {
        "name": "Summer Cooling",
        "time_slice": {
          "method": "predefined",
          "predefined_slice": "peak_cooling_months"
        },
        "target_variables": ["Cooling:EnergyTransfer [J](Hourly)"],
        "param_filters": {
          "param_name_contains": ["cooling", "window"]
        },
        "method": "pso"
      }
    ]
  }
}
```

### Example 4: Hybrid Adaptive Calibration
```json
{
  "calibration": {
    "perform_calibration": true,
    "method": "hybrid",
    "adaptive_config": {
      "enable_adaptive": true,
      "stages": [
        {
          "algorithm": "de",
          "iterations": 50,
          "strategy": "best1bin"
        },
        {
          "algorithm": "pso",
          "iterations": 30,
          "bounds_multiplier": 0.5,
          "inertia": 0.7
        },
        {
          "algorithm": "cmaes",
          "iterations": 20,
          "bounds_multiplier": 0.2,
          "sigma0": 0.1
        }
      ]
    },
    "validation": {
      "cross_validate": true,
      "n_folds": 5
    }
  }
}
```

## Available Metrics

### Error Metrics
- **RMSE**: Root Mean Square Error
- **MAE**: Mean Absolute Error
- **CVRMSE**: Coefficient of Variation of RMSE (%)
- **R²**: Coefficient of determination (minimizes 1-R²)
- **MAPE**: Mean Absolute Percentage Error (%)
- **NMBE**: Normalized Mean Bias Error (%)

### Peak-Focused Metrics
- **peak_error**: Maximum absolute error
- **peak_relative_error**: Maximum relative error (%)
- **weighted_rmse**: RMSE weighted by magnitude

### Statistical Metrics
- **cv**: Coefficient of Variation (%)

## Algorithm Comparison

| Algorithm | Best For | Pros | Cons |
|-----------|----------|------|------|
| **PSO** | Continuous parameters | Fast convergence, good for smooth landscapes | Can get stuck in local optima |
| **DE** | General purpose | Robust, good global search | Slower than PSO |
| **NSGA-II** | Multi-objective | Finds Pareto front, handles trade-offs | Requires more evaluations |
| **CMA-ES** | Difficult landscapes | Handles non-convex, noisy objectives | Complex to tune |
| **Hybrid** | Complex problems | Combines strengths of multiple methods | Longer runtime |

## Integration with Other Modules

### With Enhanced Sensitivity
- Automatically select top parameters from sensitivity analysis
- Filter parameters by sensitivity results
- Use same time slicing configuration

### With Enhanced Surrogate
- Leverage AutoML surrogate models
- Use uncertainty estimates for adaptive sampling
- Support multi-output surrogates

## Performance Tips

1. **Start Simple**: Use PSO or DE for initial testing
2. **Use Time Slicing**: Focus on periods where parameters matter most
3. **Parameter Filtering**: Reduce dimensionality using sensitivity results
4. **Multi-Stage**: Use hybrid approach for difficult problems
5. **Validation**: Always enable cross-validation for production use

## Output Files

### Standard Outputs
- `calibration_history.csv`: All parameter combinations tested
- `calibrated_params_*.csv`: Best parameters for each scenario file
- `calibration_metadata.json`: Summary and configuration

### Enhanced Outputs
- `convergence_data.json`: Algorithm convergence metrics
- `calibration_summary.json`: Multi-configuration summary
- `pareto_front.csv`: Pareto-optimal solutions (NSGA-II)

## Dependencies

### Required
- numpy, pandas, scikit-learn
- scikit-optimize (for Bayesian optimization)

### Optional (for advanced features)
- **pymoo**: For NSGA-II multi-objective optimization
- **cma**: For CMA-ES optimization

Install with:
```bash
pip install pymoo cma
```

## Backward Compatibility

All enhancements are backward compatible. Existing configurations will work without modification. New features only activate when explicitly configured.

## Migration Guide

### From Basic to Enhanced
1. Keep existing configuration
2. Add `algorithm_config` for fine-tuning
3. Add `validation` for robustness
4. Consider `time_slice` for targeted calibration

### From Single to Multi-Objective
1. Replace `target_variable` with `objectives` list
2. Change `method` to "nsga2"
3. Add weights and tolerances
4. Review Pareto front results

## Future Enhancements

Potential future additions:
- Uncertainty quantification
- Bayesian optimization with Gaussian Processes
- Distributed/parallel calibration
- Active learning for efficient sampling
- Integration with cloud computing resources