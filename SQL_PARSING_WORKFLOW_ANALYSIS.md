# SQL Parsing Workflow Analysis - E_Plus_2040_py Project

## Overview
This document provides a comprehensive analysis of the SQL parsing workflow in the E_Plus_2040_py project, focusing on zone configurations and data extraction processes.

## Zone Configurations Found

### 1. Core/Perimeter Zone Configuration
**Example: Building 4136733**
- 2 floors with 5 zones each (10 zones total)
- Floor 1:
  - ZONE1_CORE
  - ZONE1_FRONTPERIMETER
  - ZONE1_RIGHTPERIMETER
  - ZONE1_REARPERIMETER
  - ZONE1_LEFTPERIMETER
- Floor 2:
  - ZONE2_CORE
  - ZONE2_FRONTPERIMETER
  - ZONE2_RIGHTPERIMETER
  - ZONE2_REARPERIMETER
  - ZONE2_LEFTPERIMETER

### 2. Single Zone Configuration
**Example: Building 4136738**
- 1 zone total
- Zone name: ZONE1

### 3. Single Floor Core/Perimeter Configuration
**Example: Building 4136737**
- 1 floor with 5 zones
- Zones:
  - ZONE1_CORE
  - ZONE1_FRONTPERIMETER
  - ZONE1_RIGHTPERIMETER
  - ZONE1_REARPERIMETER
  - ZONE1_LEFTPERIMETER

## SQL Parsing Module Architecture

### 1. Main Coordinator: `sql_analyzer_main.py`
**Purpose**: Orchestrates the entire SQL analysis workflow
- Identifies base buildings vs. variants
- Manages multiple SQL file processing
- Coordinates data extraction and transformation
- Handles output validation

**Key Features**:
- Base/variant building identification
- Zone mapping management
- Output validation against requested variables
- Data transformation coordination

### 2. Core Analyzer: `sql_analyzer.py`
**Purpose**: Extracts time series data from SQL files
- Building and variant ID extraction from filename patterns
- Time series data extraction by category
- Variable categorization (energy_meters, site_weather, geometry, etc.)

**Variable Categories**:
- **energy_meters**: Electricity, Gas, District Cooling/Heating
- **site_weather**: Outdoor temperature, humidity, solar radiation
- **geometry**: Zone temperatures, humidity
- **materials**: Surface temperatures, heat transfer rates
- **dhw**: Water heater energy and temperatures
- **equipment**: Electric/gas equipment energy
- **lighting**: Lights energy and daylighting
- **hvac**: Cooling/heating energy, thermostat setpoints
- **ventilation**: Mechanical ventilation rates
- **infiltration**: Infiltration rates and heat loss/gain
- **shading**: Solar transmission, blind angles

### 3. Data Manager: `sql_data_manager.py`
**Purpose**: Handles data storage and transformation
- Manages base/variant data separation
- Transforms raw data to semi-wide format
- Creates frequency aggregations (hourly → daily → monthly)
- Handles comparison data for variants

**Data Organization**:
```
parsed_data/
├── timeseries/
│   ├── base_all_hourly.parquet
│   ├── base_all_daily.parquet
│   └── base_all_monthly.parquet
├── comparisons/
│   └── var_{variable}_{unit}_{freq}_b{building_id}.parquet
└── metadata/
    └── validation_results.parquet
```

### 4. Static Data Extractor: `sql_static_extractor.py`
**Purpose**: Extracts non-time series data
- Performance summaries (energy end uses, site/source energy)
- Sizing data (zone, system, component sizing)
- Building characteristics (envelope, constructions, zones)
- Equipment loads (nominal values)

**Output Structure**:
```
performance_summaries/
├── energy_end_uses.parquet
├── site_source_summary.parquet
├── comfort_metrics.parquet
├── energy_intensity.parquet
└── peak_demands.parquet

sizing_results/
├── zone_sizing.parquet
├── system_sizing.parquet
└── component_sizing.parquet

building_characteristics/
├── envelope_summary.parquet
├── construction_details.parquet
└── zone_properties.parquet
```

### 5. Enhanced Extractor: `sql_enhanced_extractor.py`
**Purpose**: Comprehensive data extraction with validation
- Zone data with full coverage tracking
- Zone-specific loads with proper mapping
- Missing data identification
- Extraction validation and reporting

**Key Features**:
- Bidirectional zone mapping (index ↔ name)
- Zone coverage validation
- Normalized values (e.g., watts/m²)
- Comprehensive error tracking

### 6. Schedule Extractor: `sql_schedule_extractor.py`
**Purpose**: Extracts schedule-related information
- Schedule metadata
- Schedule usage by equipment
- Schedule time series values (if available)
- Pattern analysis

## Data Flow

1. **SQL File Discovery**
   - Base buildings from `output_IDFs/`
   - Modified results from `Modified_Sim_Results/`

2. **Building/Variant Identification**
   - Pattern: `simulation_bldg{index}_{building_id}.sql`
   - Base: All files in `Sim_Results/`
   - Variants: Files in `Modified_Sim_Results/` (index indicates variant)

3. **Data Extraction**
   - Time series data by category
   - Static/summary data
   - Schedule information
   - Zone properties and loads

4. **Data Transformation**
   - Raw data → Semi-wide format
   - Frequency aggregations
   - Base/variant comparisons

5. **Output Organization**
   - Parquet files for efficient storage
   - Hierarchical directory structure
   - Metadata for validation and tracking

## Key Parameters Extracted

### Time Series Parameters
- Energy consumption (electricity, gas)
- Zone temperatures and humidity
- HVAC operation (cooling/heating rates)
- Ventilation and infiltration rates
- Equipment and lighting schedules
- Weather conditions

### Static Parameters
- Building geometry (floor area, volume)
- Zone properties (area, volume, multipliers)
- Construction details (materials, layers)
- Equipment nominal capacities
- System sizing results
- Window-wall ratios

### Zone-Specific Data
- Zone loads (lighting, equipment, people)
- Zone HVAC sizing
- Zone ventilation requirements
- Zone thermal properties

## Validation and Quality Control

1. **Output Validation**
   - Checks requested variables against available data
   - Tracks coverage percentage
   - Identifies missing or partial data

2. **Zone Coverage Tracking**
   - Ensures all zones have required data
   - Reports zones with missing information

3. **Error Logging**
   - Comprehensive error tracking
   - Missing data reports
   - Extraction logs

## Usage Patterns

### Typical Workflow
```python
# Initialize analyzer
analyzer = SQLAnalyzerMain(project_path, job_output_dir)

# Analyze SQL files
analyzer.analyze_sql_files(
    sql_files=sql_file_list,
    zone_mappings=zone_mappings,
    output_configs=output_configs,
    categories=['energy_meters', 'hvac', 'geometry'],
    is_modified_results=False,
    extract_static_data=True
)

# Load results
base_data = analyzer.load_base_data(frequency='daily')
variant_comparisons = analyzer.load_variant_comparisons(
    variable_name='Electricity:Facility',
    building_id='4136733'
)
```

## Important Notes

1. **Zone Configuration Differences**
   - Buildings can have different zone configurations
   - Core/perimeter is common for multi-story buildings
   - Single zone used for simpler buildings

2. **Data Frequency**
   - Original data can be hourly, daily, or monthly
   - Automatic aggregation to higher frequencies
   - Comparison data maintains original frequency

3. **Variant Tracking**
   - Base simulations from `Sim_Results/`
   - Variants from `Modified_Sim_Results/`
   - Variant ID derived from bldg index in filename

4. **Missing Data Handling**
   - Comprehensive tracking of missing variables
   - Zone coverage validation
   - Extraction reports for debugging