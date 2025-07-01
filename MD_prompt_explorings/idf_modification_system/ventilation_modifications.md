# Ventilation Modifications System

## Overview
The ventilation modification system handles controlled air exchange parameters in EnergyPlus IDF files. Unlike infiltration, ventilation represents intentional outdoor air introduction for indoor air quality, including mechanical ventilation, natural ventilation, and heat recovery systems. This system is critical for balancing energy efficiency with occupant health and comfort.

## Modified Object Types

### Mechanical Ventilation
- `ZONEVENTILATION:DESIGNFLOWRATE` - Zone-level mechanical ventilation
- `DESIGNSPECIFICATION:OUTDOORAIR` - Outdoor air requirements
- `CONTROLLER:OUTDOORAIR` - Outdoor air controller
- `CONTROLLER:MECHANICALVENTILATION` - Demand-controlled ventilation

### Natural Ventilation
- `ZONEVENTILATION:WINDANDSTACKOPENAREA` - Natural ventilation openings
- `AIRFLOWNETWORK:MULTIZONE:SURFACE` - Detailed airflow network surfaces
- `AIRFLOWNETWORK:MULTIZONE:COMPONENT:DETAILEDOPENING` - Window/door openings
- `AIRFLOWNETWORK:MULTIZONE:COMPONENT:SIMPLEOPENING` - Simple openings

### Heat Recovery
- `HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT` - Energy recovery ventilator (ERV)
- `HEATEXCHANGER:AIRTOAIR:FLATPLATE` - Heat recovery ventilator (HRV)

### Other
- `ZONEMIXING` - Inter-zone air mixing
- `ZONECROSSMIXING` - Bi-directional zone mixing
- `ZONECONTROL:CONTAMINANTCONTROLLER` - CO2-based control

## Parameters Modified

### ZONEVENTILATION:DESIGNFLOWRATE Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `design_flow_rate` | Design Flow Rate | 3 | float | m³/s | - | ventilation_energy |
| `flow_rate_per_zone_area` | Flow Rate per Zone Floor Area | 4 | float | m³/s-m² | 0.0-0.01 | ventilation_energy |
| `flow_rate_per_person` | Flow Rate per Person | 5 | float | m³/s-person | 0.0-0.05 | indoor_air_quality |
| `air_changes_per_hour` | Air Changes per Hour | 6 | float | 1/hr | 0.0-20.0 | ventilation_energy |
| `ventilation_type` | Ventilation Type | 7 | str | - | Natural/Exhaust/Intake/Balanced | ventilation_effectiveness |

### Natural Ventilation Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `opening_area` | Opening Factor or Opening Area | 3 | float | m² | 0.0-10.0 | natural_ventilation |
| `opening_effectiveness` | Opening Effectiveness | 2 | float | - | 0.0-1.0 | natural_ventilation_effectiveness |

### Outdoor Air Specification Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `outdoor_air_flow_per_person` | Outdoor Air Flow per Person | 2 | float | m³/s-person | 0.0-0.05 | indoor_air_quality |
| `outdoor_air_flow_per_zone_area` | Outdoor Air Flow per Zone Floor Area | 3 | float | m³/s-m² | 0.0-0.005 | ventilation_loads |

### Heat Recovery Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `sensible_effectiveness` | Sensible Effectiveness at 100% Heating Air Flow | 3 | float | - | 0.0-1.0 | heat_recovery_efficiency |
| `latent_effectiveness` | Latent Effectiveness at 100% Heating Air Flow | 4 | float | - | 0.0-1.0 | heat_recovery_efficiency |

## Modification Strategies

### 1. Demand Controlled Ventilation (`demand_controlled`)
- **Purpose**: Reduce ventilation based on actual occupancy
- **Modifications**:
  - Reduces Outdoor Air Flow per Person to 0.0025 m³/s (2.5 L/s)
  - Reduces Outdoor Air Flow per Zone Area to 0.0003 m³/s-m²
  - Represents:
    - CO2 sensors controlling ventilation
    - Minimum rates when unoccupied
    - ASHRAE 62.1 DCV compliance
  - Typical savings: 20-50% of ventilation energy

### 2. Natural Ventilation (`natural_ventilation`)
- **Purpose**: Enhance passive ventilation capabilities
- **Modifications**:
  - Increases Opening Effectiveness to 0.65-0.85
  - Increases Opening Areas by 20-50%
  - Represents:
    - Optimized window placement
    - Stack effect utilization
    - Cross-ventilation strategies
  - Best for mild climates

### 3. Heat Recovery Ventilation (`heat_recovery`)
- **Purpose**: Recover energy from exhaust air
- **Modifications**:
  - Sets Sensible Effectiveness to 0.75-0.85 (75-85%)
  - Sets Latent Effectiveness to 0.65-0.75 (65-75%)
  - Represents:
    - High-efficiency HRV/ERV units
    - Proper maintenance assumed
    - Cold climate optimization
  - Energy recovery potential: 60-80%

### 4. COVID-19 Mitigation (`covid_mitigation`)
- **Purpose**: Maximize ventilation for pathogen dilution
- **Modifications**:
  - Sets Air Changes per Hour to 6-10 ACH
  - Sets Outdoor Air Flow per Person to 0.01-0.015 m³/s (10-15 L/s)
  - Based on:
    - CDC recommendations
    - ASHRAE Epidemic Task Force guidance
    - Healthcare facility standards
  - Prioritizes health over energy efficiency

### 5. Energy Recovery (`energy_recovery`)
- **Purpose**: Balanced approach with heat recovery
- **Modifications**:
  - Applies heat recovery improvements
  - Sets Ventilation Type to "Balanced"
  - Combines:
    - High-efficiency heat recovery
    - Balanced supply and exhaust
    - Optimized for energy savings
  - Suitable for extreme climates

## Process Flow

### 1. System Identification
```
Ventilation Objects → Classify System Type
                   → Mechanical/Natural/Recovery
                   → Identify Control Strategy
```

### 2. Parameter Optimization
```
Base Ventilation Rate → Apply Strategy Factors
                     → Check Code Minimums
                     → Update Parameters
                     → Verify System Balance
```

### 3. Integration Checks
```
Modified Parameters → Validate Total Outdoor Air
                   → Check Pressure Balance
                   → Verify Heat Recovery Logic
                   → Create Modification Records
```

## Integration Notes

### Relationship with Other Systems
- **Infiltration**: Total outdoor air = Ventilation + Infiltration
- **HVAC**: Ventilation affects coil loads and fan energy
- **Controls**: DCV requires CO2 sensors and controllers
- **Schedules**: Ventilation typically follows occupancy

### Common Use Cases
1. **Office Buildings**: DCV for conference rooms
2. **Schools**: High ventilation with heat recovery
3. **Healthcare**: Maximum ventilation rates
4. **Residential**: Balanced ventilation with ERV
5. **Warehouses**: Natural ventilation strategies

### Performance Impact
- **Heating Energy**: Major impact in cold climates
- **Cooling Energy**: Significant in hot, humid climates
- **Fan Energy**: Proportional to flow rates
- **Indoor Air Quality**: Direct correlation with rates

## Technical Implementation Details

### Ventilation Standards Reference
| Application | ASHRAE 62.1 Minimum | Enhanced Rate | Notes |
|-------------|-------------------|---------------|--------|
| Office | 2.5 L/s per person + 0.3 L/s/m² | 5-7.5 L/s/person | Standard occupancy |
| Classroom | 5 L/s per person + 0.3 L/s/m² | 7.5-10 L/s/person | High occupancy |
| Healthcare | 7.5 L/s per person + 0.3 L/s/m² | 15+ L/s/person | Critical areas |
| Residential | 0.35 ACH or 7.5 L/s/person | 0.5-1.0 ACH | Whole house rate |

### Heat Recovery Effectiveness Guide
| Technology | Sensible | Latent | Application |
|------------|----------|---------|-------------|
| Plate HRV | 60-80% | 0% | Cold, dry climates |
| Rotary ERV | 70-85% | 50-70% | All climates |
| Membrane ERV | 70-80% | 40-60% | Moderate climates |
| Run-around coil | 45-65% | 0% | Separated streams |

### Control Strategies
1. **Fixed Outdoor Air**: Constant ventilation rate
2. **Scheduled**: Varies with occupancy schedule
3. **DCV with CO2**: Modulates based on CO2 levels
4. **Economizer**: Free cooling when appropriate
5. **Night Flush**: Pre-cooling with night air

### Error Handling
- Verify minimum code ventilation rates
- Check for balanced supply/exhaust
- Validate heat recovery physics
- Prevent over-ventilation scenarios

### Special Considerations
1. **Pressure Balance**: Ensure neutral building pressure
2. **Humidity Control**: Important in humid climates
3. **Filtration**: Higher ventilation may need better filters
4. **Noise**: Natural ventilation opening constraints
5. **Security**: Operable windows limitations