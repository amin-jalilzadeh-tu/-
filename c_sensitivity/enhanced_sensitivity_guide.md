# Enhanced Sensitivity Analysis Implementation Guide

## Overview

The enhanced sensitivity analysis module provides a comprehensive framework for understanding parameter impacts on building energy performance. It integrates with validation results, performs building-specific analysis, handles multi-objective optimization, and generates actionable recommendations for the modification and calibration stages.

## New Features

### 1. Building-Specific Sensitivity Analysis
- Analyze sensitivity patterns by building type, age, function, or custom groupings
- Identify which parameters are universally important vs. building-specific
- Weight analysis by validation performance to focus on problematic buildings

### 2. System-Level Analysis
- Group parameters by building system (HVAC, DHW, Envelope, etc.)
- Analyze system-level impacts and interactions
- Identify which systems have the most influence on energy performance

### 3. Multi-Objective Optimization Support
- Handle multiple target variables simultaneously (Heating, Cooling, Electricity)
- Identify parameters with conflicting effects
- Create composite sensitivity scores with custom weighting

### 4. Adaptive Analysis
- Use Morris screening to identify important parameters quickly
- Perform detailed Sobol analysis only on top parameters
- Save computational time for large parameter sets

### 5. Enhanced Visualization
- Interactive Plotly dashboards
- Tornado diagrams for parameter rankings
- Heatmaps showing sensitivity across building groups
- Conflict analysis plots for multi-objective trade-offs

### 6. Integration with Workflow
- Automatic parameter ranking for modification priorities
- Feature selection for surrogate modeling
- Parameter subset selection for calibration
- Validation-weighted sensitivity scores

## File Structure

```
cal/
├── enhanced_sensitivity_analyzer.py    # Main analyzer class
├── sensitivity_visualization.py        # Visualization utilities
├── time_slice_utils.py                # Time filtering utilities
├── unified_sensitivity.py             # Updated base functions
└── updated_main_cal.py                # Integrated workflow

sensitivity_analysis/               # Output directory
├── sensitivity_results.json       # Main results
├── parameter_rankings.json        # Ranked parameters
├── recommendations.json           # Actionable recommendations
├── analysis_metadata.json         # Analysis configuration
├── analysis_summary.json          # Summary statistics
├── plots/                        # Visualization outputs
│   ├── tornado_*.png
│   ├── heatmap_*.png
│   ├── system_comparison.png
│   └── ...
└── report/
    └── sensitivity_report.html   # Comprehensive HTML report
```

## Configuration

### Basic Configuration

```json
{
  "sensitivity": {
    "perform_sensitivity": true,
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results.csv",
    "target_variable": ["Heating", "Cooling", "Electricity"],
    "output_csv": "sensitivity.csv"
  }
}
```

### Enhanced Configuration

```json
{
  "sensitivity": {
    "perform_sensitivity": true,
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results.csv",
    "target_variable": ["Heating", "Cooling", "Electricity"],
    
    "building_specific": {
      "perform": true,
      "group_by": ["building_function", "age_range"],
      "minimum_buildings_per_group": 3
    },
    
    "validation_integration": {
      "use_validation_weights": true,
      "focus_on_failed_buildings": true,
      "validation_threshold": 30.0
    },
    
    "parameter_grouping": {
      "group_by_system": true,
      "analyze_interactions": true
    },
    
    "multi_objective": {
      "composite_score": true,
      "identify_conflicts": true,
      "objective_weights": {
        "Heating": 0.35,
        "Cooling": 0.35,
        "Electricity": 0.30
      }
    },
    
    "visualization": {
      "generate_plots": true,
      "plot_types": ["tornado", "heatmap", "scatter"]
    }
  }
}
```

## Usage Examples

### 1. Standard Analysis
```python
from cal.enhanced_sensitivity_analyzer import run_enhanced_sensitivity_analysis

config = {
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results.csv",
    "target_variable": "Cooling:EnergyTransfer [J](Hourly)"
}

results = run_enhanced_sensitivity_analysis(config)
```

### 2. Building-Specific Analysis
```python
config = {
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results.csv",
    "target_variable": ["Heating", "Cooling"],
    "building_specific": {
        "perform": True,
        "group_by": ["building_function"],
        "minimum_buildings_per_group": 5
    }
}

results = run_enhanced_sensitivity_analysis(config)
```

### 3. Time-Sliced Analysis
```python
config = {
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results.csv",
    "target_variable": "Cooling:EnergyTransfer [J](Hourly)",
    "time_slice_config": {
        "method": "custom",
        "custom_config": {
            "months": [7, 8],
            "hours": [14, 15, 16, 17],
            "weekdays_only": True
        }
    }
}

results = run_enhanced_sensitivity_analysis(config)
```

### 4. Multi-Objective with Conflict Analysis
```python
config = {
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results.csv",
    "target_variable": ["Heating", "Cooling", "Electricity"],
    "multi_objective": {
        "composite_score": True,
        "identify_conflicts": True,
        "objective_weights": {
            "Heating": 0.4,
            "Cooling": 0.4,
            "Electricity": 0.2
        }
    }
}

results = run_enhanced_sensitivity_analysis(config)
```

## Output Structure

### 1. Parameter Rankings (`parameter_rankings.json`)
```json
{
  "overall": [
    {
      "Parameter": "cooling_day_setpoint",
      "CompositeScore": 0.85
    },
    {
      "Parameter": "heating_day_setpoint",
      "CompositeScore": 0.78
    }
  ],
  "system_hvac": [...],
  "group_residential": [...]
}
```

### 2. Recommendations (`recommendations.json`)
```json
{
  "modification_priorities": [
    {
      "parameter": "cooling_day_setpoint",
      "impact_score": 0.85,
      "recommendation": "High priority for modification"
    }
  ],
  "calibration_focus": [
    {
      "parameter": "ventilation_rate",
      "conflict_score": 0.45,
      "recommendation": "Requires careful calibration due to conflicting effects"
    }
  ],
  "dead_parameters": [
    {
      "parameter": "material_roughness",
      "max_correlation": 0.05,
      "recommendation": "Can be fixed at nominal value"
    }
  ]
}
```

### 3. Analysis Summary (`analysis_summary.json`)
```json
{
  "analysis_timestamp": "2024-01-15T10:30:00",
  "total_parameters_analyzed": 150,
  "active_parameters": 95,
  "dead_parameters": 55,
  "building_groups_analyzed": 4,
  "systems_analyzed": 5,
  "conflicting_parameters_found": 12
}
```

## Integration with Other Modules

### 1. Surrogate Modeling
The sensitivity results automatically feed into surrogate modeling:

```json
{
  "surrogate": {
    "sensitivity_results_path": "sensitivity_analysis/parameter_rankings.json",
    "feature_selection": {
      "method": "sensitivity_based",
      "top_n": 30
    }
  }
}
```

### 2. Calibration
Top parameters from sensitivity are used for calibration:

```json
{
  "calibration": {
    "subset_sensitivity_csv": "sensitivity_analysis/parameter_rankings.json",
    "top_n_params": 20
  }
}
```

### 3. Modification
Recommendations guide modification priorities:

```python
# In modification module
with open("sensitivity_analysis/recommendations.json", 'r') as f:
    recommendations = json.load(f)

# Focus on high-priority parameters
priority_params = [
    rec["parameter"] 
    for rec in recommendations["modification_priorities"][:10]
]
```

## Best Practices

1. **Start with Screening**: Use Morris method for initial screening of large parameter sets
2. **Focus on Failed Buildings**: Use validation integration to weight sensitivity by performance
3. **Consider Time Periods**: Use time slicing for peak load analysis
4. **Check for Conflicts**: Always run multi-objective analysis when optimizing multiple targets
5. **Visualize Results**: Generate plots to understand patterns and communicate findings
6. **Use Recommendations**: Follow the automated recommendations for modification and calibration
7. **Iterate**: Re-run sensitivity after modifications to see if relationships change

## Troubleshooting

### Common Issues

1. **No sensitivity results generated**
   - Check that scenario parameters are properly loaded
   - Verify results CSV has the expected format
   - Ensure target variables exist in results

2. **Building groups too small**
   - Adjust `minimum_buildings_per_group` parameter
   - Use fewer grouping variables
   - Check building metadata availability

3. **Visualization errors**
   - Install required packages: `pip install plotly seaborn`
   - Check output directory permissions
   - Verify data completeness

4. **Memory issues with large datasets**
   - Use parameter filtering to reduce set size
   - Run adaptive analysis (screening first)
   - Process building groups separately

## Advanced Features

### Custom Time Slices
```python
# Analyze only extreme temperature days
config["time_slice_config"] = {
    "method": "custom",
    "custom_config": {
        "specific_days": [[1, 15], [7, 21]],  # Jan 15, Jul 21
        "hours": list(range(24))  # All hours
    }
}
```

### Parameter Filtering
```python
# Focus on HVAC parameters only
config["file_patterns"] = ["*hvac*.csv"]
config["param_filters"] = {
    "param_name_contains": ["setpoint", "efficiency", "cop"]
}
```

### Multiple Analysis Configurations
```python
# Run different analyses in one go
config["analysis_configs"] = [
    {
        "name": "Summer Peak",
        "time_slice_config": {"method": "predefined", "predefined_slice": "peak_cooling_months"},
        "target_variable": "Cooling"
    },
    {
        "name": "Winter Morning",
        "time_slice_config": {"method": "predefined", "predefined_slice": "winter_mornings"},
        "target_variable": "Heating"
    }
]
```

## Next Steps

After running enhanced sensitivity analysis:

1. Review the HTML report for comprehensive insights
2. Use parameter rankings to guide surrogate model feature selection
3. Focus calibration on high-impact, non-conflicting parameters
4. Prioritize modifications based on recommendations
5. Consider building-specific strategies for different groups
6. Re-run analysis after modifications to track changes