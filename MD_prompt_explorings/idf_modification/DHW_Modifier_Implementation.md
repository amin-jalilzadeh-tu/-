# DHW (Domestic Hot Water) Modifier Implementation Details

## Overview
The DHWModifier handles modifications to domestic hot water systems, including water heaters, water use equipment, and associated distribution systems.

## Parameter Definitions

### 1. Water Heater Parameters
```python
'tank_volume': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Tank Volume',
    field_index=1,
    data_type=float,
    units='m3',
    min_value=0.1,
    max_value=10.0,
    performance_impact='dhw_capacity'
)

'heater_capacity': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Heater Maximum Capacity',
    field_index=6,
    data_type=float,
    units='W',
    min_value=1000,
    max_value=50000,
    performance_impact='dhw_power'
)

'heater_efficiency': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Heater Thermal Efficiency',
    field_index=11,
    data_type=float,
    units='',
    min_value=0.5,
    max_value=0.99,
    performance_impact='dhw_efficiency'
)
```

### 2. Temperature Control Parameters
```python
'setpoint_temperature_schedule': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Setpoint Temperature Schedule Name',
    field_index=2,
    data_type=str,
    performance_impact='dhw_energy'
)

'deadband_temperature': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Deadband Temperature Difference',
    field_index=3,
    data_type=float,
    units='deltaC',
    min_value=0.5,
    max_value=10.0,
    performance_impact='dhw_cycling'
)
```

### 3. Loss and Flow Parameters
```python
'off_cycle_loss_coefficient': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Off Cycle Loss Coefficient to Ambient Temperature',
    field_index=25,
    data_type=float,
    units='W/K',
    min_value=0.0,
    max_value=10.0,
    performance_impact='dhw_standby_loss'
)

'peak_flow_rate': ParameterDefinition(
    object_type='WATERHEATER:MIXED',
    field_name='Peak Use Flow Rate',
    field_index=30,
    data_type=float,
    units='m3/s',
    min_value=0.0,
    max_value=0.01,
    performance_impact='dhw_sizing'
)

'use_flow_rate': ParameterDefinition(
    object_type='WATERUSE:EQUIPMENT',
    field_name='Peak Flow Rate',
    field_index=4,
    data_type=float,
    units='m3/s',
    min_value=0.0,
    max_value=0.001,
    performance_impact='dhw_demand'
)
```

## Modifiable Object Types
- WATERHEATER:MIXED
- WATERHEATER:STRATIFIED
- WATERUSE:EQUIPMENT
- WATERUSE:CONNECTIONS
- PLANTLOOP
- PUMP:VARIABLESPEED
- PUMP:CONSTANTSPEED
- PIPE:ADIABATIC
- PIPE:INDOOR
- PIPE:OUTDOOR

## Modification Strategies

### 1. Efficiency Upgrade Strategy (`efficiency_upgrade`)

**Process:**
1. **Heater Efficiency Improvement:**
   - Improvement factor: 10-20% (random.uniform(0.1, 0.2))
   - New efficiency = min(0.99, old_efficiency * (1 + improvement))
   - Applied to field index 11

2. **Standby Loss Reduction:**
   - Reduction factor: 20-40% (random.uniform(0.2, 0.4))
   - New loss coefficient = old_loss * (1 - reduction)
   - Applied to field index 25

**Code Example:**
```python
# Efficiency improvement
for param in obj.parameters:
    if param.field_name == 'Heater Thermal Efficiency':
        old_eff = param.numeric_value or float(param.value)
        improvement = random.uniform(0.1, 0.2)
        new_eff = min(0.99, old_eff * (1 + improvement))
        param.value = str(new_eff)
        param.numeric_value = new_eff
```

### 2. Low Flow Fixtures Strategy (`low_flow`)

**Process:**
1. Targets WATERUSE:EQUIPMENT objects
2. Reduction factor: 20-40% (random.uniform(0.2, 0.4))
3. Applies to Peak Flow Rate (field index 4)

**Implementation:**
```python
# Flow rate reduction
if param.field_name == 'Peak Flow Rate':
    old_flow = param.numeric_value or float(param.value)
    reduction = random.uniform(0.2, 0.4)
    new_flow = old_flow * (1 - reduction)
    param.value = str(new_flow)
    param.numeric_value = new_flow
```

### 3. Heat Pump Conversion Strategy (`heat_pump_conversion`)

**Process:**
1. Simulates heat pump water heater by increasing effective efficiency
2. Multiplier: 2.5x (representing COP of 2-3)
3. New efficiency = min(0.99, old_efficiency * 2.5)

**Note:** This is a simplified approach; actual heat pump implementation would require object type changes

## Output Structure

Each modification generates:
```python
ModificationResult(
    object_type='WATERHEATER:MIXED',
    object_name='Water Heater 1',
    parameter='heater_efficiency',
    original_value=0.8,
    new_value=0.96,
    change_type='efficiency_upgrade',
    validation_status='valid'
)
```

## File Loading
The modifier loads from 'dhw' category files in the parsed data structure.

## Key Implementation Details

1. **Efficiency Capping**: All efficiency values capped at 0.99 to maintain physical realism
2. **Flow Rate Units**: Handles m³/s units (very small values)
3. **Parameter Fallback**: Uses `param.numeric_value or float(param.value)` for robustness
4. **Targeted Modifications**: Each strategy targets specific parameters relevant to its purpose

## Usage Example

```python
# Initialize modifier
dhw_modifier = DHWModifier()

# Apply efficiency upgrades
modifications = dhw_modifier.apply_modifications(
    parsed_objects=parsed_objects,
    modifiable_params=modifiable_params,
    strategy='efficiency_upgrade'
)

# Results include both efficiency improvements and standby loss reductions
# Example: 80% → 96% efficiency, 5 W/K → 3 W/K standby loss
```

## Special Considerations

1. **Schedule References**: Setpoint temperature schedule is referenced by name only
2. **System Integration**: DHW systems often connect to plant loops and pumps
3. **Stratified vs Mixed**: Modifier supports both tank types but focuses on MIXED
4. **Peak Flow vs Use Flow**: Distinguishes between heater capacity and fixture demand