
Project Context: EnergyPlus Surrogate Modeling Integration


let's design a flexible configuration system for the surrogate modeling. Here's a comprehensive structure:

## 1. Input Data Configuration Options

### Parameter Selection Strategies
```yaml
parameter_selection:
  strategy: 
    - "all_parameters"           # Use all modified parameters
    - "sensitivity_based"        # Only parameters with sensitivity > threshold
    - "category_based"          # Select specific categories
    - "custom_list"             # Manually specified parameters
    - "interaction_based"       # Include parameter interactions
  
  sensitivity_options:
    threshold: 0.1              # Minimum sensitivity score
    use_elasticity: true        # Use elasticity-based ranking
    use_p_value: true          # Filter by statistical significance
    confidence_level: "high"    # Only high confidence parameters
  
  category_options:
    include: ["lighting", "ventilation", "dhw", "materials"]
    exclude: ["geometry"]       # Categories to exclude
    
  grouping:
    - "by_category"            # Group parameters by system type
    - "by_zone"                # Group by affected zones
    - "by_impact"              # Group by sensitivity magnitude
    - "by_physics"             # Group by physical behavior (thermal, flow, etc.)
```

### Input Feature Engineering
```yaml
feature_engineering:
  raw_parameters: true          # Use direct parameter values
  normalized_parameters: true   # Normalize to [0,1] or [-1,1]
  relative_changes: true        # Use % change from baseline
  
  derived_features:
    - ratios                    # e.g., surface/volume ratios
    - products                  # Parameter interactions
    - dimensionless_numbers     # Re, Pr, etc.
    
  temporal_features:
    - hour_of_day
    - day_of_week
    - month
    - heating_degree_days
    - cooling_degree_days
    
  building_features:
    - total_floor_area
    - number_of_zones
    - building_type
```

## 2. Output Variable Configuration

### Output Selection
```yaml
output_variables:
  energy_metrics:
    - total_heating_energy
    - total_cooling_energy
    - peak_heating_demand
    - peak_cooling_demand
    - water_heating_energy
    
  comfort_metrics:
    - zone_mean_temperature
    - unmet_heating_hours
    - unmet_cooling_hours
    - thermal_comfort_index
    
  system_metrics:
    - ventilation_flow_rate
    - equipment_runtime
    - system_efficiency
    
  aggregation_levels:
    - building_total
    - zone_level
    - system_level
    
  temporal_resolution:
    - annual
    - monthly
    - daily
    - hourly
    - peak_period_only
```

## 3. Validation Configuration

### Validation Strategies
```yaml
validation:
  data_split:
    method: 
      - "random_split"         # Random 80/20 split
      - "building_based"       # Hold out entire buildings
      - "temporal_split"       # Train on year 1, test on year 2
      - "parameter_range"      # Train on center, test on extremes
    
  cross_validation:
    enabled: true
    folds: 5
    stratify_by: ["building_type", "climate_zone"]
    
  metrics:
    regression:
      - mae                    # Mean Absolute Error
      - rmse                   # Root Mean Square Error
      - r2                     # R-squared
      - mape                   # Mean Absolute Percentage Error
      
    physics_based:
      - energy_balance_error   # Check conservation laws
      - peak_load_accuracy
      - sensitivity_preservation # Compare with original sensitivity
      
  uncertainty_quantification:
    enabled: true
    method: ["prediction_intervals", "bayesian", "ensemble"]
```

## 4. Model Output Structure

### Primary Outputs
```yaml
model_outputs:
  predictions:
    point_estimates:          # Single predicted values
      format: "dataframe"
      columns: ["building_id", "timestamp", "variable", "value"]
      
    uncertainty_bounds:       # Confidence/prediction intervals
      lower_bound: 5%
      upper_bound: 95%
      
  model_artifacts:
    trained_model:           # Serialized model object
    feature_importance:      # Which inputs matter most
    partial_dependencies:    # How each input affects outputs
    
  diagnostics:
    training_history:        # Loss curves, convergence
    residual_analysis:       # Error patterns
    extrapolation_warnings:  # When predicting outside training range
```

### Derived Outputs
```yaml
derived_outputs:
  sensitivity_analysis:
    local_sensitivity:       # Derivatives at specific points
    global_sensitivity:      # Sobol indices, Morris method
    
  optimization_ready:
    response_surfaces:       # Smooth approximations
    constraint_functions:    # For optimization problems
    
  scenario_analysis:
    parameter_sweeps:        # Vary one parameter at a time
    interaction_plots:       # 2D/3D visualizations
    
  performance_metrics:
    inference_time:          # Speed benchmarks
    memory_usage:
    accuracy_by_category:    # Performance breakdown
```
### other
output_variables:
  parameter_specific_outputs:
    lighting:
      - "Zone Lights Electric Energy"
      - "Zone Lights Sensible Heating Energy"
      - "Lighting Power Density"
    
    ventilation:
      - "Zone Mechanical Ventilation Mass Flow Rate"
      - "Zone Ventilation Sensible Heat Loss Energy"
      - "Zone Outdoor Air Volume Flow Rate"
    
    dhw:
      - "Water Heater Heating Energy"
      - "Water Heater Tank Temperature"
      - "DHW Flow Rate"
    
    materials:
      - "Surface Inside Face Conduction Heat Transfer Energy"
      - "Surface Heat Storage Energy"
      
  zone_configuration:
    zone_types:
      - "single_zone_per_floor"    # One zone per floor
      - "perimeter_core"           # Perimeter zones + core
      - "detailed_zoning"          # Multiple zones per floor
      
    aggregation_options:
      spatial:
        - "by_zone"               # Keep individual zones
        - "by_floor"              # Aggregate to floor level
        - "by_building"           # Total building only
        - "perimeter_vs_core"     # Separate perimeter and core
        
      temporal:
        - "maintain_resolution"    # Keep original time step
        - "peak_average"          # Peak and average values
        - "custom_periods"        # User-defined periods















## 5. Integration with Existing Workflow

### Data Flow Configuration
```yaml
integration:
  input_sources:
    modifications: "modifications_detail_*.parquet"
    base_results: "parsed_data/sql_results/*"
    modified_results: "parsed_modified_results/sql_results/*"
    sensitivity: "sensitivity_for_surrogate.parquet"
    
  preprocessing:
    handle_missing: ["interpolate", "drop", "impute"]
    outlier_detection: true
    data_cleaning: true
    
  output_destinations:
    model_storage: "models/surrogate/"
    predictions: "predictions/surrogate/"
    validation_reports: "reports/validation/"
```

## 6. Configuration Examples

### Example 1: High-fidelity Energy Model
```yaml
name: "detailed_energy_surrogate"
parameters:
  selection: "sensitivity_based"
  threshold: 0.05
  include_interactions: true
outputs:
  variables: ["heating_energy", "cooling_energy", "peak_demands"]
  resolution: "hourly"
validation:
  method: "cross_validation"
  physics_checks: true
```

### Example 2: Fast Screening Model
```yaml
name: "rapid_screening"
parameters:
  selection: "category_based"
  categories: ["lighting", "ventilation"]
outputs:
  variables: ["annual_energy"]
  resolution: "annual"
validation:
  method: "random_split"
  metrics: ["mape", "r2"]
```

### Example 3: Uncertainty-Aware Model
```yaml
name: "uncertainty_quantified"
parameters:
  selection: "all_parameters"
  include_sensitivity: true
outputs:
  include_bounds: true
  confidence_level: 0.95
validation:
  uncertainty_calibration: true
```

This structure allows you to:
1. Flexibly configure what goes into the model
2. Control what comes out
3. Validate appropriately for different use cases
4. Integrate smoothly with your existing pipeline

