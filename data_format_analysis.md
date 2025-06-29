# EnergyPlus Data Format Analysis

## Overview
The project uses two distinct data formats for storing time series data:

1. **Wide Format** (base_all_*.parquet) - Used for base data
2. **Long Format** (var_*.parquet) - Used for comparisons between base and variants

## 1. Wide Format (Base Data)

### File Pattern
- `base_all_daily.parquet`
- `base_all_monthly.parquet`
- `base_all_yearly_from_daily.parquet`
- etc.

### Structure
```
Columns:
- building_id (string)
- variant_id (string) - always 'base' for these files
- VariableName (string) - e.g., 'Electricity:Facility'
- category (string) - e.g., 'energy_meters'
- Zone (string) - e.g., 'Building', 'ZONE_1_FLR_1'
- Units (string) - e.g., 'J', 'W', 'C'
- [date columns] - One column per time period
```

### Example Daily Wide Format
```
building_id | variant_id | VariableName         | category      | Zone     | Units | 2013-01-02 | 2013-01-03 | ...
4136733     | base       | Electricity:Facility | energy_meters | Building | J     | 6399385    | 6399385    | ...
4136737     | base       | Electricity:Facility | energy_meters | Building | J     | 16273550   | 16273550   | ...
```

### Example Monthly Wide Format
```
building_id | variant_id | VariableName                   | category     | Zone         | Units | 2013-02    | 2013-03    | ...
4136733     | base       | Site Outdoor Air Temperature   | site_weather | Environment  | C     | 18.42314   | 21.17717   | ...
4136733     | base       | Cooling:EnergyTransfer         | energy_meters| Building     | J     | 3.775e9    | 4.123e9    | ...
4136733     | base       | Zone Mean Air Temperature      | hvac         | ZONE_1_FLR_1 | C     | 21.17717   | 22.35423   | ...
```

### Characteristics
- **Rows**: One row per (building, variable, zone) combination
- **Columns**: Fixed metadata columns + one column per time period
- **Multi-variable**: Contains ALL variables in a single file
- **Multi-building**: Contains ALL buildings in a single file
- **Date format in columns**: 
  - Daily: 'YYYY-MM-DD'
  - Monthly: 'YYYY-MM'
  - Hourly: 'YYYY-MM-DD_HH'

## 2. Long Format (Comparison Data)

### File Pattern
- `var_{variable}_{unit}_{frequency}_b{building_id}.parquet`
- Example: `var_electricity_facility_na_daily_b4136733.parquet`

### Structure
```
Columns:
- timestamp (datetime64[ns]) - Actual datetime object
- building_id (string)
- Zone (string) - optional, may be missing
- variable_name (string)
- category (string)
- Units (string)
- base_value (float64)
- variant_0_value (float64)
- variant_1_value (float64)
- ... (one column per variant)
```

### Example Long Format
```
timestamp   | building_id | Zone     | variable_name        | category      | Units | base_value | variant_0_value | variant_1_value | ...
2013-01-02  | 4136733     | Building | Electricity:Facility | energy_meters | J     | 6399385    | 5247968         | 5247968         | ...
2013-01-03  | 4136733     | Building | Electricity:Facility | energy_meters | J     | 6399385    | 5247968         | 5247968         | ...
```

### Characteristics
- **Rows**: One row per timestamp
- **Columns**: Fixed structure with base + variant value columns
- **Single variable**: Each file contains only ONE variable
- **Single building**: Each file contains only ONE building
- **Timestamp**: Uses actual datetime objects (stored as milliseconds in parquet)
- **Comparison-ready**: Base and variant values side-by-side

## Key Differences

| Aspect | Wide Format | Long Format |
|--------|-------------|-------------|
| Variables per file | Multiple | Single |
| Buildings per file | Multiple | Single |
| Time representation | Column names | Row values (timestamp) |
| Use case | Base data storage | Variant comparison |
| Row count | Low (variables × zones × buildings) | High (time periods) |
| Column count | High (metadata + time periods) | Low (metadata + value columns) |
| Date storage | String column names | Datetime objects |

## Frequency Handling

Both formats support multiple frequencies:
- **Timestep** (10-minute intervals)
- **Hourly**
- **Daily**
- **Monthly**
- **Yearly**

The data can be aggregated from finer to coarser frequencies:
- Timestep → Hourly → Daily → Monthly → Yearly

## Zone Handling

- Some variables are zone-specific (e.g., Zone Mean Air Temperature)
- Some variables are building-level (e.g., Electricity:Facility)
- Zone column may contain 'Building' for building-level variables

## Variable Naming

Variables follow EnergyPlus naming conventions:
- Energy meters: 'Electricity:Facility', 'Cooling:EnergyTransfer'
- Zone variables: 'Zone Mean Air Temperature', 'Zone Air System Sensible Cooling Rate'
- Surface variables: 'Surface Inside Face Temperature'
- Site variables: 'Site Outdoor Air Drybulb Temperature'

## File Naming Conventions

Wide format:
- `base_all_{frequency}.parquet`
- `base_selected_{frequency}.parquet` (subset of variables)
- `base_all_{to_freq}_from_{from_freq}.parquet` (aggregated)

Long format:
- `var_{variable_sanitized}_{unit}_{frequency}_b{building_id}.parquet`
- Variable names are sanitized (spaces → underscores, special chars removed)
- 'na' is used when units are not applicable