# IDF Parsing Documentation Overview

## Introduction
This directory contains comprehensive documentation for the EnergyPlus IDF (Input Data File) parsing system. The parser extracts building model data from IDF files and SQL simulation results, organizing them into structured formats for analysis.

## System Architecture

### Parser Components
1. **IDF Parser** (`parserr/idf_parser.py`): Reads and parses IDF text files
2. **SQL Analyzer** (`parserr/sql_analyzer.py`): Extracts timeseries results from EnergyPlus SQL output
3. **Data Managers**: Handle data organization and storage
4. **Category Mappings**: Define which IDF objects belong to which parsing categories

### Data Flow
```
IDF Files → IDF Parser → Categorized Objects → Data Manager → Parquet Files
SQL Files → SQL Analyzer → Timeseries Data → Aggregation → Parquet Files
```

## Parsing Categories

The parser organizes building data into the following categories:

### 1. [Geometry](geometry_parsing.md)
- Building zones and spaces
- Surfaces (walls, floors, roofs, windows, doors)
- Building envelope metrics (area, volume, WWR)

### 2. [Materials](materials_parsing.md)
- Material properties (conductivity, density, specific heat)
- Construction assemblies
- Window systems
- Thermal performance metrics

### 3. [HVAC](hvac_parsing.md)
- Heating and cooling equipment
- Air distribution systems
- Thermostats and controls
- System performance metrics

### 4. [Lighting](lighting_parsing.md)
- Interior and exterior lighting
- Daylighting controls
- Lighting schedules and controls
- Energy consumption metrics

### 5. [Equipment](equipment_parsing.md)
- Plug loads and process equipment
- Multiple fuel types (electric, gas, etc.)
- Equipment schedules
- Peak demand and consumption

### 6. [DHW (Domestic Hot Water)](dhw_parsing.md)
- Water heaters and storage tanks
- Distribution systems
- Water use equipment
- System efficiency metrics

### 7. [Ventilation](ventilation_parsing.md)
- Mechanical ventilation systems
- Natural ventilation
- Outdoor air requirements
- Air change rates

### 8. [Infiltration](infiltration_parsing.md)
- Air leakage modeling
- Weather-driven infiltration
- Envelope tightness metrics

### 9. [Shading](shading_parsing.md)
- Fixed shading devices
- Movable shading controls
- Solar heat gain reduction

### 10. [Schedules](schedules_parsing.md)
- Time-varying controls
- Occupancy patterns
- Operating schedules
- Setpoint profiles

### 11. [People and Occupancy](people_occupancy_parsing.md)
- Occupant loads and density
- Activity levels and metabolic rates
- Clothing insulation
- Thermal comfort metrics

### 12. [Simulation Control](simulation_control_parsing.md)
- Simulation parameters and settings
- Site location and climate data
- Run periods and timesteps
- Calculation algorithms

### 13. [Outputs Configuration](outputs_parsing.md)
- Output variable definitions
- Meter configurations
- Report specifications
- Output file controls

### 14. [SQL Static Data](sql_static_extraction.md)
- Performance summaries
- Sizing results
- Building characteristics from SQL
- Simulation metadata

## Output Structure

### IDF Data Output
Static building model data organized by category:
```
parsed_data/
└── idf_data/
    └── building_{id}/
        ├── geometry_zones.parquet
        ├── geometry_surfaces.parquet
        ├── materials_*.parquet
        ├── hvac_*.parquet
        ├── lighting.parquet
        ├── equipment.parquet
        ├── dhw.parquet
        ├── ventilation.parquet
        ├── infiltration.parquet
        ├── shading.parquet
        └── schedules.parquet
```

### SQL Timeseries Output
Simulation results with daily aggregation:
```
parsed_data/
└── timeseries/
    ├── base_all_daily.parquet      # Base building results
    └── comparisons/                 # Variant comparisons
        └── comparison_{id}.parquet
```

## Data Schema

### IDF Data Schema
Common columns across all category files:
- `building_id`: Unique building identifier
- `object_type`: IDF object type (e.g., "LIGHTS", "ZONE")
- `object_name`: User-defined name
- `zone_name`: Associated thermal zone (where applicable)
- Category-specific parameters

### Timeseries Schema
- Date columns in YYYY-MM-DD format
- `building_id`: Building identifier
- `VariableName`: EnergyPlus output variable name
- `KeyValue`: Instance identifier (zone, surface, or system name)
- `Units`: Engineering units
- Daily aggregated values (sum or average as appropriate)

## Usage Examples

### Accessing Parsed Data
```python
import pandas as pd

# Read lighting data for a building
lighting_df = pd.read_parquet('parsed_data/idf_data/building_123/lighting.parquet')

# Read timeseries results
timeseries_df = pd.read_parquet('parsed_data/timeseries/base_all_daily.parquet')

# Filter for specific variable
zone_temps = timeseries_df[
    timeseries_df['VariableName'] == 'Zone Mean Air Temperature'
]
```

### Common Analysis Tasks

1. **Calculate total lighting power density**
```python
total_power = lighting_df['design_level'].sum()
total_area = zones_df['floor_area'].sum()
lpd = total_power / total_area
```

2. **Extract HVAC equipment capacities**
```python
hvac_df = pd.read_parquet('parsed_data/idf_data/building_123/hvac_equipment.parquet')
cooling_capacity = hvac_df[hvac_df['parameter_name'] == 'cooling_capacity']['value'].sum()
```

3. **Analyze scheduling patterns**
```python
schedules_df = pd.read_parquet('parsed_data/idf_data/building_123/schedules.parquet')
occupancy_schedule = schedules_df[schedules_df['schedule_name'].str.contains('Occupancy')]
```

## Configuration

### Parsing Configuration
Control parsing through configuration:
```json
{
  "parse_mode": "all",
  "parse_types": {
    "idf": true,
    "sql": true,
    "sql_static": true
  },
  "categories": ["hvac", "lighting", "geometry"],  // null for all
  "building_selection": {
    "mode": "all",  // or "specific"
    "building_ids": [123, 456]  // if mode is "specific"
  }
}
```

### Category Mappings
The `CATEGORY_MAPPINGS` dictionary in `idf_analyzer_main.py` defines:
- Which IDF objects belong to each category
- Which SQL variables to extract
- Key parameters to parse
- Metrics to calculate

## Best Practices

1. **Memory Management**: Process large datasets in chunks
2. **Data Validation**: Verify parsed values are within expected ranges
3. **Error Handling**: Check parse_errors in building data
4. **Performance**: Use categorical data types for repeated strings
5. **Storage**: Use Parquet for efficient storage and fast queries

## Troubleshooting

### Common Issues

1. **Missing Objects**: Some IDF files may not contain all object types
2. **Schedule References**: Ensure referenced schedules exist
3. **Zone Associations**: Verify equipment is properly assigned to zones
4. **Unit Conversions**: EnergyPlus uses SI units internally
5. **Variant Tracking**: Ensure proper building ID mapping for variants

### Validation Checks

- Total floor area matches sum of zone areas
- Equipment power densities within reasonable ranges
- Schedules sum to appropriate annual hours
- Material properties within physical limits
- Surface areas match geometry calculations

## Extensions

The parsing system can be extended by:
1. Adding new categories to `CATEGORY_MAPPINGS`
2. Creating new parser modules for specialized objects
3. Adding custom metrics calculations
4. Implementing additional output formats
5. Creating visualization pipelines

## References

- [EnergyPlus Documentation](https://energyplus.net/documentation)
- [Input Output Reference](https://energyplus.net/sites/default/files/pdfs_v8.3.0/InputOutputReference.pdf)
- [Engineering Reference](https://energyplus.net/sites/default/files/pdfs_v8.3.0/EngineeringReference.pdf)