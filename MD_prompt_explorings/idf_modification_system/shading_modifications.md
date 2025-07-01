# Shading Modifications System

## Overview
The shading modification system handles solar shading and control parameters in EnergyPlus IDF files. This includes fixed shading devices (overhangs, fins), movable shading (blinds, shades), and shading control strategies. Proper shading design is crucial for balancing solar heat gains, daylighting, and glare control.

## Modified Object Types

### Fixed Shading Devices
- `SHADING:SITE:DETAILED` - Site shading (trees, adjacent buildings)
- `SHADING:BUILDING:DETAILED` - Building-attached shading
- `SHADING:ZONE:DETAILED` - Zone-level shading devices
- `SHADING:OVERHANG` - Horizontal projections above windows
- `SHADING:OVERHANG:PROJECTION` - Overhang with projection factor
- `SHADING:FIN` - Vertical projections beside windows
- `SHADING:FIN:PROJECTION` - Fin with projection factor

### Movable Shading
- `WINDOWSHADINGCONTROL` - Controls for window shading devices
- `EXTERIORSHADE` - Exterior shading materials
- `INTERIORSHADE` - Interior shading materials

## Parameters Modified

### Fixed Shading Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `shading_transmittance` | Transmittance Schedule Name | 2 | str | - | - | solar_gains |
| `shading_reflectance` | Reflectance Schedule Name | 2 | str | - | - | solar_gains |
| `overhang_projection` | Height above Window or Door | 2 | float | m | 0.0-3.0 | solar_shading |
| `overhang_depth` | Depth | 3 | float | m | 0.1-5.0 | solar_shading |
| `fin_projection` | Extension from Window/Door | 3 | float | m | 0.1-3.0 | solar_shading |

### Window Shading Control Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `shading_control_type` | Shading Control Type | 2 | str | - | See allowed values | shading_operation |
| `shading_setpoint` | Setpoint | 7 | float | varies | - | shading_control |
| `slat_angle` | Slat Angle Schedule Name | 11 | str | - | - | solar_control |

### Allowed Shading Control Types
- `AlwaysOn` - Shading always deployed
- `AlwaysOff` - Shading never deployed
- `OnIfScheduleAllows` - Schedule-based control
- `OnIfHighSolarOnWindow` - Solar intensity trigger
- `OnIfHighHorizontalSolar` - Horizontal solar trigger
- `OnIfHighOutdoorAirTemperature` - Temperature trigger
- `OnIfHighZoneAirTemperature` - Zone temperature trigger
- `OnIfHighZoneCooling` - Cooling load trigger
- `OnNightIfLowOutdoorTempAndOffDay` - Night insulation
- `OnNightIfLowInsideTempAndOffDay` - Night temperature control
- `OnNightIfHeatingAndOffDay` - Heating period control

## Modification Strategies

### 1. Dynamic Shading (`dynamic_shading`)
- **Purpose**: Implement solar-responsive shading control
- **Modifications**:
  - Sets control type to `OnIfHighSolarOnWindow`
  - Sets trigger setpoint to 200-400 W/m²
  - Represents:
    - Automated exterior blinds
    - Motorized shades
    - Smart glass controls
  - Benefits:
    - Reduced cooling loads
    - Maintained daylighting
    - Glare prevention

### 2. Fixed Shading (`fixed_shading`)
- **Purpose**: Optimize fixed shading geometry
- **Modifications**:
  - Increases overhang depth by 20-40%
  - Maximum depth capped at 3m
  - Represents:
    - Architectural shading design
    - Permanent awnings
    - Building-integrated shading
  - Ideal for:
    - South-facing windows (Northern hemisphere)
    - Consistent sun angles

### 3. Optimize Overhangs (`optimize_overhangs`)
- **Purpose**: Fine-tune overhang dimensions
- **Modifications**:
  - Sets height above window to 0.1-0.3m
  - Sets overhang depth to 0.5-1.5m
  - Based on:
    - Solar geometry optimization
    - Summer shading priority
    - Winter solar access
  - Balances heating and cooling needs

### 4. Automated Blinds (`automated_blinds`)
- **Purpose**: Implement cooling load-based control
- **Modifications**:
  - Sets control type to `OnIfHighZoneCooling`
  - Sets trigger setpoint to 50-150W cooling load
  - Represents:
    - Interior automated blinds
    - Occupant comfort priority
    - Zone-based control
  - Advantages:
    - Direct response to cooling needs
    - Prevents overheating
    - Zone-specific control

## Process Flow

### 1. Shading System Analysis
```
Shading Objects → Classify Type (Fixed/Movable)
               → Identify Control Strategy
               → Locate Key Parameters
```

### 2. Control Optimization
```
Current Settings → Apply Strategy Logic
                → Set Appropriate Triggers
                → Configure Setpoints
                → Update Control Types
```

### 3. Geometry Refinement
```
Fixed Shading → Calculate Optimal Dimensions
             → Consider Orientation
             → Apply Modifications
             → Validate Proportions
```

## Integration Notes

### Relationship with Other Systems
- **Windows**: Shading directly affects window heat gain
- **Daylighting**: Must balance shading with daylight needs
- **HVAC**: Reduced solar gains lower cooling loads
- **Lighting**: May increase artificial lighting needs

### Common Use Cases
1. **Office Buildings**: Automated blinds for glare control
2. **Residential**: Fixed overhangs for passive solar
3. **Retail**: Dynamic shading for display protection
4. **Schools**: Combination of fixed and movable shading
5. **Healthcare**: Precise control for patient comfort

### Performance Impact
- **Cooling Energy**: 10-40% reduction potential
- **Heating Energy**: May increase 5-15% (climate dependent)
- **Lighting Energy**: May increase 5-20%
- **Peak Cooling**: Significant reduction (20-50%)
- **Thermal Comfort**: Improved with proper control

## Technical Implementation Details

### Shading Design Principles

#### Overhang Sizing
```
Optimal Depth = Window Height × tan(Solar Altitude Angle)
Where: Solar Altitude Angle at summer solstice noon
```

#### Projection Factor
```
PF = Projection / Window Height
Typical values: 0.3-0.5 for balanced performance
```

### Control Strategy Selection Guide

| Climate | Priority | Recommended Control | Setpoint Range |
|---------|----------|-------------------|----------------|
| Hot, Sunny | Cooling | OnIfHighSolarOnWindow | 200-300 W/m² |
| Temperate | Balance | OnIfHighZoneCooling | 75-125 W |
| Cold | Heating | OnIfScheduleAllows | Schedule-based |
| Mixed Humid | Comfort | OnIfHighZoneAirTemperature | 24-26°C |

### Setpoint Parameter Location
- Parameter index 7 is typically the setpoint
- Field name identification is preferred
- Fallback to index-based location if needed
- Value interpretation depends on control type

### Implementation Considerations

#### Dynamic Shading
1. **Response Time**: Consider actuator speed
2. **Hysteresis**: Prevent hunting (add deadband)
3. **Override**: Allow manual control options
4. **Maintenance**: Account for mechanical reliability

#### Fixed Shading
1. **Orientation-Specific**: Design varies by facade
2. **Latitude-Dependent**: Sun angles vary by location
3. **Aesthetic Integration**: Architectural constraints
4. **Structural Support**: Weight and wind loads

### Error Handling
- Verify control type compatibility
- Check setpoint reasonableness
- Validate geometric proportions
- Handle missing field names gracefully

### Best Practices
1. **Climate-Specific Design**: Tailor to local conditions
2. **Integrated Approach**: Consider all facade elements
3. **Seasonal Balance**: Don't optimize for one season only
4. **Occupant Comfort**: Priority over energy sometimes
5. **Commissioning**: Proper setpoints crucial for performance

### Common Pitfalls
1. Over-shading causing excessive lighting use
2. Under-shading leading to overheating
3. Complex controls that maintenance can't support
4. Ignoring winter solar benefits
5. Fixed shading on wrong orientations