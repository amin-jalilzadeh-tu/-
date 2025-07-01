# Geometry Modifications System

## Overview
The geometry modification system handles building geometry parameters in EnergyPlus IDF files, including zones, surfaces, and fenestration. This system can modify zone properties, surface characteristics, and window multipliers, affecting solar gains, thermal mass, and space conditioning requirements.

## Modified Object Types

### Zone Objects
- `ZONE` - Thermal zones
- `ZONELIST` - Groups of zones
- `GLOBALGEOMETRYRULES` - Coordinate system rules

### Surface Objects
- `BUILDINGSURFACE:DETAILED` - Detailed surface geometry
- `FLOOR:DETAILED` - Floor surfaces
- `WALL:DETAILED` - Wall surfaces
- `ROOFCEILING:DETAILED` - Roof and ceiling surfaces

### Fenestration Objects
- `FENESTRATIONSURFACE:DETAILED` - Windows and skylights
- `WINDOW` - Simple window objects
- `DOOR` - Opaque doors
- `GLAZEDDOOR` - Glass doors

## Parameters Modified

### ZONE Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `zone_multiplier` | Multiplier | 6 | int | - | 1-100 | zone_loads |
| `ceiling_height` | Ceiling Height | 7 | float | m | 2.0-10.0 | zone_volume |
| `zone_volume` | Volume | 8 | float | m³ | - | zone_loads |
| `zone_floor_area` | Floor Area | 9 | float | m² | - | zone_loads |

### Surface Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `view_factor_to_ground` | View Factor to Ground | 9 | float | - | 0.0-1.0 | radiant_exchange |

### Fenestration Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `window_multiplier` | Multiplier | 9 | float | - | 1.0-10.0 | solar_gains |

**Note**: Window multiplier must be ≥ 1.0 per EnergyPlus requirements.

## Modification Strategies

### 1. Window Optimization (`window_optimization`)
- **Purpose**: Optimize window sizes for energy performance
- **Modifications**:
  - Adjusts window multiplier by factor of 1.0-1.3 (0% to +30%)
  - Only increases window area (multiplier ≥ 1.0)
  - Represents:
    - Optimized glazing ratios
    - Selective window enlargement
    - Daylighting optimization
  - Impact varies by orientation and climate

### 2. Zone Volume Adjustment (`zone_volume_adjustment`)
- **Purpose**: Modify zone volumes for natural ventilation
- **Modifications**:
  - Increases ceiling height by 5-15%
  - Maximum height capped at 10m
  - Proportionally adjusts zone volume
  - Benefits:
    - Enhanced stratification
    - Better natural ventilation
    - Improved daylighting
  - Common in high-performance designs

### 3. View Factor Optimization (`view_factor_optimization`)
- **Purpose**: Optimize radiant heat exchange with ground
- **Modifications**:
  - Adjusts view factors based on surface type:
    - Roofs: 0.0-0.2 (low view to ground)
    - Floors: 0.7-1.0 (high view to ground)
    - Walls: 0.4-0.6 (moderate view)
  - Surface type detected from object name
  - Affects:
    - Long-wave radiation exchange
    - Ground-coupled heat transfer
    - Surface temperature calculations

## Process Flow

### 1. Geometry Analysis
```
Geometry Objects → Identify Object Type
                → Zone/Surface/Fenestration
                → Locate Modifiable Parameters
```

### 2. Modification Logic
```
Current Geometry → Apply Strategy Rules
                → Validate Constraints
                → Update Dependent Values
                → Maintain Relationships
```

### 3. Consistency Checks
```
Modified Values → Verify Physical Validity
               → Check EnergyPlus Rules
               → Update Related Parameters
               → Create Modification Records
```

## Integration Notes

### Relationship with Other Systems
- **Construction**: Surface area affects material quantities
- **HVAC**: Zone volume impacts air flow requirements
- **Daylighting**: Window size affects daylight availability
- **Solar**: Surface orientation crucial for solar gains

### Common Use Cases
1. **Daylighting Studies**: Window multiplier adjustment
2. **Natural Ventilation**: Ceiling height increase
3. **Thermal Mass**: Surface area considerations
4. **Solar Optimization**: View factor adjustments
5. **Space Efficiency**: Zone multiplier usage

### Performance Impact
- **Solar Gains**: Direct correlation with window area
- **Heating/Cooling Loads**: Proportional to zone volume
- **Ventilation Effectiveness**: Improved with height
- **Daylighting**: Non-linear relationship with window size

## Technical Implementation Details

### Geometry Hierarchy
```
Building
├── Zones
│   ├── Volume
│   ├── Floor Area
│   └── Height
└── Surfaces
    ├── Walls
    ├── Floors
    ├── Roofs
    └── Fenestration
        ├── Windows
        └── Doors
```

### Parameter Dependencies
1. **Zone Volume**: May need recalculation if height changes
2. **Surface Area**: Calculated from vertices (not directly modified)
3. **Window-to-Wall Ratio**: Affected by window multiplier
4. **Zone Multiplier**: Replicates entire zone

### Coordinate Systems
- **World**: Building relative to north
- **Relative**: Surfaces relative to zone
- **Simple**: Legacy 2D system

### Validation Requirements
- Window multiplier ≥ 1.0 (EnergyPlus requirement)
- Ceiling height within reasonable range
- View factors sum appropriately
- Zone volume positive and realistic

### Error Handling
- Check for missing numeric values
- Validate multiplier constraints
- Ensure height reasonableness
- Preserve surface integrity

### Special Considerations

#### Window Multiplier Logic
- EnergyPlus uses multiplier to replicate windows
- Cannot be less than 1.0 (no partial windows)
- Affects both solar gains and conduction
- Consider frame and divider impacts

#### View Factor Physics
- Sum of all view factors from a surface = 1.0
- Ground view factor affects ground temperature impact
- Sky view factor = 1.0 - ground view factor
- Important for night sky radiation

#### Zone Volume Impacts
1. **Thermal Mass**: More air volume = more thermal capacity
2. **Stratification**: Higher ceilings allow temperature stratification
3. **Ventilation**: Affects air change calculations
4. **Acoustics**: Volume impacts reverberation

### Best Practices
1. **Incremental Changes**: Small adjustments for optimization
2. **Climate Consideration**: Strategy varies by location
3. **Orientation Awareness**: North vs. south windows
4. **System Integration**: Consider HVAC implications
5. **Validation**: Always verify modified geometry makes sense