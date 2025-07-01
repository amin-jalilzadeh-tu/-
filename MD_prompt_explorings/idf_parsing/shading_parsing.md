# Shading Parsing Documentation

## Overview
The shading parsing module extracts shading device and control data from IDF files and SQL simulation results. This includes fixed shading surfaces, window shading controls, and movable shading devices.

## IDF Objects Parsed

### 1. Window Shading Control

#### WINDOWSHADINGCONTROL
Controls for movable window shading devices.

**Parameters Extracted:**
- Shading Control Name
- Zone Name
- Shading Control Sequence Number
- `shading_type`: Shading Type (InteriorShade, ExteriorShade, ExteriorScreen, InteriorBlind, ExteriorBlind, BetweenGlassShade, BetweenGlassBlind, SwitchableGlazing)
- `construction`: Construction with Shading Name
- `control_type`: Shading Control Type:
  - AlwaysOn, AlwaysOff, OnIfScheduleAllows
  - OnIfHighSolarOnWindow, OnIfHighHorizontalSolar
  - OnIfHighOutdoorAirTemperature, OnIfHighZoneAirTemperature
  - OnIfHighZoneCooling, OnIfHighGlare
  - MeetDaylightIlluminanceSetpoint
  - OnNightIfLowOutdoorTempAndOffDay
- `schedule`: Shading Control Schedule Name
- `setpoint`: Setpoint (W/m², °C, or lux depending on control type)
- Shading Control Is Scheduled (Yes/No)
- `glare_control`: Glare Control Is Active (Yes/No)
- `slat_angle`: Slat Angle Schedule Name
- Multiple Surface Name entries

### 2. Fixed Shading Surfaces

#### SHADING:SITE
Fixed shading surface not attached to building.

**Parameters Extracted:**
- Shading Surface Name
- Transmittance Schedule Name
- Number of Vertices
- Vertex X,Y,Z coordinates
- Calculated area and orientation

#### SHADING:SITE:DETAILED
Detailed site shading with more options.

**Parameters Extracted:**
- Same as SHADING:SITE plus:
- Transmittance Schedule Name
- Number of Vertices (up to 120)
- Vertex coordinates

#### SHADING:BUILDING
Fixed shading attached to building.

**Parameters Extracted:**
- Shading Surface Name
- Transmittance Schedule Name
- Number of Vertices
- Vertex coordinates

#### SHADING:BUILDING:DETAILED
Detailed building shading.

**Parameters Extracted:**
- Same as SHADING:BUILDING:DETAILED

#### SHADING:ZONE
Shading surface within a thermal zone.

**Parameters Extracted:**
- Shading Surface Name
- Base Surface Name (host surface)
- Transmittance Schedule Name
- Number of Vertices
- Vertex coordinates

#### SHADING:ZONE:DETAILED
Detailed zone shading.

**Parameters Extracted:**
- Same as SHADING:ZONE

### 3. Simplified Shading Objects

#### SHADING:OVERHANG
Horizontal projection above window.

**Parameters Extracted:**
- Shading Surface Name
- Window or Door Name
- Height above Window or Door (m)
- Tilt Angle from Window/Door (degrees)
- Left Extension from Window/Door Width (m)
- Right Extension from Window/Door Width (m)
- Depth (m)

#### SHADING:OVERHANG:PROJECTION
Overhang specified by projection factor.

**Parameters Extracted:**
- Shading Surface Name
- Window or Door Name
- Height above Window or Door (m)
- Tilt Angle from Window/Door (degrees)
- Left Extension from Window/Door Width (m)
- Right Extension from Window/Door Width (m)
- Depth as Fraction of Window/Door Height

#### SHADING:FIN
Vertical projection beside window.

**Parameters Extracted:**
- Shading Surface Name
- Window or Door Name
- Left Extension from Window/Door (m)
- Left Distance Above Top of Window (m)
- Left Distance Below Bottom of Window (m)
- Left Tilt Angle from Window/Door (degrees)
- Left Depth (m)
- Right Extension from Window/Door (m)
- Right Distance Above Top of Window (m)
- Right Distance Below Bottom of Window (m)
- Right Tilt Angle from Window/Door (degrees)
- Right Depth (m)

#### SHADING:FIN:PROJECTION
Fin specified by projection factor.

**Parameters Extracted:**
- Same as SHADING:FIN but depths specified as fractions

## SQL Variables Extracted

1. **Surface Shading Device Is On Time Fraction** (-)
2. **Surface Window Blind Slat Angle** (degrees)
3. **Surface Window Shading Device Absorbed Solar Radiation Rate** (W)
4. **Surface Window Shading Device Absorbed Solar Radiation Energy** (J)
5. **Surface Window Transmitted Solar Radiation Rate** (W)
6. **Surface Window Transmitted Solar Radiation Energy** (J)
7. **Surface Outside Face Incident Solar Radiation Rate per Area** (W/m²)
8. **Surface Outside Face Incident Beam Solar Radiation Rate per Area** (W/m²)
9. **Surface Outside Face Incident Sky Diffuse Solar Radiation Rate per Area** (W/m²)
10. **Surface Outside Face Incident Ground Diffuse Solar Radiation Rate per Area** (W/m²)
11. **Zone Windows Total Transmitted Solar Radiation Rate** (W)
12. **Zone Windows Total Transmitted Solar Radiation Energy** (J)
13. **Zone Exterior Windows Total Transmitted Beam Solar Radiation Rate** (W)
14. **Zone Exterior Windows Total Transmitted Diffuse Solar Radiation Rate** (W)

## Key Metrics Calculated

1. **Shading Effectiveness**
   - Reduction in solar heat gain due to shading
   - Percentage of time shading is deployed
   - Units: % reduction

2. **Solar Heat Gain Reduction**
   - Difference in transmitted solar with/without shading
   - Units: kWh

3. **Annual Shading Hours**
   - Total hours when movable shading is deployed
   - Breakdown by control trigger (temperature, solar, glare)

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── shading.parquet
```

**Columns in shading.parquet:**
- building_id
- zone_name (if applicable)
- shading_surface_name
- shading_type
- host_surface_name
- control_parameters
- geometry_data
- transmittance_schedule
- control_schedule
- setpoint_values

### SQL Timeseries Output
Shading-related variables in timeseries files track solar radiation and shading device status.

## Data Processing Notes

1. **Geometry Calculation**: Fixed shading geometry affects solar calculations year-round.

2. **Control Logic**: Multiple control types can trigger shading deployment.

3. **Solar Angles**: Shading effectiveness varies with sun position.

4. **Transmittance**: Some shading allows partial light transmission.

5. **Multi-Surface Control**: One control can operate shading on multiple windows.

## Shading Strategies

### Fixed Shading
- Overhangs for summer sun control
- Fins for east/west sun control
- Optimized for specific orientations

### Movable Shading
- Deploy based on solar intensity
- Temperature-triggered for comfort
- Glare control for visual comfort
- Scheduled for predictable patterns

### Dynamic Glazing
- Electrochromic/thermochromic glass
- Variable tint based on conditions

## Control Strategies

### Solar-Based Control
```
IF Solar_Radiation > Setpoint THEN Deploy_Shading
```

### Temperature-Based Control
```
IF Zone_Temperature > Setpoint THEN Deploy_Shading
```

### Glare Control
```
IF Glare_Index > Setpoint THEN Deploy_Shading
```

### Daylight Control
```
Adjust shading to maintain target illuminance
```

## Special Considerations

1. **View Preservation**: Balance solar control with maintaining views.

2. **Diffuse Light**: Shading reduces both direct and diffuse radiation.

3. **Winter Benefit**: Fixed shading may block beneficial winter sun.

4. **Maintenance**: Movable shading requires regular maintenance.

5. **Integration**: Coordinate with daylighting and HVAC controls.

## Design Guidelines

### Overhang Sizing
- Projection Factor = Overhang Depth / Window Height
- South: PF = 0.3-0.5 typical
- Adjust for latitude

### Fin Sizing
- East/West facades
- Projection Factor = 0.5-1.0
- Consider view angles

### Control Setpoints
- Solar: 150-300 W/m² typical
- Temperature: 24-26°C typical
- Glare: DGI > 22

## Quality Checks

1. **Geometry Validation**: Shading surfaces must not intersect building.

2. **Control Logic**: Verify control type matches setpoint units.

3. **Schedule Coordination**: Shading schedules should allow operation when needed.

4. **Solar Exposure**: Check that shading surfaces actually shade target windows.

5. **Reasonable Setpoints**: Avoid too frequent on/off cycling.