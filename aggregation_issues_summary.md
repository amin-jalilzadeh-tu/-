# Validation System Aggregation Issues

## Overview
The validation system's aggregation functionality is not working properly for both base and comparison data. The system fails to properly detect frequencies and aggregate data when needed.

## Key Issues Identified

### 1. **Format Mismatch**
- **Base data**: Stored in WIDE format (dates as columns)
  - Example: `base_all_daily.parquet` has 365 date columns
- **Comparison data**: Stored in LONG format (dates as rows)  
  - Example: `var_electricity_facility_na_daily_b4136733.parquet` has timestamp rows
- The system needs different handling logic for each format

### 2. **Missing Hourly Data**
- No `base_all_hourly.parquet` file exists
- The system expects hourly data to aggregate to daily: 
  ```python
  if sim_freq == 'hourly' and target == 'daily':
      logger.info("  - Aggregating hourly simulation data to daily...")
  ```
- Only pre-aggregated daily/monthly data is available
- The SQL parser directly creates aggregated files, not raw hourly

### 3. **Frequency Detection Failure**
The `_detect_frequency()` method expects a DateTime column:
```python
if 'DateTime' not in df.columns or len(df) < 2:
    return 'unknown'
```
But wide format data has dates as column names, not a DateTime column.

### 4. **Data Loading Logic Issues**
In `load_simulation_data()`:
```python
if 'hourly' in dataset_name or dataset_info.get('frequency') == 'hourly':
```
Problems:
- Files are named `base_all_daily.parquet`, not containing "hourly"
- The discovery correctly identifies frequency but loading logic doesn't use it properly
- No hourly files exist to load

### 5. **Unnecessary Aggregation Attempts**
After converting wide to long format:
- Data that is already daily gets converted to long format with one row per day
- System then tries to aggregate daily data to daily (unnecessary)
- The aggregation logic assumes it's aggregating hourly to daily

### 6. **Comparison Files Frequency Handling**
The comparison files include frequency in filename but:
- Only daily and monthly files are loaded based on target frequency
- No logic to aggregate monthly to daily or vice versa
- Example: `var_electricity_facility_na_monthly_b4136733.parquet` has 365 rows (should be 12)

## Data Structure Examples

### Base Data (Wide Format)
```
base_all_daily.parquet:
- Columns: building_id, variant_id, VariableName, category, Zone, Units, 2013-01-02, 2013-01-03, ...
- 3 rows (one per building)
- 365 date columns
```

### Comparison Data (Long Format)
```
var_electricity_facility_na_daily_b4136733.parquet:
- Columns: timestamp, building_id, Zone, variable_name, category, Units, base_value, variant_0_value, ...
- 365 rows (one per day)
- timestamp column with datetime values
```

## Proposed Solutions

### 1. **Fix Frequency Detection**
Create a new method to detect frequency from wide format:
```python
def _detect_frequency_wide(self, df: pd.DataFrame) -> str:
    """Detect frequency from wide format data"""
    date_cols = [col for col in df.columns if self._is_date_column(col)]
    if len(date_cols) < 2:
        return 'unknown'
    
    # Parse dates and check intervals
    dates = pd.to_datetime(date_cols[:10])
    # Check if daily, monthly, etc.
```

### 2. **Update Data Loading**
- Check filename for frequency hints: `base_all_daily`, `base_all_monthly`
- Load appropriate file based on target frequency
- Don't expect hourly data if it doesn't exist

### 3. **Smart Aggregation**
- Check if data is already at target frequency before aggregating
- Handle both wide and long formats appropriately
- Add support for monthly->daily disaggregation if needed

### 4. **Unified Frequency Handling**
- Store frequency info during discovery
- Use discovered frequency instead of detecting from data
- Handle missing frequencies gracefully

### 5. **Fix Comparison File Loading**
- Load all available frequencies from comparison files
- Aggregate/disaggregate as needed to match target frequency
- Handle the mixed daily/monthly data properly

## Impact
These issues prevent the validation system from:
- Properly comparing data at different frequencies
- Utilizing monthly aggregated data when daily isn't available
- Handling the new SQL parser output format correctly
- Validating variants when only aggregated data exists