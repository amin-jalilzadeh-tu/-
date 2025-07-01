# Simulation Control Parsing Documentation

## Overview
The simulation control parsing module extracts fundamental simulation parameters, building information, site data, and calculation methods from IDF files. These settings control how EnergyPlus performs the energy simulation.

## IDF Objects Parsed

### 1. VERSION
EnergyPlus version specification.

**Parameters Extracted:**
- Version Identifier (e.g., "9.6")

### 2. SIMULATIONCONTROL
Master control for simulation options.

**Parameters Extracted:**
- Do Zone Sizing Calculation (Yes/No)
- Do System Sizing Calculation (Yes/No)
- Do Plant Sizing Calculation (Yes/No)
- Run Simulation for Sizing Periods (Yes/No)
- Run Simulation for Weather File Run Periods (Yes/No)
- Do HVAC Sizing Simulation for Sizing Periods (Yes/No)
- Maximum Number of HVAC Sizing Simulation Passes

### 3. BUILDING
Overall building parameters.

**Parameters Extracted:**
- Building Name
- North Axis (degrees)
- Terrain (Country, Suburbs, City, Ocean, Urban)
- Loads Convergence Tolerance Value
- Temperature Convergence Tolerance Value (°C)
- Solar Distribution (FullExterior, FullInteriorAndExterior, etc.)
- Maximum Number of Warmup Days
- Minimum Number of Warmup Days

### 4. TIMESTEP
Number of timesteps per hour.

**Parameters Extracted:**
- Number of Timesteps per Hour (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60)

### 5. SITE:LOCATION
Geographic location and climate data.

**Parameters Extracted:**
- Location Name
- Latitude (degrees, + North)
- Longitude (degrees, + East)
- Time Zone (hours from GMT)
- Elevation (m)

### 6. SITE:GROUNDTEMPERATURE:BUILDINGSURFACE
Monthly ground temperatures.

**Parameters Extracted:**
- January through December Ground Temperatures (°C)

### 7. SITE:WATERMAINSTEMPERATURE
Water mains temperature calculation.

**Parameters Extracted:**
- Calculation Method (Schedule, Correlation, CorrelationFromWeatherFile)
- Temperature Schedule Name
- Annual Average Outdoor Air Temperature (°C)
- Maximum Difference In Monthly Average Temperatures (°C)

### 8. SITE:PRECIPITATION
Precipitation modeling for moisture calculations.

**Parameters Extracted:**
- Precipitation Model Type
- Design/Nominal Precipitation Rate
- Schedule Name

### 9. SIZINGPERIOD:DESIGNDAY
Design day definitions for equipment sizing.

**Parameters Extracted:**
- Design Day Name
- Month and Day of Month
- Day Type
- Maximum/Minimum Dry-Bulb Temperature (°C)
- Daily Dry-Bulb Temperature Range (°C)
- Dry-Bulb Temperature Range Modifier Type
- Humidity Condition Type
- Wetbulb or Dewpoint at Maximum Dry-Bulb (°C)
- Barometric Pressure (Pa)
- Wind Speed (m/s) and Direction (degrees)
- Sky Clearness
- Rain Indicator
- Snow Indicator
- Solar Model Indicator

### 10. RUNPERIOD
Simulation period definition.

**Parameters Extracted:**
- Run Period Name
- Begin Month and Day of Month
- End Month and Day of Month
- Day of Week for Start Day
- Use Weather File Holidays and Special Days (Yes/No)
- Use Weather File Daylight Saving Period (Yes/No)
- Apply Weekend Holiday Rule (Yes/No)
- Use Weather File Rain Indicators (Yes/No)
- Use Weather File Snow Indicators (Yes/No)

### 11. RUNPERIOD:CUSTOMRANGE
Custom simulation period.

**Parameters Extracted:**
- Run Period Name
- Begin Month/Day/Year
- End Month/Day/Year
- Day of Week for Start Day
- Use Weather File Holidays/Special Days/DST/Rain/Snow settings

### 12. RUNPERIODCONTROL:SPECIALDAYS
Holiday and special day definitions.

**Parameters Extracted:**
- Special Day Name
- Start Date
- Duration (days)
- Special Day Type

### 13. RUNPERIODCONTROL:DAYLIGHTSAVINGTIME
Daylight saving time period.

**Parameters Extracted:**
- Start Date (Month/Day)
- End Date (Month/Day)

### 14. SHADOWCALCULATION
Solar shading calculation parameters.

**Parameters Extracted:**
- Shading Calculation Method
- Shading Calculation Update Frequency Method
- Shading Calculation Update Frequency
- Maximum Figures in Shadow Overlap Calculations
- Polygon Clipping Algorithm
- Pixel Counting Resolution
- Sky Diffuse Modeling Algorithm

### 15. SURFACECONVECTIONALGORITHM:INSIDE
Interior surface convection algorithm.

**Parameters Extracted:**
- Algorithm (Simple, TARP, CeilingDiffuser, AdaptiveConvectionAlgorithm)

### 16. SURFACECONVECTIONALGORITHM:OUTSIDE
Exterior surface convection algorithm.

**Parameters Extracted:**
- Algorithm (SimpleCombined, TARP, DOE-2, MoWiTT, AdaptiveConvectionAlgorithm)

### 17. HEATBALANCEALGORITHM
Heat balance solution algorithm.

**Parameters Extracted:**
- Algorithm (ConductionTransferFunction, MoisturePenetrationDepthConductionTransferFunction, ConductionFiniteDifference, CombinedHeatAndMoistureFiniteElement)
- Surface Temperature Upper Limit (°C)
- Minimum Surface Convection Heat Transfer Coefficient Value (W/m²-K)
- Maximum Surface Convection Heat Transfer Coefficient Value (W/m²-K)

### 18. CONVERGENCELIMITS
Convergence tolerance settings.

**Parameters Extracted:**
- Minimum System Timestep (minutes)
- Maximum HVAC Iterations
- Minimum Plant Iterations
- Maximum Plant Iterations

## Key Simulation Settings

### 1. Time Resolution
- Timesteps per hour affects accuracy and computation time
- Higher timesteps needed for fast-responding systems

### 2. Solar Distribution
- **MinimalShadowing**: Only self-shading, no shading from other surfaces
- **FullExterior**: Full exterior solar reflection, no interior
- **FullInteriorAndExterior**: Most detailed calculation

### 3. Terrain Type
Affects wind speed profiles:
- **Country**: Open terrain
- **Suburbs**: Some obstructions
- **City**: Urban environment
- **Ocean**: Open water
- **Urban**: Dense urban

### 4. Warmup Period
- Simulation runs until convergence before actual period
- Ensures initial conditions don't affect results

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        ├── simulation_control.parquet
        └── site_location.parquet
```

**simulation_control.parquet columns:**
- building_id
- object_type
- parameter_name
- parameter_value
- units

**site_location.parquet columns:**
- building_id
- latitude
- longitude
- timezone
- elevation
- ground_temperatures
- climate_zone (if specified)

## Data Processing Notes

1. **Version Compatibility**: Parser handles multiple EnergyPlus versions.

2. **Default Values**: Many parameters have defaults if not specified.

3. **Interdependencies**: Some settings affect available options for others.

4. **Climate Data**: Site location must match weather file location.

5. **Design Days**: Used for HVAC equipment sizing calculations.

## Quality Checks

1. **Location Verification**: Latitude/longitude match weather file.

2. **Timestep Selection**: 4-6 timesteps/hour typical for most buildings.

3. **Terrain Consistency**: Match actual building surroundings.

4. **Temperature Limits**: Check convergence tolerance values are reasonable.

5. **Solar Settings**: Higher detail increases accuracy but slows simulation.

## Impact on Simulation

### Performance Impact
- Timesteps: Linear impact on simulation time
- Solar distribution: Can increase time 2-5x
- Shadow calculations: Major impact with complex geometry

### Accuracy Impact
- Timesteps: Affects system control accuracy
- Solar distribution: Affects solar heat gains
- Convergence limits: Affects solution stability

## Special Considerations

1. **Warmup Days**: May need adjustment for buildings with high thermal mass.

2. **Design Days**: Critical for proper HVAC sizing.

3. **Ground Temperatures**: Significantly affect ground-contact heat transfer.

4. **Algorithm Selection**: Some algorithms needed for specific features (e.g., moisture).

5. **Location Accuracy**: Small changes in location can affect solar calculations.