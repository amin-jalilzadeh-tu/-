# Output Definitions Module Documentation

## Overview
The Output Definitions module configures EnergyPlus simulation outputs, including variables, meters, tables, and summary reports. It determines what data will be collected during simulation for post-processing and analysis.

## Module Structure

### 1. output_lookup.py
Centralized database of available EnergyPlus output options.

#### Available Output Categories

**Variables** (with default frequencies):
- Zone Air Temperature (Hourly)
- Zone Mean Air Humidity Ratio (Hourly)
- Zone Total Internal Total Heat Gain (Hourly)
- Zone Windows Total Heat Gain/Loss (Hourly)
- Zone Ventilation Air Change Rate (Hourly)
- Zone Infiltration Air Change Rate (Hourly)
- Zone Mechanical Ventilation Air Change Rate (Hourly)
- Facility Total Electric Demand Power (Timestep)
- Exterior Lights Electric Energy (Monthly)
- Water Heater instances (Hourly)

**Meters**:
- Electricity:Facility (Hourly)
- Electricity:Building (Hourly)
- ElectricityNet:Facility (Hourly)
- NaturalGas:Facility (Hourly)
- Cooling:Electricity (Hourly)
- Heating:NaturalGas (Hourly)
- InteriorLights:Electricity (Hourly)
- InteriorEquipment:Electricity (Hourly)
- Fans:Electricity (Hourly)
- WaterSystems:NaturalGas (Hourly)

**Tables** (Monthly summaries):
- Peak heating/cooling loads
- Energy consumption by category
- Zone temperature statistics

**Summary Reports**:
- AllSummary
- AllMonthly
- ZoneCoolingSummaryMonthly
- ZoneHeatingSummaryMonthly
- AnnualBuildingUtilityPerformanceSummary

### 2. assign_output_settings.py

Configures output settings based on user preferences.

#### Input Parameters
```python
def assign_output_settings(
    desired_variables=None,      # List of variable names to track
    desired_meters=None,         # List of meter names to monitor
    override_variable_frequency=None,  # Custom reporting frequency
    override_meter_frequency=None,     # Custom meter frequency
    include_tables=True,         # Include monthly tables
    include_summary=True         # Include summary reports
)
```

#### Processing Logic
1. If no specific variables requested, uses all from lookup
2. Filters variables/meters based on desired lists
3. Applies override frequencies if specified
4. Builds configuration dictionary

#### Output Structure
```python
{
    "variables": [
        {"key": "Zone Air Temperature", "frequency": "Hourly"},
        {"key": "Facility Total Electric Demand Power", "frequency": "Timestep"}
    ],
    "meters": [
        {"key": "Electricity:Facility", "frequency": "Hourly"}
    ],
    "tables": [...],  # If include_tables=True
    "summary_reports": [...]  # If include_summary=True
}
```

### 3. add_output_definitions.py

Creates actual IDF output objects.

#### IDF Objects Created

**OUTPUT:VARIABLE**:
```
Output:Variable,
    *,                          ! Key Value (wildcard for all zones)
    Zone Air Temperature,       ! Variable Name
    Hourly;                    ! Reporting Frequency
```

**OUTPUT:METER**:
```
Output:Meter,
    Electricity:Facility,      ! Name
    Hourly;                   ! Reporting Frequency
```

**OUTPUT:TABLE:MONTHLY**:
```
Output:Table:Monthly,
    Zone Cooling Loads,        ! Name
    ,                         ! Digits After Decimal
    Zone Air System Sensible Cooling Energy,  ! Variable 1
    SumOrAverage,             ! Aggregation Type 1
    Zone Air System Sensible Cooling Rate,    ! Variable 2
    Maximum;                  ! Aggregation Type 2
```

**OUTPUT:TABLE:SUMMARYREPORTS**:
```
Output:Table:SummaryReports,
    AllSummary,               ! Report 1
    AllMonthly,               ! Report 2
    ZoneCoolingSummaryMonthly,! Report 3
    ZoneHeatingSummaryMonthly;! Report 4
```

## Input Data

### User Configuration Options
- **desired_variables**: Subset of variables to track (None = all)
- **desired_meters**: Subset of meters to monitor (None = all)
- **override_variable_frequency**: "Timestep", "Hourly", "Daily", "Monthly", "RunPeriod"
- **override_meter_frequency**: Same options as variables
- **include_tables**: Boolean to include/exclude monthly tables
- **include_summary**: Boolean to include/exclude summary reports

### Default Configuration
If no user preferences specified:
- All variables from lookup at default frequencies
- All meters from lookup at default frequencies
- All tables and summary reports included

## Processing Flow

1. **Configuration** (`assign_output_settings`):
   - Parse user preferences
   - Filter available outputs
   - Apply frequency overrides
   - Build settings dictionary

2. **IDF Creation** (`add_output_definitions`):
   - Check for existing output objects
   - Create OUTPUT:VARIABLE objects
   - Create OUTPUT:METER objects
   - Create OUTPUT:TABLE objects
   - Add summary reports

## Key Features

1. **Duplicate Prevention**: Checks for existing output objects before creating
2. **Wildcard Support**: Uses "*" for zone-level variables to capture all zones
3. **Flexible Frequencies**: Supports all EnergyPlus reporting frequencies
4. **Comprehensive Coverage**: Tracks energy, temperature, humidity, and system performance
5. **Summary Reports**: Automatic generation of annual and monthly summaries

## Output Files Generated

During simulation, EnergyPlus creates:
- **eplusout.csv**: Time-series data for variables and meters
- **eplusout_summary.htm**: HTML summary reports
- **eplusout_monthly.csv**: Monthly aggregated data
- **Building-specific CSVs**: When using multiple buildings

## Integration with Post-Processing

Output data feeds into:
- `merge_results.py` for consolidation
- Analysis scripts for performance evaluation
- Calibration routines for model tuning
- Visualization tools for reporting

## Best Practices

1. **Variable Selection**: Choose only needed variables to reduce file size
2. **Frequency Balance**: Higher frequency = more detail but larger files
3. **Meter Coverage**: Include both facility and end-use meters
4. **Summary Reports**: Always include for quick performance overview
5. **Consistent Naming**: Use standard EnergyPlus variable names