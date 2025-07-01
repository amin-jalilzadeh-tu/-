# SQL Time Series Data Extraction

## Overview

The EnhancedSQLAnalyzer extracts time series data from EnergyPlus SQL files, categorizes variables, and manages different reporting frequencies.

## Variable Categories

The system categorizes variables into specific groups for organized extraction:

### 1. Energy Meters
```python
'energy_meters': [
    'Electricity:Facility',      # Total facility electricity
    'Electricity:Building',      # Building electricity 
    'Electricity:HVAC',          # HVAC electricity
    'Gas:Facility',              # Natural gas usage
    'Gas:Building',              
    'DistrictCooling:Facility',  # District cooling
    'DistrictHeating:Facility',  # District heating
    'Cooling:EnergyTransfer',    # Cooling energy
    'Heating:EnergyTransfer',    # Heating energy
    'HeatRejection:EnergyTransfer'
]
```

### 2. Site Weather
```python
'site_weather': [
    'Site Outdoor Air Drybulb Temperature',
    'Site Outdoor Air Wetbulb Temperature',
    'Site Outdoor Air Relative Humidity',
    'Site Wind Speed',
    'Site Wind Direction',
    'Site Diffuse Solar Radiation Rate per Area',
    'Site Direct Solar Radiation Rate per Area',
    'Site Rain Status',
    'Site Snow Depth',
    'Site Ground Temperature'
]
```

### 3. Zone Conditions (Geometry)
```python
'geometry': [
    'Zone Mean Air Temperature',
    'Zone Air Temperature',
    'Zone Operative Temperature',
    'Zone Thermal Comfort Mean Radiant Temperature',
    'Zone Mean Radiant Temperature',
    'Zone Air Relative Humidity',
    'Zone Air Humidity Ratio'
]
```

### 4. Surface/Materials
```python
'materials': [
    'Surface Inside Face Temperature',
    'Surface Outside Face Temperature',
    'Surface Inside Face Conduction Heat Transfer Rate',
    'Surface Outside Face Conduction Heat Transfer Rate',
    'Surface Inside Face Convection Heat Transfer Rate',
    'Surface Outside Face Convection Heat Transfer Rate',
    'Surface Inside Face Net Surface Thermal Radiation Heat Gain Rate',
    'Surface Window Heat Gain Rate',
    'Surface Window Heat Loss Rate'
]
```

### 5. Domestic Hot Water (DHW)
```python
'dhw': [
    'Water Heater Heating Energy',
    'Water Heater Heating Rate',
    'Water Heater Tank Temperature',
    'Water Heater Heat Loss Energy',
    'Water Use Equipment Hot Water Volume',
    'Water Use Equipment Cold Water Volume',
    'Water Use Equipment Total Volume',
    'Water Use Equipment Hot Water Temperature'
]
```

### 6. Equipment
```python
'equipment': [
    'Zone Electric Equipment Electricity Energy',
    'Zone Electric Equipment Electricity Rate',
    'Zone Electric Equipment Total Heating Energy',
    'Zone Electric Equipment Total Heating Rate',
    'Zone Gas Equipment Gas Energy',
    'Zone Gas Equipment Gas Rate',
    'Zone Other Equipment Total Heating Energy',
    'Zone Other Equipment Total Heating Rate'
]
```

### 7. Lighting
```python
'lighting': [
    'Zone Lights Electricity Energy',
    'Zone Lights Electricity Rate',
    'Zone Lights Total Heating Energy',
    'Zone Lights Total Heating Rate',
    'Zone Lights Visible Radiation Rate',
    'Daylighting Reference Point Illuminance',
    'Daylighting Lighting Power Multiplier'
]
```

### 8. HVAC
```python
'hvac': [
    'Zone Air System Sensible Cooling Energy',
    'Zone Air System Sensible Heating Energy',
    'Zone Air System Sensible Cooling Rate',
    'Zone Air System Sensible Heating Rate',
    'Zone Ideal Loads Zone Sensible Cooling Rate',
    'Zone Ideal Loads Zone Sensible Heating Rate',
    'Zone Thermostat Heating Setpoint Temperature',
    'Zone Thermostat Cooling Setpoint Temperature',
    'Fan Electricity Energy',
    'Fan Electricity Rate',
    'Cooling Coil Total Cooling Energy',
    'Heating Coil Heating Energy'
]
```

### 9. Ventilation
```python
'ventilation': [
    'Zone Mechanical Ventilation Mass Flow Rate',
    'Zone Mechanical Ventilation Volume Flow Rate',
    'Zone Mechanical Ventilation Air Change Rate',
    'Zone Ventilation Air Change Rate',
    'Zone Ventilation Volume',
    'Zone Ventilation Mass',
    'Zone Ventilation Sensible Heat Loss Energy',
    'Zone Ventilation Sensible Heat Gain Energy',
    'System Node Mass Flow Rate',
    'System Node Volume Flow Rate'
]
```

### 10. Infiltration
```python
'infiltration': [
    'Zone Infiltration Air Change Rate',
    'Zone Infiltration Volume',
    'Zone Infiltration Mass',
    'Zone Infiltration Mass Flow Rate',
    'Zone Infiltration Sensible Heat Loss Energy',
    'Zone Infiltration Sensible Heat Gain Energy',
    'Zone Infiltration Latent Heat Loss Energy',
    'Zone Infiltration Latent Heat Gain Energy'
]
```

### 11. Shading
```python
'shading': [
    'Surface Window Transmitted Solar Radiation Rate',
    'Surface Window Transmitted Beam Solar Radiation Rate',
    'Surface Window Transmitted Diffuse Solar Radiation Rate',
    'Zone Windows Total Transmitted Solar Radiation Rate',
    'Zone Windows Total Heat Gain Rate',
    'Zone Windows Total Heat Loss Rate',
    'Surface Shading Device Is On Time Fraction',
    'Surface Window Blind Slat Angle'
]
```

## Extraction Process

### 1. SQL Query Structure

The system uses this SQL query to extract time series data:

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
WHERE rdd.Name IN (?)  -- Variable list
AND t.EnvironmentPeriodIndex IN (
    SELECT EnvironmentPeriodIndex 
    FROM EnvironmentPeriods 
    WHERE EnvironmentType = 3  -- Run period
)
AND date(printf('%04d-%02d-%02d', t.Year, t.Month, t.Day)) BETWEEN ? AND ?
ORDER BY t.TimeIndex, rdd.Name
```

### 2. Data Processing Steps

1. **Variable Availability Check**: Query ReportDataDictionary for available variables
2. **Date Range Determination**: Get simulation period if not specified
3. **Data Extraction**: Execute main query for selected variables
4. **Category Assignment**: Add category to each variable row
5. **DateTime Conversion**: Convert to pandas datetime format
6. **Metadata Addition**: Add building_id and variant_id

### 3. Output Data Structure

Each extracted row contains:
```python
{
    'TimeIndex': 1234,
    'DateTime': '2023-01-01 01:00:00',
    'Variable': 'Zone Air Temperature',
    'Zone': 'THERMAL ZONE 1',
    'Value': 20.5,
    'Units': 'C',
    'ReportingFrequency': 'Hourly',
    'category': 'geometry',
    'building_id': '4136733',
    'variant_id': 'base'  # or 'variant_0', 'variant_1', etc.
}
```

## Frequency Handling

### Reporting Frequencies
EnergyPlus can report variables at different frequencies:
- **Detailed**: Every simulation timestep
- **Timestep**: Each simulation timestep
- **Hourly**: Hourly values
- **Daily**: Daily aggregates
- **Monthly**: Monthly aggregates
- **RunPeriod**: Single value for entire simulation

### Aggregation Methods
The system uses appropriate aggregation for different variable types:
- **Energy variables**: Sum
- **Rate/Power variables**: Mean
- **Temperature variables**: Mean
- **Count variables**: Sum

## Output Storage

### Raw Data Storage
Raw extracted data is temporarily stored:
```
temp_raw/
├── base/
│   └── all_variables_base_20250107_103045.parquet
└── variants/
    └── all_variables_variant_0_20250107_103046.parquet
```

### Transformed Storage
After transformation to semi-wide format:
```
timeseries/
├── base_all_hourly.parquet
├── base_all_daily.parquet
└── base_all_monthly.parquet
```

## Special Handling

### 1. Hour 24 Issue
EnergyPlus uses hour 24 (instead of hour 0), which requires special handling:
```python
WHEN t.Hour = 24 THEN datetime(..., '+1 day')
```

### 2. Environment Period Filtering
Only extracts data from actual run periods (EnvironmentType = 3), excluding:
- Design days
- Sizing periods
- Weather file statistics

### 3. Zone Mapping
The system accepts zone mappings to rename zones in output:
```python
zone_mapping = {
    'THERMAL ZONE 1': 'Zone_Office_1',
    'THERMAL ZONE 2': 'Zone_Conference'
}
```

## Performance Optimization

1. **Batch Extraction**: Extracts multiple variables in single query
2. **Category Grouping**: Processes related variables together
3. **Temporary Storage**: Uses parquet for efficient intermediate storage
4. **Lazy Transformation**: Transforms data only when needed