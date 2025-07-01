# SQL Table Structures and Data Extraction

## EnergyPlus SQL Database Schema

EnergyPlus creates SQLite databases containing comprehensive simulation results. This document details the key tables and their extracted data.

## Primary Tables for Time Series Data

### 1. ReportDataDictionary
Defines all available output variables in the simulation.

| Column | Type | Description |
|--------|------|-------------|
| ReportDataDictionaryIndex | INTEGER | Primary key |
| Name | TEXT | Variable name (e.g., "Zone Air Temperature") |
| KeyValue | TEXT | Associated key (e.g., zone name) |
| Units | TEXT | Measurement units |
| ReportingFrequency | TEXT | Timestep/Hourly/Daily/Monthly/RunPeriod |

### 2. ReportData
Contains actual time series values.

| Column | Type | Description |
|--------|------|-------------|
| ReportDataIndex | INTEGER | Primary key |
| ReportDataDictionaryIndex | INTEGER | Foreign key to dictionary |
| TimeIndex | INTEGER | Foreign key to Time table |
| Value | REAL | Actual data value |

### 3. Time
Time index definitions.

| Column | Type | Description |
|--------|------|-------------|
| TimeIndex | INTEGER | Primary key |
| EnvironmentPeriodIndex | INTEGER | Links to environment period |
| Year | INTEGER | Simulation year |
| Month | INTEGER | Month (1-12) |
| Day | INTEGER | Day of month |
| Hour | INTEGER | Hour (0-24, 24=next day 0:00) |
| Minute | INTEGER | Minute (0-59) |
| DayType | TEXT | Type of day |

### 4. EnvironmentPeriods
Defines simulation periods.

| Column | Type | Description |
|--------|------|-------------|
| EnvironmentPeriodIndex | INTEGER | Primary key |
| EnvironmentName | TEXT | Period name |
| EnvironmentType | INTEGER | 1=Design Day, 3=Weather File |

## Static Data Tables

### 5. TabularData
Contains all tabular reports (performance summaries, etc.).

| Column | Type | Description |
|--------|------|-------------|
| TabularDataIndex | INTEGER | Primary key |
| ReportNameIndex | INTEGER | Links to report name |
| TableNameIndex | INTEGER | Links to table name |
| RowNameIndex | INTEGER | Links to row name |
| ColumnNameIndex | INTEGER | Links to column name |
| UnitsIndex | INTEGER | Links to units |
| RowId | INTEGER | Row position |
| ColumnId | INTEGER | Column position |
| Value | TEXT | Cell value |

### 6. Strings
String lookup table for TabularData.

| Column | Type | Description |
|--------|------|-------------|
| StringIndex | INTEGER | Primary key |
| Value | TEXT | String value |

## Building Characteristic Tables

### 7. Zones
Zone geometry and properties.

| Column | Type | Description |
|--------|------|-------------|
| ZoneIndex | INTEGER | Primary key |
| ZoneName | TEXT | Zone identifier |
| FloorArea | REAL | Floor area (m²) |
| Volume | REAL | Zone volume (m³) |
| CeilingHeight | REAL | Average ceiling height (m) |
| Multiplier | INTEGER | Zone multiplier |
| ExtGrossWallArea | REAL | Gross exterior wall area (m²) |
| ExtWindowArea | REAL | Exterior window area (m²) |
| ExtNetWallArea | REAL | Net wall area (m²) |

### 8. Surfaces
Building surface definitions.

| Column | Type | Description |
|--------|------|-------------|
| SurfaceIndex | INTEGER | Primary key |
| SurfaceName | TEXT | Surface identifier |
| ConstructionIndex | INTEGER | Links to construction |
| ZoneIndex | INTEGER | Links to zone |
| Area | REAL | Surface area (m²) |
| Azimuth | REAL | Surface azimuth (degrees) |
| Tilt | REAL | Surface tilt (degrees) |
| SurfaceType | TEXT | Wall/Floor/Roof/Window |

### 9. Constructions & Materials
Construction assemblies and material properties.

**Constructions Table:**
| Column | Type | Description |
|--------|------|-------------|
| ConstructionIndex | INTEGER | Primary key |
| Name | TEXT | Construction name |
| TotalLayers | INTEGER | Number of layers |

**Materials Table:**
| Column | Type | Description |
|--------|------|-------------|
| MaterialIndex | INTEGER | Primary key |
| Name | TEXT | Material name |
| MaterialType | INTEGER | Type code |
| Thickness | REAL | Layer thickness (m) |
| Conductivity | REAL | Thermal conductivity (W/m-K) |
| Density | REAL | Material density (kg/m³) |
| SpecHeat | REAL | Specific heat (J/kg-K) |

**ConstructionLayers Table:**
| Column | Type | Description |
|--------|------|-------------|
| ConstructionLayersIndex | INTEGER | Primary key |
| ConstructionIndex | INTEGER | Links to construction |
| LayerIndex | INTEGER | Layer position (outside=1) |
| MaterialIndex | INTEGER | Links to material |

## Equipment and Load Tables

### 10. Nominal Equipment Tables
Define design loads and equipment.

- **NominalElectricEquipment**
- **NominalGasEquipment**
- **NominalSteamEquipment**
- **NominalHotWaterEquipment**
- **NominalOtherEquipment**
- **NominalBaseboardHeaters**

Common structure:
| Column | Type | Description |
|--------|------|-------------|
| ObjectIndex | INTEGER | Primary key |
| ObjectName | TEXT | Equipment name |
| ZoneIndex | INTEGER | Links to zone |
| ScheduleIndex | INTEGER | Links to schedule |
| DesignLevel | REAL | Design power (W) |
| FractionLatent | REAL | Latent fraction |
| FractionRadiant | REAL | Radiant fraction |
| FractionLost | REAL | Lost fraction |

### 11. NominalInfiltration
Design infiltration rates.

| Column | Type | Description |
|--------|------|-------------|
| ObjectIndex | INTEGER | Primary key |
| ObjectName | TEXT | Infiltration object name |
| ZoneIndex | INTEGER | Links to zone |
| DesignFlowRate | REAL | Design flow rate (m³/s) |

### 12. NominalVentilation
Design ventilation rates.

| Column | Type | Description |
|--------|------|-------------|
| ObjectIndex | INTEGER | Primary key |
| ObjectName | TEXT | Ventilation object name |
| ZoneIndex | INTEGER | Links to zone |
| DesignFlowRate | REAL | Design flow rate (m³/s) |

## Sizing Result Tables

### 13. ZoneSizes
Zone HVAC sizing results.

| Column | Type | Description |
|--------|------|-------------|
| ZoneSizesIndex | INTEGER | Primary key |
| ZoneName | TEXT | Zone identifier |
| CoolingDesignLoad | REAL | Design cooling load (W) |
| HeatingDesignLoad | REAL | Design heating load (W) |
| CoolingDesignAirFlow | REAL | Design cooling airflow (m³/s) |
| HeatingDesignAirFlow | REAL | Design heating airflow (m³/s) |

### 14. SystemSizes
System sizing results.

| Column | Type | Description |
|--------|------|-------------|
| SystemSizesIndex | INTEGER | Primary key |
| SystemName | TEXT | System identifier |
| CoolingDesignCapacity | REAL | Design cooling capacity (W) |
| HeatingDesignCapacity | REAL | Design heating capacity (W) |
| DesignAirFlow | REAL | Design airflow rate (m³/s) |

### 15. ComponentSizes
Individual component sizing.

| Column | Type | Description |
|--------|------|-------------|
| ComponentSizesIndex | INTEGER | Primary key |
| ComponentType | TEXT | Component type |
| ComponentName | TEXT | Component identifier |
| Description | TEXT | Sizing description |
| Value | REAL | Sized value |
| Units | TEXT | Value units |

## Schedule Tables

### 16. Schedules
Schedule definitions.

| Column | Type | Description |
|--------|------|-------------|
| ScheduleIndex | INTEGER | Primary key |
| ScheduleName | TEXT | Schedule identifier |
| ScheduleType | TEXT | Schedule type/limits |
| ScheduleMinimum | REAL | Minimum value |
| ScheduleMaximum | REAL | Maximum value |

### 17. ScheduleData
Schedule values (if using Schedule:File).

| Column | Type | Description |
|--------|------|-------------|
| ScheduleDataIndex | INTEGER | Primary key |
| ScheduleIndex | INTEGER | Links to schedule |
| HourOfDay | INTEGER | Hour (1-24) |
| DayOfWeek | INTEGER | Day (1-7) |
| Month | INTEGER | Month (1-12) |
| DayOfMonth | INTEGER | Day of month |
| Value | REAL | Schedule value |

## Metadata Tables

### 18. Simulations
Simulation metadata.

| Column | Type | Description |
|--------|------|-------------|
| SimulationIndex | INTEGER | Primary key |
| Version | TEXT | EnergyPlus version |
| TimeStamp | TEXT | Simulation timestamp |
| NumTimesteps | INTEGER | Total timesteps |
| CompletedSuccessfully | INTEGER | 1=Success, 0=Failed |

### 19. Errors
Simulation errors and warnings.

| Column | Type | Description |
|--------|------|-------------|
| ErrorIndex | INTEGER | Primary key |
| ErrorType | INTEGER | 0=Warning, 1=Severe, 2=Fatal |
| ErrorMessage | TEXT | Error description |
| Count | INTEGER | Occurrence count |

## Data Extraction Process

### Time Series Extraction Query
```sql
SELECT 
    t.TimeIndex,
    CASE 
        WHEN t.Hour = 24 THEN datetime(printf('%04d-%02d-%02d 00:00:00', 
            t.Year, t.Month, t.Day), '+1 day')
        ELSE datetime(printf('%04d-%02d-%02d %02d:%02d:00', 
            t.Year, t.Month, t.Day, t.Hour, t.Minute))
    END as DateTime,
    rdd.Name as Variable,
    rdd.KeyValue as Zone,
    rd.Value,
    rdd.Units,
    rdd.ReportingFrequency
FROM ReportData rd
JOIN Time t ON rd.TimeIndex = t.TimeIndex
JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
WHERE rdd.Name IN (variable_list)
AND t.EnvironmentPeriodIndex IN (
    SELECT EnvironmentPeriodIndex 
    FROM EnvironmentPeriods 
    WHERE EnvironmentType = 3  -- Weather file periods only
)
```

### Performance Summary Extraction
```sql
SELECT 
    s2.Value as TableName,
    s3.Value as RowName,
    s4.Value as ColumnName,
    s5.Value as Units,
    td.Value
FROM TabularData td
LEFT JOIN Strings s2 ON td.TableNameIndex = s2.StringIndex
LEFT JOIN Strings s3 ON td.RowNameIndex = s3.StringIndex
LEFT JOIN Strings s4 ON td.ColumnNameIndex = s4.StringIndex
LEFT JOIN Strings s5 ON td.UnitsIndex = s5.StringIndex
WHERE s2.Value = 'End Uses'  -- Or other table name
```

## Data Processing Notes

1. **Time Handling**: Hour=24 represents midnight of the next day
2. **Environment Types**: Type 3 = Weather file runs (exclude design days)
3. **String Lookups**: TabularData uses indirect string references
4. **Zone Keys**: KeyValue can be zone name or 'Environment' for site variables
5. **Frequency Mapping**: Original frequencies preserved, aggregations created upward