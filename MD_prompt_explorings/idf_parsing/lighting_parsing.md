# Lighting Parsing Documentation

## Overview
The lighting parsing module extracts lighting-related data from IDF files and SQL simulation results. This includes interior lighting, exterior lighting, and daylighting controls.

## IDF Objects Parsed

### 1. LIGHTS
Interior lighting definition for zones.

**Parameters Extracted:**
- `design_level`: Lighting Level (W)
- `watts_per_area`: Watts per Zone Floor Area (W/m²)
- `schedule`: Schedule Name
- `fraction_radiant`: Fraction Radiant (0-1)
- `fraction_visible`: Fraction Visible (0-1)
- `fraction_replaceable`: Fraction Replaceable (0-1)
- `return_air_fraction`: Return Air Fraction (0-1)
- `end_use`: End-Use Subcategory

### 2. DAYLIGHTING:CONTROLS
Controls for daylighting in zones.

**Parameters Extracted:**
- Zone Name
- Total Daylighting Reference Points
- Fraction of Zone Controlled
- Lighting Control Type
- Minimum Light Output Fraction
- Maximum Light Output Fraction
- Minimum Dimming Light Output Fraction
- Glare Calculation Azimuth Angle

### 3. DAYLIGHTING:REFERENCEPOINT
Reference points for daylighting calculations.

**Parameters Extracted:**
- Reference Point Name
- Zone Name
- X-Coordinate
- Y-Coordinate
- Z-Coordinate

### 4. EXTERIORLIGHTS
Exterior lighting definitions.

**Parameters Extracted:**
- Schedule Name
- Design Level (W)
- Control Option
- End-Use Subcategory

### 5. Other Objects
- DAYLIGHTING:DELIGHT:REFERENCEPOINT
- DAYLIGHTING:DELIGHT:CONTROLS
- LIGHTINGDESIGNDAY
- OUTPUT:ILLUMINANCEMAP
- OUTPUTCONTROL:ILLUMINANCEMAP:STYLE

## SQL Variables Extracted

The following variables are extracted from SQL simulation results:

1. **Zone Lights Electricity Rate** (W)
2. **Zone Lights Electricity Energy** (J)
3. **Zone Lights Total Heating Rate** (W)
4. **Zone Lights Total Heating Energy** (J)
5. **Zone Lights Visible Radiation Rate** (W)
6. **Zone Lights Visible Radiation Energy** (J)
7. **Zone Lights Convective Heating Rate** (W)
8. **Zone Lights Radiant Heating Rate** (W)
9. **Zone Lights Return Air Heating Rate** (W)
10. **Daylighting Reference Point 1 Illuminance** (lux)
11. **Daylighting Lighting Power Multiplier** (-)

## Key Metrics Calculated

1. **Lighting Power Density (LPD)**
   - Calculated as total lighting power divided by total floor area
   - Units: W/m²

2. **Annual Lighting Energy**
   - Total lighting electricity consumption over the simulation period
   - Units: kWh

3. **Daylighting Savings**
   - Reduction in lighting energy due to daylighting controls
   - Calculated from daylighting power multiplier data

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── lighting.parquet
```

**Columns in lighting.parquet:**
- building_id
- zone_name
- object_type
- object_name
- parameter_name
- parameter_value
- units
- schedule_name
- design_level
- watts_per_area
- lighting_fractions (radiant, visible, replaceable, return_air)
- end_use_subcategory

### SQL Timeseries Output
```
parsed_data/
└── timeseries/
    └── base_all_daily.parquet (for base buildings)
    └── comparisons/
        └── comparison_{building_id}.parquet (for variants)
```

**Lighting-related columns:**
- Date columns (YYYY-MM-DD format)
- building_id
- VariableName (lighting-related variables)
- KeyValue (zone names)
- Units
- Daily aggregated values

## Data Processing Notes

1. **Schedule References**: Lighting schedules are stored as references and need to be resolved from the schedules parsing output.

2. **Zone Association**: All interior lighting objects are associated with specific zones for proper energy accounting.

3. **Daylighting Integration**: Daylighting controls affect the actual lighting power consumption and are tracked through the power multiplier variable.

4. **End-Use Categories**: Lighting can be categorized by end-use subcategory for detailed energy analysis.

5. **Aggregation**: Daily values are aggregated from hourly simulation data for storage efficiency.