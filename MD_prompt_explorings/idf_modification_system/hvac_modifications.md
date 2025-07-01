# HVAC Modifications System

## Overview
The HVAC modification system handles all heating, ventilation, and air conditioning parameters in EnergyPlus IDF files, including cooling/heating equipment, fans, pumps, chillers, boilers, and thermostats.

## Modified Object Types

### Primary Equipment
- `COIL:COOLING:DX:SINGLESPEED` - Single speed DX cooling coils
- `COIL:COOLING:DX:TWOSPEED` - Two speed DX cooling coils
- `COIL:COOLING:DX:VARIABLESPEED` - Variable speed DX cooling coils
- `COIL:HEATING:ELECTRIC` - Electric heating coils
- `COIL:HEATING:GAS` - Gas heating coils
- `COIL:HEATING:DX:SINGLESPEED` - Heat pump heating coils

### Fans and Pumps
- `FAN:VARIABLEVOLUME` - Variable air volume fans
- `FAN:CONSTANTVOLUME` - Constant volume fans
- `FAN:ONOFF` - On/off cycling fans
- `PUMP:VARIABLESPEED` - Variable speed pumps
- `PUMP:CONSTANTSPEED` - Constant speed pumps

### Central Plant Equipment
- `CHILLER:ELECTRIC:EIR` - Electric chillers
- `CHILLER:ELECTRIC:REFORMULATEDEIR` - Reformed EIR chillers
- `BOILER:HOTWATER` - Hot water boilers
- `BOILER:STEAM` - Steam boilers

### Controls and Terminals
- `THERMOSTATSETPOINT:DUALSETPOINT` - Heating/cooling thermostats
- `THERMOSTATSETPOINT:SINGLEHEATING` - Heating-only thermostats
- `THERMOSTATSETPOINT:SINGLECOOLING` - Cooling-only thermostats
- `AIRTERMINAL:SINGLEDUCT:VAV:REHEAT` - VAV boxes with reheat
- `AIRTERMINAL:SINGLEDUCT:VAV:NOREHEAT` - VAV boxes without reheat

### Zone Equipment
- `ZONEHVAC:PACKAGEDTERMINALAIRCONDITIONER` - PTACs
- `ZONEHVAC:PACKAGEDTERMINALHEATPUMP` - PTHPs

### System Templates
- `HVACTEMPLATE:SYSTEM:VAV` - Variable air volume systems
- `HVACTEMPLATE:SYSTEM:PACKAGEDVAV` - Packaged VAV systems
- `HVACTEMPLATE:SYSTEM:UNITARY` - Unitary systems

## Parameters Modified

### Cooling Equipment Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `cooling_capacity` | Gross Rated Total Cooling Capacity | 4 | float | W | 1000-100000 | cooling_energy |
| `cooling_cop` | Rated COP | 8 | float | W/W | 2.0-6.0 | cooling_efficiency |
| `chiller_cop` | Reference COP | 2 | float | W/W | 3.0-7.0 | cooling_efficiency |

### Heating Equipment Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `heating_capacity` | Nominal Capacity | 1 | float | W | 1000-50000 | heating_energy |
| `heating_efficiency` | Efficiency | 2 | float | - | 0.8-1.0 | heating_efficiency |
| `boiler_efficiency` | Nominal Thermal Efficiency | 4 | float | - | 0.7-0.99 | heating_efficiency |

### Fan Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `fan_efficiency` | Fan Total Efficiency | 5 | float | - | 0.5-0.9 | fan_energy |
| `fan_pressure_rise` | Pressure Rise | 3 | float | Pa | 100-2000 | fan_energy |

### Thermostat Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `heating_setpoint` | Heating Setpoint Temperature Schedule Name | 0 | str | - | - | heating_energy |
| `cooling_setpoint` | Cooling Setpoint Temperature Schedule Name | 1 | str | - | - | cooling_energy |

## Modification Strategies

### 1. High Efficiency Equipment (`high_efficiency`)
- **Purpose**: Upgrade to high-efficiency HVAC equipment
- **Modifications**:
  - **Cooling Equipment**: Increases COP by 20-40% (max 6.0)
  - **Heating Equipment**: Increases efficiency by 10-20% (max 0.99)
  - **Fans**: Sets efficiency to 85-90%
  - **Chillers**: Improves COP with 20-40% increase (max 7.0)
  - **Boilers**: Increases thermal efficiency by 10-20%

### 2. Setpoint Optimization (`setpoint_optimization`)
- **Purpose**: Optimize temperature setpoints for energy savings
- **Modifications**:
  - Adjusts heating/cooling setpoint schedules
  - Note: Actual implementation requires schedule object modifications
  - Typically widens deadband between heating/cooling
  - Reduces heating setpoints, increases cooling setpoints

### 3. Variable Speed Upgrades (`variable_speed`)
- **Purpose**: Convert constant speed equipment to variable speed
- **Modifications**:
  - Improves pump/fan efficiency by 15-25%
  - Reduces part-load energy consumption
  - Better matches capacity to load

### 4. Heat Recovery (`heat_recovery`)
- **Purpose**: Add heat recovery capabilities
- **Modifications**:
  - Improves effective system efficiency by 10-20%
  - Applied to coils and chillers
  - Simulates energy recovery ventilation benefits

## Process Flow

1. **Equipment Identification**:
   - Scans for all HVAC-related objects
   - Identifies equipment type and current parameters
   - Maps to appropriate modification parameters

2. **Efficiency Analysis**:
   - Extracts current efficiency values
   - Determines improvement potential
   - Validates against physical limits

3. **Modification Application**:
   - Applies strategy-specific improvements
   - Maintains system relationships
   - Ensures consistent operation

4. **Validation**:
   - Checks COP values remain realistic
   - Ensures efficiency ≤ 1.0 for non-heat pumps
   - Validates capacity relationships

## Output Structure

Each modification produces a result containing:
```json
{
  "building_id": "string",
  "variant_id": "string",
  "category": "hvac",
  "object_type": "COIL:COOLING:DX:SINGLESPEED",
  "object_name": "string",
  "zone_name": "string",
  "parameter": "cooling_cop",
  "field_name": "Rated COP",
  "original_value": 3.2,
  "new_value": 4.5,
  "strategy": "high_efficiency",
  "timestamp": "ISO timestamp"
}
```

## Integration Notes

- HVAC modifications have the largest impact on building energy use
- Changes affect both energy consumption and peak demand
- Equipment sizing relationships must be maintained
- Control strategies interact with equipment efficiency
- Variable speed equipment requires appropriate control curves

## Performance Impact

- **Direct Effects**:
  - Reduces cooling/heating energy consumption
  - Reduces fan/pump energy
  - Improves part-load performance

- **Indirect Effects**:
  - Reduces peak electrical demand
  - Improves thermal comfort
  - May affect equipment cycling and longevity

## Typical Energy Savings

- **High Efficiency Equipment**: 15-30% HVAC energy reduction
- **Setpoint Optimization**: 5-15% HVAC energy reduction
- **Variable Speed Upgrades**: 20-40% fan/pump energy reduction
- **Heat Recovery**: 10-25% total HVAC energy reduction
- **Combined Measures**: Up to 50% HVAC energy reduction possible