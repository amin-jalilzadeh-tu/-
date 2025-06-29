# Complete Data Transformation Flow in E_Plus_2040_py

## Overview
This document tracks the complete data transformation flow from initial input through final output, detailing formats, structures, and transformations at each step.

## 1. Initial Input Data

### 1.1 Combined JSON Input Structure
**Format**: JSON
**Location**: POST request body to `/jobs` endpoint
**Example Structure**:
```json
{
  "dhw": [
    {
      "building_id": 413673000,
      "param_name": "occupant_density_m2_per_person",
      "min_val": 127.0,
      "max_val": 233.0
    },
    {
      "building_function": "residential00",
      "age_range": "1992-2005",
      "param_name": "setpoint_c",
      "min_val": 58.0,
      "max_val": 60.0
    }
  ],
  "epw": [
    {
      "building_id": 413673000,
      "fixed_epw_path": "data/weather/2050.epw"
    }
  ],
  "zone_sizing": [...],
  "equipment": [...],
  "shading": [...],
  "main_config": {
    "use_database": true,
    "db_filter": {...},
    "filter_by": "pand_ids",
    "idf_creation": {
      "perform_idf_creation": true,
      "scenario": "scenario1",
      "calibration_stage": "pre_calibration",
      "strategy": "B",
      "run_simulations": true
    }
  }
}
```

### 1.2 Data Splitting
**Process**: `splitter.py:split_combined_json()`
**Transformation**: Combined JSON → Individual JSON files
**Output Format**: 
- `user_configs/<job_id>/dhw.json` → `{"dhw": [...]}`
- `user_configs/<job_id>/epw.json` → `{"epw": [...]}`
- `user_configs/<job_id>/main_config.json` → `{"main_config": {...}}`

## 2. Building Data Loading

### 2.1 Database Query (if use_database=true)
**Process**: `database_handler.py:load_buildings_from_db()`
**SQL Query**:
```sql
SELECT DISTINCT ON (b.pand_id)
    b.ogc_fid, b.pand_id, b.meestvoorkomendelabel,
    b.gem_hoogte, b.gem_bouwlagen, b.b3_dak_type,
    b.area, b.perimeter, b.height, b.bouwjaar,
    b.age_range, b.average_wwr, b.building_function,
    b.residential_type, b.non_residential_type,
    b.north_side, b.east_side, b.south_side, b.west_side,
    b.building_orientation, b.x, b.y, b.lat, b.lon, b.postcode
FROM amin.buildings_1_deducted b
WHERE [filters]
ORDER BY b.pand_id, b.ogc_fid
```
**Output**: Pandas DataFrame

### 2.2 CSV Loading (if use_database=false)
**Input**: CSV file path from `paths_dict["building_data"]`
**Output**: Pandas DataFrame with same columns as database

## 3. Configuration Processing

### 3.1 Excel Overrides
**Process**: Various `override_*_from_excel_file()` functions
**Input**: Excel files with lookup tables
**Output**: Updated dictionaries for:
- DHW parameters
- EPW file mappings
- Lighting schedules
- HVAC configurations
- Ventilation settings

### 3.2 JSON User Overrides
**Process**: Merging user-specific JSON configurations
**Priority**: JSON overrides > Excel overrides > Default values

## 4. IDF Generation Process

### 4.1 Base IDF Creation
**Process**: `idf_creation.py:create_idf_for_building()`
**Base Template**: `EnergyPlus/Minimal.idf`
**Steps for each building**:

#### 4.1.1 Geometry Creation
**Process**: `geomz/building.py:create_building_with_roof_type()`
**Input Parameters**:
- Area, perimeter from building data
- Number of floors from `gem_bouwlagen`
- Total height from `gem_hoogte`
- Orientation from `building_orientation`
- Edge types (north_side, east_side, etc.)

**Transformations**:
1. **Floor height calculation**:
   - Total height / number of floors
   - Adjusted based on building function (residential: 2.5-4.0m, non-res: 3.0-6.0m)

2. **Rectangle dimensions**:
   - Computed from area and perimeter using quadratic formula
   - Width and length calculated to match constraints

3. **Polygon creation**:
   - Base polygon rotated by orientation angle
   - Vertices ordered counterclockwise

4. **Zone creation**:
   - Perimeter zones (if perimeter_depth > 0)
   - Core zone (if has_core = true)
   - Multiple floors with inter-floor linking

**Data Structure Example**:
```python
{
    "perimeter_depth": 2.5,  # meters
    "has_core": True,
    "zones": [
        {"name": "Zone1_North", "floor": 1, "type": "perimeter"},
        {"name": "Zone1_Core", "floor": 1, "type": "core"}
    ]
}
```

#### 4.1.2 Fenestration Assignment
**Process**: `fenez/fenestration.py:add_fenestration()`
**Input**: 
- Building function, age range
- Residential/non-residential type
- User overrides

**Window-to-Wall Ratio (WWR) Assignment**:
1. Lookup base WWR range from dictionaries
2. Apply strategy:
   - Strategy A: Use midpoint of range
   - Strategy B: Random value within range
3. Create window surfaces using `geomeppy.set_wwr()`

**Output**: FENESTRATIONSURFACE:DETAILED objects

#### 4.1.3 Materials and Constructions
**Process**: `fenez/materials.py`
**Updates**:
- Wall constructions based on age and type
- Window constructions (typically "Window1C")
- Roof and floor constructions

#### 4.1.4 HVAC System Addition
**Process**: `HVAC/custom_hvac.py:add_HVAC_Ideal_to_all_zones()`
**System Type**: Ideal Loads Air System
**Parameters assigned**:
- Heating/cooling setpoints
- Supply air temperatures
- Schedules (occupancy, availability)

**Schedule Creation**:
```
SCHEDULE:COMPACT objects for:
- Heating setpoint schedule
- Cooling setpoint schedule
- HVAC availability
- Zone control type
```

#### 4.1.5 Other Systems
- **Lighting**: Power density (W/m²) and schedules
- **Equipment**: Electric equipment loads and schedules
- **DHW**: Water heater sizing and schedules
- **Ventilation**: Outdoor air requirements
- **Shading**: External louvers or blinds

### 4.2 IDF File Output
**Format**: EnergyPlus IDF text format
**Location**: `output/<job_id>/output_IDFs/building_<index>.idf`
**Example Structure**:
```
!- EnergyPlus Input File
Version,9.2;

Building,
  Sample_Building_0,       !- Name
  0.0,                     !- North Axis
  ...

Zone,
  Zone1_North,             !- Name
  0,                       !- Direction of Relative North
  ...

BuildingSurface:Detailed,
  Zone1_North_Floor,       !- Name
  Floor,                   !- Surface Type
  ...
```

## 5. Simulation Execution

### 5.1 EPW File Assignment
**Process**: `epw/assign_epw_file.py`
**Logic**:
1. Check user overrides by building_id
2. Use desired_climate_year from building data
3. Select appropriate weather file

### 5.2 EnergyPlus Execution
**Process**: `epw/run_epw_sims.py:simulate_all()`
**Parallel Execution**: Using multiprocessing.Pool
**Command**: `idf.run()` from eppy library
**Output Files per building**:
- `.sql` - SQLite database with detailed results
- `.eso` - EnergyPlus simulation output
- `.err` - Error and warning messages
- `.csv` - Time series data (if readvars=true)

## 6. Output Parsing and Storage

### 6.1 SQL Database Parsing
**Process**: `parserr/sql_analyzer_main.py`
**Input**: SQLite files from simulations
**Tables Parsed**:
- ReportData - Time series values
- ReportDataDictionary - Variable definitions
- Time - Timestamp mappings
- TabularDataWithStrings - Summary reports

**Output Format**: Parquet files
**Structure**:
```
output/<job_id>/parser_output/
├── timeseries/
│   ├── base_all_daily.parquet
│   └── base_all_hourly.parquet
├── comparisons/
│   └── variant_comparison_*.parquet
└── summaries/
    └── annual_summaries.parquet
```

### 6.2 IDF Parsing
**Process**: `parserr/idf_analyzer_main.py`
**Extracts**:
- Zone definitions and mappings
- Output variable configurations
- System parameters

**Output**: JSON files with structured IDF data

## 7. Data Aggregation Formats

### 7.1 Time Series Data (Parquet)
**Schema**:
```
building_id: string
VariableName: string
Units: string
Frequency: string
2020-01-01: float
2020-01-02: float
...
```

### 7.2 Summary Data
**Annual Metrics**:
- Total energy consumption by fuel type
- Peak demands
- Zone temperatures statistics
- System performance indicators

### 7.3 Comparison Data
**For modified scenarios**:
```
building_id: string
variable: string
base_value: float
variant_value: float
absolute_difference: float
percent_difference: float
```

## 8. Post-Processing Steps

### 8.1 Sensitivity Analysis
**If enabled**: Varies input parameters and tracks output changes
**Output**: Sensitivity indices and parameter importance rankings

### 8.2 Surrogate Modeling
**If enabled**: Creates simplified models from simulation results
**Output**: Machine learning model files

### 8.3 Calibration
**If enabled**: Adjusts parameters to match measured data
**Output**: Calibrated parameter sets

## 9. Final Output Structure
```
output/<job_id>/
├── output_IDFs/           # Generated IDF files
├── simulation_results/    # Raw EnergyPlus outputs
│   ├── 2020/
│   ├── 2030/
│   └── 2050/
├── parser_output/         # Parsed and structured data
├── sensitivity/           # Sensitivity analysis results
├── surrogate/            # Surrogate model files
├── calibration/          # Calibration results
└── logs/                 # Process logs
```

## Data Flow Summary

1. **JSON Input** → Split into component files
2. **Building Data** → Loaded from DB/CSV
3. **Configurations** → Merged from defaults + Excel + JSON
4. **IDF Generation** → Text files with building physics
5. **Simulation** → SQLite + CSV outputs
6. **Parsing** → Structured Parquet files
7. **Analysis** → Various post-processing outputs

Each transformation preserves traceability through building IDs and maintains logs of parameter assignments for validation and debugging.