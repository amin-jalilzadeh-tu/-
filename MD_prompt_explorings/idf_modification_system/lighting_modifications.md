# Lighting Modifications System

## Overview
The lighting modification system handles all lighting-related parameters in EnergyPlus IDF files, including interior lighting, daylighting controls, and exterior lighting.

## Modified Object Types
- `LIGHTS` - Main interior lighting objects
- `DAYLIGHTING:CONTROLS` - Daylight harvesting controls
- `DAYLIGHTING:DETAILED` - Detailed daylighting analysis
- `LIGHTINGDESIGNOBJECT` - Lighting design templates
- `EXTERIORLIGHTS` - Outdoor/exterior lighting

## Parameters Modified

### LIGHTS Object Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `lighting_level` | Lighting Level | 4 | float | W | - | lighting_energy |
| `watts_per_area` | Watts per Zone Floor Area | 5 | float | W/m² | 0.0-30.0 | lighting_energy |
| `watts_per_person` | Watts per Person | 6 | float | W/person | 0.0-200.0 | lighting_energy |
| `fraction_radiant` | Fraction Radiant | 7 | float | - | 0.0-1.0 | zone_loads |
| `fraction_visible` | Fraction Visible | 8 | float | - | 0.0-1.0 | - |
| `return_air_fraction` | Return Air Fraction | 9 | float | - | 0.0-1.0 | zone_loads |

### DAYLIGHTING:CONTROLS Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `dimmer_control` | Lighting Control Type | 5 | str | - | Continuous/Stepped/ContinuousOff | lighting_control |
| `minimum_light_output` | Minimum Light Output Fraction | 8 | float | - | 0.0-0.5 | lighting_control |

## Modification Strategies

### 1. LED Retrofit (`led_retrofit`)
- **Purpose**: Simulate LED lighting upgrade
- **Modifications**:
  - Reduces lighting power by 50-70%
  - Updates heat fractions to LED characteristics:
    - Fraction Radiant: 0.20 (less radiant heat)
    - Fraction Visible: 0.20 (similar visible output)
    - Return Air Fraction: 0.55 (more heat removed)
    - Implicit Fraction Lost: 0.05
  - Power reduction applied based on calculation method (LightingLevel, Watts/Area, or Watts/Person)

### 2. Occupancy Sensors (`occupancy_sensors`)
- **Purpose**: Reduce lighting energy through occupancy-based control
- **Modifications**:
  - Reduces lighting power by 20-30%
  - Applied to active lighting parameters (Level, Watts/Area, or Watts/Person)
  - Note: Actual implementation would modify schedules

### 3. Daylight Harvesting (`daylight_harvesting`)
- **Purpose**: Optimize daylighting controls for energy savings
- **Modifications**:
  - Sets Lighting Control Type to "Continuous" for smooth dimming
  - Sets Minimum Light Output Fraction to 10-20% (allows deep dimming)
  - Works with existing DAYLIGHTING:CONTROLS objects

### 4. Task Tuning (`task_tuning`)
- **Purpose**: Reduce over-lighting by tuning to actual task requirements
- **Modifications**:
  - Reduces Watts per Zone Floor Area by 10-20%
  - Targets general area lighting optimization

## Process Flow

1. **Parameter Extraction**:
   - Identifies LIGHTS and DAYLIGHTING objects in parsed IDF
   - Extracts current values for all modifiable parameters
   - Determines calculation method (LightingLevel, Watts/Area, Watts/Person)

2. **Value Modification**:
   - Applies strategy-specific changes
   - Validates new values against parameter constraints
   - Ensures heat fractions sum to ≤ 1.0

3. **Zone Association**:
   - Attempts to extract zone name from object parameters
   - Falls back to pattern matching in object names (e.g., CORE_ZN_LIGHTS)
   - Used for zone-level analysis and reporting

## Output Structure

Each modification produces a result containing:
```json
{
  "building_id": "string",
  "variant_id": "string",
  "category": "lighting",
  "object_type": "LIGHTS",
  "object_name": "string",
  "zone_name": "string",
  "parameter": "parameter_key",
  "field_name": "EnergyPlus field name",
  "original_value": "numeric or string",
  "new_value": "numeric or string",
  "strategy": "strategy_name",
  "timestamp": "ISO timestamp"
}
```

## Integration Notes

- Lighting modifications interact with HVAC through zone load changes
- Heat fraction changes affect cooling/heating requirements
- Daylighting controls require appropriate sensor placement in IDF
- Schedule modifications would provide more realistic occupancy sensor simulation

## Performance Impact

- **Direct**: Reduces lighting electricity consumption
- **Indirect**: 
  - Reduces cooling loads (less heat from lights)
  - May increase heating loads in heating-dominated climates
  - Affects peak demand profiles