# Fenestration (fenez) Modification Strategies

## Overview
The fenestration module manages windows, doors, and their thermal properties including window-to-wall ratios (WWR), glazing properties (U-value, SHGC), and construction assemblies. It's critical for both thermal performance and daylighting.

## Current Implementation Structure

### 1. Core Parameters
```python
{
    # Geometric Parameters
    'wwr': float,                          # Window-to-wall ratio (0-1)
    'window_height': float,                # Window height (m)
    'window_sill_height': float,           # Sill height from floor (m)
    
    # Thermal Properties - Windows
    'window_u_value': float,               # W/m²K (1.4-5.1)
    'window_shgc': float,                  # Solar heat gain coefficient (0.4-0.8)
    'window_vt': float,                    # Visible transmittance (0.4-0.86)
    
    # Thermal Properties - Opaque
    'wall_r_value': float,                 # m²K/W (0.19-4.5)
    'roof_r_value': float,                 # m²K/W (0.22-6.0)
    'floor_r_value': float,                # m²K/W (0.15-3.5)
    'door_u_value': float,                 # W/m²K (1.4-3.4)
    
    # Material Properties
    'conductivity': float,                 # W/mK
    'density': float,                      # kg/m³
    'specific_heat': float,                # J/kgK
    'thermal_absorptance': float,          # 0-1
    'solar_absorptance': float,            # 0-1
    'visible_absorptance': float           # 0-1
}
```

### 2. Key Relationships
- **R-value to Conductivity**: `Conductivity = Thickness / R_value`
- **U-value to Conductivity**: `Conductivity = U_value × Thickness`
- **Total Window Area**: `WWR × Exterior_Wall_Area`
- **Heat Transfer**: `Q = U × A × ΔT`

## Modification Strategies

### Level 1: Window-to-Wall Ratio Optimization

#### 1.1 Climate-Based WWR
**Target Parameter**: `wwr`

**Cold Climate Strategy**:
```python
'cold_climate_wwr': {
    'north': 0.15,      # Minimize heat loss
    'south': 0.40,      # Maximize solar gain
    'east': 0.20,       # Morning sun
    'west': 0.20,       # Afternoon sun
    'average': 0.24
}
```

**Hot Climate Strategy**:
```python
'hot_climate_wwr': {
    'north': 0.30,      # Daylight without direct sun
    'south': 0.25,      # Controlled with overhangs
    'east': 0.15,       # Minimize morning heat
    'west': 0.10,       # Minimize afternoon heat
    'average': 0.20
}
```

**Temperate Climate Strategy**:
```python
'temperate_climate_wwr': {
    'north': 0.25,      # Balanced daylight
    'south': 0.35,      # Solar gain with shading
    'east': 0.25,       # Moderate morning sun
    'west': 0.25,       # Moderate afternoon sun
    'average': 0.28
}
```

#### 1.2 Building Type Specific WWR

**Office Buildings**:
```python
'office_wwr_optimization': {
    'perimeter_office': 0.40,    # Daylight/views
    'open_office': 0.35,         # Balance daylight/thermal
    'conference': 0.25,          # Glare control
    'circulation': 0.15,         # Minimal
    'core': 0.0                  # No exterior exposure
}
```

**Residential**:
```python
'residential_wwr': {
    'living_spaces': 0.30,       # Views and daylight
    'bedrooms': 0.20,            # Privacy and thermal
    'bathrooms': 0.10,           # Privacy
    'kitchens': 0.25             # Task lighting
}
```

### Level 2: Glazing Performance Enhancement

#### 2.1 U-Value Improvements
**Target Parameter**: `window_u_value`

**Progressive Window Technologies**:
```python
# Single Clear Glass
'single_clear': {
    'u_value': 5.1,
    'shgc': 0.80,
    'vt': 0.86
}

# Double Clear Glass
'double_clear': {
    'u_value': 2.8,
    'shgc': 0.68,
    'vt': 0.75
}

# Double Low-E
'double_lowe': {
    'u_value': 1.8,
    'shgc': 0.55,
    'vt': 0.65
}

# Triple Low-E
'triple_lowe': {
    'u_value': 1.4,
    'shgc': 0.40,
    'vt': 0.55
}

# Vacuum Insulated Glass (VIG)
'vacuum_glass': {
    'u_value': 0.7,
    'shgc': 0.45,
    'vt': 0.60
}
```

#### 2.2 SHGC Optimization by Climate

**Climate-Specific Selection**:
```python
def select_shgc_by_climate(climate_zone, orientation):
    climate_shgc = {
        'cold': {'south': 0.60, 'other': 0.40},
        'temperate': {'south': 0.45, 'other': 0.35},
        'hot': {'all': 0.25}
    }
    
    if climate_zone == 'hot':
        return climate_shgc['hot']['all']
    else:
        return climate_shgc[climate_zone].get(orientation, 
               climate_shgc[climate_zone]['other'])
```

### Level 3: Opaque Envelope Enhancement

#### 3.1 Wall Insulation Strategies
**Target Parameter**: `wall_r_value`

**Progressive Insulation Levels**:
```python
# Minimum Code (varies by climate)
'code_minimum': {
    'wall_r': 2.0,      # R-13 cavity
    'roof_r': 3.5,      # R-20
    'floor_r': 2.0      # R-13
}

# Energy Efficient
'energy_efficient': {
    'wall_r': 3.5,      # R-20 + continuous
    'roof_r': 5.3,      # R-30
    'floor_r': 3.5      # R-20
}

# High Performance
'high_performance': {
    'wall_r': 5.3,      # R-30 advanced wall
    'roof_r': 8.8,      # R-50
    'floor_r': 5.3      # R-30
}

# Passive House
'passive_house': {
    'wall_r': 8.8,      # R-50
    'roof_r': 14.0,     # R-80
    'floor_r': 8.8      # R-50
}
```

#### 3.2 Thermal Mass Integration
```python
'thermal_mass_strategies': {
    'lightweight': {
        'density': 50,       # kg/m³
        'specific_heat': 840,
        'thickness': 0.015   # m
    },
    'medium_mass': {
        'density': 800,
        'specific_heat': 1000,
        'thickness': 0.10
    },
    'high_mass': {
        'density': 2000,     # Concrete
        'specific_heat': 900,
        'thickness': 0.20
    }
}
```

### Level 4: Dynamic Fenestration

#### 4.1 Electrochromic Windows
```python
'electrochromic_control': {
    'clear_state': {
        'shgc': 0.50,
        'vt': 0.70
    },
    'tinted_state': {
        'shgc': 0.12,
        'vt': 0.03
    },
    'control_algorithm': 'glare_and_solar',
    'transition_time': 300  # seconds
}

# Control logic
def electrochromic_control(solar_irradiance, glare_index):
    if solar_irradiance > 400 or glare_index > 0.4:
        return 'tinted_state'
    else:
        return 'clear_state'
```

#### 4.2 Automated Shading Integration
```python
'automated_shading': {
    'exterior_blinds': {
        'solar_cutoff': 300,     # W/m²
        'slat_angle_control': 'solar_profile',
        'wind_retract': 15       # m/s
    },
    'interior_shades': {
        'glare_threshold': 2000, # cd/m²
        'openness_factor': 0.05,
        'schedule_override': True
    }
}
```

### Level 5: Orientation-Specific Strategies

#### 5.1 Facade Differentiation
```python
'facade_optimization': {
    'north': {
        'wwr': 0.30,
        'u_value': 1.4,      # Best insulation
        'shgc': 0.60,        # Max daylight
        'shading': None
    },
    'south': {
        'wwr': 0.40,
        'u_value': 1.8,
        'shgc': 0.45,
        'shading': 'horizontal_overhang'
    },
    'east': {
        'wwr': 0.25,
        'u_value': 1.8,
        'shgc': 0.35,
        'shading': 'vertical_fins'
    },
    'west': {
        'wwr': 0.20,
        'u_value': 1.8,
        'shgc': 0.25,        # Minimize heat gain
        'shading': 'exterior_blinds'
    }
}
```

### Level 6: Advanced Material Properties

#### 6.1 Spectral Selective Coatings
```python
'spectral_selective': {
    'visible_transmittance': 0.70,    # High daylight
    'solar_transmittance': 0.30,      # Low heat
    'nir_reflectance': 0.60,          # Reflect near-infrared
    'emissivity': 0.84                # Standard
}

# Performance calculation
def spectral_performance(coating):
    light_to_solar_gain = coating['visible_transmittance'] / coating['shgc']
    return light_to_solar_gain  # Target > 2.0
```

#### 6.2 Phase Change Materials
```python
'pcm_integration': {
    'melt_temperature': 23,           # °C
    'latent_heat': 180000,           # J/kg
    'conductivity_solid': 0.2,        # W/mK
    'conductivity_liquid': 0.15,
    'location': 'interior_wall_surface'
}
```

## Implementation Strategies

### Quick Wins (Immediate)
1. **WWR Adjustment**: Optimize by orientation
   ```python
   # Reduce west-facing WWR
   if orientation == 'west':
       wwr *= 0.7
   ```

2. **Glazing Upgrade**: Specify better U-values
   ```python
   # Upgrade all windows
   window_u_value = min(current_u * 0.6, 1.8)
   ```

### Medium Term (3-6 months)
1. **Envelope Upgrades**: Improve R-values systematically
2. **Shading Integration**: Add overhangs and fins
3. **Spectral Selective Glass**: For south/west facades

### Long Term (6-12 months)
1. **Dynamic Glass**: Electrochromic or thermochromic
2. **Full Facade Optimization**: Complete redesign
3. **Integrated Daylighting**: With lighting controls

## Performance Impact

| Modification | Energy Impact | Comfort Impact | Cost |
|--------------|---------------|----------------|------|
| WWR Optimization | 5-15% | Medium | Low |
| U-value 2.8→1.8 | 10-20% | High | Medium |
| SHGC Tuning | 5-20% | High | Low |
| Wall R +50% | 5-10% | Medium | High |
| Dynamic Glass | 10-30% | Very High | Very High |

## Climate Zone Recommendations

### Cold Climate (Zones 5-8)
```python
'cold_climate_package': {
    'wwr': 0.30,
    'south_wwr': 0.40,
    'window_u': 1.4,
    'window_shgc': 0.50,
    'wall_r': 5.3,
    'roof_r': 8.8
}
```

### Hot Climate (Zones 1-3)
```python
'hot_climate_package': {
    'wwr': 0.20,
    'window_u': 2.0,
    'window_shgc': 0.25,
    'wall_r': 3.5,
    'roof_r': 5.3,
    'cool_roof_reflectance': 0.7
}
```

### Mixed Climate (Zone 4)
```python
'mixed_climate_package': {
    'wwr': 0.30,
    'window_u': 1.8,
    'window_shgc': 0.35,
    'wall_r': 4.0,
    'roof_r': 6.0
}
```

## Integration Considerations

### Daylighting Coordination
- Balance WWR with lighting energy
- Maintain minimum VT for views
- Coordinate with lighting controls

### HVAC Sizing
- Reduced loads allow smaller equipment
- Consider thermal mass effects
- Account for solar gains

### Moisture Management
- Avoid condensation with better windows
- Continuous insulation prevents thermal bridges
- Vapor barriers as needed

## Future Technologies

1. **Aerogel Windows**: U-value < 0.5
2. **Building Integrated PV Glass**: Generate while shading
3. **Liquid Crystal Windows**: Instant privacy/shading
4. **Self-Cleaning Coatings**: Maintain performance