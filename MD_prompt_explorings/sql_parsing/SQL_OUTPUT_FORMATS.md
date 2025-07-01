# SQL Output Formats and Parquet Structures

## Overview

The SQL parsing system produces various output formats optimized for different use cases. All outputs are stored as Parquet files for efficient storage and fast querying.

## Time Series Data Formats

### 1. Semi-Wide Format (Base Data)

**Purpose**: Efficient storage and retrieval of base simulation results  
**Location**: `timeseries/base_all_{frequency}.parquet`

**Structure**:
```
| building_id | variant_id | VariableName | category | Zone | Units | 2020-01-01 | 2020-01-02 | ... |
|-------------|------------|--------------|----------|------|-------|------------|------------|-----|
| 1001        | base       | Zone Air Temperature | geometry | CORE_ZN | C | 21.5 | 22.1 | ... |
| 1001        | base       | Electricity:Facility | energy_meters | Building | J | 1.2e8 | 1.3e8 | ... |
```

**Key Features**:
- Dates as columns for efficient time-based queries
- All variables for a building in one file
- Preserves original reporting frequency
- Includes metadata (category, units, zone)

**Date Column Formats**:
- Hourly: `YYYY-MM-DD_HH` (e.g., "2020-01-01_14")
- Daily: `YYYY-MM-DD` (e.g., "2020-01-01")
- Monthly: `YYYY-MM` (e.g., "2020-01")
- Yearly: `YYYY` (e.g., "2020")

### 2. Long Format (Raw Time Series)

**Purpose**: Intermediate format during processing  
**Location**: Temporary during processing

**Structure**:
```
| DateTime           | Variable             | Zone    | Value | Units | ReportingFrequency | building_id | variant_id | category |
|--------------------|---------------------|---------|-------|-------|-------------------|-------------|------------|----------|
| 2020-01-01 00:00  | Zone Air Temperature | CORE_ZN | 21.5  | C     | Hourly           | 1001        | base       | geometry |
| 2020-01-01 01:00  | Zone Air Temperature | CORE_ZN | 21.3  | C     | Hourly           | 1001        | base       | geometry |
```

**Key Features**:
- Standard time series format
- Easy to filter and aggregate
- Includes full metadata per row
- Used for transformations

### 3. Comparison Format (Variants)

**Purpose**: Compare base vs variant results for individual variables  
**Location**: `comparisons/var_{variable}_{unit}_{frequency}_b{building_id}.parquet`

**Structure**:
```
| DateTime    | Zone    | category | Units | base_value | variant_0_value | variant_1_value | variant_2_value |
|-------------|---------|----------|-------|------------|-----------------|-----------------|-----------------|
| 2020-01-01  | CORE_ZN | geometry | C     | 21.5       | 20.8            | 22.3            | 21.1            |
| 2020-01-02  | CORE_ZN | geometry | C     | 22.1       | 21.4            | 22.9            | 21.7            |
```

**Key Features**:
- One file per variable per building
- All variants in columns for easy comparison
- Facilitates delta calculations
- Zone-level granularity preserved

**Filename Convention**:
- Variable name cleaned (lowercase, underscores)
- Unit extracted and included
- Frequency specified
- Building ID appended
- Example: `var_zone_air_temperature_c_daily_b1001.parquet`

## Static Data Formats

### 4. Performance Summary Tables

**Location**: `performance_summaries/`

#### Energy End Uses
**File**: `energy_end_uses.parquet`
```
| building_id | variant_id | EndUse    | Electricity | Natural Gas | District Cooling | Total |
|-------------|------------|-----------|-------------|-------------|------------------|-------|
| 1001        | base       | Heating   | 0.0         | 5.2e9       | 0.0             | 5.2e9 |
| 1001        | base       | Cooling   | 3.8e9       | 0.0         | 0.0             | 3.8e9 |
| 1001        | base       | Lighting  | 2.1e9       | 0.0         | 0.0             | 2.1e9 |
```

#### Site Source Summary
**File**: `site_source_summary.parquet`
```
| building_id | variant_id | Metric               | Value    | Units |
|-------------|------------|---------------------|----------|-------|
| 1001        | base       | Total Site Energy   | 1.5e10   | J     |
| 1001        | base       | Total Source Energy | 4.2e10   | J     |
| 1001        | base       | Site EUI            | 125.5    | kWh/m² |
```

#### Comfort Metrics
**File**: `comfort_metrics.parquet`
```
| building_id | variant_id | Zone    | Hours_Heat_Not_Met | Hours_Cool_Not_Met |
|-------------|------------|---------|-------------------|-------------------|
| 1001        | base       | CORE_ZN | 12                | 8                 |
| 1001        | base       | PERIM_ZN| 15                | 10                |
```

### 5. Sizing Results

**Location**: `sizing_results/`

#### Zone Sizing
**File**: `zone_sizing.parquet`
```
| building_id | variant_id | ZoneName | CoolingDesignLoad | HeatingDesignLoad | CoolingDesignAirFlow |
|-------------|------------|----------|-------------------|-------------------|---------------------|
| 1001        | base       | CORE_ZN  | 45000            | 32000            | 1.2                |
```

#### System Sizing
**File**: `system_sizing.parquet`
```
| building_id | variant_id | SystemName | CoolingDesignCapacity | HeatingDesignCapacity |
|-------------|------------|-----------|----------------------|----------------------|
| 1001        | base       | VAV_1     | 125000              | 95000               |
```

### 6. Building Characteristics

**Location**: `building_characteristics/`

#### Zone Properties
**File**: `zone_properties.parquet`
```
| building_id | variant_id | ZoneName | FloorArea | Volume | CeilingHeight | window_wall_ratio |
|-------------|------------|----------|-----------|--------|---------------|-------------------|
| 1001        | base       | CORE_ZN  | 500.0     | 1500.0 | 3.0          | 0.0              |
| 1001        | base       | PERIM_ZN | 300.0     | 900.0  | 3.0          | 0.4              |
```

#### Construction Details
**File**: `construction_details.parquet`
```
| building_id | variant_id | ConstructionName | LayerIndex | MaterialName | Thickness | Conductivity |
|-------------|------------|-----------------|------------|--------------|-----------|--------------|
| 1001        | base       | ExtWall         | 1          | Brick        | 0.1       | 0.9         |
| 1001        | base       | ExtWall         | 2          | Insulation   | 0.05      | 0.04        |
```

## Metadata Formats

### 7. Validation Results

**File**: `metadata/validation_results.parquet`
```
| building_id | variant_id | total_requested | found | coverage | timestamp |
|-------------|------------|----------------|-------|----------|-----------|
| 1001        | base       | 25             | 23    | 92.0     | 2024-01-15T10:30:00 |
| 1001        | variant_0  | 25             | 23    | 92.0     | 2024-01-15T10:31:00 |
```

### 8. Simulation Info

**File**: `metadata/simulation_info.parquet`
```
| building_id | variant_id | Version | TimeStamp | NumTimesteps | CompletedSuccessfully |
|-------------|------------|---------|-----------|--------------|---------------------|
| 1001        | base       | 23.2.0  | 2024-01-15T10:00:00 | 8760 | 1 |
```

## Data Type Specifications

### Numeric Precision
- **Energy values**: Float64 (maintain full precision)
- **Temperatures**: Float32 (sufficient for 0.01°C precision)
- **Percentages**: Float32
- **Counts**: Int32 or Int64 as needed

### String Handling
- **Building IDs**: String (supports various formats)
- **Variant IDs**: String (e.g., "base", "variant_0")
- **Zone names**: String (preserve original casing)
- **Variable names**: String (exact EnergyPlus names)

### DateTime Formats
- **Time series**: ISO 8601 format strings or pandas datetime64
- **Timestamps**: ISO 8601 with timezone when applicable

## Compression and Optimization

### Parquet Settings
- **Compression**: Snappy (default) or gzip for archival
- **Row group size**: Optimized for typical query patterns
- **Column encoding**: Dictionary encoding for repeated strings

### Performance Optimizations
- **Partitioning**: By building_id for large datasets
- **Sorting**: Time series sorted by DateTime
- **Indexing**: Building and variant IDs for fast filtering

## Query Examples

### Load Base Data for Specific Variable
```python
import pandas as pd

# Load daily temperature data
df = pd.read_parquet('timeseries/base_all_daily.parquet')
temp_data = df[df['VariableName'] == 'Zone Air Temperature']
```

### Compare Variants
```python
# Load comparison file
comp_df = pd.read_parquet('comparisons/var_zone_air_temperature_c_daily_b1001.parquet')

# Calculate differences
comp_df['delta_v0'] = comp_df['variant_0_value'] - comp_df['base_value']
comp_df['pct_change_v0'] = (comp_df['delta_v0'] / comp_df['base_value']) * 100
```

### Aggregate Performance Metrics
```python
# Load end uses across buildings
end_uses = pd.read_parquet('performance_summaries/energy_end_uses.parquet')

# Sum by variant
variant_totals = end_uses.groupby('variant_id')['Total'].sum()
```

## Best Practices

1. **Memory Management**
   - Use chunked reading for large files
   - Filter early in the query chain
   - Use appropriate data types

2. **File Organization**
   - Maintain consistent naming conventions
   - Document any schema changes
   - Version control metadata files

3. **Data Validation**
   - Check for missing values
   - Validate units consistency
   - Verify time continuity

4. **Performance**
   - Use columnar selection in queries
   - Leverage Parquet's predicate pushdown
   - Consider partitioning for very large datasets