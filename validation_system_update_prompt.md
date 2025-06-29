# Validation System Update Request

## Context
I need to update the validation system to work with the new SQL parsing output structure. The SQL parser has been recently updated and now stores time series data in a different location and format than what the validation system expects.

## Current Issue
The validation system reports "No simulation data found" even though SQL files exist and have been parsed. This is because the validation system is looking in the wrong directory structure.

## Directory Structure Changes

### What the validation system expects (OLD):
```
parsed_data/
├── sql_results/
│   └── timeseries/
│       ├── hourly/
│       │   └── *.parquet
│       └── aggregated/
│           └── daily/
│               └── *.parquet
```

### What the SQL parser actually creates (NEW):
```
parsed_data/
├── timeseries/
│   ├── base_all_daily.parquet
│   ├── base_all_monthly.parquet
│   ├── base_all_monthly_from_daily.parquet
│   ├── base_all_yearly_from_daily.parquet
│   └── base_all_yearly_from_monthly.parquet
├── comparisons/
│   ├── var_electricity_facility_na_daily_b4136733.parquet
│   ├── var_cooling_energytransfer_na_monthly_b4136733.parquet
│   └── ... (more comparison files)
```

## Actual File Paths (from test run)

### Base simulation data:
- `/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/timeseries/base_all_daily.parquet`
- `/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/timeseries/base_all_monthly.parquet`

### Modified simulation data:
- `/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_modified_results/timeseries/base_all_daily.parquet`
- `/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_modified_results/comparisons/var_electricity_facility_na_daily_b4136733.parquet`

## Data Format

The new SQL parser creates parquet files in a **semi-wide format** where:
- Each row represents a unique combination of building_id + Variable
- Date values are stored as columns (e.g., "2013-01-01", "2013-01-02", etc.)
- Metadata columns include: building_id, variable_source, Variable, category, Zone, Units

### Example of data structure needed:
```
Columns in base_all_daily.parquet:
- building_id (str): "4136733"
- variable_source (str): "base"
- Variable (str): "Electricity:Facility"
- category (str): "energy_meters"
- Zone (str): "Building" or specific zone name
- Units (str): "J"
- 2013-01-01 (float): 123456789.0
- 2013-01-02 (float): 234567890.0
- ... (365 date columns for daily data)
```

## Files That Need Updating

### 1. `validation/smart_validation_wrapper.py`
- Method: `discover_available_data()` (around lines 174-257)
- Current code looks for: `self.parsed_data_path / 'sql_results' / 'timeseries'`
- Should look for: `self.parsed_data_path / 'timeseries'`

### 2. `validation/validation_data_loader.py`
- Method: `load_simulated_data_from_parsed()`
- Current code expects subdirectories like `hourly/` and `aggregated/daily/`
- Should load files like `base_all_daily.parquet` directly

### 3. Data transformation needed
The validation system expects long format data with columns:
- building_id
- DateTime
- Variable
- Value
- Units
- Zone (optional)

But the new format has dates as columns, so we need to transform from wide to long format.

## Test Data Information

### Measured data format (what validation compares against):
Example from `/data/test_validation_data/measured_data_parsed_format_daily.csv`:
```csv
building_id,Variable,DateTime,TimeIndex,Value
4136737,Electricity:Facility [J](Hourly),2013-01-01,12.5,16904005313.27
4136737,Zone Air System Sensible Heating Energy,2013-01-01,12.5,12177116397.44
```

### SQL files location (source data):
- Base results: `/output/85e39910-c928-4383-b9b0-be2b945e2b48/Sim_Results/2020/simulation_bldg0_4136733.sql`
- Modified results: `/output/85e39910-c928-4383-b9b0-be2b945e2b48/Modified_Sim_Results/2020/simulation_bldg0_4136733.sql`

## Required Changes Summary

1. Update path discovery logic to look in `timeseries/` instead of `sql_results/timeseries/`
2. Update file loading to read `base_all_{frequency}.parquet` files directly
3. Add transformation from semi-wide format (dates as columns) to long format (dates as rows)
4. Handle comparison files in the `comparisons/` directory for variant analysis
5. Update frequency detection to check for file existence rather than directory existence

## Validation Configuration
The validation is configured with stages:
- "baseline": runs after "parsing" step
- "modified": runs after "modification_parsing" step

Each stage needs to know where to find its parsed data:
- Baseline: `job_output_dir/parsed_data/timeseries/`
- Modified: `job_output_dir/parsed_modified_results/timeseries/`

## Success Criteria
After the updates, the validation system should:
1. Successfully find and load the parsed SQL data
2. Transform it to the expected format
3. Compare it with measured data
4. Generate validation metrics (CVRMSE, NMBE, etc.)
5. Not report "No simulation data found" when data exists

Please update the validation system to work with this new data structure and format.