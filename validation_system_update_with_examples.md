# Validation System Update Request with Real Data Examples

## Context
The validation system needs updating to work with the new SQL parsing output structure. The system currently reports "No simulation data found" because it's looking in the wrong directory and expects a different data format.

## Actual Directory Structure

### Current validation system expects:
```
parsed_data/sql_results/timeseries/hourly/*.parquet
parsed_data/sql_results/timeseries/aggregated/daily/*.parquet
```

### Actual structure from SQL parser:
```
parsed_data/
├── timeseries/
│   ├── base_all_daily.parquet       (3 rows × 371 columns)
│   ├── base_all_monthly.parquet     (600 rows × 18 columns)
│   └── base_all_yearly_from_monthly.parquet
└── comparisons/                      (empty for base parsing)

parsed_modified_results/
├── timeseries/
│   └── (similar structure)
└── comparisons/
    ├── var_electricity_facility_na_daily_b4136733.parquet    (365 rows × 26 columns)
    ├── var_zone_mean_air_temperature_na_monthly_b4136733.parquet
    └── ... (30 total comparison files)
```

## Real Data Examples

### 1. Base Daily Data (`parsed_data/timeseries/base_all_daily.parquet`)

**Structure**: Wide format with dates as columns
**Shape**: 3 rows × 371 columns

**Column structure**:
```python
# Metadata columns (first 6):
['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']

# Date columns (365 total):
['2013-01-02', '2013-01-03', '2013-01-04', ..., '2014-01-01']
```

**Actual data rows**:
```
Row 1:
  building_id: '4136733'
  variant_id: 'base'
  VariableName: 'Electricity:Facility'
  category: 'energy_meters'
  Zone: 'Building'
  Units: 'J'
  2013-01-02: 6399384.98
  2013-01-03: 6399384.98
  2013-01-04: 6399384.98
  2013-01-05: 6399384.98
  2013-01-06: 8595361.11

Row 2:
  building_id: '4136737'
  variant_id: 'base'
  VariableName: 'Electricity:Facility'
  category: 'energy_meters'
  Zone: 'Building'
  Units: 'J'
  2013-01-02: 16273552.52
  2013-01-03: 16273552.52
  2013-01-04: 16273552.52
  2013-01-05: 16273552.52
  2013-01-06: 2348478.74
```

### 2. Base Monthly Data (`parsed_data/timeseries/base_all_monthly.parquet`)

**Structure**: Wide format with months as columns
**Shape**: 600 rows × 18 columns

**Variables included** (sample):
- Electricity:Facility
- Cooling:EnergyTransfer
- Heating:EnergyTransfer
- Site Outdoor Air Drybulb Temperature
- Zone Mean Air Temperature
- Surface Inside Face Temperature
- Infiltration Heat Gain/Loss
- Window Heat Gain/Loss

### 3. Variant Comparison Data (`parsed_modified_results/comparisons/var_electricity_facility_na_daily_b4136733.parquet`)

**Structure**: Long format with dates as rows
**Shape**: 365 rows × 26 columns

**Column structure**:
```python
['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units',
 'base_value', 'variant_0_value', 'variant_10_value', 'variant_11_value',
 'variant_12_value', 'variant_13_value', 'variant_14_value', 'variant_15_value',
 'variant_16_value', 'variant_17_value', 'variant_18_value', 'variant_1_value',
 'variant_2_value', 'variant_3_value', 'variant_4_value', 'variant_5_value',
 'variant_6_value', 'variant_7_value', 'variant_8_value', 'variant_9_value']
```

**Actual data rows**:
```
Row 1:
  timestamp: 2013-01-02 00:00:00
  building_id: '4136733'
  Zone: 'Building'
  variable_name: 'Electricity:Facility'
  category: 'energy_meters'
  Units: 'J'
  base_value: 6399384.98
  variant_0_value: 4623530.0   (-27.75%)
  variant_1_value: 5005716.0   (-21.78%)
  variant_2_value: 3857608.0   (-39.72%)
  variant_3_value: 4257536.0   (-33.47%)
  ... (16 more variants)

Row 2:
  timestamp: 2013-01-03 00:00:00
  building_id: '4136733'
  # Same values as Row 1 (typical weekday pattern)
```

## Required Data Transformations

### 1. Transform Wide to Long Format (for base data)

The validation system expects long format:
```python
# Expected format:
columns = ['building_id', 'DateTime', 'Variable', 'Value', 'Units', 'Zone']

# From wide format:
building_id: '4136733'
VariableName: 'Electricity:Facility'
2013-01-02: 6399384.98
2013-01-03: 6399384.98

# To long format:
building_id  DateTime    Variable              Value        Units  Zone
4136733      2013-01-02  Electricity:Facility  6399384.98   J      Building
4136733      2013-01-03  Electricity:Facility  6399384.98   J      Building
```

### 2. Handle Comparison Files (for modified data)

Comparison files are already in long format but need column renaming:
```python
# Current columns in comparison file:
timestamp, building_id, variable_name, base_value, variant_X_value

# Need to transform to:
DateTime, building_id, Variable, Value (selecting appropriate variant)
```

## Files to Update

### 1. `validation/smart_validation_wrapper.py`
**Method**: `discover_available_data()` (lines ~174-257)

**Change**:
```python
# OLD:
ts_path = self.parsed_data_path / 'sql_results' / 'timeseries'
hourly_path = ts_path / 'hourly'
daily_path = ts_path / 'aggregated' / 'daily'

# NEW:
ts_path = self.parsed_data_path / 'timeseries'
# Check for base_all_*.parquet files directly
if (ts_path / 'base_all_daily.parquet').exists():
    available_freqs.add('daily')
if (ts_path / 'base_all_hourly.parquet').exists():
    available_freqs.add('hourly')
if (ts_path / 'base_all_monthly.parquet').exists():
    available_freqs.add('monthly')
```

### 2. `validation/validation_data_loader.py`
**Method**: `load_simulated_data_from_parsed()`

**Change**: Load and transform data from wide to long format
```python
# NEW approach:
if frequency == "daily":
    file_path = self.parsed_data_dir / "timeseries" / "base_all_daily.parquet"
    if file_path.exists():
        df = pd.read_parquet(file_path)
        # Transform from wide to long
        date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}', col)]
        df_long = df.melt(
            id_vars=['building_id', 'VariableName', 'Units', 'Zone'],
            value_vars=date_cols,
            var_name='DateTime',
            value_name='Value'
        )
        df_long['DateTime'] = pd.to_datetime(df_long['DateTime'])
        df_long.rename(columns={'VariableName': 'Variable'}, inplace=True)
```

## Test Validation Data Format

From `test_validation_data/measured_data_parsed_format_daily.csv`:
```csv
building_id,Variable,DateTime,TimeIndex,Value
4136737,Electricity:Facility [J](Hourly),2013-01-01,12.5,16904005313.27
4136737,Zone Air System Sensible Heating Energy,2013-01-01,12.5,12177116397.44
4136737,Zone Air System Sensible Cooling Energy,2013-01-01,12.5,583584013.8
```

Note: The test data includes "[J](Hourly)" in variable names, while parsed data just has the unit in a separate column.

## Success Validation

After updates, running validation should:
1. Find data files at `parsed_data/timeseries/base_all_daily.parquet`
2. Successfully transform from wide to long format
3. Match variables between simulated and measured data
4. Calculate CVRMSE and NMBE metrics
5. Show results like:
   ```
   Validation complete for stage 'baseline':
   - Pass rate: 85.2%
   - Buildings validated: 3
   - Variables validated: 1
   ```

## Additional Notes

1. The system uses a staged validation approach:
   - "baseline" stage runs after parsing
   - "modified" stage runs after modification parsing

2. For modified results, the system should:
   - Use comparison files from `comparisons/` directory
   - Select appropriate variant column based on configuration

3. Variable name matching needs to handle:
   - Test data: "Electricity:Facility [J](Hourly)"
   - Parsed data: "Electricity:Facility" (with Units='J' separately)