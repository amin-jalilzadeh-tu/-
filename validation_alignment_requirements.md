# Validation System Alignment Requirements

## Overview

This document details the necessary changes to align the validation system with the recent major changes in SQL parsing and time series data generation in the E+ 2040 workflow.

## Current System Architecture

### 1. SQL Parsing Improvements
- **Enhanced SQL Analyzer**: New implementation extracts time series data directly from EnergyPlus SQL files
- **Categorized Variables**: Variables are now organized into predefined categories (energy, HVAC, lighting, etc.)
- **Multi-frequency Support**: Data is available in hourly, daily, monthly, and yearly aggregations
- **Variant Tracking**: System tracks base buildings vs modified variants

### 2. Time Series Data Structure
```
parsed_data/
├── timeseries/
│   ├── base_all_daily.parquet
│   ├── base_all_monthly.parquet
│   └── base_all_yearly_from_monthly.parquet
├── comparisons/
│   └── var_{variable}_{unit}_{frequency}_b{building_id}.parquet
└── relationships/
    ├── zone_mappings.parquet
    └── equipment_assignments.parquet
```

### 3. Multi-Stage Validation Support
- **Baseline Validation**: After initial parsing
- **Modified Validation**: After modification and re-simulation
- **Comparison Reports**: Automated comparison between stages

## Required Changes for Alignment

### 1. Data Format Compatibility

#### A. Update Measured Data Format
The measured data should align with the new parsed format:

```csv
building_id,Variable,DateTime,TimeIndex,Value
4136737,Electricity:Facility [J](Hourly),2013-01-01,12.5,16904005313.27
```

**Required Changes:**
- Add `TimeIndex` column for EnergyPlus compatibility
- Use full variable names with units and frequency: `Variable [Unit](Frequency)`
- Ensure DateTime format matches: `YYYY-MM-DD`

#### B. Variable Name Mapping
Create a mapping configuration for common variable names:

```json
{
  "variable_mappings": {
    "measured_electricity": "Electricity:Facility [J](Hourly)",
    "measured_heating": "Zone Air System Sensible Heating Energy [J](Hourly)",
    "measured_cooling": "Zone Air System Sensible Cooling Energy [J](Hourly)",
    "measured_temperature": "Zone Mean Air Temperature [C](Hourly)"
  }
}
```

### 2. Validation Configuration Updates

#### A. Multi-Stage Configuration
Update validation configs to support staged validation:

```json
{
  "validation": {
    "perform_validation": true,
    "stages": {
      "baseline": {
        "enabled": true,
        "run_after": "parsing",
        "config": {
          "real_data_path": "measured_data_baseline.csv",
          "thresholds": {
            "cvrmse": 30,
            "nmbe": 10
          }
        }
      },
      "modified": {
        "enabled": true,
        "run_after": "modification_parsing",
        "config": {
          "real_data_path": "measured_data_baseline.csv",
          "thresholds": {
            "cvrmse": 25,
            "nmbe": 8
          }
        }
      }
    }
  }
}
```

#### B. Time Series Aggregation Support
Add support for different time frequencies:

```json
{
  "config": {
    "time_frequency": "daily",
    "aggregation_method": {
      "energy": "sum",
      "temperature": "mean",
      "power": "mean"
    }
  }
}
```

### 3. Data Loading Enhancements

#### A. Smart Data Discovery
The validation system should automatically discover available data:

```python
def discover_simulation_data(parsed_data_dir):
    """Discover available time series data"""
    timeseries_dir = Path(parsed_data_dir) / "timeseries"
    
    # Check for base data at different frequencies
    available_data = {
        "daily": timeseries_dir / "base_all_daily.parquet",
        "monthly": timeseries_dir / "base_all_monthly.parquet",
        "yearly": timeseries_dir / "base_all_yearly_from_monthly.parquet"
    }
    
    return {freq: path for freq, path in available_data.items() if path.exists()}
```

#### B. Zone-Level Validation
Support validation at zone level using relationship data:

```python
def load_zone_relationships(parsed_data_dir):
    """Load zone mapping information"""
    zone_map = pd.read_parquet(parsed_data_dir / "relationships" / "zone_mappings.parquet")
    equipment_map = pd.read_parquet(parsed_data_dir / "relationships" / "equipment_assignments.parquet")
    return zone_map, equipment_map
```

### 4. Validation Workflow Integration

#### A. Automatic Stage Detection
```python
def determine_validation_stage(job_output_dir, current_workflow_step):
    """Determine which validation stage to run"""
    if current_workflow_step == "parsing":
        return "baseline"
    elif current_workflow_step == "modification_parsing":
        return "modified"
    return None
```

#### B. Results Aggregation
Implement comparison between validation stages:

```python
def compare_validation_stages(baseline_results, modified_results):
    """Compare validation metrics between stages"""
    comparison = {
        "cvrmse_improvement": {},
        "nmbe_improvement": {},
        "newly_passing": [],
        "newly_failing": []
    }
    
    # Calculate improvements per variable
    for var in baseline_results:
        if var in modified_results:
            cvrmse_delta = baseline_results[var]["cvrmse"] - modified_results[var]["cvrmse"]
            comparison["cvrmse_improvement"][var] = cvrmse_delta
    
    return comparison
```

### 5. Output Structure Updates

#### A. Validation Results Format
Align output format with new structure:

```
validation_results/
├── baseline/
│   ├── validation_summary.json
│   ├── detailed_results.parquet
│   └── plots/
├── modified/
│   ├── validation_summary.json
│   ├── detailed_results.parquet
│   └── plots/
└── combined_summary.json
```

#### B. Enhanced Summary Reports
Include new metrics in validation summaries:

```json
{
  "summary": {
    "stage": "baseline",
    "timestamp": "2025-06-29T00:00:00",
    "buildings_validated": 3,
    "variables_validated": 4,
    "pass_rate": 75.0,
    "data_frequency": "daily",
    "aggregation_methods_used": {
      "energy": "sum",
      "temperature": "mean"
    },
    "zone_level_validation": true,
    "unit_conversions": 2,
    "missing_data_handling": "interpolation"
  }
}
```

### 6. Test Data Updates

#### A. Create New Test Files
Generate test data matching the new format:

1. **measured_data_timeseries_format.csv**: Daily aggregated data
2. **measured_data_zones.csv**: Zone-level measurements
3. **validation_config_timeseries.json**: Configuration for time series validation
4. **validation_config_zones.json**: Configuration for zone-level validation

#### B. Update Existing Test Files
Modify existing test files to include:
- TimeIndex column
- Full variable names with units
- Multiple frequencies (hourly, daily, monthly)

### 7. Backwards Compatibility

#### A. Legacy Format Support
Maintain support for old data formats:

```python
def detect_data_format(data_df):
    """Detect if data is in legacy or new format"""
    has_timeindex = "TimeIndex" in data_df.columns
    has_units_in_variable = data_df["Variable"].str.contains(r"\[.*\]\(.*\)").any()
    
    if has_timeindex and has_units_in_variable:
        return "new_format"
    return "legacy_format"
```

#### B. Format Conversion
Implement automatic conversion:

```python
def convert_legacy_to_new_format(legacy_df):
    """Convert legacy format to new time series format"""
    # Add TimeIndex
    legacy_df["TimeIndex"] = range(len(legacy_df))
    
    # Update variable names
    variable_mapping = {
        "electricity": "Electricity:Facility [J](Hourly)",
        "heating": "Zone Air System Sensible Heating Energy [J](Hourly)"
    }
    
    legacy_df["Variable"] = legacy_df["Variable"].map(variable_mapping)
    return legacy_df
```

### 8. Implementation Priority

1. **High Priority**
   - Update data loading to handle new parquet format
   - Support multi-stage validation configuration
   - Add time frequency support

2. **Medium Priority**
   - Implement zone-level validation
   - Create comparison reports between stages
   - Update test data files

3. **Low Priority**
   - Enhanced visualization for time series
   - Automated unit conversion
   - Legacy format migration tools

### 9. Testing Strategy

#### A. Unit Tests
- Test parquet file reading
- Test variable name mapping
- Test aggregation methods
- Test stage detection

#### B. Integration Tests
- Full workflow validation with new data
- Multi-stage validation sequence
- Comparison report generation

#### C. Regression Tests
- Ensure legacy format still works
- Verify existing validations pass

### 10. Migration Checklist

- [ ] Update `validation_data_loader.py` to read parquet files
- [ ] Modify `smart_validation_wrapper.py` for multi-stage support
- [ ] Update test data files to new format
- [ ] Create variable name mapping configuration
- [ ] Implement time frequency support
- [ ] Add zone-level validation capability
- [ ] Update validation configurations
- [ ] Create migration guide for users
- [ ] Update documentation
- [ ] Test backwards compatibility

## Conclusion

The validation system requires significant updates to align with the new SQL parsing and time series data structure. The key focus areas are:

1. Supporting the new parquet-based data format
2. Implementing multi-stage validation
3. Adding time series aggregation support
4. Maintaining backwards compatibility

These changes will enable more sophisticated validation workflows while preserving existing functionality.