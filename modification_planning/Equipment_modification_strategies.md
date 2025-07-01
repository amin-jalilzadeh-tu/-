# Equipment (eequip) Modification Strategies

## Overview
The equipment module models plug loads and miscellaneous electric loads (MELs) in buildings. This includes computers, appliances, and other electrical equipment that contribute to internal heat gains and energy consumption.

## Current Implementation Structure

### 1. Core Parameters
```python
{
    'EQUIP_WM2': float,                    # Power density (W/m²)
    'EQUIP_FRACTION_LATENT': float,        # Latent heat fraction (default: 0.0)
    'EQUIP_FRACTION_RADIANT': float,       # Radiant heat fraction (default: 0.1)
    'EQUIP_FRACTION_LOST': float,          # Lost heat fraction (default: 0.8)
    'schedule': dict,                      # Hourly usage fractions
    'tD': float,                          # Daytime hours (informational)
    'tN': float                           # Nighttime hours (informational)
}
```

### 2. Key Formulas
- **Hourly Energy**: `EQUIP_WM2 × Zone_Floor_Area × Schedule_Fraction`
- **Sensible Heat**: `Total_Heat × (1 - Fraction_Latent)`
- **Convective Heat**: `Sensible_Heat × (1 - Fraction_Radiant - Fraction_Lost)`
- **Heat to Space**: `Total_Heat × (1 - Fraction_Lost)`

## Modification Strategies

### Level 1: Power Density Optimization

#### 1.1 Technology-Based Reductions
**Target Parameter**: `EQUIP_WM2`

**Office Equipment Evolution**:
```python
# Legacy Equipment (pre-2000)
'EQUIP_WM2_range': [10.0, 15.0]  # CRT monitors, desktop PCs

# Standard Current (2000-2015)
'EQUIP_WM2_range': [6.0, 10.0]   # LCD monitors, efficient PCs

# Energy Star (2015-2020)
'EQUIP_WM2_range': [4.0, 6.0]    # LED monitors, laptops

# Best Practice (2020+)
'EQUIP_WM2_range': [2.5, 4.0]    # Thin clients, efficient laptops

# Future/Net-Zero
'EQUIP_WM2_range': [1.5, 2.5]    # Cloud computing, minimal local
```

**Residential Equipment**:
```python
# Standard Home
'EQUIP_WM2_range': [3.0, 5.0]

# Efficient Home (Energy Star appliances)
'EQUIP_WM2_range': [2.0, 3.5]

# Smart Home (connected, optimized)
'EQUIP_WM2_range': [1.5, 2.5]
```

#### 1.2 Building Type Specific Strategies

**Data Centers/Server Rooms**:
```python
# Traditional
'EQUIP_WM2': 200-500  # Server rooms

# Virtualized
'EQUIP_WM2': 100-200  # Consolidated servers

# Cloud-based
'EQUIP_WM2': 20-50    # Minimal on-site
```

**Retail**:
```python
# Standard Retail
'EQUIP_WM2': 5-8      # POS, displays

# Big Box/Electronics
'EQUIP_WM2': 8-12     # Many displays

# Efficient Retail
'EQUIP_WM2': 3-5      # LED displays, efficient POS
```

### Level 2: Schedule Optimization

#### 2.1 Occupancy-Based Controls
**Target**: Schedule fractions

**Standard Office Schedule**:
```python
'schedule_weekday': {
    '0-6': 0.05,    # Night standby
    '7': 0.20,      # Startup
    '8-12': 0.90,   # Morning work
    '12-13': 0.50,  # Lunch reduction
    '13-17': 0.90,  # Afternoon work
    '18': 0.30,     # Departure
    '19-23': 0.05   # Night standby
}
```

**Optimized with Occupancy Sensors**:
```python
'schedule_weekday': {
    '0-6': 0.02,    # Deep standby
    '7': 0.10,      # Pre-occupancy
    '8-12': 0.70,   # Actual usage (not all occupied)
    '12-13': 0.30,  # Lunch reduction
    '13-17': 0.70,  # Actual usage
    '18': 0.15,     # Rapid shutdown
    '19-23': 0.02   # Deep standby
}
```

**Advanced Plug Load Management**:
```python
# Tiered control system
'control_tiers': {
    'always_on': 0.02,      # Servers, emergency
    'occupied_only': 0.00,  # Turns off completely
    'scheduled': 0.05,      # Follows schedule
    'demand_response': 0.50 # Can be curtailed
}

# Resulting schedule
'optimized_schedule': {
    'unoccupied': sum([always_on]),
    'occupied': sum([always_on, occupied_only, scheduled]),
    'peak_demand': sum([always_on, scheduled * demand_response])
}
```

#### 2.2 Day Type Variations

**Flexible Work Schedules**:
```python
# Monday/Friday (hybrid work)
'schedule_hybrid_day': {
    '8-17': 0.60,  # Reduced occupancy
    'other': 0.05
}

# Tuesday-Thursday (full occupancy)
'schedule_full_day': {
    '8-17': 0.90,
    'other': 0.05
}

# Weekend (minimal)
'schedule_weekend': {
    'all_hours': 0.02
}
```

### Level 3: Heat Fraction Optimization

#### 3.1 Equipment Type Based Distribution
**Target**: Heat fractions

**Standard IT Equipment**:
```python
'heat_fractions': {
    'fraction_radiant': 0.1,   # Minimal radiant
    'fraction_latent': 0.0,    # No moisture
    'fraction_lost': 0.8       # Most heat exhausted
}
```

**Kitchen Equipment**:
```python
'heat_fractions': {
    'fraction_radiant': 0.3,   # Cooking surfaces
    'fraction_latent': 0.2,    # Steam/moisture
    'fraction_lost': 0.4       # Hood exhaust
}
```

**Optimized Server Room**:
```python
'heat_fractions': {
    'fraction_radiant': 0.05,  # Minimal
    'fraction_latent': 0.0,    
    'fraction_lost': 0.9       # Direct exhaust
}
```

#### 3.2 HVAC Integration Strategies

**Heat Recovery Potential**:
```python
# Identify recoverable heat
if fraction_lost > 0.5:
    recovery_potential = equipment_heat * fraction_lost * 0.6
    # Route to heat recovery system
```

**Zone-Based Distribution**:
```python
# Perimeter zones (heating needed)
'perimeter_equipment': {
    'fraction_lost': 0.3,      # Keep more heat
    'fraction_radiant': 0.3    # Offset heating
}

# Core zones (cooling dominated)
'core_equipment': {
    'fraction_lost': 0.8,      # Remove more heat
    'fraction_radiant': 0.1    # Minimize radiant
}
```

### Level 4: Advanced Control Strategies

#### 4.1 Smart Power Strips
```python
'smart_strip_config': {
    'master_threshold': 10,     # Watts to trigger
    'slave_devices': ['monitor', 'printer', 'charger'],
    'standby_power': 0.5,       # Watts when off
    'active_power': 'measured'  # Actual usage
}

# Implementation
def calculate_smart_strip_usage(master_on):
    if master_on:
        return active_power
    else:
        return standby_power
```

#### 4.2 Demand Response Integration
```python
'demand_response_levels': {
    'normal': 1.0,             # 100% available
    'moderate': 0.7,           # 30% reduction
    'aggressive': 0.4,         # 60% reduction
    'emergency': 0.2           # 80% reduction
}

# Time-based implementation
'dr_schedule': {
    'peak_hours': [14, 18],    # 2 PM - 6 PM
    'dr_level': 'moderate',
    'excluded_loads': ['critical_equipment']
}
```

### Level 5: Building-Specific Optimization

#### 5.1 Office Buildings
```python
'office_optimization': {
    # Workstation optimization
    'workstation_wm2': 30,     # W per workstation
    'workstation_density': 0.1, # Workstations per m²
    'resulting_wm2': 3.0,
    
    # Common area reduction
    'conference_standby': 0.02,
    'kitchen_schedule': 'meal_times_only',
    'printer_consolidation': 0.5  # 50% reduction
}
```

#### 5.2 Schools
```python
'school_optimization': {
    # Classroom controls
    'projector_auto_off': 15,    # Minutes
    'computer_lab_schedule': 'class_schedule',
    'summer_setback': 0.01,      # Near zero
    
    # Administrative
    'office_controls': 'occupancy_based',
    'server_room': 'constant_low'
}
```

#### 5.3 Retail
```python
'retail_optimization': {
    # Display optimization
    'display_dimming': {
        'closed_hours': 0.0,
        'low_traffic': 0.5,
        'normal': 1.0
    },
    
    # POS optimization
    'pos_standby': 'transaction_triggered',
    'backoffice_schedule': 'business_hours_only'
}
```

### Level 6: Measurement and Verification

#### 6.1 Submetering Strategy
```python
'metering_points': {
    'panel_level': ['lighting', 'equipment', 'HVAC'],
    'circuit_level': ['server_room', 'kitchen', 'workstations'],
    'device_level': ['major_equipment']
}

# Calibration factors from measurements
'measured_adjustments': {
    'workstation_actual': 25,    # W, vs 30W estimated
    'standby_actual': 0.03,      # vs 0.05 estimated
    'peak_coincidence': 0.8      # Not all peak together
}
```

#### 6.2 Continuous Optimization
```python
'optimization_triggers': {
    'usage_increase': 1.2,       # 20% above baseline
    'schedule_mismatch': 0.3,    # 30% difference
    'standby_creep': 1.5        # 50% increase
}

# Adaptive response
def adaptive_equipment_control(measurements):
    if measurements['standby'] > baseline * 1.5:
        implement_deeper_setback()
    if measurements['peak'] > target:
        implement_demand_response()
```

## Implementation Guide

### 1. Quick Wins (Immediate)
- Reduce standby power: 0.05 → 0.02
- Implement lunch setback: 0.9 → 0.5
- Adjust heat fractions for zone type

### 2. Medium Term (3-6 months)
- Deploy occupancy sensors
- Install smart power strips
- Implement tiered control

### 3. Long Term (6-12 months)
- Full demand response integration
- Equipment replacement program
- Continuous commissioning

## Performance Metrics

| Strategy | Energy Savings | Cost | Complexity |
|----------|---------------|------|------------|
| Schedule optimization | 10-20% | Low | Low |
| Power density reduction | 20-40% | Medium | Medium |
| Smart controls | 25-35% | Medium | Medium |
| Demand response | 15-25% | Low | High |
| Equipment upgrade | 30-50% | High | Low |

## Validation Requirements

1. **Power Density Bounds**:
   - Minimum: 1.0 W/m² (nearly empty building)
   - Maximum: 50 W/m² (data center areas)
   - Typical: 3-10 W/m²

2. **Schedule Constraints**:
   - Minimum standby: ≥ 0.01 (some always-on loads)
   - Peak usage: ≤ 1.0 (cannot exceed 100%)
   - Smooth transitions (avoid instant 0→1)

3. **Heat Balance**:
   - Radiant + Latent + Lost ≤ 1.0
   - Convective = 1 - Radiant - Latent - Lost

## Integration with Other Systems

### HVAC Interaction
- Equipment heat affects cooling loads
- Schedule coordination for optimal efficiency
- Heat recovery opportunities

### Lighting Coordination
- Combined occupancy sensing
- Integrated controls
- Peak demand management

### Renewable Integration
- Solar PV sizing based on equipment loads
- Battery storage for peak shaving
- DC power distribution potential