# Equipment Modifier Implementation Details

## Overview
The EquipmentModifier handles modifications to internal equipment loads (plug loads), including electric equipment, fuel-based equipment, and other internal gains.

## Parameter Definitions

### 1. Power/Energy Parameters
```python
'design_level': ParameterDefinition(
    object_type='ELECTRICEQUIPMENT',
    field_name='Design Level',
    field_index=4,
    data_type=float,
    units='W',
    min_value=0.0,
    max_value=100000.0,
    performance_impact='equipment_energy'
)

'watts_per_area': ParameterDefinition(
    object_type='ELECTRICEQUIPMENT',
    field_name='Watts per Zone Floor Area',
    field_index=5,
    data_type=float,
    units='W/m2',
    min_value=0.0,
    max_value=1000.0,
    performance_impact='equipment_energy'
)

'watts_per_person': ParameterDefinition(
    object_type='ELECTRICEQUIPMENT',
    field_name='Watts per Person',
    field_index=6,
    data_type=float,
    units='W/person',
    min_value=0.0,
    max_value=500.0,
    performance_impact='equipment_energy'
)
```

### 2. Heat Fraction Parameters
```python
'fraction_latent': ParameterDefinition(
    object_type='ELECTRICEQUIPMENT',
    field_name='Fraction Latent',
    field_index=7,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='zone_loads'
)

'fraction_radiant': ParameterDefinition(
    object_type='ELECTRICEQUIPMENT',
    field_name='Fraction Radiant',
    field_index=8,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='zone_loads'
)

'fraction_lost': ParameterDefinition(
    object_type='ELECTRICEQUIPMENT',
    field_name='Fraction Lost',
    field_index=9,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='zone_loads'
)
```

### 3. Fuel Type Parameter
```python
'fuel_type': ParameterDefinition(
    object_type='FUELEQUIPMENT',
    field_name='Fuel Type',
    field_index=10,
    data_type=str,
    allowed_values=['Electricity', 'NaturalGas', 'Propane', 'FuelOil#1', 'FuelOil#2'],
    performance_impact='equipment_energy'
)
```

## Modifiable Object Types
- ELECTRICEQUIPMENT
- FUELEQUIPMENT
- HOTWAREREQUIPMENT
- STEAMEQUIPMENT
- OTHEREQUIPMENT

## Modification Strategies

### 1. Efficient Equipment Strategy (`efficient_equipment`)

**Process:**
1. Identifies calculation method (usually parameter index 3)
2. Applies power reduction based on calculation method:
   - Reduction factor: 15-30% (random.uniform(0.15, 0.30))
3. Modifies appropriate parameter:
   - EquipmentLevel → Design Level
   - Watts/Area → Watts per Zone Floor Area
   - Watts/Person → Watts per Person

**Code Example:**
```python
if calc_method == 'EquipmentLevel':
    for param in obj.parameters:
        if param.field_name == 'Design Level' and param.numeric_value:
            old_value = param.numeric_value
            new_value = old_value * (1 - reduction)
            param.value = str(new_value)
            param.numeric_value = new_value
```

### 2. Energy Star Strategy (`energy_star`)

**Process:**
1. More aggressive reduction than efficient_equipment
2. Reduction factor: 20-50% (random.uniform(0.20, 0.50))
3. Applies same calculation method logic

**Implementation:**
```python
# Higher reduction for Energy Star
reduction = random.uniform(0.20, 0.50)
# Same application logic as efficient_equipment
```

### 3. Plug Load Reduction Strategy (`plug_load_reduction`)

**Process:**
1. **Power Reduction:**
   - Reduction factor: 10-25% (random.uniform(0.10, 0.25))
   - Simulates smart power strips and controls

2. **Fraction Lost Adjustment:**
   - Reduces fraction lost by 50%
   - Represents better equipment that wastes less heat to outdoors

**Code Example:**
```python
# Reduce fraction lost (heat wasted to outdoors)
for param in obj.parameters:
    if param.field_name == 'Fraction Lost':
        old_value = param.numeric_value or float(param.value or 0)
        new_value = old_value * 0.5  # 50% reduction
        param.value = str(new_value)
        param.numeric_value = new_value
```

## Output Structure

```python
ModificationResult(
    object_type='ELECTRICEQUIPMENT',
    object_name='Zone Office Equipment',
    parameter='watts_per_area',
    original_value=10.0,
    new_value=7.5,
    change_type='efficient_equipment',
    validation_status='valid'
)
```

## Key Implementation Details

### 1. Calculation Method Detection
```python
# Check parameter index 3 for calculation method
calc_method = None
if len(obj.parameters) > 3:
    calc_method = obj.parameters[3].value
```

### 2. Parameter Mapping
- EquipmentLevel → 'design_level'
- Watts/Area → 'watts_per_area'
- Watts/Person → 'watts_per_person'

### 3. Heat Fraction Considerations
- Fraction Latent: Moisture added to space
- Fraction Radiant: Radiant heat to surfaces
- Fraction Lost: Heat lost to outdoors
- Convective fraction: Implicit (1 - sum of others)

### 4. File Loading
Loads from 'equipment' category files

## Usage Example

```python
# Initialize modifier
equipment_modifier = EquipmentModifier()

# Apply Energy Star equipment upgrades
modifications = equipment_modifier.apply_modifications(
    parsed_objects=parsed_objects,
    modifiable_params=modifiable_params,
    strategy='energy_star'
)

# Example results:
# - Office equipment: 10 W/m² → 5 W/m² (50% reduction)
# - Computer room: 50 W/m² → 35 W/m² (30% reduction)
# - Fraction lost: 0.1 → 0.05 (better equipment)
```

## Special Considerations

1. **Schedule Dependencies**: Equipment schedules not modified (referenced by name)
2. **Zone Relationships**: Equipment is zone-specific
3. **Heat Balance**: Sum of heat fractions must be ≤ 1.0
4. **Fuel Types**: Different equipment types use different fuels
5. **IT Equipment**: Special considerations for data centers (high densities)