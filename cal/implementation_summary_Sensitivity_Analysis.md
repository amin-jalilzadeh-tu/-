# Enhanced Sensitivity Analysis - Implementation Summary

## Files Added/Modified

### 1. **NEW FILE: `cal/time_slice_utils.py`**

- Utilities for filtering simulation results by time periods
- Functions for parsing E+ time columns
- Predefined time slices (peak cooling/heating, afternoons, etc.)
- Custom time filtering by months, hours, weekdays/weekends

### 2. **UPDATED: `cal/unified_sensitivity.py`**

- Added `file_patterns` parameter to select which scenario files to include
- Added `param_filters` to filter parameters by name, inclusion/exclusion lists
- Added `time_slice_config` for time-based sensitivity analysis
- Added `analysis_configs` to run multiple analyses in one call
- Enhanced `load_scenario_params()` with filtering capabilities
- New `correlation_sensitivity_with_time_slice()` function

### 3. **UPDATED: `cal/main cal.py`** (example usage)

- Demonstrates all new features with practical examples

### 4. **NO CHANGES to `orchestrator.py`**

- Works with existing orchestrator without modifications
- New features configured through `main_config.json`

## New Features

### 1. Time Slice Analysis

Perform sensitivity analysis on specific time periods:

**Predefined slices:**

- `peak_cooling_months`: July, August
- `peak_heating_months`: January, February
- `afternoon_peak`: 2-6 PM weekdays
- `morning_startup`: 6-9 AM weekdays
- `weekend_base`: All weekend hours
- `summer_afternoons`: June-August, 12-6 PM
- `winter_mornings`: Dec-Feb, 6-10 AM

**Custom slices:**

```json
{
  "time_slice_config": {
    "method": "custom",
    "custom_config": {
      "months": [6, 7, 8],
      "hours": [14, 15, 16, 17],
      "weekdays_only": true
    }
  }
}
```

### 2. File Selection

Choose which scenario files to process:

```json
{
  "file_patterns": ["*hvac*.csv", "*dhw*.csv", "*vent*.csv"]
}
```

### 3. Parameter Filtering

Control which parameters to include in analysis:

```json
{
  "param_filters": {
    "include_params": ["heating_day_setpoint", "cooling_day_setpoint"],
    "exclude_params": ["roughness"],
    "param_name_contains": ["setpoint", "temperature"],
    "source_files": ["scenario_params_hvac.csv"]
  }
}
```

### 4. Multiple Analysis Configurations

Run multiple analyses with different settings:

```json
{
  "analysis_configs": [
    {
      "name": "Peak Cooling",
      "method": "correlation",
      "target_variable": "Cooling:EnergyTransfer [J](Hourly)",
      "output_csv": "peak_cooling_sensitivity.csv",
      "time_slice_config": {...},
      "param_filters": {...}
    },
    {
      "name": "Winter Heating",
      ...
    }
  ]
}
```

## Usage Examples

### Example 1: Analyze cooling during peak summer afternoons

```python
run_sensitivity_analysis(
    scenario_folder="scenarios",
    method="correlation",
    results_csv="results.csv",
    target_variable="Cooling:EnergyTransfer [J](Hourly)",
    output_csv="summer_peak_cooling.csv",
    time_slice_config={
        "method": "custom",
        "custom_config": {
            "months": [7, 8],
            "hours": [14, 15, 16, 17, 18],
            "weekdays_only": True
        }
    },
    file_patterns=["*hvac*.csv", "*vent*.csv"],
    param_filters={
        "param_name_contains": ["cooling", "temperature"]
    }
)
```

### Example 2: Weekend electricity base load analysis

```python
run_sensitivity_analysis(
    scenario_folder="scenarios",
    method="correlation",
    results_csv="results.csv",
    target_variable="Electricity:Facility [J](Hourly)",
    output_csv="weekend_electricity.csv",
    time_slice_config={
        "method": "predefined",
        "predefined_slice": "weekend_base"
    },
    file_patterns=["*elec*.csv", "*equipment*.csv"]
)
```

### Example 3: Multiple time periods in one run

```python
analysis_configs = [
    {
        "name": "Morning Startup",
        "time_slice_config": {"method": "predefined", "predefined_slice": "morning_startup"},
        "target_variable": "Heating:EnergyTransfer [J](Hourly)",
        "output_csv": "morning_heating.csv"
    },
    {
        "name": "Afternoon Peak", 
        "time_slice_config": {"method": "predefined", "predefined_slice": "afternoon_peak"},
        "target_variable": "Cooling:EnergyTransfer [J](Hourly)",
        "output_csv": "afternoon_cooling.csv"
    }
]

run_sensitivity_analysis(
    scenario_folder="scenarios",
    method="correlation",
    results_csv="results.csv",
    analysis_configs=analysis_configs
)
```

## Configuration in main_config.json

Add to your existing sensitivity configuration:

```json
{
  "sensitivity": {
    "perform_sensitivity": true,
    "scenario_folder": "scenarios",
    "method": "correlation",
    "results_csv": "results_scenarioes/merged_daily_mean_scenarios.csv",
    "target_variable": ["Heating:EnergyTransfer [J](Hourly)", "Cooling:EnergyTransfer [J](Hourly)"],
    "output_csv": "sensitivity_output.csv",
  
    "time_slice_config": {
      "method": "predefined",
      "predefined_slice": "peak_cooling_months"
    },
  
    "file_patterns": ["*hvac*.csv", "*dhw*.csv"],
  
    "param_filters": {
      "param_name_contains": ["setpoint", "temperature"]
    }
  }
}
```

## Benefits

1. **Targeted Analysis**: Focus on specific time periods when certain parameters have the most impact
2. **Reduced Noise**: Exclude irrelevant time periods that might dilute sensitivity results
3. **Parameter Control**: Analyze only the parameters you care about
4. **Efficiency**: Process only the scenario files you need
5. **Flexibility**: Run multiple analyses with different configurations in one workflow

## Backward Compatibility

All changes are backward compatible. Existing configurations will work without modification. New features are optional and only activate when configured.










=========================





Based on your code and project overview, here's what I recommend for enhancing the sensitivity analysis module:

## Current State Analysis

You already have a good foundation with:

* Correlation-based sensitivity analysis
* Morris and Sobol methods (SALib integration)
* Time slice filtering (peak hours, specific periods)
* Parameter filtering capabilities
* Multi-variable target support

## Recommended Updates and Additions

### 1. **Building-Specific Sensitivity Analysis**

* Add capability to perform sensitivity analysis per building or building type
* Compare sensitivity patterns across different building characteristics (age, function, size)
* Identify which parameters are universally important vs. building-specific

### 2. **Integration with Validation Results**

* Weight sensitivity analysis by validation performance
* Focus on parameters that might improve poorly performing buildings
* Create a "validation-informed sensitivity score"

### 3. **Hierarchical Parameter Grouping**

* Group parameters by system (HVAC, DHW, Envelope, etc.)
* Analyze sensitivity at both individual parameter and system level
* Identify interactions between parameter groups

### 4. **Enhanced Output Structure**

* Save sensitivity results in a structured format that the modification module can use
* Include metadata about analysis conditions (time slice, building subset, etc.)
* Create a "parameter importance ranking" for modification prioritization

### 5. **Multi-Objective Sensitivity**

* Since you analyze Heating, Cooling, and Electricity together:
  * Create composite sensitivity scores
  * Identify parameters that affect multiple objectives
  * Find parameters with conflicting effects (good for one, bad for another)

### 6. **Scenario Effectiveness Analysis**

* Analyze which parameter combinations from your scenarios had the most impact
* Identify "dead" parameters that don't significantly affect outputs
* Suggest parameter ranges for future scenario generation

### 7. **Sensitivity Visualization Module**

* Create sensitivity heatmaps (parameters vs buildings)
* Generate tornado diagrams for top influential parameters
* Plot sensitivity over time (using your time slice feature)
* Create building cluster visualizations based on sensitivity patterns

### 8. **Uncertainty Propagation**

* Add confidence intervals to sensitivity indices
* Consider parameter uncertainty from the IDF parsing
* Propagate measurement uncertainty from validation data

### 9. **Adaptive Sensitivity Analysis**

* Start with screening (Morris) to identify important parameters
* Then do detailed analysis (Sobol) only on important parameters
* Save computational time for large parameter sets

### 10. **Feedback Loop Preparation**

* Create a "sensitivity database" that tracks how sensitivity changes across iterations
* Identify parameters that become more/less sensitive after modifications
* Generate recommendations for the next modification round

## Data Flow Integration

**Inputs needed from previous steps:**

* Scenario parameter files (from scenario generation)
* Simulation results (from batch simulations)
* Validation results (to identify problem buildings)
* Building metadata (for building-specific analysis)

**Outputs to provide for next steps:**

* Ranked parameter list for modification
* Building-specific parameter recommendations
* Parameter ranges that show high impact
* Sensitivity metadata for surrogate model training

## Configuration Structure Additions

Add to your `combined.json`:

```json
"sensitivity": {
  // ... existing config ...
  
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
    "analyze_interactions": true,
    "systems": ["hvac", "dhw", "envelope", "lighting"]
  },
  
  "multi_objective": {
    "composite_score": true,
    "identify_conflicts": true,
    "objective_weights": {
      "Heating:EnergyTransfer": 0.35,
      "Cooling:EnergyTransfer": 0.35,
      "Electricity:Facility": 0.30
    }
  },
  
  "visualization": {
    "generate_plots": true,
    "plot_types": ["tornado", "heatmap", "time_series", "scatter"],
    "output_dir": "sensitivity_plots"
  },
  
  "adaptive_analysis": {
    "screening_first": true,
    "screening_method": "morris",
    "detailed_top_n": 20,
    "detailed_method": "sobol"
  }
}
```

This structure will make your sensitivity analysis more actionable and better integrated with your modification and calibration pipeline. Would you like me to elaborate on any of these recommendations or start implementing specific components?
