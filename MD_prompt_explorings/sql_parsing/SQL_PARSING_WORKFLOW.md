# SQL Parsing Workflow in E_Plus_2040_py

## Overview
SQL parsing is a critical component that extracts simulation results from EnergyPlus SQLite output files and transforms them into analysis-ready parquet format. The system handles both base simulations and modified variant simulations with proper data organization.

## When SQL Parsing Occurs

### 1. After Base IDF Simulation
- **Trigger**: Completion of base building simulations
- **Location**: Called from `orchestrator/main.py` after IDF creation step
- **Configuration Flag**: `parsing.perform_parsing: true`
- **Output Directory**: `parsed_data/`

### 2. After Modified IDF Simulation
- **Trigger**: Completion of modified building simulations
- **Location**: Called within modification step after post-modification simulations
- **Configuration Flag**: `modification.post_modification.parse_results: true`
- **Output Directory**: `parsed_modified_results/`

## SQL Parsing Components

### 1. Main Coordinator: `SQLAnalyzerMain`
**File**: `parserr/sql_analyzer_main.py`

```python
class SQLAnalyzerMain:
    def __init__(self, project_path: Path, job_output_dir: Path = None):
        # Identifies base buildings from output_IDFs/
        # Initializes data manager
        # Sets up analyzers dictionary
    
    def analyze_sql_files(self, sql_files, ..., is_modified_results=False):
        # Main entry point for SQL parsing
        # Routes to appropriate data storage based on is_modified_results
```

### 2. SQL Analyzer: `EnhancedSQLAnalyzer`
**File**: `parserr/sql_analyzer.py`

- Connects to SQLite database
- Extracts time series data by category
- Handles variable name mapping
- Processes hourly/daily/monthly data

### 3. Static Data Extractor: `SQLStaticExtractor`
**File**: `parserr/sql_static_extractor.py`

- Extracts non-time series data
- Building characteristics
- System sizing results
- Schedule definitions
- Summary statistics

### 4. Data Manager: `SQLDataManager`
**File**: `parserr/sql_data_manager.py`

- Organizes extracted data
- Transforms to semi-wide format
- Manages base vs variant separation
- Creates comparison files

## Data Flow Process

### Step 1: SQL File Discovery
```python
# For base simulations
sql_files = find_sql_files("Sim_Results/")

# For modified simulations  
sql_files = find_sql_files("Modified_Sim_Results/")
```

### Step 2: Building ID Extraction
```python
# From filename: simulation_bldg1_4136733.sql
building_id = "4136733"
variant_id = "base"  # or "variant_0", "variant_1", etc.
```

### Step 3: Data Extraction
1. **Time Series Data**
   - Categories: HVAC, Lighting, Equipment, etc.
   - Variables defined in `SQL_CATEGORY_MAPPINGS`
   - Hourly values aggregated to daily

2. **Static Data** (if enabled)
   - Building properties
   - Component summaries
   - Annual totals

### Step 4: Data Transformation
1. **Base Data** → Semi-wide format
   ```
   building_id | VariableName | KeyValue | 2020-01-01 | 2020-01-02 | ...
   4136733     | Heating      | Zone1    | 1234.5     | 2345.6     | ...
   ```

2. **Variant Data** → Comparison format
   ```
   building_id | variant_id | VariableName | base_value | variant_value | delta
   4136733     | variant_0  | Heating      | 1234.5     | 1111.1       | -123.4
   ```

## Directory Structure

### Base Parsing Output
```
parsed_data/
├── timeseries/
│   ├── base_all_daily.parquet      # All buildings, daily values
│   ├── base_all_monthly.parquet    # Monthly aggregation
│   └── base_all_yearly.parquet     # Yearly aggregation
├── idf_data/
│   └── [IDF object data]
├── metadata/
│   ├── validation_results.parquet
│   └── data_availability.json
├── building_characteristics/
├── schedules/
├── sizing_results/
└── parsing_summary.json
```

### Modified Parsing Output
```
parsed_modified_results/
├── comparisons/
│   ├── var_electricity_4136733.parquet
│   ├── var_hvac_4136733.parquet
│   └── var_zone_4136733.parquet
├── timeseries/
│   └── [variant time series if needed]
├── metadata/
└── parsing_summary.json
```

## Configuration Options

### Basic Parsing Configuration
```json
{
  "parsing": {
    "perform_parsing": true,
    "parse_mode": "all",
    "parse_types": {
      "idf": true,
      "sql": true,
      "sql_static": true
    },
    "categories": ["hvac", "electricity", "equipment"]
  }
}
```

### Post-Modification Parsing
```json
{
  "modification": {
    "post_modification": {
      "run_simulations": true,
      "parse_results": {
        "categories": ["hvac", "electricity"],
        "parse_types": {
          "sql": true,
          "sql_static": false
        }
      }
    }
  }
}
```

## Key Functions

### 1. `run_parsing()` - Base Data Parsing
```python
def run_parsing(parsing_cfg, main_config, job_output_dir, job_id, logger):
    # Creates parsed_data directory
    # Initializes CombinedAnalyzer
    # Identifies base buildings
    # Parses SQL files
    # Saves as base data
```

### 2. `run_parsing_modified_results()` - Variant Data Parsing
```python
def run_parsing_modified_results(parse_cfg, job_output_dir, ...):
    # Creates parsed_modified_results directory
    # Matches modified IDFs to SQL files
    # Parses with variant tracking
    # Creates comparison files
```

## SQL Categories and Variables

### HVAC Category
- Zone Air System Sensible Heating Energy
- Zone Air System Sensible Cooling Energy
- Zone Air Temperature
- Zone Mean Air Temperature

### Electricity Category
- Facility Total Electricity Demand
- Electricity:Facility
- InteriorLights:Electricity
- InteriorEquipment:Electricity

### Equipment Category
- Electric Equipment Power
- Electric Equipment Energy

## Important Implementation Details

1. **Base Building Identification**
   - Scans `output_IDFs/` directory for building_*.idf files
   - Extracts building IDs from filenames
   - Used to differentiate base vs variant data

2. **Variant Matching**
   - Modified IDF: `building_4136733_variant_0.idf`
   - SQL file: `simulation_bldg1_4136733.sql`
   - Matches based on building ID and simulation index

3. **Data Aggregation**
   - Hourly → Daily: Sum for energy, average for temperature
   - Daily → Monthly: Preserve aggregation rules
   - Handles missing data appropriately

4. **Comparison Generation**
   - Loads base data from `parsed_data/`
   - Calculates deltas: variant - base
   - Percentage change where applicable
   - Preserves all metadata

## Performance Considerations

1. **Batch Processing**
   - Multiple SQL files processed in sequence
   - Data accumulated in memory
   - Single write operation per category

2. **Memory Management**
   - Large SQL files processed in chunks
   - Parquet compression reduces storage
   - Old data structure cleaned after transformation

3. **Parallel Potential**
   - SQL file parsing can be parallelized
   - Currently sequential for data consistency
   - Future optimization opportunity

## Troubleshooting

### Common Issues

1. **Missing SQL Files**
   - Check simulation completed successfully
   - Verify SQL output enabled in IDF
   - Check file permissions

2. **Building ID Mismatch**
   - Ensure consistent naming convention
   - Check `extracted_idf_buildings.csv`
   - Verify variant naming pattern

3. **Empty Comparison Files**
   - Confirm base data exists in `parsed_data/`
   - Check variant has matching building ID
   - Verify categories match between base and variant

### Debug Points

1. **Check Parsing Summary**
   ```bash
   cat parsed_data/parsing_summary.json
   cat parsed_modified_results/parsing_summary.json
   ```

2. **Verify Data Structure**
   ```python
   import pandas as pd
   df = pd.read_parquet('parsed_data/timeseries/base_all_daily.parquet')
   print(df.info())
   ```

3. **SQL File Validation**
   ```sql
   sqlite3 simulation_bldg1_4136733.sql
   .tables
   SELECT COUNT(*) FROM ReportData;
   ```