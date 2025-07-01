# IDF Objects Creation Overview

## Summary
This document provides a comprehensive overview of all IDF object creation processes in the E_Plus_2040_py system. The system creates EnergyPlus Input Data Files (IDF) by processing building data through multiple specialized modules, each responsible for different aspects of the building energy model.

## IDF Creation Flow

```
1. Geometry Creation (base building structure)
   ↓
2. Materials & Constructions (fenestration module)
   ↓
3. Windows & Fenestration
   ↓
4. Internal Loads:
   - Lighting
   - Equipment
   - Domestic Hot Water
   ↓
5. HVAC Systems (Ideal Loads)
   ↓
6. Ventilation & Infiltration
   ↓
7. Shading Objects
   ↓
8. Zone Sizing Parameters
   ↓
9. Ground Temperatures
   ↓
10. Output Definitions
```

## Module Summary Table

| Module | Primary IDF Objects | Key Parameters | Data Sources |
|--------|-------------------|----------------|--------------|
| **Geometry** | ZONE, BUILDINGSURFACE:DETAILED | Zone dimensions, surface vertices | Building area, perimeter, height |
| **Fenestration** | FENESTRATIONSURFACE:DETAILED, MATERIAL, CONSTRUCTION | WWR, U-values, material properties | Building type, age, scenario |
| **Lighting** | LIGHTS, ELECTRICEQUIPMENT (parasitic) | W/m², schedules, heat fractions | Building function, occupancy patterns |
| **Equipment** | ELECTRICEQUIPMENT | W/m², schedules, heat fractions | Building type, plug load data |
| **DHW** | WATERHEATER:MIXED | Tank size, temperature, flow rates | Occupancy, building type, NTA 8800 |
| **HVAC** | ZONEHVAC:IDEALLOADSAIRSYSTEM, THERMOSTAT | Setpoints, supply temperatures | Building type, age, scenario |
| **Ventilation** | ZONEINFILTRATION, ZONEVENTILATION | Flow rates, schedules, coefficients | Building age, ventilation system type |
| **Shading** | WINDOWMATERIAL:BLIND, WINDOWSHADINGCONTROL | Slat properties, control logic | Shading configuration, strategy |
| **Zone Sizing** | SIZING:ZONE | Supply air conditions, flow methods | Building function, HVAC requirements |
| **Ground Temp** | SITE:GROUNDTEMPERATURE | Monthly temperatures | Climate data, calibration stage |

## Key Design Patterns

### 1. Archetype-Based Approach
Buildings are categorized by:
- **Function**: Residential vs Non-Residential
- **Type**: Specific subtypes (e.g., Apartment, Office Function)
- **Age**: Construction period (e.g., "1946-1964", "2015 and later")
- **Scenario**: Simulation scenario variations

### 2. Parameter Assignment Strategy
All modules follow a consistent pattern:
```python
# 1. Lookup default ranges
ranges = lookup_table[calibration_stage][building_type][parameter]

# 2. Apply overrides (if any)
if user_override_matches:
    ranges = apply_override(ranges)

# 3. Select final value
if strategy == "A":
    value = (min + max) / 2  # Midpoint
elif strategy == "B":
    value = random.uniform(min, max)  # Random
else:
    value = min  # Conservative
```

### 3. Hierarchical Override System
Parameters can be overridden at multiple levels:
1. Base lookup tables (default)
2. Excel-based rules
3. JSON user configurations
4. Building-specific overrides

### 4. Calibration Support
Two stages with different parameter ranges:
- **pre_calibration**: Wider ranges for initial modeling
- **post_calibration**: Narrower ranges based on calibration results

## Input Data Requirements

### Building Data (Required)
- `ogc_fid`: Unique building identifier
- `building_function`: Primary function category
- `area`: Floor area (m²)
- `perimeter`: Building perimeter (m)
- `age_range`: Construction period

### Building Data (Optional)
- `gem_hoogte`: Building height
- `gem_bouwlagen`: Number of floors
- `occupant_count`: Number of occupants
- Window/wall areas
- Specific building subtypes

### Configuration Parameters
- `scenario`: Simulation scenario name
- `calibration_stage`: pre/post calibration
- `strategy`: A (midpoint) or B (random)
- `random_seed`: For reproducibility

## Output Structure

Each module creates:
1. **IDF Objects**: The actual EnergyPlus objects
2. **Schedules**: Time-varying patterns for operation
3. **Log Entries**: Tracking assigned values

Example log structure:
```python
{
    "building_123": {
        "dhw": {
            "tank_volume": {"range": [100, 200], "selected": 150},
            "setpoint": {"range": [58, 60], "selected": 59}
        },
        "lighting": {
            "watts_per_m2": {"range": [3.2, 5.6], "selected": 4.4}
        }
        # ... other modules
    }
}
```

## Key Calculations

### Window-to-Wall Ratio (WWR)
```
WWR = (window_area + door_area) / exterior_wall_area
```

### DHW Peak Flow
```
peak_flow = (daily_liters/1000 × usage_split_factor) / (peak_hours × 3600)
```

### Infiltration Rate
```
infiltration = base_rate × year_factor × (1Pa/10Pa)^flow_exponent
```

### Zone Ventilation Distribution
```
zone_flow = total_flow × (zone_area / building_area)
```

## Schedule Patterns

Different schedules for:
- **Occupancy**: Weekday/weekend patterns
- **Equipment**: Work hours vs off hours
- **Lighting**: Daylight responsive
- **HVAC**: Setback during unoccupied hours
- **DHW**: Morning/evening peaks
- **Ventilation**: Continuous or scheduled

## Integration Notes

1. **Zone Lists**: Most internal loads apply to "ALL_ZONES"
2. **Construction Naming**: Building-specific with ogc_fid suffix
3. **Material Instances**: Unique materials per building
4. **Schedule Reuse**: Some schedules shared across zones
5. **Default Fallbacks**: Every parameter has safe defaults

## Future Extensibility

The modular design allows:
- Adding new building types to lookup tables
- Implementing additional HVAC system types
- Incorporating measured data for calibration
- Supporting different climate scenarios
- Adding renewable energy systems