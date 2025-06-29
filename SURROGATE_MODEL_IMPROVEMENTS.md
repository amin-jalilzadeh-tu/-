# Surrogate Model Improvements and Data Structure Alignment

## Overview
This document describes the improvements made to the surrogate modeling pipeline to handle the evolved data structure in the E_Plus_2040_py project.

## Problem Analysis

### Original Issues
1. **Type Error**: The code attempted to check `.empty` on dictionary objects, causing AttributeError
2. **Data Structure Mismatch**: The pipeline expected single DataFrames but received dictionaries of DataFrames for comparison outputs
3. **Missing Data Consolidation**: No mechanism to combine multiple comparison output files into unified features and targets

## Solution Implementation

### 1. Fixed Type Checking Issues

#### In `surrogate_data_extractor.py`:
- Line 111: Changed from `if df is not None and not df.empty:` to `if isinstance(df, pd.DataFrame) and not df.empty:`
- Added proper handling for dictionary data types in quality report generation

### 2. Created Data Consolidator (`surrogate_data_consolidator.py`)

New component that:
- Consolidates dictionary of comparison DataFrames into a single DataFrame
- Creates aligned feature-target matrices from:
  - Modification parameters (features)
  - Energy consumption outputs (targets)
- Handles validation data if available

#### Key Methods:
- `consolidate_comparison_outputs()`: Combines all comparison files
- `create_feature_target_alignment()`: Aligns features with targets based on building_id and variant_id
- `get_validation_data()`: Extracts validation results for model evaluation

### 3. Enhanced Data Preprocessor

Updated `surrogate_data_preprocessor.py` to:
- Check for pre-consolidated data first
- Handle both legacy and new data structures
- Support the new comparison output format

### 4. Updated Unified Surrogate Pipeline

Modified `unified_surrogate.py` to:
- Add consolidation step when comparison_outputs is a dictionary
- Use appropriate target variable names for the new structure
- Pass consolidated data through the preprocessing pipeline

## New Data Flow

```
1. Data Extraction
   ├── Modifications (parameter changes)
   ├── Comparison Outputs (dictionary of DataFrames)
   ├── Sensitivity Rankings
   └── Building Registry

2. Data Consolidation (NEW)
   ├── Combine comparison outputs
   ├── Create feature matrix from modifications
   ├── Create target matrix from outputs
   └── Align features and targets

3. Data Preprocessing
   ├── Use consolidated data if available
   ├── Filter by sensitivity
   ├── Normalize features
   └── Handle categorical variables

4. Model Building
   ├── Train surrogate model
   ├── Evaluate performance
   └── Export model and metadata
```

## Data Structure Examples

### Features DataFrame
```
building_id | variant_id | shading_setpoint | ventilation_rate | dhw_efficiency | ...
------------|------------|------------------|------------------|----------------|----
4136733     | variant_0  | 0.15             | -0.10           | 0.0            | ...
4136733     | variant_1  | 0.0              | 0.20            | 0.10           | ...
```

### Targets DataFrame
```
building_id | variant_id | electricity_yearly | heating_yearly | cooling_yearly | ...
------------|------------|-------------------|----------------|----------------|----
4136733     | variant_0  | 45000.5          | 23000.2       | 18000.7       | ...
4136733     | variant_1  | 43500.3          | 21500.8       | 19200.4       | ...
```

## Configuration Updates

### Surrogate Config Example
```python
surrogate_config = {
    'enabled': True,
    'data_extraction': {},
    'preprocessing': {
        'aggregation_level': 'building',
        'use_sensitivity_filter': True,
        'sensitivity_threshold': 0.1
    },
    'target_variables': [
        'electricity_facility_na_yearly_from_monthly',
        'heating_energytransfer_na_yearly_from_monthly',
        'cooling_energytransfer_na_yearly_from_monthly'
    ],
    'model_type': 'random_forest'
}
```

## Testing

Use `test_surrogate_pipeline.py` to verify:
1. Data extraction works correctly
2. Consolidation produces aligned features and targets
3. Preprocessing handles the new structure
4. Full pipeline executes without errors

## Benefits

1. **Robust Error Handling**: Properly handles different data types
2. **Flexible Data Structure**: Supports both legacy and new formats
3. **Better Data Alignment**: Ensures features and targets match correctly
4. **Validation Integration**: Can use validation results for model evaluation
5. **Scalable Design**: Easy to add new output variables or features

## Future Improvements

1. Add support for time-series features (monthly/daily patterns)
2. Implement cross-validation using building groups
3. Add feature importance analysis
4. Create visualization of model predictions vs actual
5. Implement model versioning and tracking