# Site Location Modifications System

## Overview
The site location modification system handles geographical and climate-related parameters in EnergyPlus IDF files. This includes location coordinates, elevation, ground temperatures, design day conditions, and simulation period settings. These parameters are crucial for accurate climate-responsive energy modeling.

## Modified Object Types

### Location and Climate
- `SITE:LOCATION` - Geographic coordinates and elevation
- `SITE:GROUNDTEMPERATURE:BUILDINGSURFACE` - Monthly ground temperatures
- `SITE:GROUNDTEMPERATURE:FCfactorMethod` - F-factor ground temperatures
- `SITE:GROUNDTEMPERATURE:SHALLOW` - Shallow ground temperatures
- `SITE:GROUNDTEMPERATURE:DEEP` - Deep ground temperatures
- `SITE:GROUNDREFLECTANCE` - Ground solar reflectance
- `SITE:HEIGHTVARIATION` - Wind profile parameters
- `SITE:WATERMAINSTEMPERATURE` - Water supply temperatures

### Simulation Periods
- `SIZINGPERIOD:DESIGNDAY` - Equipment sizing conditions
- `SIZINGPERIOD:WEATHERFILECONDITIONTYPE` - Weather file extremes
- `SIZINGPERIOD:WEATHERFILEDAYS` - Specific weather file days
- `RUNPERIOD` - Simulation period definition
- `RUNPERIODCONTROL:SPECIALDAYS` - Holidays and special days
- `RUNPERIODCONTROL:DAYLIGHTSAVINGTIME` - Daylight saving time

## Parameters Modified

### SITE:LOCATION Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `latitude` | Latitude | 1 | float | degrees | -90 to 90 | solar_angles |
| `longitude` | Longitude | 2 | float | degrees | -180 to 180 | solar_timing |
| `time_zone` | Time Zone | 3 | float | hours | -12 to 14 | solar_timing |
| `elevation` | Elevation | 4 | float | m | -300 to 8848 | air_pressure |

### Ground Temperature Parameters (Monthly)

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `ground_temp_january` | January Ground Temperature | 0 | float | °C | -30 to 40 | ground_heat_transfer |
| `ground_temp_february` | February Ground Temperature | 1 | float | °C | -30 to 40 | ground_heat_transfer |
| ... | ... | ... | ... | ... | ... | ... |
| `ground_temp_december` | December Ground Temperature | 11 | float | °C | -30 to 40 | ground_heat_transfer |

### Design Day Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `design_day_max_temp` | Maximum Dry-Bulb Temperature | 1 | float | °C | -50 to 60 | equipment_sizing |
| `design_day_min_temp` | Minimum Dry-Bulb Temperature | 2 | float | °C | -50 to 60 | equipment_sizing |
| `design_day_humidity` | Humidity Condition at Maximum Dry-Bulb | 10 | float | kgWater/kgDryAir | 0 to 0.03 | equipment_sizing |

### Run Period Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `begin_month` | Begin Month | 1 | int | - | 1-12 | simulation_period |
| `begin_day` | Begin Day of Month | 2 | int | - | 1-31 | simulation_period |
| `end_month` | End Month | 3 | int | - | 1-12 | simulation_period |
| `end_day` | End Day of Month | 4 | int | - | 1-31 | simulation_period |

### Other Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `wind_sensor_height` | Wind Sensor Height Above Ground | 0 | float | m | 0.5-100 | wind_calculations |

## Modification Strategies

### 1. Climate Adjustment (`climate_adjustment`)
- **Purpose**: Study climate change impacts
- **Modifications**:
  - Elevation: ±200 to 500m adjustment
  - Ground temperatures: +1 to 3°C warming
  - Represents:
    - Future climate scenarios
    - Elevation sensitivity studies
    - Ground warming effects
  - Applications:
    - Climate resilience planning
    - Future-proofing designs

### 2. Extreme Weather (`extreme_weather`)
- **Purpose**: Test building resilience
- **Modifications**:
  - Cooling design days: +3 to 5°C
  - Heating design days: -3 to 5°C
  - Based on climate extremes
  - Tests:
    - Equipment sizing adequacy
    - Passive survivability
    - Peak load conditions

### 3. Ground Coupling (`ground_coupling`)
- **Purpose**: Optimize ground heat exchange
- **Modifications**:
  - Reduces ground temperature variation by 50%
  - Creates more stable temperatures
  - Benefits:
    - Earth-coupled buildings
    - Basement thermal analysis
    - Slab-on-grade optimization

### 4. Seasonal Analysis (`seasonal_analysis`)
- **Purpose**: Focus on specific seasons
- **Modifications**:
  - Summer: June-August
  - Winter: December-February
  - Spring: March-May
  - Fall: September-November
  - Enables:
    - Season-specific optimization
    - Reduced simulation time
    - Targeted analysis

## Process Flow

### 1. Location Analysis
```
Site Parameters → Extract Current Values
               → Identify Modification Goals
               → Apply Strategy Rules
```

### 2. Temperature Adjustments
```
Ground Temperatures → Calculate Average
                   → Apply Warming/Damping
                   → Maintain Monthly Pattern
                   → Update All Months
```

### 3. Period Configuration
```
Run Period → Determine Season/Dates
          → Update Month/Day Values
          → Ensure Valid Date Ranges
          → Handle Year Boundaries
```

## Integration Notes

### Climate Data Sources
1. **Weather Files**: Primary climate data (EPW files)
2. **Design Days**: From ASHRAE climate data
3. **Ground Temperatures**: From local measurements or calculations
4. **Elevation**: From site surveys or maps

### Common Use Cases
1. **Climate Studies**: Future weather scenarios
2. **Site Comparison**: Multiple location analysis
3. **Extreme Events**: Resilience testing
4. **Optimization**: Season-specific strategies
5. **Code Compliance**: Local climate requirements

### Performance Impact
- **Solar Gains**: Strong latitude dependence
- **Ground Coupling**: 5-20% of heating/cooling
- **Design Sizing**: Critical for equipment capacity
- **Wind Effects**: Elevation and terrain impacts

## Technical Implementation Details

### Ground Temperature Models
```
Typical Profile:
- Surface temperatures lag air by 1-2 months
- Amplitude decreases with depth
- Deep ground ≈ annual average air temperature
```

### Monthly Ground Temperature Patterns
| Month | Typical Range | Peak Lag |
|-------|--------------|-----------|
| January | Cold climates: -5 to 5°C | 1-2 months behind air |
| July | Hot climates: 20 to 30°C | 1-2 months behind air |

### Elevation Effects
```
Temperature: -6.5°C per 1000m elevation gain
Pressure: -12% per 1000m elevation gain
Solar Intensity: +3% per 1000m elevation gain
```

### Design Day Selection
| Type | Purpose | Typical Conditions |
|------|---------|-------------------|
| Summer Cooling | Size cooling equipment | 99.6% or 99% design temp |
| Winter Heating | Size heating equipment | 0.4% or 1% design temp |
| Humidity | Dehumidification sizing | Coincident wetbulb |

### Seasonal Run Periods
```python
Season definitions:
- Winter: Dec 21 - Mar 20 (may span year boundary)
- Spring: Mar 21 - Jun 20
- Summer: Jun 21 - Sep 20
- Fall: Sep 21 - Dec 20
```

### Error Handling
- Validate latitude/longitude ranges
- Check elevation reasonableness
- Ensure ground temps are plausible
- Handle month boundaries correctly

### Best Practices
1. **Use Local Data**: Site-specific ground temperatures
2. **Consider Microclimate**: Urban heat island effects
3. **Future Climate**: Use projected weather files
4. **Validate Extremes**: Check design day selection
5. **Document Sources**: Track data provenance

### Special Considerations

#### Ground Temperature Selection
1. **Building Surface**: For slab-on-grade
2. **Shallow**: 0.5m depth for shallow foundations
3. **Deep**: 4m depth for basements
4. **FCfactor Method**: Simplified approach

#### Time Zone Impacts
- Solar noon timing
- Schedule coordination
- Daylight saving time handling

#### Elevation Impacts
1. **Air Density**: Affects fan power
2. **Boiling Point**: Affects equipment operation
3. **Solar Radiation**: Higher at elevation
4. **Temperature**: Cooler at elevation

### Common Issues
1. **Wrong Ground Temps**: Using defaults instead of local
2. **Time Zone Errors**: Incorrect solar timing
3. **Elevation Neglect**: Missing pressure effects
4. **Season Spanning**: Winter crossing year boundary
5. **Design Day Mismatch**: Not representing actual extremes