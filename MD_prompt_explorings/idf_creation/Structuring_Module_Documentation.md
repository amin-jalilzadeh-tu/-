# Structuring Module Documentation

## Overview
The Structuring module transforms flat parameter assignment logs into structured formats suitable for scenario generation and sensitivity analysis. It extracts ranges, associates parameters with EnergyPlus objects, and prepares data for calibration workflows.

## Module Components

### 1. dhw_structuring.py

#### Purpose
Transforms DHW parameter assignments into structured format with explicit min/max ranges.

#### Input Data
`assigned_dhw_params.csv`:
```csv
ogc_fid,zone_name,param_name,assigned_value
123,Zone1,occupant_density_range,"[30.0, 50.0]"
123,Zone1,occupant_density,40.0
123,Zone1,tank_volume_range,"[150.0, 200.0]"
123,Zone1,tank_volume,175.0
```

#### Processing Steps
1. **Range Parsing**: Extracts min/max from "_range" parameters
2. **Value Association**: Links ranges with actual assigned values
3. **Object Mapping**: Associates parameters with EnergyPlus object types
4. **Row Consolidation**: Combines value and range into single rows

#### Output Structure
`structured_dhw_params.csv`:
```csv
ogc_fid,zone_name,param_name,param_value,param_min,param_max,ep_object_type,ep_object_name
123,Zone1,occupant_density,40.0,30.0,50.0,WaterHeater:Mixed,DHW_Zone1
123,Zone1,tank_volume,175.0,150.0,200.0,WaterHeater:Mixed,DHW_Zone1
```

### 2. equipment_structuring.py

#### Purpose
Simple pass-through structuring for equipment parameters (already structured).

#### Input/Output
- Input: `assigned_equipment.csv`
- Output: `structured_equipment.csv` (copy with potential future enhancements)

### 3. fenestration_structuring.py

#### Purpose
Structures window and material parameters with ranges for sensitivity analysis.

#### Input Data
`assigned_fenez_params.csv`:
```csv
ogc_fid,zone_name,param_name,assigned_value
123,,fenez_windows_opq_U_value_range,"[1.5, 2.5]"
123,,fenez_windows_opq_U_value,2.0
123,,fenez_exterior_wall_R_value_range,"[2.0, 4.0]"
123,,fenez_exterior_wall_R_value,3.0
```

#### Processing Steps
1. **Prefix Filtering**: Selects only "fenez_" parameters
2. **Sub-key Extraction**: Parses element types (windows_opq, doors_opq, etc.)
3. **Range Parsing**: Extracts numeric ranges from string representations
4. **Material Association**: Links to EnergyPlus material objects

#### Output Structure
```csv
ogc_fid,element_type,param_name,param_value,param_min,param_max,material_name
123,windows,U_value,2.0,1.5,2.5,Window_Generic_123
123,exterior_wall,R_value,3.0,2.0,4.0,ExtWall_Material_123
```

### 4. flatten_assigned_vent.py

#### Purpose
Splits ventilation parameters into building-level and zone-level components.

#### Input Data
`assigned_ventilation.csv`:
```csv
ogc_fid,zone_name,param_name,assigned_value
123,,vent_type,SystemD
123,,f_ctrl,0.8
123,Zone1,infiltration_flow_per_exterior_area,0.0005
123,Zone2,infiltration_flow_per_exterior_area,0.0005
```

#### Processing Logic
1. **Null Zone Check**: Separates building-level (zone_name=null) from zone-level
2. **Value Parsing**: Handles complex values (dicts/lists) while preserving strings
3. **Column Renaming**: `assigned_value` → `param_value`

#### Output Files
1. `assigned_vent_building.csv`: Building-wide settings
2. `assigned_vent_zones.csv`: Zone-specific parameters

### 5. flatten_hvac.py

#### Purpose
Similar to ventilation flattening but for HVAC parameters.

#### Processing
- Identical logic to `flatten_assigned_vent.py`
- Separates building-level HVAC settings from zone-specific ones

#### Output Files
1. `assigned_hvac_building.csv`: System-wide HVAC parameters
2. `assigned_hvac_zones.csv`: Zone-specific setpoints and schedules

### 6. shading_structuring.py

#### Purpose
Adds variation ranges to shading parameters based on user-defined rules.

#### Input Data
- `assigned_shading_params.csv`: Current shading assignments
- User shading rules dictionary:
```python
shading_rules = {
    "slat_angle": {"min": 0, "max": 45},
    "solar_transmittance": {"min": 0.1, "max": 0.3},
    "control_type": {"choices": ["AlwaysOn", "OnIfScheduleAllows"]}
}
```

#### Processing Steps
1. **Rule Matching**: Maps parameters to user rules
2. **Range Application**: Adds min/max for numeric parameters
3. **Choice Lists**: Adds discrete options for categorical parameters
4. **Fixed Values**: Preserves parameters without rules

#### Output Structure
```csv
ogc_fid,zone_name,param_name,param_value,param_min,param_max,choices
123,Zone1,slat_angle,25,0,45,
123,Zone1,solar_transmittance,0.2,0.1,0.3,
123,Zone1,control_type,AlwaysOn,,,["AlwaysOn","OnIfScheduleAllows"]
```

### 7. zone_sizing_structuring.py

#### Purpose
Structures zone sizing and outdoor air parameters with variation options.

#### Input Data
- `assigned_zone_sizing_outdoor_air.csv`
- User sizing rules:
```python
sizing_rules = {
    "cooling_supply_air_temp": {"min": 12, "max": 14},
    "heating_supply_air_temp": {"min": 40, "max": 50},
    "air_flow_method": {"choices": ["DesignDay", "Flow/Area"]}
}
```

#### Processing Features
1. **Numeric Ranges**: Min/max columns for continuous parameters
2. **Discrete Choices**: JSON-encoded choice lists
3. **Default Handling**: Parameters without rules keep assigned values
4. **Type Preservation**: Maintains numeric vs string types

#### Output Structure
```csv
ogc_fid,zone_name,param_name,param_value,param_min,param_max,choices
123,Zone1,cooling_supply_air_temp,13,12,14,
123,Zone1,air_flow_method,DesignDay,,,["DesignDay","Flow/Area"]
```

## Common Patterns

### Range Parsing Function
```python
def parse_range_value(value_str):
    """Extract min/max from string like '[1.0, 2.0]'"""
    try:
        values = ast.literal_eval(value_str)
        return float(values[0]), float(values[1])
    except:
        return None, None
```

### Parameter Association
Most modules maintain mappings between:
- Parameter names
- EnergyPlus object types
- Object instance names
- Valid value ranges

### Output Standardization
All structured outputs follow similar format:
- `ogc_fid`: Building identifier
- `zone_name`: Zone identifier (if applicable)
- `param_name`: Parameter name
- `param_value`: Assigned value
- `param_min`/`param_max`: Variation range
- `choices`: Discrete options (if applicable)

## Integration with Workflows

### 1. Scenario Generation
Structured data enables:
- Monte Carlo sampling within ranges
- Discrete choice selection
- Sensitivity analysis
- Uncertainty quantification

### 2. Calibration
- Compare simulated vs measured data
- Adjust parameters within valid ranges
- Track parameter evolution

### 3. Optimization
- Define parameter bounds
- Explore design space
- Multi-objective optimization

## Best Practices

1. **Consistent Naming**: Use standard parameter names across modules
2. **Range Validation**: Ensure min < max for all ranges
3. **Type Safety**: Preserve numeric types for calculations
4. **Missing Data**: Handle null/empty values gracefully
5. **Documentation**: Include units in parameter names when relevant