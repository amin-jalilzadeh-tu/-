# HVAC Modifier Implementation Details

## Overview
The HVACModifier handles modifications to heating, ventilation, and air conditioning systems, including cooling/heating coils, fans, pumps, chillers, boilers, and thermostats.

## Parameter Definitions

### 1. Cooling Equipment Parameters
```python
'cooling_capacity': ParameterDefinition(
    object_type='COIL:COOLING:DX:SINGLESPEED',
    field_name='Gross Rated Total Cooling Capacity',
    field_index=4,
    data_type=float,
    units='W',
    min_value=1000,
    max_value=100000,
    performance_impact='cooling_energy'
)

'cooling_cop': ParameterDefinition(
    object_type='COIL:COOLING:DX:SINGLESPEED',
    field_name='Rated COP',
    field_index=8,
    data_type=float,
    units='W/W',
    min_value=2.0,
    max_value=6.0,
    performance_impact='cooling_efficiency'
)

'chiller_cop': ParameterDefinition(
    object_type='CHILLER:ELECTRIC:EIR',
    field_name='Reference COP',
    field_index=2,
    data_type=float,
    units='W/W',
    min_value=3.0,
    max_value=7.0,
    performance_impact='cooling_efficiency'
)
```

### 2. Heating Equipment Parameters
```python
'heating_capacity': ParameterDefinition(
    object_type='COIL:HEATING:ELECTRIC',
    field_name='Nominal Capacity',
    field_index=1,
    data_type=float,
    units='W',
    min_value=1000,
    max_value=50000,
    performance_impact='heating_energy'
)

'heating_efficiency': ParameterDefinition(
    object_type='COIL:HEATING:ELECTRIC',
    field_name='Efficiency',
    field_index=2,
    data_type=float,
    units='',
    min_value=0.8,
    max_value=1.0,
    performance_impact='heating_efficiency'
)

'boiler_efficiency': ParameterDefinition(
    object_type='BOILER:HOTWATER',
    field_name='Nominal Thermal Efficiency',
    field_index=4,
    data_type=float,
    units='',
    min_value=0.7,
    max_value=0.99,
    performance_impact='heating_efficiency'
)
```

### 3. Fan Parameters
```python
'fan_efficiency': ParameterDefinition(
    object_type='FAN:VARIABLEVOLUME',
    field_name='Fan Total Efficiency',
    field_index=5,
    data_type=float,
    units='',
    min_value=0.5,
    max_value=0.9,
    performance_impact='fan_energy'
)

'fan_pressure_rise': ParameterDefinition(
    object_type='FAN:VARIABLEVOLUME',
    field_name='Pressure Rise',
    field_index=3,
    data_type=float,
    units='Pa',
    min_value=100,
    max_value=2000,
    performance_impact='fan_energy'
)
```

### 4. Thermostat Parameters
```python
'heating_setpoint': ParameterDefinition(
    object_type='THERMOSTATSETPOINT:DUALSETPOINT',
    field_name='Heating Setpoint Temperature Schedule Name',
    field_index=0,
    data_type=str,
    performance_impact='heating_energy'
)

'cooling_setpoint': ParameterDefinition(
    object_type='THERMOSTATSETPOINT:DUALSETPOINT',
    field_name='Cooling Setpoint Temperature Schedule Name',
    field_index=1,
    data_type=str,
    performance_impact='cooling_energy'
)
```

## Modifiable Object Types

### HVAC Templates
- HVACTEMPLATE:SYSTEM:VAV
- HVACTEMPLATE:SYSTEM:PACKAGEDVAV
- HVACTEMPLATE:SYSTEM:UNITARY

### Cooling Equipment
- COIL:COOLING:DX:SINGLESPEED
- COIL:COOLING:DX:TWOSPEED
- COIL:COOLING:DX:VARIABLESPEED
- CHILLER:ELECTRIC:EIR
- CHILLER:ELECTRIC:REFORMULATEDEIR

### Heating Equipment
- COIL:HEATING:ELECTRIC
- COIL:HEATING:GAS
- COIL:HEATING:DX:SINGLESPEED
- BOILER:HOTWATER
- BOILER:STEAM

### Air Movement
- FAN:VARIABLEVOLUME
- FAN:CONSTANTVOLUME
- FAN:ONOFF
- PUMP:VARIABLESPEED
- PUMP:CONSTANTSPEED

### Controls & Terminals
- THERMOSTATSETPOINT:DUALSETPOINT
- THERMOSTATSETPOINT:SINGLEHEATING
- THERMOSTATSETPOINT:SINGLECOOLING
- AIRTERMINAL:SINGLEDUCT:VAV:REHEAT
- AIRTERMINAL:SINGLEDUCT:VAV:NOREHEAT
- ZONEHVAC:PACKAGEDTERMINALAIRCONDITIONER
- ZONEHVAC:PACKAGEDTERMINALHEATPUMP

## Modification Strategies

### 1. High Efficiency Strategy (`high_efficiency`)

**Process:**

**Cooling Equipment:**
- Searches for objects with 'COOLING' in type
- Looks for parameters with 'COP' in field name
- Improvement factor: 20-40% (random.uniform(1.2, 1.4))
- Caps at maximum 6.0

**Heating Equipment:**
- Searches for objects with 'HEATING' in type
- Looks for parameters with 'EFFICIENCY' in field name
- Improvement factor: 10-20% (random.uniform(1.1, 1.2))
- Caps at maximum 0.99

**Fan Equipment:**
- Searches for objects with 'FAN' in type
- Sets new efficiency: 85-90% (random.uniform(0.85, 0.90))

**Code Example:**
```python
# Cooling COP improvement
if 'COOLING' in obj_type:
    for param in obj.parameters:
        if 'COP' in param.field_name.upper():
            old_cop = param.numeric_value or float(param.value)
            improvement = random.uniform(1.2, 1.4)
            new_cop = min(old_cop * improvement, 6.0)
            param.value = str(new_cop)
            param.numeric_value = new_cop
```

### 2. Setpoint Optimization Strategy (`setpoint_optimization`)

**Process:**
- Identifies THERMOSTATSETPOINT objects
- Currently returns placeholder indicating schedule modification needed

**Note:** Actual implementation requires modifying referenced schedule objects

### 3. Variable Speed Strategy (`variable_speed`)

**Process:**
- Targets PUMP and FAN objects
- Searches for 'EFFICIENCY' in field names
- Improvement factor: 15-25% (random.uniform(1.15, 1.25))
- Caps at maximum 0.95

### 4. Heat Recovery Strategy (`heat_recovery`)

**Process:**
- Targets COIL and CHILLER objects
- Searches for 'COP' or 'EFFICIENCY' in field names
- Improvement factor: 10-20% (random.uniform(1.1, 1.2))
- Different caps:
  - COP parameters: max 7.0
  - Efficiency parameters: max 0.99

## Output Structure

```python
ModificationResult(
    object_type='COIL:COOLING:DX:SINGLESPEED',
    object_name='Zone1 Cooling Coil',
    parameter='cooling_cop',
    original_value=3.5,
    new_value=4.9,
    change_type='high_efficiency',
    validation_status='valid'
)
```

## Key Implementation Features

### 1. Flexible Parameter Matching
Uses uppercase string matching to handle variations:
- Searches for 'COP' in field names
- Searches for 'EFFICIENCY' in field names
- Handles different naming conventions

### 2. Object Type Pattern Matching
- 'COOLING' in obj_type
- 'HEATING' in obj_type
- 'FAN' in obj_type
- 'PUMP' in obj_type

### 3. Multi-File Support
Loads from multiple category files:
- hvac_equipment
- hvac_systems
- hvac_thermostats

### 4. Dynamic Field Name Handling
Creates parameter keys dynamically:
```python
param.field_name.lower().replace(' ', '_')
```

## Usage Example

```python
# Initialize modifier
hvac_modifier = HVACModifier()

# Apply high efficiency upgrades
modifications = hvac_modifier.apply_modifications(
    parsed_objects=parsed_objects,
    modifiable_params=modifiable_params,
    strategy='high_efficiency'
)

# Results might include:
# - Cooling COP: 3.5 → 4.9 (40% improvement)
# - Heating efficiency: 0.82 → 0.90 (10% improvement)  
# - Fan efficiency: 0.60 → 0.87 (45% improvement)
```

## Special Considerations

1. **Schedule References**: Thermostat setpoints reference schedules by name
2. **Equipment Sizing**: Capacity modifications should consider connected zones
3. **System Integration**: HVAC components are highly interconnected
4. **Performance Curves**: Some equipment uses performance curves (not modified here)
5. **Control Logic**: Advanced control strategies require additional object creation