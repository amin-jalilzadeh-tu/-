# HVAC System Modifications

## Overview

The HVAC modifier handles modifications to heating, ventilation, and air conditioning systems in EnergyPlus models. It supports various HVAC object types and implements strategies for improving energy efficiency and comfort.

## Supported HVAC Objects

### 1. Ideal Loads Air System
```
ZONEHVAC:IDEALLOADSAIRSYSTEM
├── Heating/Cooling Availability
├── Supply Air Temperature
├── Supply Air Humidity
├── Heating/Cooling Limits
├── Outdoor Air Requirements
└── Heat Recovery
```

### 2. Thermostats
```
THERMOSTATSETPOINT:DUALSETPOINT
├── Heating Setpoint Schedule
├── Cooling Setpoint Schedule
└── Zone Control Type
```

### 3. Cooling Equipment
```
COIL:COOLING:DX:SINGLESPEED
├── Rated Total Cooling Capacity
├── Rated COP
├── Rated Air Flow Rate
└── Performance Curves

COIL:COOLING:DX:TWOSPEED
├── High/Low Speed Capacity
├── High/Low Speed COP
└── Speed Control
```

### 4. Heating Equipment
```
COIL:HEATING:GAS
├── Nominal Capacity
├── Efficiency
└── Parasitic Loads

COIL:HEATING:ELECTRIC
├── Nominal Capacity
└── Efficiency (always 1.0)
```

### 5. Fans
```
FAN:CONSTANTVOLUME
├── Maximum Flow Rate
├── Pressure Rise
├── Total Efficiency
└── Motor Efficiency

FAN:VARIABLEVOLUME
├── Maximum Flow Rate
├── Fan Power Coefficients
└── Minimum Flow Fraction
```

## HVAC Modification Strategies

### 1. High Efficiency Strategy

Improves equipment efficiency across all HVAC components.

```python
HIGH_EFFICIENCY_PARAMETERS = {
    "cooling_cop": {
        "current_value": "parse",
        "modification": "multiplier",
        "factor": 1.3,
        "minimum": 4.0,
        "maximum": 6.0
    },
    "heating_efficiency": {
        "current_value": "parse",
        "modification": "multiplier",
        "factor": 1.15,
        "minimum": 0.90,
        "maximum": 0.98
    },
    "fan_total_efficiency": {
        "current_value": "parse",
        "modification": "absolute",
        "value": 0.7,
        "minimum": 0.6,
        "maximum": 0.9
    }
}
```

**Implementation Example:**
```python
def apply_high_efficiency(self, obj, params):
    if obj['object_type'] == 'COIL:COOLING:DX:SINGLESPEED':
        current_cop = float(obj['fields'][13])  # Gross Rated COP
        new_cop = min(6.0, max(4.0, current_cop * 1.3))
        obj['fields'][13] = str(new_cop)
        
    elif obj['object_type'] == 'COIL:HEATING:GAS':
        current_eff = float(obj['fields'][2])  # Burner Efficiency
        new_eff = min(0.98, max(0.90, current_eff * 1.15))
        obj['fields'][2] = str(new_eff)
```

### 2. Setpoint Optimization Strategy

Adjusts temperature setpoints to reduce energy while maintaining comfort.

```python
SETPOINT_OPTIMIZATION = {
    "cooling_setpoint": {
        "adjustment": "+2°C",
        "summer_range": [24, 27],
        "comfort_limit": 26
    },
    "heating_setpoint": {
        "adjustment": "-2°C", 
        "winter_range": [19, 21],
        "comfort_limit": 20
    },
    "deadband": {
        "minimum": 3,
        "recommended": 4
    }
}
```

**Setpoint Schedule Modification:**
```python
def modify_setpoint_schedule(self, schedule_name, offset):
    schedule = self.get_schedule(schedule_name)
    for time_value in schedule['values']:
        original = float(time_value['value'])
        new_value = original + offset
        # Apply comfort constraints
        if offset > 0:  # Cooling
            new_value = min(new_value, 27)
        else:  # Heating  
            new_value = max(new_value, 19)
        time_value['value'] = str(new_value)
```

### 3. Variable Speed Strategy

Converts constant speed equipment to variable speed for better part-load efficiency.

```python
VARIABLE_SPEED_CONVERSION = {
    "fan_type_change": {
        "from": "FAN:CONSTANTVOLUME",
        "to": "FAN:VARIABLEVOLUME"
    },
    "fan_parameters": {
        "fan_power_coefficient_1": 0.0013,
        "fan_power_coefficient_2": 0.147,
        "fan_power_coefficient_3": 0.9506,
        "fan_power_coefficient_4": -0.0998,
        "fan_power_coefficient_5": 0,
        "minimum_flow_fraction": 0.3
    },
    "pump_parameters": {
        "pump_control_type": "Intermittent",
        "minimum_flow_rate_fraction": 0.2
    }
}
```

### 4. Heat Recovery Strategy

Adds or improves heat recovery systems.

```python
HEAT_RECOVERY_PARAMETERS = {
    "heat_exchanger_type": "Plate",
    "sensible_effectiveness": {
        "heating_100": 0.75,
        "heating_75": 0.78,
        "cooling_100": 0.70,
        "cooling_75": 0.73
    },
    "latent_effectiveness": {
        "heating_100": 0.65,
        "heating_75": 0.68,
        "cooling_100": 0.60,
        "cooling_75": 0.63
    },
    "economizer_control": "DifferentialEnthalpy"
}
```

### 5. Capacity Optimization Strategy

Right-sizes equipment based on actual loads.

```python
CAPACITY_OPTIMIZATION = {
    "sizing_factor": {
        "cooling": 1.15,  # 15% oversizing
        "heating": 1.25   # 25% oversizing
    },
    "minimum_unmet_hours": 50,
    "maximum_unmet_hours": 300,
    "load_calculation_method": "DesignDay"
}
```

## HVAC-Specific Validation Rules

### 1. Capacity-Flow Relationships
```python
def validate_capacity_flow(self, capacity_w, flow_m3s):
    """Ensure proper capacity to flow rate ratio"""
    # Typical range: 350-450 cfm per ton
    # 1 ton = 3517 W, 1 cfm = 0.000472 m³/s
    tons = capacity_w / 3517
    cfm = flow_m3s / 0.000472
    cfm_per_ton = cfm / tons
    return 350 <= cfm_per_ton <= 450
```

### 2. Temperature Limits
```python
TEMPERATURE_CONSTRAINTS = {
    "supply_air_cooling": {
        "minimum": 12,  # °C
        "maximum": 18   # °C
    },
    "supply_air_heating": {
        "minimum": 30,  # °C
        "maximum": 50   # °C
    },
    "setpoint_range": {
        "cooling": [23, 28],  # °C
        "heating": [18, 23]   # °C
    }
}
```

### 3. Efficiency Constraints
```python
EFFICIENCY_LIMITS = {
    "cooling_cop": {
        "minimum": 2.0,
        "maximum": 6.0,
        "realistic_range": [3.0, 5.0]
    },
    "heating_gas": {
        "minimum": 0.70,
        "maximum": 0.98,
        "condensing_minimum": 0.90
    },
    "fan_total": {
        "minimum": 0.30,
        "maximum": 0.90,
        "typical": 0.60
    }
}
```

## Complex HVAC Modifications

### 1. System Type Conversion
```python
def convert_system_type(self, from_type, to_type):
    """Convert between HVAC system types"""
    conversions = {
        ("IDEALLOADS", "DX_COOLING"): self.idealloads_to_dx,
        ("CONSTANT_VOLUME", "VAV"): self.cv_to_vav,
        ("SINGLE_ZONE", "MULTI_ZONE"): self.single_to_multi
    }
    conversion_func = conversions.get((from_type, to_type))
    if conversion_func:
        return conversion_func()
```

### 2. Control Strategy Implementation
```python
def implement_control_strategy(self, strategy_type):
    """Add advanced control strategies"""
    if strategy_type == "demand_controlled_ventilation":
        self.add_dcv_controls()
    elif strategy_type == "optimal_start":
        self.add_optimal_start()
    elif strategy_type == "night_setback":
        self.modify_schedule_for_setback()
```

### 3. Performance Curve Adjustments
```python
def adjust_performance_curves(self, equipment_type, improvement_factor):
    """Modify equipment performance curves"""
    curve_objects = self.get_curve_objects(equipment_type)
    for curve in curve_objects:
        if curve['curve_type'] == 'Quadratic':
            # Adjust coefficients to reflect improvement
            c0, c1, c2 = curve['coefficients']
            curve['coefficients'] = [
                c0 * improvement_factor,
                c1,
                c2 / improvement_factor
            ]
```

## HVAC Modification Examples

### Example 1: Comprehensive HVAC Upgrade
```json
{
  "hvac": {
    "enabled": true,
    "strategy": "comprehensive_upgrade",
    "parameters": {
      "upgrade_cooling": {
        "cop_improvement": 1.3,
        "add_economizer": true
      },
      "upgrade_heating": {
        "efficiency_target": 0.95,
        "add_heat_recovery": true
      },
      "upgrade_fans": {
        "convert_to_variable": true,
        "efficiency_target": 0.75
      },
      "optimize_controls": {
        "widen_deadband": 3,
        "add_dcv": true,
        "optimal_start": true
      }
    }
  }
}
```

### Example 2: Climate-Specific Modifications
```python
def apply_climate_specific_mods(self, climate_zone):
    if climate_zone in ['1A', '2A', '2B']:  # Hot climates
        modifications = {
            "increase_cooling_cop": 1.4,
            "raise_cooling_setpoint": 2,
            "add_economizer": False
        }
    elif climate_zone in ['6A', '6B', '7', '8']:  # Cold climates
        modifications = {
            "increase_heating_efficiency": 1.2,
            "lower_heating_setpoint": 1,
            "add_heat_recovery": True
        }
    return modifications
```

## Performance Metrics

Track HVAC modification impacts:

```python
HVAC_METRICS = {
    "energy": [
        "cooling_electricity",
        "heating_gas",
        "fan_electricity",
        "pump_electricity"
    ],
    "comfort": [
        "unmet_cooling_hours",
        "unmet_heating_hours",
        "mean_air_temperature"
    ],
    "equipment": [
        "cooling_cop_average",
        "heating_efficiency_average",
        "fan_power_per_flow"
    ]
}
```

## Best Practices

1. **Maintain System Balance**: Ensure capacity, flow rates, and controls are coordinated
2. **Consider Climate**: Apply climate-appropriate strategies
3. **Validate Comfort**: Check that modifications don't compromise comfort
4. **Check Dependencies**: Verify related systems are compatible
5. **Document Changes**: Track all modifications for analysis