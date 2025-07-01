# Key IDF Modification Examples - Summary

## Quick Reference: High-Impact Modifications by Category

### 1. DHW (Domestic Hot Water) - Top 3 Strategies

#### Strategy 1: Temperature Setpoint Reduction
```python
# Reduce setpoint from 60°C to 55°C (saves 10-15% energy)
'dhw_modifications': {
    'setpoint_c': 55,  # Was 60
    'legionella_cycle': {'temperature': 65, 'frequency': 'weekly'}
}
```

#### Strategy 2: Usage Pattern Optimization
```python
# Reduce peak flow by spreading demand
'usage_optimization': {
    'liters_per_person_per_day': 40,  # Was 50
    'usage_split_factor': 0.4,        # Was 0.6 (less peaky)
}
```

#### Strategy 3: Equipment Efficiency
```python
# Upgrade to heat pump water heater
'equipment_upgrade': {
    'fuel_type': 'Electricity',
    'efficiency': 3.0,  # COP (was 0.9 for gas)
}
```

### 2. Equipment (eequip) - Top 3 Strategies

#### Strategy 1: Power Density Reduction
```python
# Modern efficient equipment
'equipment_efficiency': {
    'EQUIP_WM2': 3.0,  # Was 6.0 W/m² (50% reduction)
}
```

#### Strategy 2: Smart Scheduling
```python
# Deep setback during unoccupied hours
'smart_schedule': {
    'night_standby': 0.02,  # Was 0.05
    'lunch_setback': 0.30,  # Was 0.50
}
```

#### Strategy 3: Plug Load Management
```python
# Smart power strips and controls
'plug_load_control': {
    'master_threshold': 10,  # Watts
    'standby_reduction': 0.5  # Watts when off
}
```

### 3. Lighting (Elec) - Top 3 Strategies

#### Strategy 1: LED Conversion
```python
# Upgrade to LED technology
'led_upgrade': {
    'P_light': 3.0,  # Was 10.0 W/m² (70% reduction)
}
```

#### Strategy 2: Daylight Harvesting
```python
# Zone-based daylight control
'daylight_control': {
    'perimeter_zone_FD': 0.3,  # 70% artificial light reduction
    'core_zone_FD': 1.0        # No daylight
}
```

#### Strategy 3: Occupancy Control
```python
# Aggressive occupancy sensing
'occupancy_factors': {
    'Fo_D': 0.6,   # Was 0.9 (actual occupancy)
    'Fo_N': 0.02,  # Was 0.1 (security only)
}
```

### 4. Fenestration (fenez) - Top 3 Strategies

#### Strategy 1: Window Performance
```python
# Upgrade to triple-pane low-e
'window_upgrade': {
    'window_u_value': 1.4,  # Was 2.8 W/m²K
    'window_shgc': 0.35,    # Was 0.68
}
```

#### Strategy 2: WWR Optimization
```python
# Climate-specific window-to-wall ratios
'wwr_by_orientation': {
    'north': 0.25,
    'south': 0.35,
    'east': 0.20,
    'west': 0.15   # Minimize west exposure
}
```

#### Strategy 3: Dynamic Glazing
```python
# Electrochromic windows
'dynamic_glazing': {
    'clear_shgc': 0.50,
    'tinted_shgc': 0.12,
    'control': 'solar_and_glare'
}
```

### 5. Geometry (geomz) - Top 3 Strategies

#### Strategy 1: Optimal Form Factor
```python
# Compact building form
'form_optimization': {
    'aspect_ratio': 1.5,        # Balanced rectangle
    'surface_to_volume': 0.4,   # Compact
}
```

#### Strategy 2: Smart Zoning
```python
# Daylight-based perimeter depth
'zoning_strategy': {
    'perimeter_depth': 4.5,  # Optimal for daylight
    'has_core': True,        # For large buildings
}
```

#### Strategy 3: Orientation
```python
# Climate-specific orientation
'building_orientation': {
    'cold_climate': 0,    # Long axis E-W
    'hot_climate': 90,    # Long axis N-S
}
```

### 6. HVAC - Top 3 Strategies

#### Strategy 1: Setpoint Optimization
```python
# Widen temperature deadband
'efficient_setpoints': {
    'heating_day': 20,     # Was 21°C
    'cooling_day': 26,     # Was 24°C
    'deadband': 6          # Was 3°C
}
```

#### Strategy 2: Heat Recovery
```python
# Add energy recovery ventilation
'heat_recovery': {
    'effectiveness': 0.75,
    'type': 'enthalpy_wheel'
}
```

#### Strategy 3: Variable Speed Control
```python
# VSD on fans and pumps
'variable_speed': {
    'fan_min_speed': 0.3,
    'pump_min_speed': 0.2,
    'control': 'demand_based'
}
```

## Additional Objects - Quick Reference

### Ventilation
```python
# Demand-controlled ventilation
'dcv_control': {
    'co2_setpoint': 800,  # ppm
    'min_flow': 0.003,    # m³/s per m²
}
```

### Shading
```python
# Automated exterior shading
'shading_control': {
    'solar_setpoint': 300,  # W/m²
    'schedule': 'cooling_season_only'
}
```

### Ground Temperature
```python
# Site-specific ground temps
'ground_temps': {
    'monthly_values': [10, 11, 13, 15, 18, 20, 22, 21, 19, 16, 13, 11]
}
```

### Zone Sizing
```python
# Right-size HVAC equipment
'sizing_factors': {
    'heating_factor': 1.15,  # Was 1.25
    'cooling_factor': 1.10   # Was 1.25
}
```

## Implementation Priority Matrix

| Modification | Energy Impact | Cost | Complexity | Payback |
|-------------|--------------|------|------------|---------|
| HVAC Setpoints | 10-15% | None | Low | Immediate |
| Lighting Controls | 20-30% | Low | Low | <1 year |
| Equipment Schedule | 15-20% | Low | Low | <1 year |
| Window Upgrade | 15-25% | High | Medium | 5-10 years |
| Heat Recovery | 20-40% | High | High | 3-7 years |
| LED Conversion | 40-60% | Medium | Low | 2-4 years |

## Combined Strategy Example

### Comprehensive Retrofit Package
```python
'deep_retrofit': {
    # Envelope
    'windows': {'u_value': 1.4, 'shgc': 0.35},
    'walls': {'r_value': 5.3},
    
    # Systems
    'hvac': {'heat_recovery': 0.75, 'vsd': True},
    'lighting': {'lpd': 3.0, 'controls': 'full'},
    
    # Operations
    'setpoints': {'heat': 20, 'cool': 26},
    'schedules': {'optimized': True},
    
    # Expected savings: 50-70%
}
```