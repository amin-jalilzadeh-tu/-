# Lighting (Elec) Modification Strategies

## Overview
The lighting module models both primary lighting loads and parasitic power (controls, emergency lighting) in buildings. It follows NTA 8800 standards and provides extensive modification capabilities for energy optimization.

## Current Implementation Structure

### 1. Core Parameters
```python
{
    'P_light': float,                      # Lighting power density (W/m²)
    'P_parasitic': float,                  # Parasitic power (W/m²) - default 0.285
    'tD': float,                          # Daytime burning hours
    'tN': float,                          # Nighttime burning hours
    'LIGHT_FRACTION_RADIANT': float,       # Radiant heat fraction
    'LIGHT_FRACTION_VISIBLE': float,       # Visible light fraction
    'LIGHT_FRACTION_RETURN_AIR': float,    # Return air heat fraction
    'schedule': dict,                      # Hourly usage patterns
    'FC': float,                          # Replacement value compensation factor
    'Fo_D': float,                        # Daytime occupancy factor
    'Fo_N': float,                        # Nighttime occupancy factor
    'FD': float                           # Daylight factor
}
```

### 2. Key Formulas (NTA 8800)
- **Total Energy**: `W_total = W_lighting + W_parasitic`
- **Lighting Energy**: `W_L = (P_n × FC) × (tD × Fo_D × FD + tN × Fo_N) / 1000`
- **Parasitic Power**: `W_p = 0.285 W/m² × Floor_Area` (24/7 operation)
- **Heat to Space**: `Q_lighting = P_light × (1 - Fraction_Return_Air) × Schedule`

## Modification Strategies

### Level 1: Lighting Power Density Optimization

#### 1.1 Technology-Based LPD Reduction
**Target Parameter**: `P_light`

**Office Lighting Evolution**:
```python
# Traditional Fluorescent T12 (1980s)
'P_light_range': [15.0, 20.0]  # W/m²

# Standard T8 Fluorescent (1990s-2000s)
'P_light_range': [10.0, 15.0]  # W/m²

# Efficient T5/T8 with Electronic Ballasts (2000s-2010s)
'P_light_range': [6.0, 10.0]   # W/m²

# LED Retrofit (2010s-2020s)
'P_light_range': [4.0, 6.0]    # W/m²

# Advanced LED with Controls (2020s+)
'P_light_range': [2.0, 4.0]    # W/m²

# Next-Gen Smart LED (Future)
'P_light_range': [1.5, 3.0]    # W/m²
```

**Task-Based LPD Targets**:
```python
# By visual task requirements
'task_based_lpd': {
    'circulation': 2.0,      # Corridors, lobbies
    'general_office': 3.5,   # Open offices
    'detailed_work': 5.0,    # Design, drafting
    'retail_display': 8.0,   # Merchandise highlighting
    'warehouse': 1.5,        # Storage areas
    'parking': 1.0          # Garages
}
```

#### 1.2 Building Type Specific Strategies

**Healthcare Facilities**:
```python
'healthcare_lpd': {
    'patient_room': 3.0,     # Dimmable, circadian
    'exam_room': 6.0,        # High accuracy tasks
    'surgery': 15.0,         # Specialized task lighting
    'corridor': 2.0,         # 24/7 operation
    'nurses_station': 4.0    # Variable tasks
}
```

**Educational Facilities**:
```python
'education_lpd': {
    'classroom': 3.5,        # Daylight integration
    'laboratory': 5.0,       # Task specific
    'gymnasium': 3.0,        # High bay LED
    'library': 4.0,          # Reading tasks
    'cafeteria': 2.5        # Social space
}
```

### Level 2: Control Strategy Implementation

#### 2.1 Occupancy-Based Controls
**Target Parameters**: `Fo_D`, `Fo_N`, Schedule fractions

**Basic Occupancy Control**:
```python
# Standard occupancy factors
'occupancy_factors': {
    'Fo_D': 0.9,  # 90% during day
    'Fo_N': 0.1   # 10% at night
}

# With occupancy sensors
'occupancy_sensors': {
    'Fo_D': 0.7,  # Actual occupancy
    'Fo_N': 0.05, # Minimal night use
    'vacancy_timeout': 15  # Minutes
}

# Advanced presence detection
'advanced_occupancy': {
    'Fo_D': 0.6,  # Zone-based control
    'Fo_N': 0.02, # Security only
    'granularity': 'workstation'  # Individual control
}
```

**Schedule Optimization**:
```python
# Traditional schedule
'traditional_schedule': {
    '0-6': 0.05,   # Security lighting
    '7-18': 0.90,  # Full operation
    '19-23': 0.30  # Cleaning/late work
}

# Optimized with controls
'controlled_schedule': {
    '0-6': 0.02,   # Emergency only
    '7-8': 0.30,   # Arrival ramp-up
    '9-17': 0.70,  # Actual usage
    '18-19': 0.20, # Departure ramp-down
    '20-23': 0.02  # Emergency only
}
```

#### 2.2 Daylight Harvesting
**Target Parameter**: `FD` (Daylight factor)

**Daylight Zone Definition**:
```python
# Zone depths from windows
'daylight_zones': {
    'primary': {      # 0-4.5m from window
        'FD': 0.3,    # 70% reduction possible
        'control': 'continuous_dimming'
    },
    'secondary': {    # 4.5-9m from window
        'FD': 0.7,    # 30% reduction possible
        'control': 'stepped_dimming'
    },
    'core': {         # >9m from window
        'FD': 1.0,    # No daylight
        'control': 'on_off'
    }
}
```

**Advanced Daylight Integration**:
```python
# Dynamic daylight control
def calculate_daylight_factor(zone_location, window_area, time_of_day):
    base_FD = daylight_zones[zone_location]['FD']
    
    # Adjust for time of day
    solar_angle_factor = get_solar_angle_factor(time_of_day)
    
    # Adjust for window area ratio
    window_factor = min(window_area / zone_area, 0.3)
    
    return base_FD * (1 - solar_angle_factor * window_factor)
```

### Level 3: Heat Distribution Optimization

#### 3.1 Heat Fraction Management
**Target Parameters**: Fraction settings

**LED vs Fluorescent Heat Distribution**:
```python
# Fluorescent T8
'fluorescent_fractions': {
    'fraction_radiant': 0.37,
    'fraction_visible': 0.18,
    'fraction_return_air': 0.20,
    'fraction_convected': 0.25  # Calculated
}

# LED Technology
'led_fractions': {
    'fraction_radiant': 0.20,    # Less IR radiation
    'fraction_visible': 0.35,    # Higher efficacy
    'fraction_return_air': 0.30, # Better heat management
    'fraction_convected': 0.15   # Less convective heat
}
```

#### 3.2 HVAC Integration
```python
# Return air fraction optimization
'return_air_strategy': {
    'heating_mode': 0.0,    # Keep heat in space
    'cooling_mode': 0.5,    # Remove heat via return
    'transition': 0.25      # Moderate removal
}

# Implementation
def optimize_return_air_fraction(zone_temp, setpoint):
    if zone_temp < setpoint - 2:
        return 0.0  # Heating mode
    elif zone_temp > setpoint + 2:
        return 0.5  # Cooling mode
    else:
        return 0.25  # Transition
```

### Level 4: Advanced Lighting Strategies

#### 4.1 Task Tuning
```python
'task_tuning_factors': {
    'over_designed': 0.7,    # Reduce 30%
    'properly_designed': 1.0,
    'under_designed': 1.2    # Increase 20%
}

# Age-based depreciation
'age_factors': {
    'new': 0.9,              # Over-designed for depreciation
    '5_years': 1.0,
    '10_years': 1.1,         # Compensate for lumen depreciation
    'retrofit_needed': 1.3
}
```

#### 4.2 Personal Control Systems
```python
'personal_control': {
    'workstation_range': [0.3, 1.0],  # 30-100% of base
    'default_preference': 0.7,         # Most prefer less
    'learning_enabled': True,          # AI adjustment
    'energy_limit': 0.8                # Max 80% of design
}
```

### Level 5: Smart Lighting Systems

#### 4.1 IoT Integration
```python
'iot_lighting_config': {
    'sensors': {
        'occupancy': 'PIR_ultrasonic',
        'daylight': 'photosensor',
        'task': 'computer_vision'
    },
    'control_algorithm': 'predictive',
    'communication': 'wireless_mesh',
    'update_frequency': 30  # seconds
}

# Predictive control
def predictive_lighting_control(historical_data, current_conditions):
    predicted_occupancy = ml_model.predict(historical_data)
    daylight_forecast = weather_api.get_cloud_cover()
    
    return optimize_schedule(predicted_occupancy, daylight_forecast)
```

#### 4.2 Circadian Lighting
```python
'circadian_schedule': {
    '6-9': {'intensity': 0.8, 'CCT': 5000},    # Morning activation
    '9-12': {'intensity': 1.0, 'CCT': 5500},   # Peak alertness
    '12-14': {'intensity': 0.9, 'CCT': 5000},  # Post-lunch
    '14-17': {'intensity': 0.85, 'CCT': 4500}, # Afternoon
    '17-19': {'intensity': 0.7, 'CCT': 3500},  # Evening transition
    '19-6': {'intensity': 0.3, 'CCT': 2700}    # Night/cleaning
}
```

### Level 6: Parasitic Power Reduction

#### 6.1 Control System Optimization
**Target Parameter**: `P_parasitic`

```python
# Standard parasitic (controls + emergency)
'standard_parasitic': 0.285  # W/m²

# Optimized systems
'optimized_parasitic': {
    'wireless_controls': 0.15,   # No wired infrastructure
    'integrated_emergency': 0.10, # LED emergency lights
    'smart_drivers': 0.08,       # Efficient electronics
    'total': 0.33               # vs 0.285 standard
}

# Advanced reduction
'advanced_parasitic': {
    'dc_grid': 0.05,            # DC power distribution
    'poe_lighting': 0.03,       # Power over Ethernet
    'emergency_testing': 0.02,   # Smart testing cycles
    'total': 0.10               # 65% reduction
}
```

## Implementation Strategies

### Quick Wins (Immediate)
1. **LPD Reduction**: Apply multiplier to existing values
   ```python
   new_lpd = current_lpd * 0.7  # 30% reduction
   ```

2. **Schedule Tightening**: Reduce off-hours usage
   ```python
   night_fraction = 0.02  # vs 0.05
   ```

3. **Simple Controls**: Basic occupancy sensing
   ```python
   Fo_D = 0.8  # vs 0.9
   ```

### Medium Term (3-6 months)
1. **Daylight Harvesting**: Implement FD factors by zone
2. **Advanced Scheduling**: Predictive controls
3. **Task Tuning**: Adjust levels to actual needs

### Long Term (6-12 months)
1. **Full LED Conversion**: Complete technology upgrade
2. **IoT Integration**: Smart building platform
3. **Personal Control**: Individual preferences

## Performance Metrics

| Strategy | Energy Savings | Payback | Complexity |
|----------|---------------|---------|------------|
| LED Conversion | 40-60% | 2-4 years | Low |
| Occupancy Sensors | 20-30% | 1-2 years | Low |
| Daylight Harvesting | 20-40% | 3-5 years | Medium |
| Task Tuning | 15-25% | <1 year | Low |
| Smart Controls | 30-50% | 3-5 years | High |
| Personal Control | 10-20% | 2-3 years | Medium |

## Code Compliance Considerations

### ASHRAE 90.1 LPD Limits
```python
'ashrae_90_1_2019': {
    'office': 6.5,
    'retail': 9.5,
    'school': 7.2,
    'healthcare': 8.8,
    'warehouse': 4.2
}
```

### EN 15193 (European Standard)
```python
'en_15193_leni_targets': {  # kWh/m²/year
    'office': 25,
    'education': 20,
    'healthcare': 35,
    'retail': 40
}
```

## Integration with Other Systems

### HVAC Coordination
- Lighting heat affects cooling loads
- Return air fraction optimization
- Scheduled pre-cooling/heating

### Equipment Synergy
- Combined occupancy sensing
- Shared control infrastructure
- Integrated demand response

### Renewable Integration
- DC microgrid compatibility
- Solar-responsive dimming
- Battery backup for emergency

## Future Technologies

1. **Li-Fi Integration**: Data through light
2. **Quantum Dot LED**: Ultra-high efficiency
3. **Organic LED (OLED)**: Architectural integration
4. **AI-Driven Optimization**: Self-learning systems