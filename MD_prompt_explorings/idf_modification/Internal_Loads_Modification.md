# Internal Loads Modifications

## Overview

The internal loads modifiers handle modifications to lighting, equipment, and occupancy-related heat gains in buildings. These modifications significantly impact cooling loads and overall energy consumption.

## Supported Internal Load Objects

### 1. Lighting
```
LIGHTS
├── Design Level Calculation Method
├── Lighting Level (W, W/m², W/person)
├── Schedule Name
├── Fraction Radiant
├── Fraction Visible
├── Fraction Return Air
└── End-Use Subcategory

DAYLIGHTING:CONTROLS
├── Control Type
├── Setpoint
├── Minimum Input Power Fraction
└── Number of Steps
```

### 2. Electric Equipment
```
ELECTRICEQUIPMENT
├── Design Level Calculation Method
├── Equipment Level (W, W/m², W/person)
├── Schedule Name
├── Fraction Radiant
├── Fraction Latent
├── Fraction Lost
└── End-Use Subcategory

ELECTRICEQUIPMENT:ITE:AIRCOOLED
├── Server Power
├── CPU Loading Schedule
├── Supply Air Method
└── Environmental Class
```

### 3. People/Occupancy
```
PEOPLE
├── Number of People Calculation Method
├── Number of People/People per Area/Area per Person
├── Activity Level Schedule
├── Fraction Radiant
├── Sensible Heat Fraction
└── Carbon Dioxide Generation Rate
```

### 4. Other Internal Gains
```
OTHERVEQUIPMENT
├── Fuel Type
├── Design Level
└── Heat Gain Fractions

ZONEBASEBOARD:OUTDOORTEMPERATURECONTROLLED
├── Capacity at Low Temperature
├── Low/High Temperature
└── Fraction Radiant
```

## Lighting Modification Strategies

### 1. LED Retrofit Strategy

Converts existing lighting to LED technology.

```python
LED_RETROFIT_PARAMETERS = {
    "power_reduction": {
        "incandescent_to_led": 0.15,  # 85% reduction
        "fluorescent_to_led": 0.50,    # 50% reduction
        "hid_to_led": 0.40             # 60% reduction
    },
    "efficacy": {
        "led": 150,         # lm/W
        "fluorescent": 85,
        "incandescent": 15,
        "hid": 100
    },
    "heat_fractions": {
        "led": {
            "radiant": 0.30,
            "visible": 0.20,
            "convective": 0.50
        }
    },
    "lifetime_hours": 50000
}
```

**Implementation Example:**
```python
def apply_led_retrofit(self, lights_obj):
    # Determine current technology
    current_lpd = float(lights_obj['watts_per_zone_floor_area'])
    
    # Apply reduction based on building type
    building_type = self.get_building_type()
    reduction_factor = self.LED_REDUCTION_FACTORS[building_type]
    
    new_lpd = current_lpd * reduction_factor
    lights_obj['watts_per_zone_floor_area'] = str(new_lpd)
    
    # Update heat fractions for LED
    lights_obj['fraction_radiant'] = "0.30"
    lights_obj['fraction_visible'] = "0.20"
    lights_obj['return_air_fraction'] = "0.0"
```

### 2. Daylighting Control Strategy

Implements daylight harvesting controls.

```python
DAYLIGHTING_PARAMETERS = {
    "control_types": {
        "continuous": {
            "minimum_power_fraction": 0.3,
            "minimum_light_fraction": 0.2
        },
        "stepped": {
            "number_of_steps": 3,
            "step_levels": [1.0, 0.66, 0.33, 0.0]
        },
        "continuous_off": {
            "minimum_power_fraction": 0.0,
            "minimum_light_fraction": 0.0
        }
    },
    "setpoints": {
        "office": 500,      # lux
        "classroom": 500,
        "retail": 750,
        "warehouse": 200
    },
    "zones": {
        "perimeter_depth": 4.5,  # m
        "skylight_coverage": 0.03  # 3% of roof
    }
}
```

**Daylighting Zone Creation:**
```python
def create_daylighting_zones(self, zone_obj):
    """Create daylighting control points"""
    
    # Calculate perimeter area
    perimeter_area = self.calculate_perimeter_area(zone_obj)
    total_area = zone_obj['floor_area']
    
    if perimeter_area / total_area > 0.3:
        # Add daylighting controls
        control_point = {
            "x": zone_obj['centroid_x'],
            "y": zone_obj['centroid_y'] - 2.0,  # 2m from window
            "z": 0.8,  # Work plane height
            "illuminance_setpoint": 500,
            "control_type": "Continuous",
            "minimum_power_fraction": 0.3
        }
        self.add_daylighting_control(zone_obj, control_point)
```

### 3. Occupancy Sensor Strategy

Adds occupancy-based lighting controls.

```python
OCCUPANCY_SENSOR_PARAMETERS = {
    "sensor_types": {
        "pir": {
            "coverage": 0.85,
            "false_on_rate": 0.05,
            "delay_minutes": 15
        },
        "ultrasonic": {
            "coverage": 0.95,
            "false_on_rate": 0.10,
            "delay_minutes": 10
        },
        "dual_technology": {
            "coverage": 0.98,
            "false_on_rate": 0.02,
            "delay_minutes": 20
        }
    },
    "space_types": {
        "private_office": {
            "reduction": 0.30,
            "sensor": "pir"
        },
        "open_office": {
            "reduction": 0.15,
            "sensor": "dual_technology"
        },
        "conference": {
            "reduction": 0.45,
            "sensor": "dual_technology"
        },
        "restroom": {
            "reduction": 0.50,
            "sensor": "ultrasonic"
        }
    }
}
```

### 4. Task Tuning Strategy

Optimizes lighting levels for actual needs.

```python
TASK_TUNING_LEVELS = {
    "circulation": {
        "target_lpd": 3.0,  # W/m²
        "illuminance": 150  # lux
    },
    "office_work": {
        "target_lpd": 8.0,
        "illuminance": 500
    },
    "detailed_work": {
        "target_lpd": 12.0,
        "illuminance": 750
    },
    "storage": {
        "target_lpd": 2.0,
        "illuminance": 100
    }
}
```

## Equipment Modification Strategies

### 1. Energy Star Equipment Strategy

Upgrades to Energy Star rated equipment.

```python
ENERGY_STAR_EQUIPMENT = {
    "computers": {
        "desktop_to_laptop": 0.3,  # 70% reduction
        "standard_to_energy_star": 0.7
    },
    "monitors": {
        "crt_to_lcd": 0.3,
        "lcd_to_led": 0.7,
        "sleep_mode_factor": 0.5
    },
    "office_equipment": {
        "printers": {
            "old_to_energy_star": 0.5,
            "centralization_factor": 0.7
        },
        "copiers": {
            "old_to_energy_star": 0.6,
            "sleep_mode_usage": 0.8
        }
    },
    "kitchen_equipment": {
        "refrigerators": 0.7,
        "dishwashers": 0.8,
        "cooking": 0.85
    }
}
```

### 2. Plug Load Management Strategy

Implements advanced plug load controls.

```python
PLUG_LOAD_MANAGEMENT = {
    "control_types": {
        "timer_based": {
            "reduction": 0.15,
            "schedule": "occupancy_based"
        },
        "occupancy_controlled": {
            "reduction": 0.25,
            "delay": 30  # minutes
        },
        "load_sensing": {
            "reduction": 0.30,
            "threshold": 5  # watts
        },
        "advanced_power_strips": {
            "reduction": 0.35,
            "master_controlled": True
        }
    },
    "receptacle_control": {
        "controlled_percentage": 0.5,
        "always_on_loads": ["servers", "refrigerators", "emergency"]
    }
}
```

### 3. IT Equipment Optimization

Optimizes data center and IT equipment loads.

```python
IT_OPTIMIZATION = {
    "server_virtualization": {
        "consolidation_ratio": 10,  # 10:1
        "power_reduction": 0.8
    },
    "cooling_optimization": {
        "hot_aisle_containment": 0.8,
        "raised_floor_optimization": 0.9,
        "free_cooling_hours": 0.3
    },
    "ups_efficiency": {
        "old_ups": 0.85,
        "new_ups": 0.95,
        "eco_mode": 0.98
    },
    "environmental_classes": {
        "class_1": {"temp_range": [15, 32]},
        "class_2": {"temp_range": [10, 35]},
        "class_3": {"temp_range": [5, 40]}
    }
}
```

## Occupancy Modification Strategies

### 1. Occupancy Schedule Optimization

Adjusts occupancy schedules based on actual usage.

```python
OCCUPANCY_OPTIMIZATION = {
    "schedule_types": {
        "traditional": {
            "start": 8,
            "end": 18,
            "peak_factor": 0.95
        },
        "flexible": {
            "core_hours": [10, 15],
            "peak_factor": 0.7,
            "diversity": 1.2
        },
        "hoteling": {
            "average_occupancy": 0.6,
            "peak_factor": 0.8
        }
    },
    "density_adjustments": {
        "covid_spacing": 1.5,  # multiplier on area/person
        "open_plan": 0.8,
        "private_office": 1.2
    }
}
```

### 2. Activity Level Adjustments

Modifies metabolic rates based on actual activities.

```python
ACTIVITY_LEVELS = {
    "seated_quiet": {
        "metabolic_rate": 60,  # W/person
        "co2_generation": 0.0000000382  # m³/s
    },
    "seated_light_work": {
        "metabolic_rate": 70,
        "co2_generation": 0.0000000444
    },
    "standing_light_work": {
        "metabolic_rate": 95,
        "co2_generation": 0.0000000600
    },
    "walking": {
        "metabolic_rate": 115,
        "co2_generation": 0.0000000730
    }
}
```

## Complex Load Interactions

### 1. Load Scheduling Coordination
```python
def coordinate_load_schedules(self, zone_loads):
    """Coordinate schedules between different load types"""
    
    # Get base occupancy schedule
    occupancy_schedule = zone_loads['people']['schedule']
    
    # Align lighting with occupancy
    lighting_schedule = self.create_dependent_schedule(
        base=occupancy_schedule,
        lead_time=-0.25,  # 15 min early
        lag_time=0.5,     # 30 min late
        minimum=0.1       # 10% minimum
    )
    
    # Align equipment with occupancy
    equipment_schedule = self.create_dependent_schedule(
        base=occupancy_schedule,
        lead_time=0,
        lag_time=1.0,     # 1 hour late
        minimum=0.3       # 30% minimum for always-on
    )
    
    return {
        'lighting': lighting_schedule,
        'equipment': equipment_schedule
    }
```

### 2. Heat Gain Redistribution
```python
def redistribute_heat_gains(self, load_object, hvac_type):
    """Adjust heat gain fractions based on HVAC type"""
    
    if hvac_type == 'underfloor':
        # More heat stays in occupied zone
        fractions = {
            'radiant': 0.4,
            'convective': 0.6,
            'return_air': 0.0
        }
    elif hvac_type == 'displacement':
        # Heat rises to return
        fractions = {
            'radiant': 0.3,
            'convective': 0.5,
            'return_air': 0.2
        }
    else:  # overhead
        fractions = {
            'radiant': 0.35,
            'convective': 0.45,
            'return_air': 0.2
        }
    
    load_object.update(fractions)
```

## Validation Rules

### 1. Load Density Limits
```python
LOAD_DENSITY_LIMITS = {
    "lighting": {
        "minimum": 1.0,   # W/m²
        "maximum": 50.0,  # W/m²
        "code_maximum": {
            "office": 9.0,
            "retail": 13.0,
            "warehouse": 6.0
        }
    },
    "equipment": {
        "minimum": 0.0,
        "maximum": 1000.0,  # W/m² (data center)
        "typical": {
            "office": 10.0,
            "residential": 5.0,
            "laboratory": 20.0
        }
    },
    "occupancy": {
        "minimum": 0.001,  # people/m²
        "maximum": 1.0,    # people/m²
        "typical": {
            "office": 0.05,
            "assembly": 0.7,
            "residential": 0.02
        }
    }
}
```

### 2. Heat Fraction Validation
```python
def validate_heat_fractions(self, load_object):
    """Ensure heat fractions are valid"""
    
    fractions = {
        'radiant': float(load_object.get('fraction_radiant', 0)),
        'visible': float(load_object.get('fraction_visible', 0)),
        'return_air': float(load_object.get('return_air_fraction', 0)),
        'latent': float(load_object.get('fraction_latent', 0))
    }
    
    # Check individual ranges
    for name, value in fractions.items():
        if not 0 <= value <= 1:
            return False, f"{name} fraction out of range"
    
    # Check lighting constraint
    if load_object['type'] == 'LIGHTS':
        total = fractions['radiant'] + fractions['visible'] + fractions['return_air']
        if total > 1.0:
            return False, "Lighting fractions sum > 1.0"
    
    return True, "Valid"
```

## Performance Metrics

```python
INTERNAL_LOAD_METRICS = {
    "energy_use": [
        "lighting_electricity",
        "equipment_electricity",
        "peak_lighting_demand",
        "peak_equipment_demand"
    ],
    "load_factors": [
        "lighting_load_factor",
        "equipment_diversity_factor",
        "occupancy_utilization"
    ],
    "controls_effectiveness": [
        "daylighting_savings",
        "occupancy_sensor_savings",
        "plug_load_reduction"
    ],
    "heat_gain": [
        "total_internal_gain",
        "sensible_gain",
        "latent_gain"
    ]
}
```

## Best Practices

1. **Realistic Schedules**: Use measured data when available
2. **Control Integration**: Layer multiple control strategies
3. **Diversity Factors**: Account for non-coincident peaks
4. **Future Proofing**: Plan for changing space uses
5. **Measurement**: Include submetering for verification