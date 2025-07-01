# HVAC Modification Strategies

## Overview
The HVAC module manages heating, ventilation, and air conditioning systems including setpoints, schedules, system types, and efficiency parameters. It's the most critical component for building energy consumption.

## Current Implementation Structure

### 1. Core Parameters
```python
{
    # Temperature Setpoints
    'heating_day_setpoint': float,         # °C (19-21)
    'heating_night_setpoint': float,       # °C (15-16)
    'cooling_day_setpoint': float,         # °C (26-34)
    'cooling_night_setpoint': float,       # °C (26-34)
    
    # Supply Air Temperatures
    'max_heating_supply_air_temp': float,  # °C (45-55)
    'min_cooling_supply_air_temp': float,  # °C (12-14)
    
    # System Parameters
    'hvac_availability': dict,             # Schedule fractions
    'outdoor_air_flow_rate': float,        # m³/s per person
    'heat_recovery_effectiveness': float,   # 0-1
    'economizer_control': str,             # Control type
    
    # Equipment Efficiency
    'heating_cop': float,                  # Coefficient of performance
    'cooling_cop': float,                  # Coefficient of performance
    'fan_efficiency': float,               # 0-1
    'pump_efficiency': float               # 0-1
}
```

### 2. System Types
- **Ideal Loads Air System**: Simplified perfect control
- **VAV with Reheat**: Variable air volume systems
- **Fan Coil Units**: Zone-level hydronic
- **VRF Systems**: Variable refrigerant flow
- **Radiant Systems**: Hydronic floor/ceiling
- **Natural Ventilation**: Passive cooling

## Modification Strategies

### Level 1: Setpoint Optimization

#### 1.1 Temperature Setpoint Strategies
**Target Parameters**: Heating/cooling setpoints

**Energy-Efficient Setpoints**:
```python
# Standard Comfort (ASHRAE 55)
'standard_setpoints': {
    'heating_day': 21.0,
    'heating_night': 18.0,
    'cooling_day': 24.0,
    'cooling_night': 26.0
}

# Energy Saving
'energy_saving_setpoints': {
    'heating_day': 20.0,
    'heating_night': 16.0,
    'cooling_day': 26.0,
    'cooling_night': 28.0
}

# Aggressive Saving
'aggressive_setpoints': {
    'heating_day': 19.0,
    'heating_night': 15.0,
    'cooling_day': 28.0,
    'cooling_night': 30.0
}

# Adaptive Comfort (EN 15251)
def adaptive_setpoint(outdoor_temp):
    comfort_temp = 0.33 * outdoor_temp + 18.8
    heating_setpoint = comfort_temp - 3.0
    cooling_setpoint = comfort_temp + 3.0
    return heating_setpoint, cooling_setpoint
```

#### 1.2 Deadband Management
```python
'deadband_strategies': {
    'narrow': {
        'heating_max': 21.0,
        'cooling_min': 23.0,
        'deadband': 2.0  # °C
    },
    'standard': {
        'heating_max': 21.0,
        'cooling_min': 24.0,
        'deadband': 3.0
    },
    'wide': {
        'heating_max': 20.0,
        'cooling_min': 26.0,
        'deadband': 6.0
    }
}
```

### Level 2: Schedule Optimization

#### 2.1 Occupancy-Based Scheduling
**Target**: HVAC availability schedules

**Office Building Schedules**:
```python
'optimized_office_schedule': {
    'weekday': [
        ('00:00', 0.0),  # Off
        ('05:00', 0.5),  # Pre-conditioning
        ('07:00', 1.0),  # Full operation
        ('18:00', 0.5),  # Reduced
        ('20:00', 0.0)   # Off
    ],
    'saturday': [
        ('00:00', 0.0),
        ('08:00', 0.3),  # Partial
        ('14:00', 0.0)
    ],
    'sunday': 'always_off'
}

# Optimal start/stop
def optimal_start_time(outdoor_temp, indoor_temp, target_temp):
    temp_diff = abs(target_temp - indoor_temp)
    if outdoor_temp < 0:
        minutes_needed = temp_diff * 30  # Cold weather
    else:
        minutes_needed = temp_diff * 15  # Mild weather
    return minutes_needed
```

#### 2.2 Demand-Controlled Ventilation
```python
'dcv_strategies': {
    'co2_based': {
        'min_outdoor_air': 0.003,  # m³/s per m²
        'max_outdoor_air': 0.01,
        'co2_setpoint': 800,       # ppm
        'control': 'proportional'
    },
    'occupancy_based': {
        'unoccupied_flow': 0.0,
        'occupied_flow': 0.008,    # m³/s per person
        'sensor_type': 'PIR'
    }
}
```

### Level 3: System Efficiency Improvements

#### 3.1 Heat Recovery Systems
**Target Parameter**: `heat_recovery_effectiveness`

```python
'heat_recovery_types': {
    'none': {
        'effectiveness': 0.0,
        'pressure_drop': 0
    },
    'sensible_wheel': {
        'effectiveness': 0.75,
        'pressure_drop': 150  # Pa
    },
    'enthalpy_wheel': {
        'effectiveness': 0.80,
        'latent_effectiveness': 0.75,
        'pressure_drop': 200
    },
    'plate_exchanger': {
        'effectiveness': 0.65,
        'pressure_drop': 100
    },
    'heat_pipe': {
        'effectiveness': 0.60,
        'pressure_drop': 80
    }
}
```

#### 3.2 Variable Speed Drives
```python
'vsd_control': {
    'fan_control': {
        'min_speed': 0.3,      # 30% minimum
        'control': 'pressure',
        'energy_savings': 0.5   # 50% at part load
    },
    'pump_control': {
        'min_speed': 0.2,
        'control': 'differential_pressure',
        'energy_savings': 0.6
    }
}

# Fan power calculation
def fan_power_with_vsd(flow_fraction):
    # Cube law for fans
    return flow_fraction ** 3
```

### Level 4: Advanced System Types

#### 4.1 High-Performance VAV
```python
'high_performance_vav': {
    'supply_air_temp_reset': {
        'cooling_max': 16.0,
        'cooling_min': 13.0,
        'reset_based_on': 'zone_demand'
    },
    'static_pressure_reset': {
        'max_pressure': 500,    # Pa
        'min_pressure': 150,
        'control': 'critical_zone'
    },
    'terminal_units': {
        'min_flow_fraction': 0.2,
        'reheat_type': 'hot_water',
        'parallel_fan_powered': True
    }
}
```

#### 4.2 VRF System Optimization
```python
'vrf_optimization': {
    'operating_modes': {
        'cooling_only': {'cop': 4.5},
        'heating_only': {'cop': 4.0},
        'heat_recovery': {'cop': 5.5}
    },
    'part_load_performance': {
        '100%': 1.0,
        '75%': 1.15,   # Better efficiency
        '50%': 1.25,
        '25%': 1.10
    },
    'refrigerant_pipe_length': {
        'max_vertical': 50,     # m
        'max_total': 300,
        'correction_factor': 0.95
    }
}
```

### Level 5: Natural Ventilation Integration

#### 5.1 Mixed-Mode Strategies
```python
'mixed_mode_control': {
    'changeover': {
        'outdoor_temp_min': 18,
        'outdoor_temp_max': 24,
        'indoor_temp_max': 26,
        'wind_speed_max': 5,    # m/s
        'mode': 'natural_priority'
    },
    'concurrent': {
        'zones': ['perimeter'],
        'mechanical_reduction': 0.5,
        'window_control': 'automated'
    }
}

def natural_vent_availability(outdoor_temp, indoor_temp, wind_speed):
    if 18 <= outdoor_temp <= 24:
        if outdoor_temp < indoor_temp - 2:
            if wind_speed < 5:
                return True
    return False
```

### Level 6: Predictive Control

#### 6.1 Model Predictive Control
```python
'mpc_parameters': {
    'prediction_horizon': 24,      # hours
    'control_horizon': 4,
    'optimization_objectives': [
        'minimize_energy',
        'maintain_comfort',
        'reduce_peak_demand'
    ],
    'constraints': {
        'temp_min': 20,
        'temp_max': 26,
        'ramp_rate': 2         # °C/hour
    }
}

# Simple predictive pre-cooling
def predictive_precool(forecast_high_temp, current_hour):
    if forecast_high_temp > 30:
        if 2 <= current_hour <= 6:
            return 20  # Pre-cool to 20°C
    return None
```

## Quick Implementation Examples

### Example 1: Immediate Energy Savings (10-20%)
```python
# Widen temperature deadband
'quick_wins': {
    'heating_day': 20.0,      # Was 21.0
    'cooling_day': 26.0,      # Was 24.0
    'night_setback': 4.0,     # Was 2.0
    'weekend_setback': True
}
```

### Example 2: Schedule Optimization (15-25%)
```python
# Reduce HVAC runtime
'schedule_optimization': {
    'start_delay': 30,        # Minutes after occupancy
    'early_shutdown': 60,     # Minutes before leaving
    'lunch_reduction': 0.5,   # 50% capacity
    'weekend_mode': 'off'
}
```

### Example 3: System Efficiency (20-40%)
```python
# Add heat recovery and VSD
'efficiency_upgrades': {
    'heat_recovery': 0.75,
    'fan_vsd': True,
    'supply_temp_reset': True,
    'economizer': 'differential_enthalpy'
}
```

## Performance Metrics

| Strategy | Energy Savings | Comfort Impact | Implementation Cost |
|----------|---------------|----------------|-------------------|
| Setpoint adjustment | 5-15% | Medium | None |
| Schedule optimization | 10-25% | Low | Low |
| Heat recovery | 20-40% | None | High |
| VSD installation | 20-50% | None | Medium |
| Natural ventilation | 10-40% | Variable | Medium |
| Full optimization | 40-70% | Positive | High |

## Key Takeaways

1. **Start with setpoints**: Easy, no-cost savings
2. **Optimize schedules**: Match HVAC to actual occupancy
3. **Add controls**: VSDs, heat recovery, economizers
4. **Consider climate**: Natural ventilation where applicable
5. **Monitor and adjust**: Continuous commissioning critical