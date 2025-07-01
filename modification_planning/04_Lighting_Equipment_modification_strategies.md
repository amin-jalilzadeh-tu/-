# Lighting and Equipment Modification Strategies

## Overview
Lighting and plug loads represent 20-50% of commercial building energy use and significant portions in residential buildings. This document outlines modification strategies for both lighting (Elec) and equipment (eequip) systems.

## Parameter Structure

### Lighting Parameters
```yaml
lighting_parameters:
  power_density:
    lights_wm2: 
      residential: 0.0  # Handled separately
      office: [8.0, 12.0]  # W/m²
      retail: [12.0, 24.0]
      warehouse: [4.0, 8.0]
    parasitic_wm2: [0.1, 0.3]  # Ballast/driver losses
  
  distribution:
    fraction_radiant: 0.1
    fraction_visible: 0.1
    fraction_replaceable: 1.0
    fraction_return_air: 0.8  # For plenum returns

equipment_parameters:
  power_density:
    equip_wm2:
      residential: [1.2, 4.0]  # W/m²
      office: [8.0, 15.0]
      retail: [4.0, 8.0]
      healthcare: [10.0, 20.0]
  
  heat_fractions:
    latent: 0.0
    radiant: 0.1
    lost: 0.8  # To unconditioned space
    convective: 0.1  # By difference
```

## Lighting Modification Strategies

### 1. LED Retrofit Strategy
**Goal**: Replace existing lighting with high-efficiency LED

#### Implementation Approach:
```python
class LEDRetrofitStrategy:
    def __init__(self, existing_system):
        self.existing = existing_system
        self.led_efficacy = {
            'standard': 100,  # lm/W
            'high_performance': 150,
            'future': 200
        }
    
    def calculate_retrofit(self):
        """Calculate LED retrofit parameters"""
        # Determine existing technology
        existing_efficacy = self._identify_existing_efficacy()
        
        # Calculate new power density
        illuminance_target = self._get_illuminance_target()
        new_lpd = illuminance_target / self.led_efficacy['high_performance']
        
        modifications = {
            'lights_wm2': {
                'method': 'absolute',
                'value': new_lpd,
                'reduction': 1 - (new_lpd / self.existing['lights_wm2'])
            },
            'parasitic_wm2': {
                'method': 'absolute',
                'value': new_lpd * 0.05,  # 5% for LED drivers
                'reduction': 0.7  # 70% reduction from ballasts
            },
            'spectrum': {
                'CCT_options': [3000, 4000, 5000],  # K
                'CRI': 85,  # Color Rendering Index
                'tunability': 'available'
            }
        }
        return modifications
    
    def _get_illuminance_target(self):
        """Get target illuminance by space type"""
        targets = {
            'office': 500,  # lux
            'retail': 750,
            'warehouse': 200,
            'circulation': 100,
            'detailed_work': 1000
        }
        return targets.get(self.existing['space_type'], 300)
```

#### Advanced LED Features:
```python
advanced_led_features = {
    'color_tuning': {
        'circadian': {
            'morning_CCT': 5000,  # Cool white
            'afternoon_CCT': 4000,  # Neutral
            'evening_CCT': 3000,  # Warm white
            'schedule': 'astronomical_clock'
        },
        'productivity': {
            'focus_mode': 5000,
            'relax_mode': 3000,
            'trigger': 'user_controlled'
        }
    },
    'connected_lighting': {
        'protocol': 'PoE',  # Power over Ethernet
        'features': [
            'individual_control',
            'occupancy_data',
            'energy_monitoring',
            'predictive_maintenance'
        ]
    }
}
```

### 2. Lighting Controls Strategy
**Goal**: Reduce lighting runtime through intelligent controls

#### Control Systems:
```python
lighting_control_strategies = {
    'occupancy_sensing': {
        'sensor_types': ['PIR', 'ultrasonic', 'dual_technology'],
        'coverage': 'per_fixture',  # or per_zone
        'timeout': {
            'private_office': 20,  # minutes
            'open_office': 30,
            'corridor': 10,
            'restroom': 15
        },
        'savings_potential': 0.3  # 30% reduction
    },
    'daylight_harvesting': {
        'sensor_placement': 'perimeter_zones',
        'control_type': 'continuous_dimming',
        'target_illuminance': 500,  # lux
        'deadband': 100,  # lux
        'maximum_output': 0.1,  # 10% minimum
        'savings_potential': 0.4  # 40% in daylit zones
    },
    'scheduling': {
        'base_schedule': 'occupancy_based',
        'override_capability': True,
        'sweep_timer': {
            'after_hours': 2,  # hours
            'warning': 'visual_signal'
        },
        'savings_potential': 0.2  # 20% reduction
    },
    'task_tuning': {
        'method': 'high_end_trim',
        'reduction': 0.15,  # 15% reduction from overlighting
        'user_adjustable': True
    }
}
```

#### Integrated Control Strategy:
```python
class IntegratedLightingControl:
    def __init__(self, zone_characteristics):
        self.zone = zone_characteristics
        
    def optimize_controls(self):
        """Combine multiple control strategies"""
        base_load = self.zone['installed_lpd']
        
        # Apply controls sequentially
        reductions = {
            'occupancy': self._calculate_occupancy_savings(),
            'daylight': self._calculate_daylight_savings(),
            'schedule': self._calculate_schedule_savings(),
            'task_tuning': 0.15
        }
        
        # Calculate combined savings (not purely additive)
        combined_factor = 1.0
        for strategy, reduction in reductions.items():
            combined_factor *= (1 - reduction)
        
        return {
            'effective_lpd': base_load * combined_factor,
            'total_reduction': 1 - combined_factor,
            'control_integration': self._design_control_system(reductions)
        }
```

### 3. Daylighting Integration Strategy
**Goal**: Maximize useful daylight to reduce electric lighting

#### Daylighting Design:
```python
daylighting_modifications = {
    'aperture_optimization': {
        'skylights': {
            'area_ratio': 0.03,  # 3% of roof area
            'spacing': 'uniform_grid',
            'glazing': {'VLT': 0.7, 'SHGC': 0.3}
        },
        'clerestory': {
            'height': 0.5,  # m
            'orientation': 'north_preferred',
            'light_shelf': True
        },
        'light_tubes': {
            'diameter': 0.35,  # m
            'locations': 'interior_zones',
            'efficiency': 0.5
        }
    },
    'surface_optimization': {
        'ceiling_reflectance': 0.9,
        'wall_reflectance': 0.7,
        'floor_reflectance': 0.3,
        'furniture_reflectance': 0.5
    },
    'control_integration': {
        'photo_sensors': {
            'type': 'closed_loop',
            'calibration': 'annual',
            'zones': 'perimeter_15ft'
        }
    }
}
```

## Equipment Modification Strategies

### 1. Efficient Equipment Strategy
**Goal**: Replace equipment with high-efficiency alternatives

#### Equipment Efficiency Improvements:
```python
class EquipmentEfficiencyStrategy:
    def __init__(self, equipment_inventory):
        self.inventory = equipment_inventory
        self.efficiency_standards = {
            'computers': {
                'desktop_to_laptop': 0.5,  # 50% reduction
                'energy_star': 0.7,  # 30% reduction
                'thin_client': 0.3  # 70% reduction
            },
            'displays': {
                'LED_monitor': 0.6,  # vs CRT/LCD
                'auto_brightness': 0.8,
                'aggressive_sleep': 0.7
            },
            'imaging': {
                'multifunction': 0.7,  # vs separate devices
                'default_duplex': 0.9,
                'pull_printing': 0.8
            },
            'kitchen': {
                'energy_star_refrigerator': 0.8,
                'induction_cooking': 0.7,
                'heat_pump_water_heater': 0.4
            }
        }
    
    def calculate_replacement_impact(self):
        """Calculate impact of equipment replacement"""
        total_reduction = 0
        
        for category, equipment_list in self.inventory.items():
            if category in self.efficiency_standards:
                category_reduction = self._calculate_category_reduction(
                    category, equipment_list
                )
                total_reduction += category_reduction
        
        return {
            'new_equip_wm2': self.inventory['total_wm2'] * (1 - total_reduction),
            'reduction_percentage': total_reduction * 100,
            'priority_replacements': self._identify_priorities()
        }
```

### 2. Plug Load Management Strategy
**Goal**: Reduce parasitic and standby loads

#### Smart Power Management:
```python
plug_load_management = {
    'smart_power_strips': {
        'types': {
            'timer_based': {
                'schedule': 'occupancy_hours',
                'savings': 0.1  # 10%
            },
            'load_sensing': {
                'master_threshold': 10,  # W
                'controlled_outlets': 0.7,  # 70% of outlets
                'savings': 0.15  # 15%
            },
            'occupancy_controlled': {
                'sensor': 'integrated',
                'timeout': 30,  # minutes
                'savings': 0.25  # 25%
            }
        },
        'deployment': {
            'workstations': 'load_sensing',
            'break_rooms': 'timer_based',
            'conference_rooms': 'occupancy_controlled'
        }
    },
    'centralized_control': {
        'system': 'building_automation',
        'features': [
            'scheduled_shutdowns',
            'demand_response',
            'real_time_monitoring',
            'user_override'
        ],
        'savings_potential': 0.3  # 30%
    }
}
```

### 3. Behavioral Modification Strategy
**Goal**: Influence occupant behavior to reduce equipment energy

#### Engagement Programs:
```python
behavioral_programs = {
    'awareness_campaigns': {
        'energy_dashboards': {
            'display_location': 'lobby',
            'metrics': ['real_time_use', 'daily_trends', 'comparisons'],
            'impact': 0.05  # 5% reduction
        },
        'competitions': {
            'type': 'department_vs_department',
            'duration': 'monthly',
            'rewards': 'recognition',
            'impact': 0.1  # 10% during competition
        }
    },
    'policy_changes': {
        'IT_policies': {
            'sleep_settings': 'enforced',
            'evening_shutdown': 'automated',
            'print_quotas': 'implemented'
        },
        'procurement': {
            'energy_star_required': True,
            'lifecycle_cost_analysis': True,
            'right_sizing': True
        }
    },
    'enabling_infrastructure': {
        'personal_comfort': {
            'desk_fans': 'provided',
            'task_lighting': 'available',
            'impact': 'reduces_HVAC_complaints'
        }
    }
}
```

## Combined Lighting and Equipment Strategies

### 1. Integrated Load Reduction
```python
class IntegratedLoadReduction:
    def __init__(self, building_data):
        self.building = building_data
        
    def develop_integrated_strategy(self):
        """Develop coordinated lighting and equipment strategy"""
        
        # Assess interaction effects
        interactions = {
            'reduced_lighting_heat': {
                'cooling_reduction': 0.3,  # kW cooling per kW lighting
                'heating_increase': 0.2   # May need more heating
            },
            'reduced_equipment_heat': {
                'cooling_reduction': 0.25,
                'ventilation_adjustment': 0.9  # Can reduce
            }
        }
        
        # Prioritize by cost-effectiveness
        measures = self._rank_measures_by_roi()
        
        # Package complementary measures
        packages = {
            'quick_wins': {
                'measures': ['LED_lamps', 'smart_strips', 'occupancy_sensors'],
                'cost': 'low',
                'savings': '20-30%',
                'payback': '<2 years'
            },
            'deep_retrofit': {
                'measures': ['LED_system', 'controls_integration', 'equipment_replacement'],
                'cost': 'high',
                'savings': '50-70%',
                'payback': '5-7 years'
            }
        }
        
        return packages
```

### 2. Peak Demand Management
```python
peak_demand_strategies = {
    'load_scheduling': {
        'pre_cooling': {
            'hours': [4, 7],  # AM
            'lighting_level': 0.3,  # 30% during pre-cool
            'equipment': 'essential_only'
        },
        'peak_period': {
            'hours': [14, 18],  # PM
            'lighting_reduction': 0.2,  # 20%
            'equipment_cycling': True,
            'non_critical_off': True
        }
    },
    'demand_response': {
        'triggers': ['price_signal', 'grid_request', 'demand_threshold'],
        'levels': {
            'moderate': {
                'lighting_dim': 0.15,
                'equipment_defer': ['dishwashers', 'non_essential']
            },
            'aggressive': {
                'lighting_dim': 0.3,
                'equipment_shutdown': ['non_critical'],
                'pre_event_prep': True
            }
        }
    }
}
```

## Space-Specific Strategies

### 1. Office Spaces
```python
office_specific_strategies = {
    'private_office': {
        'lighting': {
            'base_lpd': 8.0,  # W/m²
            'controls': ['occupancy', 'daylight', 'personal'],
            'target_lpd': 3.0
        },
        'equipment': {
            'base_epd': 10.0,  # W/m²
            'measures': ['laptop_policy', 'smart_strips', 'cloud_computing'],
            'target_epd': 5.0
        }
    },
    'open_office': {
        'lighting': {
            'base_lpd': 10.0,
            'controls': ['occupancy_zones', 'daylight_rows', 'task_ambient'],
            'target_lpd': 4.0
        },
        'equipment': {
            'base_epd': 12.0,
            'measures': ['shared_resources', 'efficient_workstations'],
            'target_epd': 6.0
        }
    }
}
```

### 2. Retail Spaces
```python
retail_specific_strategies = {
    'sales_floor': {
        'lighting': {
            'display_lighting': {
                'accent_ratio': 3.0,  # 3:1 to ambient
                'LED_track': True,
                'controls': 'scheduled_scenes'
            },
            'general_lighting': {
                'uniformity': 0.7,
                'adaptation': 'daylight_responsive'
            }
        },
        'equipment': {
            'POS_systems': 'energy_star',
            'display_screens': 'LED_with_sensors',
            'music_systems': 'zoned_control'
        }
    }
}
```

## Implementation Roadmap

### 1. Assessment Phase
```python
assessment_protocol = {
    'lighting_audit': {
        'inventory': ['fixture_types', 'lamp_types', 'control_systems'],
        'measurements': ['illuminance_levels', 'power_draw', 'operating_hours'],
        'analysis': ['over_lit_areas', 'control_opportunities', 'age_assessment']
    },
    'equipment_audit': {
        'inventory': ['device_types', 'age', 'energy_labels'],
        'measurements': ['plug_load_monitoring', 'usage_patterns'],
        'analysis': ['base_vs_peak', 'parasitic_loads', 'replacement_candidates']
    }
}
```

### 2. Design Phase
```python
design_considerations = {
    'lighting_design': {
        'standards_compliance': {
            'IES_recommendations': True,
            'local_codes': True,
            'accessibility': True
        },
        'quality_metrics': {
            'color_rendering': 'CRI > 80',
            'flicker': '<5%',
            'glare': 'UGR < 19'
        }
    },
    'controls_integration': {
        'system_architecture': 'distributed',
        'communication': 'wireless_mesh',
        'user_interface': 'intuitive'
    }
}
```

## Monitoring and Verification

### 1. Performance Tracking
```python
monitoring_framework = {
    'metrics': {
        'energy': {
            'lighting_kWh': 'by_circuit',
            'equipment_kWh': 'by_panel',
            'peak_demand': 'interval_data'
        },
        'operation': {
            'runtime_hours': 'by_zone',
            'override_frequency': 'by_control',
            'failure_alerts': 'real_time'
        },
        'quality': {
            'light_levels': 'spot_checks',
            'user_satisfaction': 'surveys',
            'maintenance_needs': 'tracked'
        }
    },
    'reporting': {
        'frequency': 'monthly',
        'format': 'dashboard',
        'stakeholders': ['facility', 'finance', 'occupants']
    }
}
```

### 2. Continuous Optimization
```python
optimization_cycle = {
    'data_analysis': {
        'pattern_recognition': 'ML_algorithms',
        'anomaly_detection': 'statistical_methods',
        'prediction': 'usage_forecasting'
    },
    'adjustments': {
        'control_tuning': 'quarterly',
        'schedule_updates': 'seasonal',
        'setpoint_optimization': 'continuous'
    },
    'upgrades': {
        'technology_tracking': 'annual_review',
        'roi_recalculation': 'with_utility_changes',
        'pilot_testing': 'new_technologies'
    }
}
```

## Cost-Benefit Summary

### Typical Project Economics
| Measure | Cost/m² | Energy Savings | Simple Payback |
|---------|---------|----------------|----------------|
| LED Retrofit (lamps only) | €10-20 | 40-60% | 1-2 years |
| LED + Basic Controls | €30-50 | 60-75% | 2-3 years |
| Integrated Controls | €50-100 | 70-85% | 3-5 years |
| Equipment Upgrades | €20-40 | 20-30% | 3-5 years |
| Plug Load Management | €10-20 | 15-25% | 2-3 years |

### Utility Incentives
```python
incentive_opportunities = {
    'lighting': {
        'prescriptive': '€X per fixture',
        'custom': '€X per kWh saved',
        'controls_bonus': '25% adder'
    },
    'equipment': {
        'early_retirement': 'available',
        'energy_star': 'instant_rebates',
        'custom_measures': 'engineering_support'
    }
}
```