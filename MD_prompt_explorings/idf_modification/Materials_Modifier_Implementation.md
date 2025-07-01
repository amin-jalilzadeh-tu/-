# Materials Modifier Implementation Details

## Overview
The MaterialsModifier handles modifications to building envelope materials, including opaque materials, windows, and construction assemblies. It supports thermal property modifications for energy efficiency improvements.

## Parameter Definitions

### 1. Regular Material Parameters
```python
'thickness': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Thickness',
    field_index=2,
    data_type=float,
    units='m',
    min_value=0.001,
    max_value=1.0,
    performance_impact='thermal_resistance'
)

'conductivity': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Conductivity',
    field_index=3,
    data_type=float,
    units='W/m-K',
    min_value=0.001,
    max_value=10.0,
    performance_impact='thermal_resistance'
)

'density': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Density',
    field_index=4,
    data_type=float,
    units='kg/m3',
    min_value=10.0,
    max_value=3000.0,
    performance_impact='thermal_mass'
)

'specific_heat': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Specific Heat',
    field_index=5,
    data_type=float,
    units='J/kg-K',
    min_value=100.0,
    max_value=5000.0,
    performance_impact='thermal_mass'
)
```

### 2. Surface Property Parameters
```python
'thermal_absorptance': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Thermal Absorptance',
    field_index=6,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='surface_heat_transfer'
)

'solar_absorptance': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Solar Absorptance',
    field_index=7,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='solar_gains'
)

'visible_absorptance': ParameterDefinition(
    object_type='MATERIAL',
    field_name='Visible Absorptance',
    field_index=8,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='daylighting'
)
```

### 3. No-Mass Material Parameters
```python
'thermal_resistance': ParameterDefinition(
    object_type='MATERIAL:NOMASS',
    field_name='Thermal Resistance',
    field_index=2,
    data_type=float,
    units='m2-K/W',
    min_value=0.001,
    max_value=10.0,
    performance_impact='thermal_resistance'
)
```

### 4. Window Material Parameters
```python
'u_factor': ParameterDefinition(
    object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
    field_name='U-Factor',
    field_index=1,
    data_type=float,
    units='W/m2-K',
    min_value=0.1,
    max_value=6.0,
    performance_impact='window_heat_loss'
)

'shgc': ParameterDefinition(
    object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
    field_name='Solar Heat Gain Coefficient',
    field_index=2,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='solar_gains'
)

'visible_transmittance': ParameterDefinition(
    object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
    field_name='Visible Transmittance',
    field_index=3,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='daylighting'
)
```

## Modifiable Object Types
- MATERIAL
- MATERIAL:NOMASS
- MATERIAL:INFRAREDTRANSPARENT
- MATERIAL:AIRGAP
- WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM
- WINDOWMATERIAL:GLAZING
- WINDOWMATERIAL:GAS
- WINDOWMATERIAL:GASMIXTURE
- WINDOWMATERIAL:SHADE
- WINDOWMATERIAL:BLIND
- WINDOWMATERIAL:SCREEN
- CONSTRUCTION
- CONSTRUCTION:CFACTORUNDERGROUNDWALL
- CONSTRUCTION:FFACTORGROUNDFLOOR
- CONSTRUCTION:WINDOWDATAFILE

## Modification Strategies

### 1. Insulation Upgrade Strategy (`insulation_upgrade`)

**Process for Regular Materials:**
1. Identifies insulation materials (conductivity < 0.1 W/m-K)
2. **Conductivity Reduction:**
   - Reduction factor: 20-40% (random.uniform(0.2, 0.4))
   - New conductivity = old * (1 - reduction)
3. **Thickness Increase:**
   - Increase factor: 20-50% (random.uniform(1.2, 1.5))
   - Capped at maximum 0.5m

**Process for No-Mass Materials:**
- Thermal resistance increase: 50-100% (random.uniform(1.5, 2.0))

**Code Example:**
```python
# For regular materials
if obj.parameters[3].numeric_value < 0.1:  # Insulation check
    # Reduce conductivity
    old_k = param.numeric_value
    reduction = random.uniform(0.2, 0.4)
    new_k = old_k * (1 - reduction)
    
    # Increase thickness
    old_thickness = thickness_param.numeric_value
    increase = random.uniform(1.2, 1.5)
    new_thickness = min(old_thickness * increase, 0.5)
```

### 2. Window Upgrade Strategy (`window_upgrade`)

**Process:**
1. Sets high-performance window properties:
   - U-Factor: 0.8-1.5 W/m²-K (random.uniform)
   - SHGC: 0.25-0.4 (optimized for cooling)
   - Visible Transmittance: 0.6-0.8 (maintains daylighting)

**Implementation:**
```python
# Set high-performance U-factor
new_u = random.uniform(0.8, 1.5)
param.value = str(new_u)
param.numeric_value = new_u

# Set optimized SHGC
new_shgc = random.uniform(0.25, 0.4)
```

### 3. Thermal Mass Strategy (`thermal_mass`)

**Process:**
1. Targets materials with density < 2000 kg/m³
2. **Density Increase:**
   - Increase factor: 20-50% (random.uniform(1.2, 1.5))
3. **Specific Heat Increase:**
   - Increase factor: 10-30% (random.uniform(1.1, 1.3))

### 4. Cool Roof Strategy (`cool_roof`)

**Process:**
1. **Solar Absorptance Reduction:**
   - New value: 0.2-0.3 (high reflectance)
2. **Thermal Absorptance Increase:**
   - New value: 0.85-0.95 (good emittance)

**Code Example:**
```python
# Cool roof - high solar reflectance
if param.field_name == 'Solar Absorptance':
    new_solar_abs = random.uniform(0.2, 0.3)
    param.value = str(new_solar_abs)
    
# High thermal emittance
if param.field_name == 'Thermal Absorptance':
    new_thermal_abs = random.uniform(0.85, 0.95)
    param.value = str(new_thermal_abs)
```

## File Loading Specifics

The modifier handles special parser output naming:
```python
def _get_parsed_file_data(self, parsed_data, file_key):
    # Handle parser output file naming
    if file_key == 'materials':
        keys_to_try = [
            'materials_materials',
            'materials_windowmaterials',
            'windowmaterials'
        ]
        combined_data = {}
        for key in keys_to_try:
            if key in parsed_data:
                combined_data.update(parsed_data[key])
        return combined_data if combined_data else {}
```

## Output Structure

```python
ModificationResult(
    object_type='MATERIAL',
    object_name='Insulation Board',
    parameter='conductivity',
    original_value=0.04,
    new_value=0.028,
    change_type='insulation_upgrade',
    validation_status='valid'
)
```

## Key Implementation Details

### 1. Material Type Detection
- Insulation: conductivity < 0.1 W/m-K
- High mass: density > 1000 kg/m³
- Windows: Separate object types

### 2. Physical Constraints
- Maximum thickness: 0.5m
- Minimum conductivity: 0.001 W/m-K
- SHGC + VT relationship maintained

### 3. Multi-Parameter Coordination
- Insulation: Both conductivity and thickness
- Thermal mass: Both density and specific heat
- Windows: U-factor, SHGC, and VT together

## Usage Example

```python
# Initialize modifier
materials_modifier = MaterialsModifier()

# Apply insulation upgrades
modifications = materials_modifier.apply_modifications(
    parsed_objects=parsed_objects,
    modifiable_params=modifiable_params,
    strategy='insulation_upgrade'
)

# Example results:
# - Wall insulation: k=0.04 → 0.028, thickness=0.1 → 0.15
# - Window upgrade: U=2.8 → 1.2, SHGC=0.7 → 0.35
# - Cool roof: solar_abs=0.8 → 0.25
```

## Special Considerations

1. **R-Value Calculation**: R = thickness / conductivity
2. **Construction Assembly**: Materials are referenced by constructions
3. **Climate Appropriateness**: Window SHGC varies by climate
4. **Moisture Properties**: Not currently modified
5. **Air Gap Materials**: Special handling for air spaces