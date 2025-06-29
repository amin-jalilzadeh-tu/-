# EnergyPlus Time Series Data Structure Analysis Prompt

## Overview
This document provides a comprehensive understanding of the time series data structures output from the EnergyPlus 2040 Python workflow, focusing on how building energy simulation data is organized, modified, and compared across different analysis stages.

## System Architecture

### 1. Data Processing Pipeline
The workflow follows this sequence:
```
IDF Creation → Base Simulation → Parsing → Modification → Modified Simulation → Comparison Analysis
```

### 2. Key Components
- **IDF Files**: EnergyPlus input data format describing building geometry, materials, and systems
- **SQL Files**: Simulation output databases containing time series results
- **Parquet Files**: Columnar storage format for efficient time series analysis

## Time Series Data Structures

### 1. Base Time Series Data (`parsed_data/timeseries/`)

#### Wide Format Structure
The base simulation results are stored in wide format parquet files:

**File Types:**
- `base_all_daily.parquet` - Daily resolution (365 columns for dates)
- `base_all_monthly.parquet` - Monthly aggregated (12 columns)
- `base_all_yearly_from_daily.parquet` - Annual totals from daily
- `base_all_yearly_from_monthly.parquet` - Annual totals from monthly

**Schema:**
```
| Column Type | Columns | Description |
|-------------|---------|-------------|
| Metadata | building_id | Unique building identifier |
| | variant_id | Always "base" for original simulations |
| | VariableName | EnergyPlus output variable name |
| | category | Variable category (e.g., "energy", "temperature") |
| | Zone | Zone name or "building" for whole-building metrics |
| | Units | Engineering units (J, C, W, etc.) |
| Data | 2013-01-02...2014-01-01 | Date columns with numeric values |
```

**Example Row:**
```
building_id: "4136733"
variant_id: "base"
VariableName: "Electricity:Facility [J](Daily)"
category: "energy"
Zone: "building"
Units: "J"
2013-01-02: 1234567.89
2013-01-03: 1345678.90
...
```

### 2. Modification Tracking Data (`modified_idfs/`)

#### Long Format Structure
Modifications are tracked in long format for detailed analysis:

**File: `modifications_detail_long_YYYYMMDD_HHMMSS.parquet`**

**Schema:**
```python
{
    'timestamp': 'string',              # ISO format timestamp
    'building_id': 'string',            # Building identifier
    'variant_id': 'string',             # variant_0, variant_1, etc.
    'parameter_scope': 'object',        # building/zone level
    'zone_name': 'object',              # Specific zone if applicable
    'category': 'category',             # materials, hvac, lighting, etc.
    'object_type': 'category',          # IDF object type
    'object_name': 'string',            # IDF object name
    'parameter': 'string',              # Combined category_field
    'field': 'string',                  # IDF field name
    'original_value': 'string',         # Original parameter value
    'new_value': 'string',              # Modified parameter value
    'original_value_numeric': 'float64', # Numeric original (if applicable)
    'new_value_numeric': 'float64',     # Numeric new (if applicable)
    'change_type': 'category',          # absolute, percentage, multiplier
    'change_percentage': 'float64',     # Percent change
    'rule_applied': 'string',           # Modification rule/strategy
    'action': 'category',               # modify, add, delete
    'scenario': 'string',               # Scenario identifier
    'modifier': 'category',             # Which modifier class
    'validation_status': 'category',    # valid, warning, error
    'success': 'bool',                  # Success flag
    'message': 'string'                 # Additional messages
}
```

#### Wide Format Structure
For easier cross-variant comparison:

**File: `modifications_detail_wide_YYYYMMDD_HHMMSS.parquet`**

**Schema:**
```
| Metadata Columns | Variant Columns |
|------------------|-----------------|
| building_id | original |
| parameter_scope | variant_0 |
| zone_name | variant_1 |
| category | ... |
| object_type | variant_18 |
| object_name | |
| field | |
| change_type | |
```

### 3. Comparison Time Series (`parsed_modified_results/comparisons/`)

#### Long Format Comparison Structure
Comparison files show base vs. variant values:

**File Pattern:** `var_{metric}_{category}_na_{resolution}_b{building_id}.parquet`

**Examples:**
- `var_electricity_facility_na_monthly_b4136733.parquet`
- `var_zone_mean_air_temperature_zone_na_daily_b4136737.parquet`

**Schema:**
```python
{
    'timestamp': 'datetime64[ns]',     # Time point
    'building_id': 'string',           # Building identifier
    'Zone': 'string',                  # Zone name
    'variable_name': 'string',         # Full variable name
    'category': 'string',              # Variable category
    'Units': 'string',                 # Engineering units
    'base_value': 'float64',           # Original simulation value
    'variant_0_value': 'float64',      # Variant 0 value
    'variant_1_value': 'float64',      # Variant 1 value
    ...
    'variant_18_value': 'float64'      # Variant 18 value
}
```

### 4. Variable Categories and Types

**Energy Variables:**
- `electricity_facility` - Whole building electricity [J]
- `cooling_energytransfer` - Cooling energy transfer [J]
- `heating_energytransfer` - Heating energy transfer [J]

**Temperature Variables:**
- `zone_mean_air_temperature` - Zone air temperature [C]
- `surface_inside_face_temperature` - Interior surface temp [C]
- `surface_outside_face_temperature` - Exterior surface temp [C]

**HVAC Variables:**
- `zone_air_system_sensible_cooling_rate` - Cooling rate [W]
- `zone_air_system_sensible_heating_rate` - Heating rate [W]
- `zone_mechanical_ventilation_mass_flow_rate` - Ventilation [kg/s]

**Solar Variables:**
- `site_diffuse_solar_radiation_rate_per_area` - Solar radiation [W/m2]
- `surface_window_transmitted_solar_radiation_rate` - Window solar [W]

**Window Variables:**
- `surface_window_heat_gain_rate` - Window heat gain [W]
- `surface_window_blind_slat_angle` - Blind angle [deg]

### 5. Temporal Aggregation Patterns

**Aggregation Hierarchy:**
```
Sub-hourly → Hourly → Daily → Monthly → Yearly
```

**Aggregation Methods by Variable Type:**
- **Energy (J)**: Sum over period
- **Power (W)**: Average over period
- **Temperature (C)**: Average over period
- **Rates (kg/s, W/m2)**: Average over period

### 6. Zone Hierarchy

Buildings contain multiple zones:
```
Building
├── ZONE1_CORE
├── ZONE1_FRONTPERIMETER
├── ZONE1_BACKPERIMETER
├── ZONE1_LEFTPERIMETER
├── ZONE1_RIGHTPERIMETER
└── ... (additional zones)
```

## Data Access Patterns

### 1. Finding Base Performance
```python
# Load base daily data
base_data = pd.read_parquet('parsed_data/timeseries/base_all_daily.parquet')
# Filter for specific building and variable
building_energy = base_data[
    (base_data['building_id'] == '4136733') & 
    (base_data['VariableName'].str.contains('Electricity:Facility'))
]
```

### 2. Comparing Variants
```python
# Load comparison file
comparisons = pd.read_parquet(
    'parsed_modified_results/comparisons/var_electricity_facility_na_monthly_b4136733.parquet'
)
# Calculate percent changes
for i in range(19):
    comparisons[f'variant_{i}_pct_change'] = (
        (comparisons[f'variant_{i}_value'] - comparisons['base_value']) / 
        comparisons['base_value'] * 100
    )
```

### 3. Tracking Modifications
```python
# Load modification details
mods = pd.read_parquet('modified_idfs/modifications_detail_long_20250629_120407.parquet')
# Find HVAC modifications for a building
hvac_mods = mods[
    (mods['building_id'] == '4136733') & 
    (mods['category'] == 'hvac')
]
```

## Key Insights for Analysis

1. **Data Granularity**: Zone-level data provides spatial detail within buildings
2. **Variant Tracking**: Up to 19 variants (0-18) per building for sensitivity analysis
3. **Time Resolution**: Multiple temporal aggregations support different analysis needs
4. **Parameter Linking**: Modification tracking connects input changes to output impacts
5. **Efficiency**: Parquet format enables fast queries on large time series datasets

## Common Analysis Tasks

1. **Energy Savings Calculation**: Compare base vs. variant energy consumption
2. **Peak Load Analysis**: Identify maximum heating/cooling demands
3. **Comfort Analysis**: Evaluate temperature distributions across zones
4. **Sensitivity Ranking**: Determine which parameters most affect outcomes
5. **Temporal Patterns**: Identify seasonal or daily usage patterns

This structure supports comprehensive building performance analysis from individual parameter changes through whole-building annual metrics.