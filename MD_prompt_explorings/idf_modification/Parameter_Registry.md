# IDF Modification Parameter Registry

## Overview

The Parameter Registry defines all modifiable parameters in the IDF modification system. Each parameter is carefully defined with its constraints, validation rules, and performance impacts.

## Parameter Definition Structure

Each parameter is defined using the following structure:

```python
ParameterDefinition(
    category='hvac',
    object_type='COIL:COOLING:DX:SINGLESPEED',
    field_name='Gross Rated Total Cooling Capacity',
    field_index=4,
    data_type=float,
    units='W',
    min_value=1000,
    max_value=1000000,
    default_value=None,  # Use existing value
    performance_impact=['cooling_energy', 'peak_cooling'],
    dependencies=['fan_flow_rate', 'zone_area'],
    validation_rules=['capacity_per_area_check'],
    modification_methods=['absolute', 'multiplier', 'percentage']
)
```

## Parameter Categories

### 1. HVAC Parameters

#### Cooling Systems
```python
COOLING_PARAMETERS = {
    "cooling_capacity": {
        "object_type": "COIL:COOLING:DX:SINGLESPEED",
        "field_name": "Gross Rated Total Cooling Capacity",
        "units": "W",
        "range": [1000, 1000000],
        "typical_values": {
            "residential": [3500, 17500],  # 1-5 tons
            "commercial": [17500, 350000]   # 5-100 tons
        }
    },
    
    "cooling_cop": {
        "object_type": "COIL:COOLING:DX:SINGLESPEED",
        "field_name": "Gross Rated COP",
        "units": "W/W",
        "range": [2.0, 6.0],
        "code_minimum": 3.0,
        "high_efficiency": 4.5
    },
    
    "cooling_setpoint": {
        "object_type": "THERMOSTATSETPOINT:DUALSETPOINT",
        "field_name": "Cooling Setpoint Temperature",
        "units": "°C",
        "range": [20, 30],
        "default": 24,
        "comfort_range": [23, 26]
    }
}
```

#### Heating Systems
```python
HEATING_PARAMETERS = {
    "heating_capacity": {
        "object_type": "COIL:HEATING:GAS",
        "field_name": "Nominal Capacity",
        "units": "W",
        "range": [1000, 500000]
    },
    
    "heating_efficiency": {
        "object_type": "COIL:HEATING:GAS",
        "field_name": "Gas Burner Efficiency",
        "units": "fraction",
        "range": [0.7, 0.98],
        "code_minimum": 0.80,
        "high_efficiency": 0.95
    },
    
    "heating_setpoint": {
        "object_type": "THERMOSTATSETPOINT:DUALSETPOINT",
        "field_name": "Heating Setpoint Temperature",
        "units": "°C",
        "range": [15, 25],
        "default": 21,
        "comfort_range": [20, 22]
    }
}
```

#### Fans and Pumps
```python
FAN_PARAMETERS = {
    "fan_efficiency": {
        "object_type": "FAN:CONSTANTVOLUME",
        "field_name": "Fan Total Efficiency",
        "units": "fraction",
        "range": [0.3, 0.9],
        "typical": 0.6,
        "high_efficiency": 0.8
    },
    
    "fan_pressure_rise": {
        "object_type": "FAN:CONSTANTVOLUME",
        "field_name": "Pressure Rise",
        "units": "Pa",
        "range": [100, 1500],
        "typical_values": {
            "residential": [125, 250],
            "commercial": [500, 1000]
        }
    }
}
```

### 2. Envelope Parameters

#### Materials
```python
MATERIAL_PARAMETERS = {
    "insulation_conductivity": {
        "object_type": "MATERIAL",
        "field_name": "Conductivity",
        "units": "W/m-K",
        "range": [0.02, 0.2],
        "insulation_types": {
            "fiberglass": 0.040,
            "cellulose": 0.039,
            "spray_foam": 0.026,
            "rigid_foam": 0.029
        }
    },
    
    "insulation_thickness": {
        "object_type": "MATERIAL",
        "field_name": "Thickness",
        "units": "m",
        "range": [0.025, 0.5],
        "r_value_calculation": "thickness / conductivity"
    },
    
    "mass_density": {
        "object_type": "MATERIAL",
        "field_name": "Density",
        "units": "kg/m³",
        "range": [10, 3000],
        "typical_values": {
            "insulation": [10, 100],
            "wood": [400, 800],
            "concrete": [2000, 2400],
            "steel": [7850, 7850]
        }
    }
}
```

#### Windows
```python
WINDOW_PARAMETERS = {
    "window_u_value": {
        "object_type": "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
        "field_name": "U-Factor",
        "units": "W/m²-K",
        "range": [0.1, 6.0],
        "performance_levels": {
            "single_pane": 5.8,
            "double_pane": 2.8,
            "double_low_e": 1.8,
            "triple_pane": 0.8
        }
    },
    
    "window_shgc": {
        "object_type": "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
        "field_name": "Solar Heat Gain Coefficient",
        "units": "fraction",
        "range": [0.1, 0.9],
        "climate_recommendations": {
            "hot": [0.2, 0.3],
            "mixed": [0.3, 0.4],
            "cold": [0.4, 0.6]
        }
    },
    
    "window_vt": {
        "object_type": "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
        "field_name": "Visible Transmittance",
        "units": "fraction",
        "range": [0.1, 0.9],
        "typical": 0.6,
        "daylighting_minimum": 0.4
    }
}
```

### 3. Internal Loads Parameters

#### Lighting
```python
LIGHTING_PARAMETERS = {
    "lighting_power_density": {
        "object_type": "LIGHTS",
        "field_name": "Watts per Zone Floor Area",
        "units": "W/m²",
        "range": [1.0, 25.0],
        "building_type_values": {
            "office": 10.8,
            "retail": 14.0,
            "warehouse": 6.5,
            "residential": 5.4
        },
        "technology_levels": {
            "incandescent": 20.0,
            "fluorescent": 12.0,
            "led": 6.0
        }
    },
    
    "lighting_fractions": {
        "return_air": {
            "field_name": "Return Air Fraction",
            "range": [0, 1],
            "typical": 0.2
        },
        "radiant": {
            "field_name": "Fraction Radiant",
            "range": [0, 1],
            "typical": 0.37
        },
        "visible": {
            "field_name": "Fraction Visible",
            "range": [0, 1],
            "typical": 0.18
        }
    }
}
```

#### Equipment
```python
EQUIPMENT_PARAMETERS = {
    "equipment_power_density": {
        "object_type": "ELECTRICEQUIPMENT",
        "field_name": "Watts per Zone Floor Area",
        "units": "W/m²",
        "range": [1.0, 50.0],
        "building_type_values": {
            "office": 10.0,
            "data_center": 1000.0,
            "residential": 5.0,
            "restaurant": 20.0
        }
    },
    
    "equipment_fractions": {
        "latent": {
            "field_name": "Fraction Latent",
            "range": [0, 0.5],
            "typical": 0.0
        },
        "radiant": {
            "field_name": "Fraction Radiant",
            "range": [0, 1],
            "typical": 0.3
        },
        "lost": {
            "field_name": "Fraction Lost",
            "range": [0, 1],
            "typical": 0.0
        }
    }
}
```

### 4. Ventilation and Infiltration Parameters

#### Infiltration
```python
INFILTRATION_PARAMETERS = {
    "infiltration_rate": {
        "object_type": "ZONEINFILTRATION:DESIGNFLOWRATE",
        "field_name": "Air Changes per Hour",
        "units": "ACH",
        "range": [0.05, 2.0],
        "performance_levels": {
            "very_tight": 0.1,
            "tight": 0.25,
            "average": 0.5,
            "leaky": 1.0
        }
    },
    
    "infiltration_coefficients": {
        "constant": {
            "field_name": "Constant Term Coefficient",
            "range": [0, 1],
            "default": 1
        },
        "temperature": {
            "field_name": "Temperature Term Coefficient",
            "range": [0, 1],
            "default": 0
        },
        "wind_speed": {
            "field_name": "Velocity Term Coefficient",
            "range": [0, 1],
            "default": 0
        }
    }
}
```

#### Ventilation
```python
VENTILATION_PARAMETERS = {
    "ventilation_rate_per_person": {
        "object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
        "field_name": "Flow Rate per Person",
        "units": "m³/s-person",
        "range": [0.0, 0.02],
        "ashrae_minimum": 0.0025,
        "high_quality": 0.01
    },
    
    "ventilation_rate_per_area": {
        "object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
        "field_name": "Flow Rate per Zone Floor Area",
        "units": "m³/s-m²",
        "range": [0.0, 0.01],
        "typical": 0.0003
    },
    
    "heat_recovery_efficiency": {
        "object_type": "HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT",
        "field_name": "Sensible Effectiveness at 100% Heating Air Flow",
        "units": "fraction",
        "range": [0.0, 0.95],
        "typical": 0.7,
        "high_efficiency": 0.85
    }
}
```

### 5. DHW Parameters

```python
DHW_PARAMETERS = {
    "water_heater_efficiency": {
        "object_type": "WATERHEATER:MIXED",
        "field_name": "Heater Thermal Efficiency",
        "units": "fraction",
        "range": [0.7, 0.99],
        "fuel_type_values": {
            "gas": 0.82,
            "electric": 0.98,
            "heat_pump": 3.5  # COP
        }
    },
    
    "tank_volume": {
        "object_type": "WATERHEATER:MIXED",
        "field_name": "Tank Volume",
        "units": "m³",
        "range": [0.1, 1.0],
        "residential_typical": 0.19,  # 50 gallons
        "commercial_range": [0.3, 1.0]
    },
    
    "setpoint_temperature": {
        "object_type": "WATERHEATER:MIXED",
        "field_name": "Setpoint Temperature Schedule Name",
        "units": "°C",
        "range": [40, 60],
        "default": 60,
        "legionella_minimum": 60
    }
}
```

### 6. Shading Parameters

```python
SHADING_PARAMETERS = {
    "overhang_projection": {
        "object_type": "SHADING:OVERHANG:PROJECTION",
        "field_name": "Depth",
        "units": "m",
        "range": [0.1, 3.0],
        "typical": 0.6,
        "climate_factors": {
            "hot": [1.0, 2.0],
            "cold": [0.3, 0.6]
        }
    },
    
    "blind_slat_angle": {
        "object_type": "WINDOWMATERIAL:BLIND",
        "field_name": "Slat Angle",
        "units": "degrees",
        "range": [0, 180],
        "typical": 45,
        "control_strategy": "scheduled|solar"
    },
    
    "shade_transmittance": {
        "object_type": "WINDOWMATERIAL:SHADE",
        "field_name": "Solar Transmittance",
        "units": "fraction",
        "range": [0.0, 0.8],
        "shade_types": {
            "light": 0.5,
            "medium": 0.3,
            "dark": 0.1
        }
    }
}
```

## Parameter Dependencies

Some parameters have dependencies that must be considered:

```python
PARAMETER_DEPENDENCIES = {
    "cooling_capacity": {
        "depends_on": ["zone_area", "design_load"],
        "relationship": "capacity >= design_cooling_load"
    },
    
    "fan_flow_rate": {
        "depends_on": ["cooling_capacity", "heating_capacity"],
        "relationship": "flow_rate >= max(cooling_cfm, heating_cfm)"
    },
    
    "lighting_fractions": {
        "depends_on": ["return_air_fraction", "radiant_fraction", "visible_fraction"],
        "relationship": "sum(fractions) <= 1.0"
    }
}
```

## Validation Rules

```python
VALIDATION_RULES = {
    "capacity_per_area": {
        "parameters": ["cooling_capacity", "zone_area"],
        "rule": lambda cap, area: 50 <= cap/area <= 500  # W/m²
    },
    
    "window_fraction": {
        "parameters": ["window_area", "wall_area"],
        "rule": lambda win, wall: win/wall <= 0.8
    },
    
    "setpoint_deadband": {
        "parameters": ["cooling_setpoint", "heating_setpoint"],
        "rule": lambda cool, heat: cool - heat >= 2.0  # °C
    }
}
```

## Performance Impact Mapping

```python
PERFORMANCE_IMPACTS = {
    "cooling_cop": ["cooling_energy", "electricity_peak"],
    "insulation_thickness": ["heating_energy", "cooling_energy"],
    "window_shgc": ["cooling_energy", "lighting_energy"],
    "lighting_power_density": ["lighting_energy", "cooling_energy"],
    "infiltration_rate": ["heating_energy", "cooling_energy"]
}
```

## Units and Conversions

```python
UNIT_CONVERSIONS = {
    "temperature": {
        "C_to_F": lambda c: c * 9/5 + 32,
        "F_to_C": lambda f: (f - 32) * 5/9
    },
    "area": {
        "m2_to_ft2": lambda m2: m2 * 10.764,
        "ft2_to_m2": lambda ft2: ft2 / 10.764
    },
    "power": {
        "W_to_Btu/h": lambda w: w * 3.412,
        "Btu/h_to_W": lambda btu: btu / 3.412
    }
}
```