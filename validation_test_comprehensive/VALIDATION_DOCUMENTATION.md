# Smart Validation Wrapper - Comprehensive Documentation

Generated: 2025-06-29 15:39:45

## Overview

The Smart Validation Wrapper provides intelligent validation of EnergyPlus simulation results against measured data.
It handles variable mapping, frequency alignment, unit conversions, and multi-zone aggregation automatically.

## Core Functions

### 1. `run_smart_validation()`
**Purpose**: Main entry point for validation

**Parameters**:
- `parsed_data_path`: Path to parsed simulation data
- `real_data_path`: Path to measured/real data CSV
- `config`: Configuration dictionary
- `output_path`: Where to save results
- `validate_variants`: Enable variant validation (default: False)

**Returns**: Dictionary with validation results

### 2. `SmartValidationWrapper` Class
**Key Methods**:

#### `discover_available_data()`
- Scans parsed data directory
- Identifies available timeseries files
- Finds comparison files for variants
- Detects zones and aggregation needs

#### `load_and_parse_real_data()`
- Loads measured data CSV
- Handles multiple datetime formats
- Infers units from variable names
- Detects data frequency

#### `load_simulation_data()`
- Loads from timeseries or comparison files
- Handles multi-frequency data
- Supports wide and long formats

#### `align_frequencies()`
- Aligns real and simulated data frequencies
- Aggregates using appropriate methods:
  - Energy variables: sum
  - Temperature variables: mean
  - Power variables: mean

#### `create_variable_mappings()`
- Maps measured variables to simulation variables
- Uses three matching strategies:
  1. **Exact Match**: Variables match exactly
  2. **Fuzzy Match**: Levenshtein distance < 0.8
  3. **Semantic Match**: Pattern-based matching

#### `validate_all()` / `validate_all_variants()`
- Performs actual validation
- Calculates metrics (CVRMSE, NMBE)
- Handles zone aggregation
- Generates results and recommendations

## Configuration Options

### Basic Configuration
```python
config = {
    'target_frequency': 'daily',  # daily, monthly, yearly
    'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
    'cvrmse_threshold': 30,  # ASHRAE Guideline 14
    'nmbe_threshold': 10     # ASHRAE Guideline 14
}
```

### Advanced Configuration
```python
config = {
    'target_frequency': 'monthly',
    'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
    
    # Aggregation settings
    'aggregation': {
        'target_frequency': 'monthly',
        'frequency_mapping': {
            'electricity': 'monthly',
            'heating': 'monthly'
        },
        'methods': {
            'energy': 'sum',
            'temperature': 'mean',
            'power': 'mean'
        }
    },
    
    # Custom thresholds
    'thresholds': {
        'default': {
            'cvrmse': 30.0,
            'nmbe': 10.0
        },
        'by_variable': {
            'temperature': {
                'cvrmse': 15.0,
                'nmbe': 5.0
            }
        }
    },
    
    # Logging options
    'logging': {
        'level': 'INFO',
        'show_mappings': True,
        'show_aggregations': True,
        'show_unit_conversions': True
    },
    
    # Variable mappings
    'variable_mappings': {
        'Custom Name': 'Simulation Variable Name'
    }
}
```

## Test Results

### TEST1_BASIC

**Summary**:
- total_mappings: 3
- successful_validations: 1
- passed_validations: 0
- pass_rate: 0.0
- buildings_validated: 1
- variables_validated: 1
- mapping_types: {'exact': 2, 'semantic': 1, 'fuzzy': 0}
- unit_conversions: 0
- zone_aggregations: 0
- data_issues: 0

**Variable Mappings**:
- Zone Air System Sensible Cooling Energy → Zone Air System Sensible Cooling Energy (confidence: 1.00, type: exact)
- Zone Air System Sensible Heating Energy → Zone Air System Sensible Heating Energy (confidence: 1.00, type: exact)
- Electricity:Facility [J](Hourly) → Electricity:Facility (confidence: 0.64, type: semantic)

**Validation Results**:
- Building 4136733, Electricity:Facility [J](Hourly):
  - CVRMSE: 100.7% (threshold: 30.0%)
  - NMBE: -100.0% (threshold: ±10.0%)
  - Pass: ✗

### TEST2_FREQUENCY

### TEST3_MAPPING

**Summary**:
- total_mappings: 3
- successful_validations: 1
- passed_validations: 0
- pass_rate: 0.0
- buildings_validated: 1
- variables_validated: 1
- mapping_types: {'exact': 0, 'semantic': 3, 'fuzzy': 0}
- unit_conversions: 0
- zone_aggregations: 0
- data_issues: 0

**Variable Mappings**:
- Cooling Energy Usage → Zone Air System Sensible Cooling Energy (confidence: 0.22, type: semantic)
- Heating Energy Usage → Water Heater Heating Energy (confidence: 0.28, type: semantic)
- Total Electricity Consumption → Electricity:Facility (confidence: 0.17, type: semantic)

**Validation Results**:
- Building 4136733, Total Electricity Consumption:
  - CVRMSE: 100.5% (threshold: 30.0%)
  - NMBE: -100.0% (threshold: ±10.0%)
  - Pass: ✗

### TEST4_VARIANTS

**Summary**:
- total_configurations: 20
- configurations_validated: 20
- best_configuration: base
- best_pass_rate: 0.0
- best_cvrmse: 100.3873573805121
- improvements_found: []

### TEST5_WIDE

**Summary**:
- status: No validation results

**Variable Mappings**:
- Zone Air System Sensible Cooling Energy → Zone Air System Sensible Cooling Energy (confidence: 1.00, type: exact)
- Zone Air System Sensible Heating Energy → Zone Air System Sensible Heating Energy (confidence: 1.00, type: exact)
- Electricity:Facility [J](Hourly) → Electricity:Facility (confidence: 0.64, type: semantic)

### TEST6_ADVANCED

**Summary**:
- total_mappings: 4
- successful_validations: 4
- passed_validations: 0
- pass_rate: 0.0
- buildings_validated: 1
- variables_validated: 4
- mapping_types: {'exact': 3, 'semantic': 1, 'fuzzy': 0}
- unit_conversions: 0
- zone_aggregations: 3
- data_issues: 0

**Variable Mappings**:
- Zone Air System Sensible Cooling Energy → Zone Air System Sensible Cooling Energy (confidence: 1.00, type: exact)
- Zone Mean Air Temperature → Zone Mean Air Temperature (confidence: 1.00, type: exact)
- Zone Air System Sensible Heating Energy → Zone Air System Sensible Heating Energy (confidence: 1.00, type: exact)
- Electricity:Facility [J](Hourly) → Electricity:Facility (confidence: 0.64, type: semantic)

**Validation Results**:
- Building 4136733, Zone Air System Sensible Cooling Energy:
  - CVRMSE: 124.1% (threshold: 30.0%)
  - NMBE: -100.0% (threshold: ±10.0%)
  - Pass: ✗
- Building 4136733, Zone Mean Air Temperature:
  - CVRMSE: nan% (threshold: 15.0%)
  - NMBE: nan% (threshold: ±5.0%)
  - Pass: ✗
- Building 4136733, Zone Air System Sensible Heating Energy:
  - CVRMSE: 123.0% (threshold: 30.0%)
  - NMBE: -100.0% (threshold: ±10.0%)
  - Pass: ✗
- Building 4136733, Electricity:Facility [J](Hourly):
  - CVRMSE: 100.8% (threshold: 25.0%)
  - NMBE: -100.0% (threshold: ±10.0%)
  - Pass: ✗

## Output Files Generated

For each validation run, the following files are created:

1. **validation_summary.json**: Complete results in JSON format
2. **validation_results.parquet**: Detailed metrics in Parquet format
3. **validation_results.csv**: Same metrics in CSV format
4. **variable_mappings.csv**: How variables were mapped

## Validation Metrics

### CVRMSE (Coefficient of Variation of Root Mean Square Error)
```
CVRMSE = (RMSE / mean(measured)) × 100%
```
- ASHRAE Guideline 14: < 30% for monthly data

### NMBE (Normalized Mean Bias Error)
```
NMBE = (sum(simulated - measured) / sum(measured)) × 100%
```
- ASHRAE Guideline 14: ±10% for monthly data

## Common Issues and Solutions

1. **No validation results generated**
   - Check date overlap between measured and simulated data
   - Ensure building IDs match

2. **Variable mapping failures**
   - Use explicit variable_mappings in config
   - Check variable names in both datasets

3. **High CVRMSE values**
   - Check unit consistency (J vs kWh)
   - Verify aggregation methods
   - Consider zone aggregation needs

4. **Missing data issues**
   - Ensure complete time series
   - Check for NaN values
   - Verify datetime parsing

