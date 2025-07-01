# DHW (Domestic Hot Water) Modification Strategies

## Overview
The DHW system in EnergyPlus models hot water demand, equipment sizing, and operational schedules. This document outlines comprehensive modification strategies for optimizing DHW systems.

## Current Implementation Structure

### 1. Core Parameters
```python
{
    'occupant_density_m2_per_person': float,  # Floor area per person
    'liters_per_person_per_day': float,       # Daily hot water consumption
    'default_tank_volume_liters': float,      # Storage tank size
    'default_heater_capacity_w': float,       # Heater power capacity
    'setpoint_c': float,                      # Water temperature setpoint
    'usage_split_factor': float,              # Peak usage fraction
    'peak_hours': float,                      # Duration of peak period
    'schedule_fractions': {                   # Usage distribution
        'morning': float,
        'peak': float,
        'afternoon': float,
        'evening': float
    }
}
```

### 2. Key Formulas
- **Occupant Count**: `floor_area_m2 / occupant_density`
- **Daily Usage**: `occupant_count * liters_per_person_per_day`
- **Peak Flow Rate**: `(daily_m3 * usage_split_factor) / (peak_hours * 3600)`
- **NTA 8800 Area-based**: `annual_liters = factor_kwh * area * 13.76`

## Modification Strategies

### Level 1: Basic Parameter Tuning

#### 1.1 Occupancy-Based Modifications
**Target Parameters**: `occupant_density_m2_per_person`, `liters_per_person_per_day`

**Strategies**:
- **Conservative**: Increase occupant density by 10-20% (fewer people)
- **Standard**: Use baseline values from lookup tables
- **Aggressive**: Decrease occupant density by 10-20% (more people)

**Implementation**:
```python
# Modify in dhw_lookup.py
'occupant_density_m2_per_person': {
    'pre_calibration': [25, 35],    # Original
    'post_calibration': [20, 30],   # Aggressive (more occupants)
    'conservative': [30, 40]        # Conservative (fewer occupants)
}
```

#### 1.2 Consumption Pattern Modifications
**Target Parameters**: `liters_per_person_per_day`, `usage_split_factor`

**Strategies**:
- **Low Usage**: 30-40 L/person/day
- **Medium Usage**: 40-60 L/person/day (standard)
- **High Usage**: 60-80 L/person/day

**Peak Usage Redistribution**:
```python
# Standard: 60% in peak hours
'usage_split_factor': 0.6

# Flattened: 40% in peak hours (more distributed)
'usage_split_factor': 0.4

# Concentrated: 80% in peak hours
'usage_split_factor': 0.8
```

### Level 2: Schedule Optimization

#### 2.1 Time-of-Use Patterns
**Target**: Schedule fractions and timing

**Residential Profiles**:
```python
# Working Family (shift evening peak)
'schedule_fractions': {
    'morning': 0.15,     # 6-8 AM
    'peak': 0.10,        # 8-10 AM (reduced)
    'afternoon': 0.25,   # 10 AM-5 PM
    'evening': 0.50      # 5-9 PM (increased)
}

# Retiree/Home-based (distributed usage)
'schedule_fractions': {
    'morning': 0.25,
    'peak': 0.25,
    'afternoon': 0.30,
    'evening': 0.20
}

# Student Housing (late schedule)
'schedule_fractions': {
    'morning': 0.10,     # Low morning
    'peak': 0.20,
    'afternoon': 0.30,
    'evening': 0.40      # High evening
}
```

**Non-Residential Profiles**:
```python
# Office (minimal evening)
'schedule_fractions': {
    'morning': 0.30,
    'peak': 0.40,
    'afternoon': 0.25,
    'evening': 0.05
}

# Healthcare (24/7 operation)
'schedule_fractions': {
    'morning': 0.25,
    'peak': 0.25,
    'afternoon': 0.25,
    'evening': 0.25
}
```

### Level 3: Equipment Efficiency Modifications

#### 3.1 Water Heater Efficiency
**Target**: Fuel type and efficiency values

**Strategies**:
```python
# Standard Gas Heater
'fuel_type': 'NaturalGas',
'efficiency': 0.8  # Non-residential
'efficiency': 0.9  # Residential

# High-Efficiency Gas
'fuel_type': 'NaturalGas',
'efficiency': 0.95  # Condensing heater

# Heat Pump Water Heater
'fuel_type': 'Electricity',
'efficiency': 3.0   # COP of heat pump

# Solar with Backup
'fuel_type': 'Electricity',  # Backup
'efficiency': 0.95,
'solar_fraction': 0.6  # 60% from solar
```

#### 3.2 Tank Sizing Optimization
**Formula**: `tank_volume = daily_usage * diversity_factor * storage_factor`

**Strategies**:
```python
# Minimal Storage (instant/tankless)
'storage_factor': 0.1
'diversity_factor': 0.7

# Standard Storage
'storage_factor': 0.5
'diversity_factor': 0.8

# Large Storage (solar/HP systems)
'storage_factor': 1.5
'diversity_factor': 0.9
```

### Level 4: Advanced Control Strategies

#### 4.1 Temperature Setpoint Management
**Target**: `setpoint_c` and control schedules

**Strategies**:
```python
# Standard Fixed
'setpoint_c': 60  # Constant

# Time-Based Reduction
'setpoint_schedule': {
    'occupied': 60,
    'unoccupied': 50,
    'night': 45
}

# Legionella Prevention
'setpoint_c': 55,  # Normal operation
'legionella_cycle': {
    'temperature': 65,
    'frequency': 'weekly',
    'duration': 2  # hours
}
```

#### 4.2 Demand Response Integration
```python
# Load Shifting
'preheat_schedule': {
    'start': 5,  # 5 AM
    'setpoint': 65,  # Overheat
    'coast_period': [7, 19]  # Coast 7 AM - 7 PM
}

# Peak Shaving
'peak_hours': [16, 20],  # 4-8 PM
'peak_reduction': 0.5,   # 50% capacity during peak
```

### Level 5: System Integration Strategies

#### 5.1 Combined Systems
**HVAC Heat Recovery**:
```python
'heat_recovery_source': 'HVAC_Cooling',
'recovery_efficiency': 0.6,
'preheat_tank': True
```

**Solar Integration**:
```python
'solar_collector_area': building_area * 0.02,  # 2% of floor area
'tilt_angle': latitude,
'azimuth': 180,  # South facing
'collector_efficiency': 0.7
```

#### 5.2 Building Type Specific Strategies

**Residential Apartments**:
- Central system with circulation loop
- Higher diversity factor (0.3-0.5)
- Reduced per-unit storage

**Hotels**:
- High morning peak (0.4-0.5 fraction)
- Larger storage factors (1.5-2.0)
- Higher setpoints (65°C)

**Offices**:
- Minimal evening usage
- Point-of-use heaters for kitchenettes
- Lower total capacity

### Level 6: Calibration-Specific Modifications

#### 6.1 Measurement-Based Tuning
```python
# If measured data available
'calibration_factors': {
    'usage_multiplier': measured_daily / calculated_daily,
    'peak_shift_hours': measured_peak_time - scheduled_peak_time,
    'efficiency_correction': measured_energy / theoretical_energy
}
```

#### 6.2 Uncertainty Ranges
```python
# For sensitivity analysis
'parameter_ranges': {
    'liters_per_person': {
        'min': value * 0.7,
        'max': value * 1.3,
        'distribution': 'normal'
    }
}
```

## Implementation Guide

### 1. Direct Modification
Edit values in `dhw_lookup.py` for global changes.

### 2. Excel Override
Use `dhw_overrides_from_excel.py` with structured Excel file:
- Column A: building_id
- Column B: parameter_name
- Column C: new_value

### 3. User Config Override
Add entries to `user_config_dhw`:
```python
{
    'building_id': 'specific_id',
    'dhw_key': 'Apartment',
    'liters_per_person_per_day': 45,
    'efficiency': 0.95
}
```

### 4. Programmatic Modification
```python
# In assign_dhw_values.py
if building_age < 1990:
    values['efficiency'] *= 0.9  # 10% degradation
if building_type == 'Healthcare':
    values['setpoint_c'] = 65  # Higher for safety
```

## Performance Impact Indicators

| Modification | Energy Impact | Comfort Impact | Cost Impact |
|--------------|---------------|----------------|-------------|
| Reduce setpoint 5°C | -10% to -15% | Medium | Low |
| Improve efficiency 0.8→0.95 | -15% to -18% | None | Medium |
| Reduce usage 20% | -20% | High | None |
| Add heat recovery | -30% to -40% | None | High |
| Optimize schedules | -5% to -10% | Low | None |

## Validation Checks

1. **Physical Constraints**:
   - Tank volume ≥ peak hour demand
   - Heater capacity ≥ peak flow rate * ΔT * specific heat
   - Efficiency ≤ 1.0 for non-heat pump

2. **Comfort Standards**:
   - Setpoint ≥ 55°C for Legionella prevention
   - Peak capacity meets 99% demand hours

3. **Code Compliance**:
   - NTA 8800 minimum requirements
   - Local plumbing codes for temperatures

## Future Enhancement Opportunities

1. **Machine Learning Integration**:
   - Occupancy prediction for dynamic setpoints
   - Usage pattern learning

2. **IoT Integration**:
   - Real-time demand response
   - Predictive maintenance

3. **Renewable Integration**:
   - PV-powered heat pumps
   - Thermal storage optimization

4. **District Systems**:
   - Shared DHW systems for multi-family
   - Waste heat recovery networks