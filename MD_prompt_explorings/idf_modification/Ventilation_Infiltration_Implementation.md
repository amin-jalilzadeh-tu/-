# Ventilation and Infiltration Modifier Implementation Details

## Ventilation Modifier

### Overview
The VentilationModifier handles mechanical ventilation, natural ventilation, outdoor air requirements, and heat recovery systems.

### Parameter Definitions

#### Mechanical Ventilation Parameters
```python
'design_flow_rate': ParameterDefinition(
    object_type='ZONEVENTILATION:DESIGNFLOWRATE',
    field_name='Design Flow Rate',
    field_index=4,
    data_type=float,
    units='m3/s',
    min_value=0.0,
    max_value=10.0,
    performance_impact='ventilation_energy'
)

'flow_rate_per_zone_area': ParameterDefinition(
    object_type='ZONEVENTILATION:DESIGNFLOWRATE',
    field_name='Flow Rate per Zone Floor Area',
    field_index=5,
    data_type=float,
    units='m3/s-m2',
    min_value=0.0,
    max_value=0.01,
    performance_impact='ventilation_energy'
)

'flow_rate_per_person': ParameterDefinition(
    object_type='ZONEVENTILATION:DESIGNFLOWRATE',
    field_name='Flow Rate per Person',
    field_index=6,
    data_type=float,
    units='m3/s-person',
    min_value=0.0,
    max_value=0.1,
    performance_impact='ventilation_energy'
)

'air_changes_per_hour': ParameterDefinition(
    object_type='ZONEVENTILATION:DESIGNFLOWRATE',
    field_name='Air Changes per Hour',
    field_index=7,
    data_type=float,
    units='1/hr',
    min_value=0.0,
    max_value=50.0,
    performance_impact='ventilation_energy'
)
```

#### Natural Ventilation Parameters
```python
'opening_area': ParameterDefinition(
    object_type='ZONEVENTILATION:WINDANDSTACKOPENAREA',
    field_name='Opening Area',
    field_index=2,
    data_type=float,
    units='m2',
    min_value=0.0,
    max_value=100.0,
    performance_impact='natural_ventilation'
)

'opening_effectiveness': ParameterDefinition(
    object_type='ZONEVENTILATION:WINDANDSTACKOPENAREA',
    field_name='Opening Effectiveness',
    field_index=4,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='natural_ventilation'
)
```

#### Heat Recovery Parameters
```python
'sensible_effectiveness': ParameterDefinition(
    object_type='HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT',
    field_name='Sensible Effectiveness at 100% Heating Air Flow',
    field_index=2,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='heat_recovery'
)

'latent_effectiveness': ParameterDefinition(
    object_type='HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT',
    field_name='Latent Effectiveness at 100% Heating Air Flow',
    field_index=4,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='heat_recovery'
)
```

### Modifiable Object Types
- ZONEVENTILATION:DESIGNFLOWRATE
- ZONEVENTILATION:WINDANDSTACKOPENAREA
- DESIGNSPECIFICATION:OUTDOORAIR
- HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT
- AIRFLOWNETWORK:* (various)
- CONTROLLER:MECHANICALVENTILATION
- ZONEHVAC:ENERGYRECOVERYVENTILATOR

### Modification Strategies

#### 1. Demand Controlled Ventilation (`demand_controlled`)
**Process:**
- Sets minimum ventilation rates:
  - Per person: 0.0025 m³/s (2.5 L/s)
  - Per area: 0.0003 m³/s-m² (0.3 L/s-m²)
- Reduces base flow rates to these minimums

#### 2. Natural Ventilation (`natural_ventilation`)
**Process:**
- Increases opening effectiveness: 0.65-0.85
- Increases opening areas by 20-50%

#### 3. Heat Recovery (`heat_recovery`)
**Process:**
- Sensible effectiveness: 0.75-0.85
- Latent effectiveness: 0.65-0.75

#### 4. COVID Mitigation (`covid_mitigation`)
**Process:**
- Sets high ACH: 6-10 (CDC recommendation)
- Maximizes outdoor air: 0.010-0.015 m³/s per person

#### 5. Energy Recovery (`energy_recovery`)
**Process:**
- Applies heat recovery improvements
- Sets ventilation type to "Balanced"

---

## Infiltration Modifier

### Overview
The InfiltrationModifier handles uncontrolled air leakage through the building envelope.

### Parameter Definitions

#### Flow Rate Parameters
```python
'design_flow_rate': ParameterDefinition(
    object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
    field_name='Design Flow Rate',
    field_index=4,
    data_type=float,
    units='m3/s',
    min_value=0.0,
    max_value=1.0,
    performance_impact='infiltration_loads'
)

'flow_per_zone_area': ParameterDefinition(
    object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
    field_name='Flow per Zone Floor Area',
    field_index=5,
    data_type=float,
    units='m3/s-m2',
    min_value=0.0,
    max_value=0.001,
    performance_impact='infiltration_loads'
)

'air_changes_per_hour': ParameterDefinition(
    object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
    field_name='Air Changes per Hour',
    field_index=7,
    data_type=float,
    units='1/hr',
    min_value=0.0,
    max_value=5.0,
    performance_impact='infiltration_loads'
)
```

#### Coefficient Parameters
```python
'constant_coefficient': ParameterDefinition(
    object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
    field_name='Constant Term Coefficient',
    field_index=8,
    data_type=float,
    min_value=0.0,
    max_value=1.0,
    performance_impact='infiltration_loads'
)

'temperature_coefficient': ParameterDefinition(
    object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
    field_name='Temperature Term Coefficient',
    field_index=9,
    data_type=float,
    min_value=0.0,
    max_value=0.05,
    performance_impact='infiltration_loads'
)

'velocity_coefficient': ParameterDefinition(
    object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
    field_name='Velocity Term Coefficient',
    field_index=10,
    data_type=float,
    min_value=0.0,
    max_value=0.5,
    performance_impact='infiltration_loads'
)
```

### Modifiable Object Types
- ZONEINFILTRATION:DESIGNFLOWRATE
- ZONEINFILTRATION:EFFECTIVELEAKAGEAREA
- ZONEINFILTRATION:FLOWCOEFFICIENT

### Modification Strategies

#### 1. Air Sealing (`air_sealing`)
**Process:**
- Identifies calculation method (parameter index 3)
- Reduces rates by 20-40%
- Maintains minimum 10% of original value
- Adjusts based on method:
  - Flow/Zone → design_flow_rate
  - Flow/Area → flow_per_zone_area
  - AirChanges/Hour → air_changes_per_hour

**Code Example:**
```python
if calc_method == 'AirChanges/Hour':
    for param in obj.parameters:
        if param.field_name == 'Air Changes per Hour':
            old_ach = param.numeric_value
            reduction = random.uniform(0.2, 0.4)
            new_ach = max(old_ach * (1 - reduction), old_ach * 0.1)
```

#### 2. Tight Construction (`tight_construction`)
**Process:**
- Sets ACH to 0.1-0.3 (tight building standard)
- Reduces constant coefficient by 50%

#### 3. Passive House (`passive_house`)
**Process:**
- Sets ACH to exactly 0.05
- Sets very low coefficients:
  - Constant: 0.1
  - Temperature: 0.001
  - Velocity: 0.001
  - Velocity Squared: 0.0001

## Output Structure

Both modifiers produce:
```python
ModificationResult(
    object_type='ZONEVENTILATION:DESIGNFLOWRATE',
    object_name='Zone1 Ventilation',
    parameter='flow_rate_per_person',
    original_value=0.01,
    new_value=0.0025,
    change_type='demand_controlled',
    validation_status='valid'
)
```

## Key Implementation Details

### 1. Calculation Method Detection
Both modifiers check parameter index 3 for the calculation method to determine which parameters to modify.

### 2. COVID-Specific Requirements
Ventilation modifier includes special high-ventilation mode for pandemic response.

### 3. Building Standards
- ASHRAE 62.1: Minimum ventilation rates
- Passive House: 0.05 ACH infiltration
- CDC: 6-10 ACH for COVID mitigation

### 4. Coefficient Relationships
Infiltration = Design Flow × (A + B×|Tzone-Toutdoor| + C×WindSpeed + D×WindSpeed²)

## Usage Example

```python
# Ventilation modification
vent_modifier = VentilationModifier()
vent_mods = vent_modifier.apply_modifications(
    parsed_objects, modifiable_params, 'demand_controlled'
)

# Infiltration modification
inf_modifier = InfiltrationModifier()
inf_mods = inf_modifier.apply_modifications(
    parsed_objects, modifiable_params, 'passive_house'
)
```