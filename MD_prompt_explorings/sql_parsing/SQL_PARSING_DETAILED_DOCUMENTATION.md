# SQL Parsing System - Detailed Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Input/Output Flow](#inputoutput-flow)
3. [Core Components](#core-components)
4. [Data Extraction Process](#data-extraction-process)
5. [Parameters Extracted](#parameters-extracted)
6. [Output Structures](#output-structures)
7. [Integration with Other Systems](#integration-with-other-systems)
8. [File Naming Conventions](#file-naming-conventions)
9. [Performance Optimizations](#performance-optimizations)

## System Overview

The SQL parsing system is designed to extract and process comprehensive simulation results from EnergyPlus SQLite database files. It handles two primary workflows:

1. **Base Simulations**: Initial IDF creation results stored in `Sim_Results/`
2. **Modified Simulations**: Parameter-tweaked results stored in `Modified_Sim_Results/`

### Key Capabilities
- Automatic building and variant identification
- Time series data extraction with frequency preservation
- Static/summary data extraction (performance metrics, sizing, characteristics)
- Schedule extraction and analysis
- Base vs. variant comparison generation
- Multi-frequency aggregation (upward only)
- Validation support for requested outputs

## Input/Output Flow

### Input Structure
```
Job_Output_Directory/
├── Sim_Results/                    # Base simulations
│   └── 2020/
│       ├── simulation_bldg0_1001.sql
│       ├── simulation_bldg1_1002.sql
│       └── ...
└── Modified_Sim_Results/           # Variant simulations
    └── 2020/
        ├── simulation_bldg0_1001.sql  # variant_0 of building 1001
        ├── simulation_bldg1_1001.sql  # variant_1 of building 1001
        └── ...
```

### Output Structure
```
parsed_data/                        # Base results
├── timeseries/
│   ├── base_all_hourly.parquet
│   ├── base_all_daily.parquet
│   └── base_all_monthly.parquet
├── performance_summaries/
├── sizing_results/
├── building_characteristics/
├── metadata/
└── schedules/

parsed_modified_results/            # Variant results
├── timeseries/
├── comparisons/                    # Base vs. variant comparisons
│   ├── var_zone_air_temperature_c_daily_b1001.parquet
│   └── ...
└── [same structure as base]
```

## Core Components

### 1. SQL Analyzer Main (`sql_analyzer_main.py`)
**Primary Coordinator Module**

**Responsibilities:**
- Orchestrates the entire SQL analysis workflow
- Identifies base buildings from output_IDFs directory
- Manages multiple SQL file processing
- Coordinates validation of requested outputs
- Handles base/variant separation logic

**Key Methods:**
- `analyze_sql_files()`: Main entry point for processing
- `_identify_base_buildings()`: Determines which buildings are base
- `_validate_outputs()`: Checks if requested variables exist
- `get_analysis_summary()`: Provides processing statistics

### 2. Enhanced SQL Analyzer (`sql_analyzer.py`)
**Time Series Data Extractor**

**Responsibilities:**
- Connects to SQLite databases
- Extracts time series data by category
- Handles building/variant ID extraction
- Categorizes variables automatically

**Key Features:**
- Variable categorization into 12 categories
- Frequency-aware extraction
- Date/time handling (including Hour=24 edge case)
- Cache for repeated queries

**Categories Defined:**
```python
SQL_CATEGORY_MAPPINGS = {
    'energy_meters': [...],      # Electricity, gas, district energy
    'site_weather': [...],       # Outdoor conditions
    'geometry': [...],           # Zone temperatures, humidity
    'materials': [...],          # Surface heat transfer
    'dhw': [...],               # Domestic hot water
    'equipment': [...],          # Internal gains
    'lighting': [...],           # Lighting and daylighting
    'hvac': [...],              # HVAC operation
    'ventilation': [...],        # Air flow rates
    'infiltration': [...],       # Air leakage
    'shading': [...]            # Solar control
}
```

### 3. SQL Data Manager (`sql_data_manager.py`)
**Data Storage and Transformation Module**

**Responsibilities:**
- Manages data storage structure
- Transforms between data formats (long ↔ semi-wide)
- Creates frequency aggregations
- Generates base/variant comparisons

**Key Transformations:**
1. **Long to Semi-Wide**: Pivots time series with dates as columns
2. **Frequency Aggregation**: Hourly → Daily → Monthly
3. **Comparison Format**: Aligns base and variant values by timestamp

**Aggregation Rules:**
- Energy variables: Sum
- Temperature/rate variables: Mean
- Only upward aggregation (no data interpolation)

### 4. SQL Static Extractor (`sql_static_extractor.py`)
**Non-Time Series Data Extractor**

**Responsibilities:**
- Extracts performance summaries from TabularData
- Retrieves sizing results (zones, systems, components)
- Collects building characteristics
- Gathers simulation metadata

**Data Categories:**
1. **Performance Summaries**
   - Energy end uses by fuel type
   - Site and source energy
   - Comfort metrics (hours not met)
   - Energy intensity (per floor area)
   - Peak demands

2. **Sizing Results**
   - Zone heating/cooling loads
   - System capacities
   - Component sizes

3. **Building Characteristics**
   - Envelope properties
   - Construction layers and materials
   - Zone geometry and properties
   - Window-wall ratios

4. **Equipment Loads**
   - Nominal electric/gas equipment
   - Design infiltration/ventilation rates

### 5. Schedule Extractor (`sql_schedule_extractor.py`)
**Schedule Analysis Module**

**Responsibilities:**
- Extracts schedule definitions
- Maps schedule usage to equipment
- Analyzes schedule patterns
- Extracts typical day profiles

**Output:**
- Schedule metadata (min/max values)
- Schedule usage mapping
- Pattern analysis (constant, lighting, HVAC, etc.)
- Typical day profiles for seasonal analysis

## Data Extraction Process

### Step 1: Initialization
```python
# Building/Variant identification from filename
# Pattern: simulation_bldg{index}_{building_id}.sql
if in Modified_Sim_Results:
    variant_id = f'variant_{bldg_index}'
else:
    variant_id = 'base'
```

### Step 2: Time Series Extraction
```sql
-- Core extraction query
SELECT 
    DateTime (with Hour=24 handling),
    Variable Name,
    Zone/Key,
    Value,
    Units,
    ReportingFrequency
FROM ReportData
JOIN Time ON TimeIndex
JOIN ReportDataDictionary ON Index
WHERE EnvironmentType = 3  -- Weather file periods only
```

### Step 3: Data Transformation
1. **Raw Data Collection** → Temporary storage
2. **Frequency Grouping** → Separate by reporting frequency
3. **Format Conversion** → Long to semi-wide format
4. **Aggregation** → Create higher frequency summaries

### Step 4: Comparison Generation (Variants Only)
1. Load base data for building
2. Align variant data by timestamp and zone
3. Create per-variable comparison files
4. Include all variants in single file

### Step 5: Static Data Extraction
- Performance summaries from TabularData
- Direct table queries for sizing/characteristics
- Metadata collection

## Parameters Extracted

### Time Series Variables (by Category)

#### Energy Meters
- `Electricity:Facility`, `Electricity:Building`, `Electricity:HVAC`
- `Gas:Facility`, `Gas:Building`
- `DistrictCooling:Facility`, `DistrictHeating:Facility`
- `Cooling:EnergyTransfer`, `Heating:EnergyTransfer`

#### Site Weather
- `Site Outdoor Air Drybulb/Wetbulb Temperature`
- `Site Outdoor Air Relative Humidity`
- `Site Wind Speed/Direction`
- `Site Solar Radiation` (Direct/Diffuse)
- `Site Rain Status`, `Site Snow Depth`

#### Zone Conditions (Geometry)
- `Zone Air Temperature`, `Zone Operative Temperature`
- `Zone Mean Radiant Temperature`
- `Zone Air Relative Humidity`, `Zone Air Humidity Ratio`

#### HVAC Operation
- `Zone Air System Sensible Cooling/Heating Energy`
- `Zone Thermostat Cooling/Heating Setpoint Temperature`
- `Fan Electricity Energy/Rate`
- `Cooling Coil Total Cooling Energy`
- `Heating Coil Heating Energy`

#### Ventilation & Infiltration
- `Zone Mechanical Ventilation Mass/Volume Flow Rate`
- `Zone Ventilation Air Change Rate`
- `Zone Infiltration Air Change Rate`
- `Zone Infiltration Sensible Heat Loss/Gain Energy`

### Static Parameters

#### Performance Metrics
- Annual energy consumption by end use
- Peak electric/gas demands
- Comfort hours not met
- Energy use intensity (kWh/m²)

#### Sizing Parameters
- Design heating/cooling loads (W)
- Design air flow rates (m³/s)
- System capacities (W)
- Component sizes with units

#### Building Properties
- Zone floor areas and volumes
- Wall/window areas
- Construction U-values
- Material thermal properties

## Output Structures

### 1. Semi-Wide Format (Base Data)
```
| building_id | variant_id | VariableName | category | Zone | Units | 2020-01-01 | 2020-01-02 | ... |
|-------------|------------|--------------|----------|------|-------|------------|------------|-----|
| 1001 | base | Zone Air Temperature | geometry | CORE_ZN | C | 21.5 | 22.1 | ... |
```

### 2. Comparison Format (Variants)
```
| timestamp | building_id | Zone | variable_name | category | Units | base_value | variant_0_value | variant_1_value |
|-----------|-------------|------|---------------|----------|-------|------------|-----------------|-----------------|
| 2020-01-01 | 1001 | CORE_ZN | Zone Air Temperature | geometry | C | 21.5 | 20.8 | 22.3 |
```

### 3. Static Data Format
```
| building_id | variant_id | metric_name | value | units |
|-------------|------------|-------------|-------|-------|
| 1001 | base | Annual_Electricity | 125000 | kWh |
| 1001 | base | Peak_Cooling_Load | 45.5 | kW |
```

## Integration with Other Systems

### 1. IDF Parser Integration
- Shares building_id for linking
- SQL provides outputs, IDF provides inputs
- Combined for complete building model

### 2. Modification System
- Variant tracking through consistent IDs
- Links modifications to results
- Enables parameter sensitivity analysis

### 3. Time Series Aggregation
- Provides pre-aggregated data
- Maintains frequency metadata
- Supports further custom aggregation

### 4. Validation System
- Compares simulated vs. measured data
- Uses consistent time formats
- Supports multiple comparison metrics

### 5. Surrogate Modeling
- SQL outputs serve as training targets
- Combined with IDF inputs for modeling
- Maintains parameter-output relationships

### 6. Calibration Workflow
- Provides performance metrics for optimization
- Supports multi-objective calibration
- Tracks improvements across variants

## File Naming Conventions

### SQL Files
- Base: `simulation_bldg{index}_{building_id}.sql`
- Index determines variant in Modified_Sim_Results

### Output Files
- Time series: `base_all_{frequency}.parquet`
- Comparisons: `var_{variable}_{unit}_{freq}_b{building_id}.parquet`
- Static: `{category}_{metric}.parquet`

### Variable Name Cleaning
- Colons → underscores
- Spaces → underscores
- Remove brackets and parentheses
- Lowercase conversion

## Performance Optimizations

### 1. Query Optimization
- Caches available variables query
- Uses indexed lookups
- Filters by environment period early

### 2. Memory Management
- Processes data by frequency groups
- Temporary file storage for large datasets
- Cleanup after processing

### 3. Parallel Processing Support
- Can process multiple buildings concurrently
- Independent file outputs
- No shared state between buildings

### 4. Incremental Updates
- Append mode for static data
- Deduplication by building/variant ID
- Preserves existing data

### 5. Data Compression
- Parquet format with compression
- Efficient storage of sparse data
- Fast read performance