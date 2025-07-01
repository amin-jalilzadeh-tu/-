# SQL Static Data Extraction

## Overview

The SQLStaticExtractor extracts non-time series data from EnergyPlus SQL files, including performance summaries, sizing results, building characteristics, and metadata.

## Extracted Data Categories

### 1. Performance Summaries

#### Energy End Uses
Extracted from TabularData table where TableName = 'End Uses':
```python
# Output structure
{
    'ReportName': 'AnnualBuildingUtilityPerformanceSummary',
    'TableName': 'End Uses',
    'RowName': 'Heating',        # End use category
    'Electricity [GJ]': 0.0,     # By fuel type
    'Natural Gas [GJ]': 123.45,
    'District Cooling [GJ]': 0.0,
    'District Heating [GJ]': 0.0,
    'Water [m3]': 0.0,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

End use categories include:
- Heating
- Cooling
- Interior Lighting
- Exterior Lighting
- Interior Equipment
- Exterior Equipment
- Fans
- Pumps
- Heat Rejection
- Humidification
- Heat Recovery
- Water Systems
- Refrigeration
- Generators

#### Site and Source Energy
Extracted from 'Site and Source Energy' table:
```python
{
    'Total Site Energy [GJ]': 456.78,
    'Net Site Energy [GJ]': 456.78,
    'Total Source Energy [GJ]': 912.34,
    'Net Source Energy [GJ]': 912.34,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### Comfort Metrics
From 'Comfort and Setpoint Not Met Summary':
```python
{
    'Facility [Hours]': {
        'Time Setpoint Not Met During Occupied Cooling': 10,
        'Time Setpoint Not Met During Occupied Heating': 5,
        'Time Not Comfortable Based on Simple ASHRAE 55-2004': 15
    },
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### Energy Intensity
From 'Utility Use Per Conditioned Floor Area':
```python
{
    'Electricity Intensity [MJ/m2]': 234.5,
    'Natural Gas Intensity [MJ/m2]': 456.7,
    'Total Energy Intensity [MJ/m2]': 691.2,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### Peak Demands
From 'DemandEndUseComponentsSummary':
```python
{
    'TableName': 'End Uses',
    'EndUse': 'Cooling',
    'Metric': 'Electricity Peak Demand',
    'Units': 'W',
    'Value': 45678.9,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

### 2. Sizing Data

#### Zone Sizing
From ZoneSizes table:
```python
{
    'ZoneName': 'THERMAL ZONE 1',
    'LoadType': 'Cooling',
    'CalcDesLoad': 12345.6,      # W
    'UserDesLoad': 13500.0,       # W
    'CalcDesAirFlow': 0.567,      # m3/s
    'UserDesAirFlow': 0.600,      # m3/s
    'DesDayName': 'CHICAGO ANN CLG .4% CONDNS DB=>MWB',
    'PeakHrMin': '15:00',
    'PeakTemp': 32.5,             # C
    'PeakHumRat': 0.015,          # kg/kg
    'CalcOutAirFlow': 0.025,      # m3/s
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### System Sizing
From SystemSizes table:
```python
{
    'SystemName': 'VAV SYS 1',
    'LoadType': 'Cooling',
    'PeakLoadType': 'Sensible',
    'UserDesCap': 45000.0,        # W
    'CalcDesVolFlow': 2.345,      # m3/s
    'UserDesVolFlow': 2.500,      # m3/s
    'DesDayName': 'CHICAGO ANN CLG .4% CONDNS DB=>MWB',
    'PeakHrMin': '15:00',
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### Component Sizing
From ComponentSizes table:
```python
{
    'CompType': 'Coil:Cooling:DX:SingleSpeed',
    'CompName': 'Main Cooling Coil',
    'Description': 'Rated Total Cooling Capacity',
    'Value': 35000.0,
    'Units': 'W',
    'building_id': '4136733',
    'variant_id': 'base'
}
```

### 3. Building Characteristics

#### Zone Information
From Zones table and related tables:
```python
{
    'ZoneName': 'THERMAL ZONE 1',
    'RelNorth': 0.0,              # degrees
    'OriginX': 0.0,               # m
    'OriginY': 0.0,               # m
    'OriginZ': 0.0,               # m
    'CentroidX': 10.5,            # m
    'CentroidY': 8.3,             # m
    'CentroidZ': 1.5,             # m
    'Volume': 450.0,              # m3
    'FloorArea': 150.0,           # m2
    'Multiplier': 1,
    'ListMultiplier': 1,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### Construction Layers
Combining Constructions and ConstructionLayers:
```python
{
    'ConstructionName': 'Exterior Wall',
    'LayerIndex': 1,
    'MaterialIndex': 5,
    'MaterialName': 'Brick',
    'Thickness': 0.1,             # m
    'Conductivity': 0.72,         # W/m-K
    'Density': 1920.0,            # kg/m3
    'SpecificHeat': 790.0,        # J/kg-K
    'TotalThickness': 0.35,       # m
    'TotalRValue': 2.45,          # m2-K/W
    'building_id': '4136733',
    'variant_id': 'base'
}
```

#### Surface Summary
From TabularData 'Opaque Exterior' and other surface reports:
```python
{
    'Surface Type': 'ExteriorWall',
    'Construction': 'Exterior Wall',
    'Reflectance': 0.22,
    'U-Factor [W/m2-K]': 0.408,
    'Gross Area [m2]': 125.4,
    'Net Area [m2]': 98.7,
    'Azimuth [deg]': 180.0,
    'Tilt [deg]': 90.0,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

### 4. Metadata

#### Simulation Information
From multiple sources:
```python
{
    'ProgramVersion': 'EnergyPlus, Version 24.1.0-abc123',
    'TimeStamp': '2024-01-07 10:30:45',
    'RunPeriod': {
        'StartDate': '2023-01-01',
        'EndDate': '2023-12-31',
        'DaysSimulated': 365
    },
    'Location': {
        'LocationName': 'Chicago Ohare Intl Ap',
        'Latitude': 41.98,
        'Longitude': -87.92,
        'Elevation': 201.0,
        'TimeZone': -6.0
    },
    'building_id': '4136733',
    'variant_id': 'base'
}
```

## Schedule Data Extraction

The ScheduleExtractor handles schedule-specific data:

### Schedule Metadata
From Schedules table:
```python
{
    'ScheduleIndex': 1,
    'ScheduleName': 'OFFICE OCCUPANCY',
    'ScheduleType': 'Fraction',
    'ScheduleTypeLimitsName': 'Fraction',
    'building_id': '4136733',
    'variant_id': 'base'
}
```

### Schedule Usage
Links schedules to equipment:
```python
{
    'ObjectName': 'OFFICE LIGHTS',
    'ZoneIndex': 1,
    'ScheduleIndex': 5,
    'ScheduleName': 'OFFICE LIGHTING SCHEDULE',
    'EquipmentType': 'Lighting',
    'building_id': '4136733',
    'variant_id': 'base'
}
```

### Schedule Time Series
If reported, actual schedule values:
```python
{
    'ScheduleName': 'OFFICE OCCUPANCY',
    'DateTime': '2023-01-01 08:00:00',
    'Value': 0.95,
    'building_id': '4136733',
    'variant_id': 'base'
}
```

## Output Directory Structure

Static data is organized by category:

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
├── zone_information.parquet
├── construction_layers.parquet
├── surface_summary.parquet
└── internal_gains_summary.parquet

metadata/
├── simulation_info.parquet
├── location_weather.parquet
└── validation_results.parquet

schedules/
├── schedule_metadata.parquet
├── schedule_usage.parquet
└── schedule_patterns.parquet
```

## Data Saving Strategy

The extractor uses an append strategy to handle multiple buildings:

```python
def _save_or_append(self, df: pd.DataFrame, output_path: Path):
    """Save or append data to parquet file"""
    if output_path.exists():
        # Append to existing file
        existing_df = pd.read_parquet(output_path)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df.to_parquet(output_path, index=False)
    else:
        # Create new file
        df.to_parquet(output_path, index=False)
```

This ensures all buildings and variants are collected in single files per data type.