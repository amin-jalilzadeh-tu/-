# IDF Modification Rules and Validation

## Overview

The rules and validation system ensures that all modifications produce valid IDF files and maintain physical, logical, and performance constraints. It prevents invalid configurations and enforces best practices.

## Rule Categories

### 1. Physical Constraints
Rules that enforce physical laws and material properties.

### 2. EnergyPlus Requirements
Rules that ensure IDF validity for EnergyPlus simulation.

### 3. Performance Standards
Rules based on building codes and efficiency standards.

### 4. Dependency Rules
Rules that maintain relationships between parameters.

### 5. Comfort Rules
Rules that ensure occupant comfort is maintained.

## Physical Constraint Rules

### 1. Material Property Limits

```python
MATERIAL_PHYSICAL_LIMITS = {
    "conductivity": {
        "rule": "range_check",
        "min": 0.001,  # W/m-K (aerogel)
        "max": 400,    # W/m-K (copper)
        "message": "Conductivity must be within physical limits"
    },
    
    "density": {
        "rule": "range_check", 
        "min": 10,     # kg/m³ (insulation foam)
        "max": 8000,   # kg/m³ (steel)
        "message": "Density must be within material limits"
    },
    
    "specific_heat": {
        "rule": "range_check",
        "min": 100,    # J/kg-K
        "max": 5000,   # J/kg-K (water: 4186)
        "message": "Specific heat must be realistic"
    },
    
    "thickness": {
        "rule": "range_check",
        "min": 0.001,  # m (1mm minimum)
        "max": 1.0,    # m (1m maximum for single layer)
        "message": "Layer thickness must be practical"
    }
}
```

### 2. Thermodynamic Constraints

```python
class ThermodynamicRules:
    @staticmethod
    def validate_cop(cop_value, equipment_type):
        """Validate Coefficient of Performance"""
        limits = {
            "dx_cooling": {"min": 2.0, "max": 6.0, "carnot_limit": 8.0},
            "heat_pump_heating": {"min": 2.0, "max": 5.0},
            "chiller": {"min": 3.0, "max": 7.0}
        }
        
        if equipment_type in limits:
            limit = limits[equipment_type]
            if not limit["min"] <= cop_value <= limit["max"]:
                return False, f"COP {cop_value} outside range for {equipment_type}"
                
            # Check Carnot efficiency limit
            if "carnot_limit" in limit and cop_value > limit["carnot_limit"]:
                return False, f"COP exceeds theoretical Carnot limit"
                
        return True, "Valid"
    
    @staticmethod
    def validate_efficiency(efficiency, fuel_type):
        """Validate combustion efficiency"""
        limits = {
            "gas": {"min": 0.7, "max": 0.98},
            "oil": {"min": 0.7, "max": 0.95},
            "electric": {"min": 0.98, "max": 1.0}
        }
        
        if fuel_type in limits:
            limit = limits[fuel_type]
            if not limit["min"] <= efficiency <= limit["max"]:
                return False, f"Efficiency outside range for {fuel_type}"
                
        return True, "Valid"
```

### 3. Heat Transfer Constraints

```python
HEAT_TRANSFER_RULES = {
    "window_u_factor": {
        "single_pane": {"min": 4.0, "max": 6.0},
        "double_pane": {"min": 1.5, "max": 3.0},
        "triple_pane": {"min": 0.5, "max": 1.5},
        "validation": lambda u, panes: validate_u_by_panes(u, panes)
    },
    
    "r_value_additivity": {
        "rule": "sum_of_layers",
        "validation": lambda layers: sum(layer.thickness/layer.conductivity 
                                       for layer in layers)
    },
    
    "thermal_mass_time_constant": {
        "rule": "calculate_time_constant",
        "min_hours": 1,
        "max_hours": 24,
        "calculation": lambda mass, area, u: (mass * cp) / (area * u * 3600)
    }
}
```

## EnergyPlus Requirement Rules

### 1. Object Reference Integrity

```python
class ReferenceIntegrityRules:
    def __init__(self, parsed_objects):
        self.parsed_objects = parsed_objects
        self.build_reference_map()
    
    def build_reference_map(self):
        """Build map of all object references"""
        self.references = {
            "zones": set(),
            "schedules": set(),
            "constructions": set(),
            "materials": set()
        }
        
        for obj_type, objects in self.parsed_objects.items():
            for obj in objects:
                if obj_type == "ZONE":
                    self.references["zones"].add(obj["name"])
                elif "SCHEDULE" in obj_type:
                    self.references["schedules"].add(obj["name"])
                # ... etc
    
    def validate_zone_reference(self, zone_name):
        """Check if zone exists"""
        if zone_name not in self.references["zones"]:
            return False, f"Zone '{zone_name}' not found"
        return True, "Valid"
    
    def validate_schedule_reference(self, schedule_name):
        """Check if schedule exists"""
        if schedule_name not in self.references["schedules"]:
            return False, f"Schedule '{schedule_name}' not found"
        return True, "Valid"
```

### 2. Field Requirements

```python
ENERGYPLUS_FIELD_RULES = {
    "COIL:COOLING:DX:SINGLESPEED": {
        "required_fields": [
            "Name",
            "Availability Schedule Name",
            "Gross Rated Total Cooling Capacity",
            "Gross Rated Sensible Heat Ratio",
            "Gross Rated COP"
        ],
        "conditional_fields": {
            "Air Inlet Node Name": "required_if_not_outdoor_air",
            "Air Outlet Node Name": "required_if_not_outdoor_air"
        }
    },
    
    "ZONE": {
        "required_fields": [
            "Name"
        ],
        "numeric_fields": {
            "Volume": {"min": 1.0, "max": 1000000.0},
            "Floor Area": {"min": 1.0, "max": 10000.0},
            "Ceiling Height": {"min": 2.0, "max": 30.0}
        }
    }
}
```

### 3. Object Relationships

```python
class ObjectRelationshipRules:
    @staticmethod
    def validate_construction_layers(construction_obj, materials):
        """Validate construction has valid material layers"""
        errors = []
        
        # Check at least one layer
        if len(construction_obj["layers"]) == 0:
            errors.append("Construction must have at least one layer")
        
        # Check all layers exist
        for layer in construction_obj["layers"]:
            if layer not in materials:
                errors.append(f"Material '{layer}' not found")
        
        # Check layer order (optional)
        if len(construction_obj["layers"]) > 1:
            # Outside layer should be weather-resistant
            # Inside layer should be finish material
            pass
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_hvac_connections(hvac_obj, zones):
        """Validate HVAC serves valid zones"""
        zone_name = hvac_obj.get("Zone Name")
        if zone_name and zone_name not in zones:
            return False, f"HVAC serves non-existent zone: {zone_name}"
        return True, "Valid"
```

## Dependency Rules

### 1. Parameter Dependencies

```python
PARAMETER_DEPENDENCIES = {
    "cooling_capacity_flow": {
        "primary": "cooling_capacity",
        "dependent": "rated_air_flow_rate",
        "relationship": lambda cap: cap / 12000 * 400,  # 400 CFM per ton
        "tolerance": 0.2,  # ±20%
        "message": "Air flow should be ~400 CFM per ton of cooling"
    },
    
    "window_frame_conductance": {
        "primary": "window_u_value",
        "dependent": "frame_conductance", 
        "relationship": lambda u: u * 1.2,  # Frame typically worse
        "constraint": "greater_than",
        "message": "Frame conductance should exceed glass U-value"
    },
    
    "heating_cooling_setpoints": {
        "primary": ["heating_setpoint", "cooling_setpoint"],
        "constraint": lambda h, c: c - h >= 2.0,  # Minimum deadband
        "message": "Cooling setpoint must be at least 2°C above heating"
    }
}
```

### 2. Cross-Category Dependencies

```python
class CrossCategoryDependencies:
    def validate_envelope_hvac_consistency(self, modifications):
        """Ensure envelope and HVAC modifications are compatible"""
        
        rules = []
        
        # If improving envelope, can reduce HVAC capacity
        if self.envelope_improved(modifications):
            rules.append({
                "check": "hvac_capacity_appropriate",
                "validation": lambda: self.hvac_not_oversized(modifications)
            })
        
        # If adding thermal mass, need appropriate controls
        if self.thermal_mass_added(modifications):
            rules.append({
                "check": "thermal_mass_controls",
                "validation": lambda: self.has_night_flush_capability(modifications)
            })
        
        return self.run_validations(rules)
```

### 3. Sequential Dependencies

```python
MODIFICATION_SEQUENCE_RULES = {
    "insulation_before_hvac": {
        "sequence": ["envelope", "hvac"],
        "reason": "Size HVAC after envelope improvements"
    },
    
    "controls_after_equipment": {
        "sequence": ["equipment", "controls"],
        "reason": "Configure controls for actual equipment"
    },
    
    "validation": lambda mods: validate_modification_order(mods)
}
```

## Comfort Rules

### 1. Temperature Comfort

```python
COMFORT_TEMPERATURE_RULES = {
    "occupied_heating": {
        "min": 18.0,  # °C
        "max": 24.0,
        "recommended": 21.0,
        "message": "Heating setpoint outside comfort range"
    },
    
    "occupied_cooling": {
        "min": 22.0,
        "max": 28.0,
        "recommended": 24.0,
        "message": "Cooling setpoint outside comfort range"
    },
    
    "temperature_drift": {
        "max_rate": 2.0,  # °C/hour
        "message": "Temperature change rate too fast"
    },
    
    "radiant_asymmetry": {
        "max_delta": 10.0,  # °C
        "surfaces": ["floor", "ceiling", "walls"],
        "message": "Radiant temperature asymmetry too high"
    }
}
```

### 2. Air Quality Rules

```python
INDOOR_AIR_QUALITY_RULES = {
    "minimum_ventilation": {
        "ashrae_62.1": {
            "people_component": 0.0025,  # m³/s per person
            "area_component": 0.0003,    # m³/s per m²
            "calculation": lambda people, area: 
                people * 0.0025 + area * 0.0003
        }
    },
    
    "co2_limits": {
        "max_ppm": 1000,
        "calculation": lambda ventilation, occupancy: 
            validate_co2_levels(ventilation, occupancy)
    },
    
    "humidity_control": {
        "min_rh": 30,  # %
        "max_rh": 60,  # %
        "message": "Humidity outside comfort range"
    }
}
```

## Validation Implementation

### 1. Rule Engine

```python
class RuleEngine:
    def __init__(self):
        self.rules = self.load_all_rules()
        self.results = []
    
    def validate_modification(self, modification):
        """Run all applicable rules on a modification"""
        
        category = modification["category"]
        parameter = modification["parameter"]
        
        # Get applicable rules
        rules = self.get_rules_for_parameter(category, parameter)
        
        # Run validations
        for rule in rules:
            result = self.execute_rule(rule, modification)
            self.results.append(result)
        
        return all(r["valid"] for r in self.results)
    
    def execute_rule(self, rule, modification):
        """Execute a single validation rule"""
        
        if rule["type"] == "range_check":
            return self.validate_range(
                modification["new_value"],
                rule["min"],
                rule["max"],
                rule.get("message", "Value out of range")
            )
        elif rule["type"] == "dependency":
            return self.validate_dependency(
                modification,
                rule["dependency"],
                rule.get("message", "Dependency violation")
            )
        # ... other rule types
```

### 2. Validation Workflow

```python
def validate_complete_modification_set(modifications):
    """Validate all modifications together"""
    
    validation_steps = [
        ("individual", validate_individual_modifications),
        ("dependencies", validate_dependencies),
        ("performance", validate_performance_impacts),
        ("comfort", validate_comfort_maintained),
        ("energy_code", validate_code_compliance)
    ]
    
    results = {}
    for step_name, validator in validation_steps:
        result = validator(modifications)
        results[step_name] = result
        
        if not result["valid"]:
            # Stop on first failure
            break
    
    return {
        "valid": all(r["valid"] for r in results.values()),
        "details": results
    }
```

### 3. Custom Rule Definition

```python
class CustomRule:
    def __init__(self, name, condition, message):
        self.name = name
        self.condition = condition
        self.message = message
    
    def validate(self, value, context=None):
        """Run custom validation"""
        try:
            result = self.condition(value, context)
            return {
                "valid": result,
                "rule": self.name,
                "message": self.message if not result else "Valid"
            }
        except Exception as e:
            return {
                "valid": False,
                "rule": self.name,
                "message": f"Rule error: {str(e)}"
            }

# Example custom rule
efficiency_rule = CustomRule(
    name="high_efficiency_check",
    condition=lambda eff, equip_type: eff >= MIN_EFFICIENCY[equip_type],
    message="Equipment efficiency below minimum requirement"
)
```

## Best Practices

1. **Fail Fast**: Validate as early as possible in the modification process
2. **Clear Messages**: Provide actionable error messages
3. **Context Awareness**: Consider building type and climate in validations
4. **Performance**: Cache validation results when possible
5. **Extensibility**: Allow easy addition of new rules
6. **Documentation**: Document why each rule exists
7. **Override Capability**: Allow expert users to override with justification