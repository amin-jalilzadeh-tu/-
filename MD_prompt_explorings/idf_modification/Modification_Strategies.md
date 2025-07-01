# IDF Modification Strategies

## Overview

Modification strategies define how the system selects parameters and applies changes to create building variants. The system supports multiple strategy types, from simple scenarios to complex optimization approaches.

## Strategy Types

### 1. Scenario-Based Strategies

Predefined packages of modifications representing common building improvement scenarios.

**Configuration:**
```json
{
  "modification_strategy": {
    "type": "scenarios",
    "scenarios": ["high_performance_envelope", "efficient_hvac"]
  }
}
```

**Available Scenarios:**

#### a) **baseline**
- No modifications applied
- Used as reference for comparisons

#### b) **code_minimum**
- Modifications to meet minimum energy code requirements
- Updates insulation, glazing, and equipment to code levels
- Example modifications:
  ```python
  {
    "wall_insulation_r_value": 13,
    "roof_insulation_r_value": 30,
    "window_u_value": 0.32,
    "lighting_power_density": 0.9  # W/ft²
  }
  ```

#### c) **high_performance_envelope**
- Enhanced building envelope performance
- Modifications include:
  - Increased insulation (R-30 walls, R-60 roof)
  - High-performance windows (U-0.20, SHGC-0.25)
  - Reduced infiltration (0.25 ACH)
  - Thermal bridging mitigation

#### d) **efficient_hvac**
- High-efficiency HVAC equipment
- Modifications include:
  - Increased cooling COP (4.5+)
  - High heating efficiency (0.95+)
  - Variable speed fans
  - Optimized setpoints

#### e) **reduced_loads**
- Internal load reductions
- Modifications include:
  - LED lighting (0.6 W/ft²)
  - Energy Star equipment
  - Occupancy-based controls
  - Daylight harvesting

#### f) **net_zero_ready**
- Comprehensive improvements for net-zero potential
- Combines all high-performance strategies
- Adds renewable-ready features

#### g) **comfort_optimization**
- Focus on occupant comfort
- Modifications include:
  - Tighter temperature bands
  - Improved ventilation rates
  - Better humidity control
  - Radiant temperature optimization

### 2. Sampling-Based Strategies

Generate variants using statistical sampling methods for uncertainty analysis and optimization.

**Configuration:**
```json
{
  "modification_strategy": {
    "type": "sampling",
    "method": "latin_hypercube",
    "num_variants": 100,
    "seed": 42,
    "parameter_ranges": {
      "wall_conductivity": [0.03, 0.15],
      "window_u_value": [0.20, 0.50],
      "cooling_cop": [3.0, 5.0]
    }
  }
}
```

**Sampling Methods:**

#### a) **uniform**
- Random sampling within parameter ranges
- Each parameter independently sampled
- Good for exploration

#### b) **latin_hypercube**
- Stratified sampling ensuring coverage
- Better space-filling properties
- Preferred for sensitivity analysis

#### c) **sobol**
- Quasi-random sequences
- Low-discrepancy sampling
- Optimal for high-dimensional spaces

#### d) **morris**
- One-at-a-time sampling
- Designed for screening
- Efficient for large parameter sets

### 3. Optimization-Based Strategies

Iterative search for optimal parameter combinations.

**Configuration:**
```json
{
  "modification_strategy": {
    "type": "optimization",
    "algorithm": "genetic",
    "objective": "minimize_energy",
    "constraints": {
      "budget": 100000,
      "comfort_hours": 0.95
    },
    "generations": 50,
    "population_size": 20
  }
}
```

**Optimization Algorithms:**

#### a) **genetic**
- Evolutionary algorithm
- Good for discrete/mixed variables
- Handles multiple objectives

#### b) **particle_swarm**
- Swarm intelligence method
- Continuous variables
- Fast convergence

#### c) **simulated_annealing**
- Probabilistic method
- Avoids local optima
- Single objective

## Category-Specific Strategies

Each modifier category can have its own strategies:

### HVAC Strategies

```python
HVAC_STRATEGIES = {
    "baseline": {},  # No changes
    
    "high_efficiency": {
        "cooling_cop_multiplier": 1.3,
        "heating_efficiency_multiplier": 1.1,
        "fan_efficiency": 0.7
    },
    
    "setpoint_optimization": {
        "cooling_setpoint_offset": 2,  # °C higher
        "heating_setpoint_offset": -2,  # °C lower
        "deadband": 3  # °C
    },
    
    "variable_speed": {
        "fan_type": "variable_speed",
        "pump_type": "variable_speed",
        "minimum_flow_fraction": 0.3
    }
}
```

### Envelope Strategies

```python
ENVELOPE_STRATEGIES = {
    "super_insulation": {
        "wall_r_multiplier": 2.0,
        "roof_r_multiplier": 2.0,
        "foundation_r_add": 10
    },
    
    "thermal_mass": {
        "mass_thickness_multiplier": 1.5,
        "mass_density": 2400,  # kg/m³
        "mass_specific_heat": 840  # J/kg·K
    },
    
    "glazing_upgrade": {
        "window_u_value": 0.20,
        "window_shgc": 0.25,
        "window_vt": 0.50
    }
}
```

### Lighting Strategies

```python
LIGHTING_STRATEGIES = {
    "led_retrofit": {
        "power_density_multiplier": 0.5,
        "efficacy": 100  # lm/W
    },
    
    "daylighting": {
        "daylight_sensors": true,
        "dimming_fraction": 0.3,
        "control_zones": "perimeter"
    },
    
    "occupancy_control": {
        "sensor_type": "dual_technology",
        "off_delay": 15,  # minutes
        "coverage": 0.9  # fraction of space
    }
}
```

## Modification Methods

How values are changed:

### 1. **absolute**
Set to specific value:
```python
new_value = target_value
```

### 2. **multiplier**
Multiply by factor:
```python
new_value = original_value * multiplier
```

### 3. **offset**
Add/subtract value:
```python
new_value = original_value + offset
```

### 4. **percentage**
Change by percentage:
```python
new_value = original_value * (1 + percentage/100)
```

### 5. **range**
Random within bounds:
```python
new_value = random.uniform(min_value, max_value)
```

### 6. **discrete**
Choose from options:
```python
new_value = random.choice(options)
```

## Strategy Selection Logic

The system selects strategies based on:

1. **Building Type**
   - Residential vs. commercial
   - Size and complexity
   - Climate zone

2. **Performance Goals**
   - Energy reduction targets
   - Comfort requirements
   - Budget constraints

3. **Iteration Context**
   - Previous results
   - Convergence status
   - Time constraints

## Advanced Strategy Features

### 1. Progressive Modification
```python
def get_progressive_multiplier(iteration: int) -> float:
    """Increase modification intensity with iterations"""
    base = 1.0
    increment = 0.1
    return base + (iteration * increment)
```

### 2. Adaptive Strategies
```python
def adapt_strategy(previous_results: dict) -> dict:
    """Adjust strategy based on previous performance"""
    if previous_results['energy_reduction'] < 0.1:
        return {"multiplier": 1.5}  # More aggressive
    else:
        return {"multiplier": 1.1}  # Conservative
```

### 3. Composite Strategies
```python
COMPOSITE_STRATEGIES = {
    "deep_retrofit": [
        "super_insulation",
        "efficient_hvac",
        "led_retrofit",
        "occupancy_control"
    ]
}
```

## Strategy Constraints

### 1. Physical Constraints
- Material properties limits
- Equipment capacity ranges
- Geometric feasibility

### 2. Code Constraints
- Minimum ventilation rates
- Safety requirements
- Accessibility standards

### 3. Comfort Constraints
- Temperature ranges
- Humidity limits
- Air quality requirements

### 4. Economic Constraints
- Budget limits
- Payback requirements
- First cost caps

## Custom Strategy Development

To create custom strategies:

1. **Define Strategy Class:**
```python
class CustomStrategy:
    def __init__(self, config: dict):
        self.config = config
    
    def select_parameters(self, building_data: dict) -> list:
        """Select parameters to modify"""
        
    def calculate_values(self, current_values: dict) -> dict:
        """Calculate new parameter values"""
```

2. **Register Strategy:**
```python
STRATEGY_REGISTRY['custom'] = CustomStrategy
```

3. **Configure Usage:**
```json
{
  "modification_strategy": {
    "type": "custom",
    "config": {
      "custom_param": "value"
    }
  }
}
```

## Strategy Performance Metrics

Track strategy effectiveness:

1. **Energy Metrics**
   - Total energy reduction
   - Peak demand reduction
   - Energy cost savings

2. **Comfort Metrics**
   - Unmet hours
   - PMV/PPD indices
   - Temperature stability

3. **Economic Metrics**
   - Implementation cost
   - Payback period
   - Net present value

4. **Environmental Metrics**
   - Carbon reduction
   - Water savings
   - Material efficiency