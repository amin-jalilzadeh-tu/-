# Validation System Alignment with New SQL Parsing Structure

## Overview
This document details the changes needed to align the validation system with the recent major changes in SQL parsing and time series data generation. The main issue is a structural mismatch between where the SQL parser stores data and where the validation system expects to find it.

## Key Changes in SQL Parsing Structure

### Previous Structure
```
parsed_data/
└── sql_results/
    └── timeseries/
        ├── hourly/
        └── aggregated/
            └── daily/
```

### New Structure
```
parsed_data/
└── timeseries/
    ├── base_all_daily.parquet
    ├── base_all_monthly.parquet
    ├── base_all_monthly_from_daily.parquet
    ├── base_all_yearly_from_daily.parquet
    └── base_all_yearly_from_monthly.parquet
```

## Required Changes

### 1. Update Validation Data Discovery

**File**: `validation/smart_validation_wrapper.py`

**Changes needed in `discover_available_data()` method (lines 174-257)**:
```python
# OLD CODE:
ts_path = self.parsed_data_path / 'sql_results' / 'timeseries'

# NEW CODE:
ts_path = self.parsed_data_path / 'timeseries'
```

**Update frequency detection logic**:
```python
# OLD: Look for hourly/daily subdirectories
# NEW: Look for base_all_{frequency}.parquet files
if (ts_path / 'base_all_hourly.parquet').exists():
    available_freqs.add('hourly')
if (ts_path / 'base_all_daily.parquet').exists():
    available_freqs.add('daily')
if (ts_path / 'base_all_monthly.parquet').exists():
    available_freqs.add('monthly')
```

### 2. Update Data Loading Logic

**File**: `validation/validation_data_loader.py`

**Changes needed in `load_simulated_data_from_parsed()` method**:
```python
# OLD CODE:
if frequency == "hourly":
    data_paths = [self.parsed_data_dir / "sql_results" / "timeseries" / "hourly"]
elif frequency == "daily":
    data_paths = [
        self.parsed_data_dir / "sql_results" / "timeseries" / "aggregated" / "daily",
        self.parsed_data_dir / "sql_results" / "timeseries" / "hourly"
    ]

# NEW CODE:
if frequency == "hourly":
    data_file = self.parsed_data_dir / "timeseries" / "base_all_hourly.parquet"
elif frequency == "daily":
    data_file = self.parsed_data_dir / "timeseries" / "base_all_daily.parquet"
elif frequency == "monthly":
    data_file = self.parsed_data_dir / "timeseries" / "base_all_monthly.parquet"
```

### 3. Handle New Data Format

The new SQL parser creates semi-wide format files where:
- Rows represent building_id + variable combinations
- Columns are dates (e.g., "2013-01-01", "2013-01-02", etc.)
- Metadata columns: building_id, Variable, Units, Zone (if applicable)

**Required transformation**:
```python
def transform_wide_to_long(df):
    """Transform semi-wide format to long format expected by validation."""
    # Identify date columns (format: YYYY-MM-DD)
    date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}', col)]
    
    # Melt the dataframe
    id_vars = ['building_id', 'Variable', 'Units']
    if 'Zone' in df.columns:
        id_vars.append('Zone')
    
    long_df = df.melt(
        id_vars=id_vars,
        value_vars=date_cols,
        var_name='DateTime',
        value_name='Value'
    )
    
    # Convert DateTime to proper datetime
    long_df['DateTime'] = pd.to_datetime(long_df['DateTime'])
    
    return long_df
```

### 4. Update Variant Data Handling

For modified results, the comparison files are stored in:
```
comparisons/
└── var_{variable}_{unit}_{frequency}_b{building_id}.parquet
```

These files contain both base and variant values in wide format with columns like:
- building_id, variant_id, Variable, Units
- Date columns with values
- Comparison columns (base_YYYY-MM-DD, var_YYYY-MM-DD)

### 5. Configuration Updates

**Update validation configuration to support new format**:
```json
{
  "validation": {
    "perform_validation": true,
    "stages": {
      "baseline": {
        "enabled": true,
        "run_after": "parsing",
        "config": {
          "real_data_path": "measured_data.csv",
          "data_format": "semi_wide",  // NEW: Specify data format
          "frequency_mapping": {        // NEW: Map file names to frequencies
            "daily": "base_all_daily.parquet",
            "monthly": "base_all_monthly.parquet"
          }
        }
      },
      "modified": {
        "enabled": true,
        "run_after": "modification_parsing",
        "config": {
          "real_data_path": "measured_data.csv",
          "data_format": "semi_wide",
          "use_comparison_files": true  // NEW: Use comparison files for variants
        }
      }
    }
  }
}
```

## Improved Output Format

### 1. Enhanced Validation Summary
Add more detailed metrics to the validation summary:
```json
{
  "timestamp": "2025-06-29T10:00:00",
  "job_id": "xxx",
  "data_discovery": {
    "parsed_data_found": true,
    "data_format": "semi_wide",
    "frequencies_available": ["daily", "monthly"],
    "buildings_found": ["4136733", "4136737", "4136738"],
    "variables_found": 45,
    "date_range": {
      "start": "2013-01-01",
      "end": "2013-12-31"
    }
  },
  "validation_results": {
    // existing results...
  }
}
```

### 2. Data Quality Report
Add data quality checks:
```python
def generate_data_quality_report(df):
    """Generate data quality metrics for parsed data."""
    return {
        "total_rows": len(df),
        "missing_values": df.isnull().sum().to_dict(),
        "zero_values": (df == 0).sum().to_dict(),
        "negative_values": (df < 0).sum().to_dict(),
        "date_coverage": {
            "expected_days": 365,
            "actual_days": df['DateTime'].nunique(),
            "missing_dates": list(missing_dates)
        },
        "variable_coverage": {
            "expected": list(expected_vars),
            "found": list(found_vars),
            "missing": list(missing_vars)
        }
    }
```

### 3. Visualization Improvements
Generate comparison plots automatically:
```python
def create_validation_plots(real_df, sim_df, output_dir):
    """Create validation comparison plots."""
    for variable in common_variables:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Time series comparison
        ax1.plot(real_df['DateTime'], real_df[variable], label='Measured', alpha=0.7)
        ax1.plot(sim_df['DateTime'], sim_df[variable], label='Simulated', alpha=0.7)
        ax1.set_title(f'{variable} - Time Series Comparison')
        ax1.legend()
        
        # Scatter plot
        ax2.scatter(real_df[variable], sim_df[variable], alpha=0.5)
        ax2.plot([min_val, max_val], [min_val, max_val], 'r--', label='1:1 line')
        ax2.set_xlabel('Measured')
        ax2.set_ylabel('Simulated')
        ax2.set_title(f'{variable} - Scatter Plot')
        
        plt.tight_layout()
        plt.savefig(output_dir / f'{variable}_validation.png')
        plt.close()
```

## Implementation Priority

1. **Critical (Immediate)**:
   - Update data discovery paths in validation system
   - Add wide-to-long format transformation
   - Fix frequency detection logic

2. **High Priority**:
   - Update data loading for new file structure
   - Handle comparison files for variants
   - Add data format detection

3. **Medium Priority**:
   - Enhanced validation summary with data discovery info
   - Data quality reporting
   - Configuration updates for format specification

4. **Low Priority**:
   - Automated visualization generation
   - Performance optimizations for large datasets
   - Additional statistical metrics

## Testing Requirements

1. **Unit Tests**:
   - Test wide-to-long transformation
   - Test new path discovery logic
   - Test frequency detection from file names

2. **Integration Tests**:
   - Test full validation workflow with new data structure
   - Test variant comparison functionality
   - Test aggregation compatibility

3. **Test Data Updates**:
   - Create test files in new semi-wide format
   - Update existing test configurations
   - Add variant comparison test cases

## Migration Guide

For existing projects:
1. Re-run parsing step to generate new format
2. Update validation configurations
3. Clear old parsed_data directories
4. Run validation with new system

## Performance Considerations

The new semi-wide format is more memory-efficient for storage but requires transformation for validation:
- Consider caching transformed data
- Implement lazy loading for large datasets
- Use chunked processing for very large files

## Conclusion

These changes will align the validation system with the new SQL parsing structure while improving output quality and adding better diagnostics. The modular approach allows for gradual implementation based on priority.