# Geometry (geomz) Modification Strategies

## Overview
The geometry module defines building form, dimensions, zoning strategies, and spatial relationships. These parameters significantly impact heating/cooling loads, daylighting potential, and natural ventilation opportunities.

## Current Implementation Structure

### 1. Core Parameters
```python
{
    # Building Dimensions
    'building_area': float,                # Total floor area (m²)
    'building_perimeter': float,           # External perimeter (m)
    'building_height': float,              # Total height (m)
    'number_of_floors': int,               # Floor count
    'floor_height': float,                 # Individual floor height (m)
    'orientation': float,                  # Rotation angle (degrees)
    
    # Zoning Parameters
    'perimeter_depth': float,              # Depth of perimeter zones (m)
    'has_core': bool,                      # Core zone presence
    'zone_multiplier': int,                # Zone repetition factor
    
    # Calculated Properties
    'width': float,                        # Building width (m)
    'length': float,                       # Building length (m)
    'aspect_ratio': float,                 # Length/width ratio
    'surface_to_volume': float,            # S/V ratio
    'floor_to_floor': float                # Floor-to-floor height
}
```

### 2. Key Relationships
- **Dimensions**: `Width = Area / (Perimeter / 4)`
- **Aspect Ratio**: `Length / Width`
- **Surface/Volume**: `Total_Exterior_Surface / Total_Volume`
- **Core Area**: `Total_Area - Perimeter_Area`
- **Floor Height Logic**: Intelligent adjustment based on building type

## Modification Strategies

### Level 1: Building Form Optimization

#### 1.1 Aspect Ratio Optimization
**Target**: Building length/width ratio

**Climate-Based Strategies**:
```python
# Cold Climate - Minimize surface area
'cold_climate_form': {
    'target_aspect_ratio': 1.0,    # Square plan
    'orientation': 0,              # Long axis E-W
    'reasoning': 'Minimize heat loss'
}

# Hot Climate - Maximize cross ventilation
'hot_climate_form': {
    'target_aspect_ratio': 2.5,    # Rectangular
    'orientation': 90,             # Long axis N-S
    'reasoning': 'Minimize east/west exposure'
}

# Temperate Climate - Balance
'temperate_climate_form': {
    'target_aspect_ratio': 1.5,    # Moderate rectangle
    'orientation': 0,              # Long axis E-W
    'reasoning': 'Optimize south exposure'
}
```

**Implementation**:
```python
def optimize_building_dimensions(area, perimeter, climate):
    # Current aspect ratio
    width = area / (perimeter / 4)
    length = area / width
    current_ratio = length / width
    
    # Target based on climate
    target_ratio = climate_targets[climate]['target_aspect_ratio']
    
    # Adjust dimensions maintaining area
    new_width = sqrt(area / target_ratio)
    new_length = area / new_width
    new_perimeter = 2 * (new_width + new_length)
    
    return new_width, new_length, new_perimeter
```

#### 1.2 Surface-to-Volume Optimization
```python
# Compact forms for energy efficiency
'form_factor_targets': {
    'highly_efficient': 0.3,      # Very compact
    'efficient': 0.4,             # Compact
    'standard': 0.5,              # Typical
    'complex': 0.7                # Articulated form
}

def calculate_sv_ratio(building):
    exterior_area = (2 * width * height + 2 * length * height + 
                    2 * width * length)
    volume = width * length * height
    return exterior_area / volume
```

### Level 2: Zoning Strategy Enhancement

#### 2.1 Perimeter Depth Optimization
**Target Parameter**: `perimeter_depth`

**Daylight-Based Perimeter Depth**:
```python
'daylight_based_perimeter': {
    'single_sided_daylight': 2.5 * floor_height,  # Rule of thumb
    'double_sided_daylight': 5.0 * floor_height,  # Cross-lit
    'minimum_depth': 3.0,                          # Practical minimum
    'maximum_depth': 6.0                           # Practical maximum
}

def calculate_optimal_perimeter_depth(floor_height, window_head_height):
    # Based on 30° daylight angle
    daylight_depth = 2.0 * window_head_height
    return min(max(daylight_depth, 3.0), 6.0)
```

**HVAC-Based Perimeter Depth**:
```python
'hvac_based_perimeter': {
    'vav_system': 4.5,          # Typical VAV zone
    'fan_coil': 3.0,            # Smaller zones
    'radiant': 6.0,             # Larger zones OK
    'natural_vent': 2 * floor_height  # Cross-ventilation
}
```

#### 2.2 Core Zone Strategies
**Target Parameter**: `has_core`

```python
'core_zone_decision': {
    # Minimum building depth for core
    'min_depth_for_core': 15.0,  # meters
    
    # Function-based rules
    'always_core': ['Office', 'Retail', 'Healthcare'],
    'never_core': ['Apartment', 'Detached House'],
    'conditional_core': ['Education', 'Hotel']
}

def should_have_core(building_type, width, length, perimeter_depth):
    min_dimension = min(width, length)
    
    # No core if building too narrow
    if min_dimension < 2 * perimeter_depth + 3.0:
        return False
    
    # Type-based rules
    if building_type in core_zone_decision['always_core']:
        return True
    elif building_type in core_zone_decision['never_core']:
        return False
    else:
        # Conditional based on size
        return min_dimension > 15.0
```

### Level 3: Floor Height Optimization

#### 3.1 Thermal Stratification Management
**Target Parameter**: `floor_height`

```python
'stratification_heights': {
    'low_ceiling': {
        'height': 2.4,
        'advantages': 'Less volume to condition',
        'disadvantages': 'Poor daylight penetration'
    },
    'standard': {
        'height': 3.0,
        'advantages': 'Balanced performance',
        'disadvantages': 'Average'
    },
    'high_ceiling': {
        'height': 3.6,
        'advantages': 'Better daylight, natural ventilation',
        'disadvantages': 'More volume, stratification'
    },
    'double_height': {
        'height': 6.0,
        'advantages': 'Stack effect ventilation',
        'disadvantages': 'Significant stratification'
    }
}

# Stratification factor
def stratification_factor(floor_height):
    if floor_height <= 3.0:
        return 1.0
    else:
        return 1.0 + 0.05 * (floor_height - 3.0)
```

#### 3.2 Function-Based Heights
```python
'function_based_heights': {
    # Residential
    'apartment': 2.6,
    'house': 2.8,
    'luxury': 3.0,
    
    # Commercial
    'office': 3.0,
    'retail': 4.0,
    'warehouse': 6.0,
    
    # Special
    'gym': 6.0,
    'theater': 8.0,
    'atrium': 12.0
}
```

### Level 4: Orientation Strategies

#### 4.1 Solar Optimization
**Target Parameter**: `orientation`

```python
'solar_orientation': {
    'heating_dominated': {
        'orientation': 0,        # Long axis E-W
        'south_glazing': 0.4,    # High WWR
        'north_glazing': 0.15    # Low WWR
    },
    'cooling_dominated': {
        'orientation': 90,       # Long axis N-S
        'south_glazing': 0.25,   # Moderate WWR
        'north_glazing': 0.25    # Balanced
    },
    'balanced': {
        'orientation': -15,      # Slight rotation
        'reasoning': 'Morning sun preference'
    }
}

def optimize_orientation(climate_data, building_use):
    heating_hours = sum(climate_data['heating_hours'])
    cooling_hours = sum(climate_data['cooling_hours'])
    
    if heating_hours > cooling_hours * 1.5:
        return solar_orientation['heating_dominated']
    elif cooling_hours > heating_hours * 1.5:
        return solar_orientation['cooling_dominated']
    else:
        return solar_orientation['balanced']
```

### Level 5: Advanced Geometric Strategies

#### 5.1 Courtyard Buildings
```python
'courtyard_geometry': {
    'min_building_area': 2000,   # m²
    'courtyard_ratio': 0.2,      # Courtyard/total area
    'benefits': [
        'Natural ventilation',
        'Daylighting to interior',
        'Reduced external exposure'
    ]
}

def create_courtyard_zones(width, length, courtyard_size):
    # Create donut-shaped floor plan
    outer_zones = create_perimeter_zones(width, length)
    inner_zones = create_perimeter_zones(
        width - 2*courtyard_size,
        length - 2*courtyard_size,
        reverse=True  # Inside faces courtyard
    )
    return outer_zones + inner_zones
```

#### 5.2 Atrium Integration
```python
'atrium_strategies': {
    'central_atrium': {
        'size_ratio': 0.1,       # 10% of floor area
        'height': 'full_height',
        'benefits': 'Stack ventilation, daylight'
    },
    'linear_atrium': {
        'width': 6.0,
        'length': 'building_length * 0.7',
        'benefits': 'Circulation, ventilation'
    }
}
```

### Level 6: Multi-Building Configurations

#### 6.1 Building Clustering
```python
'cluster_configurations': {
    'compact_cluster': {
        'spacing': 'minimum_fire_separation',
        'shared_walls': True,
        'benefit': 'Reduced exposure'
    },
    'campus_style': {
        'spacing': '2 * building_height',
        'orientation': 'varied',
        'benefit': 'Daylight access'
    },
    'linear_array': {
        'spacing': '1.5 * building_height',
        'orientation': 'consistent',
        'benefit': 'Wind protection'
    }
}
```

## Performance Optimization

### Thermal Performance
```python
'thermal_optimization': {
    'minimize_envelope': {
        'target_sv_ratio': 0.3,
        'compact_form': True,
        'shared_walls': True
    },
    'maximize_solar': {
        'orientation': 0,
        'aspect_ratio': 1.7,
        'south_perimeter_depth': 6.0
    }
}
```

### Daylighting Performance
```python
'daylight_optimization': {
    'shallow_plan': {
        'max_depth': 15.0,
        'perimeter_depth': 5.0,
        'has_core': False
    },
    'courtyard_plan': {
        'max_depth': 30.0,
        'courtyard_size': 10.0,
        'perimeter_depth': 5.0
    }
}
```

### Natural Ventilation
```python
'ventilation_optimization': {
    'cross_ventilation': {
        'max_depth': 15.0,
        'aspect_ratio': 2.5,
        'orientation': 'perpendicular_to_wind'
    },
    'stack_ventilation': {
        'floor_height': 3.6,
        'atrium': True,
        'operable_clerestory': True
    }
}
```

## Implementation Guide

### Quick Modifications
1. **Adjust perimeter depth**: Based on daylight needs
2. **Toggle core zones**: For appropriate building types
3. **Optimize orientation**: Based on climate

### Advanced Modifications
1. **Reshape building**: Modify aspect ratio
2. **Add courtyards/atria**: For large buildings
3. **Vary floor heights**: By function

## Validation Rules

1. **Geometric Constraints**:
   - Min floor height: 2.4m (residential), 2.7m (commercial)
   - Max perimeter depth: 0.5 × min(width, length)
   - Min core size: 3m × 3m

2. **Practical Limits**:
   - Aspect ratio: 0.5 - 4.0
   - S/V ratio: 0.2 - 1.0
   - Floor height: 2.4 - 6.0m (typical)

3. **Zoning Rules**:
   - Core only if building depth > 2 × perimeter_depth + 3m
   - Max 5 zones per floor (4 perimeter + 1 core)

## Future Enhancements

1. **Parametric Forms**: Beyond rectangular
2. **Adaptive Facades**: Orientation-specific properties
3. **Mixed-Use Zoning**: Different strategies by floor
4. **Urban Context**: Shading from adjacent buildings