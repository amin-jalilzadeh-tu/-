# Simulation Control Modifications System

## Overview
The simulation control modification system handles simulation parameters that affect calculation methods, accuracy, speed, and output generation in EnergyPlus. These parameters don't directly represent physical building components but control how EnergyPlus performs its calculations and reports results.

## Modified Object Types

### Core Simulation Controls
- `SIMULATIONCONTROL` - Master simulation settings
- `BUILDING` - Building-level parameters including terrain and solar distribution
- `TIMESTEP` - Simulation timestep control
- `CONVERGENCELIMITS` - Convergence criteria for iterative calculations

### Calculation Methods
- `SHADOWCALCULATION` - Shadow and solar calculation frequency
- `HEATBALANCEALGORITHM` - Surface heat balance solution method
- `SURFACECONVECTIONALGORITHM:INSIDE` - Interior convection algorithms
- `SURFACECONVECTIONALGORITHM:OUTSIDE` - Exterior convection algorithms
- `ZONECAPACITANCEMULTIPLIER:RESEARCHSPECIAL` - Thermal mass multipliers

### Output Controls
- `OUTPUT:VARIABLE` - Variable output specifications
- `OUTPUT:METER` - Energy meter outputs
- `OUTPUT:SQLITE` - Database output options
- `OUTPUTCONTROL:TABLE:STYLE` - Tabular report formatting

## Parameters Modified

### Timestep Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `timesteps_per_hour` | Number of Timesteps per Hour | 0 | int | - | 1-60 | simulation_accuracy |

**Allowed values**: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60 (must evenly divide 60)

### Shadow Calculation Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `shadow_calculation_frequency` | Calculation Frequency | 0 | int | days | 1-365 | simulation_speed |
| `maximum_shadow_figures` | Maximum Figures in Shadow Overlap Calculations | 1 | int | - | 200-50000 | simulation_accuracy |

### Convergence Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `minimum_system_timestep` | Minimum System Timestep | 0 | float | minutes | 1-60 | convergence |
| `maximum_hvac_iterations` | Maximum HVAC Iterations | 1 | int | - | 1-50 | convergence |

### Heat Balance Algorithm Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `algorithm_type` | Algorithm | 0 | str | - | See allowed values | simulation_method |
| `surface_temperature_upper_limit` | Surface Temperature Upper Limit | 1 | float | °C | 100-300 | convergence |

**Allowed algorithms**:
- `ConductionTransferFunction` - Fast, standard method
- `MoisturePenetrationDepthConductionTransferFunction` - Includes moisture
- `ConductionFiniteDifference` - More accurate, slower
- `CombinedHeatAndMoistureFiniteElement` - Most detailed

### Building Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `terrain` | Terrain | 5 | str | - | See allowed values | wind_calculations |
| `solar_distribution` | Solar Distribution | 7 | str | - | See allowed values | solar_calculations |

**Terrain types**: Country, Suburbs, City, Ocean, Urban

**Solar distribution options**:
- `MinimalShadowing` - Fastest, least accurate
- `FullExterior` - Exterior solar distribution only
- `FullInteriorAndExterior` - Interior and exterior solar
- `FullExteriorWithReflections` - Includes exterior reflections
- `FullInteriorAndExteriorWithReflections` - Most detailed

### Output Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `output_variable_reporting_frequency` | Reporting Frequency | 2 | str | - | See allowed values | output_file_size |

**Reporting frequencies**: Detailed, Timestep, Hourly, Daily, Monthly, RunPeriod, Environment, Annual

## Modification Strategies

### 1. Accuracy Focus (`accuracy_focus`)
- **Purpose**: Maximum simulation accuracy at the cost of speed
- **Modifications**:
  - Timesteps per hour: 10 (6-minute intervals)
  - Shadow calculations: Weekly (every 7 days)
  - Maximum shadow figures: 15,000
  - Solar distribution: FullInteriorAndExteriorWithReflections
  - Use for:
    - Final design verification
    - Research studies
    - Complex shading scenarios

### 2. Speed Focus (`speed_focus`)
- **Purpose**: Faster simulations for iterative design
- **Modifications**:
  - Timesteps per hour: 4 (15-minute intervals)
  - Shadow calculations: Monthly (every 30 days)
  - Maximum shadow figures: 1,000
  - Solar distribution: FullExterior
  - Use for:
    - Early design iterations
    - Parametric studies
    - Quick comparisons

### 3. Detailed Output (`detailed_output`)
- **Purpose**: Maximum output detail for analysis
- **Modifications**:
  - Output frequency: Timestep
  - Captures all variations
  - Large output files
  - Use for:
    - Detailed troubleshooting
    - Research analysis
    - Control tuning

### 4. Balanced Settings (`balanced`)
- **Purpose**: Good accuracy with reasonable speed
- **Modifications**:
  - Timesteps per hour: 6 (10-minute intervals)
  - HVAC iterations: 25
  - Balanced convergence
  - Use for:
    - Standard design analysis
    - Code compliance
    - Energy modeling

## Process Flow

### 1. Strategy Selection
```
User Intent → Accuracy vs Speed Priority
           → Output Detail Requirements
           → Select Appropriate Strategy
```

### 2. Parameter Optimization
```
Base Settings → Apply Strategy Multipliers
             → Validate Allowed Values
             → Check Interdependencies
             → Update Parameters
```

### 3. Validation
```
Modified Settings → Check Convergence Impact
                 → Estimate Runtime Change
                 → Verify Output Size
                 → Create Modification Records
```

## Integration Notes

### Performance Trade-offs

| Setting | Accuracy Impact | Speed Impact | When to Use |
|---------|----------------|--------------|-------------|
| High Timesteps | +20% accuracy | -50% speed | Final runs |
| Frequent Shadows | +10% accuracy | -30% speed | Complex shading |
| Full Solar Dist. | +15% accuracy | -40% speed | Daylighting studies |
| Detailed Output | No impact | -20% speed | Troubleshooting |

### Common Use Cases
1. **Design Development**: Speed focus for iterations
2. **Final Documentation**: Accuracy focus for reports
3. **LEED Submission**: Balanced with hourly output
4. **Research**: Maximum accuracy and detail
5. **Optimization**: Speed focus with key outputs only

### Impact on Results
- **Energy Use**: ±2-5% based on timestep
- **Peak Loads**: ±5-10% based on settings
- **Comfort Metrics**: ±3-7% based on timestep
- **Runtime**: 10x variation possible

## Technical Implementation Details

### Timestep Selection Guide
```
Timesteps/Hour | Interval | Use Case
1              | 60 min   | Never recommended
4              | 15 min   | Quick studies
6              | 10 min   | Standard modeling
10             | 6 min    | High accuracy
60             | 1 min    | Research only
```

### Shadow Calculation Frequency
```
Days | Update Frequency | Accuracy | Speed
1    | Daily           | Highest  | Slowest
7    | Weekly          | High     | Moderate
30   | Monthly         | Standard | Fast
365  | Once per year   | Low      | Fastest
```

### Solar Distribution Complexity
1. **MinimalShadowing**: No beam solar on exterior
2. **FullExterior**: Beam solar on all exterior surfaces
3. **FullInteriorAndExterior**: + Interior solar distribution
4. **FullExteriorWithReflections**: + Exterior reflections
5. **FullInteriorAndExteriorWithReflections**: All effects

### Convergence Settings Impact
- **Minimum timestep**: Prevents infinite loops
- **Maximum iterations**: Limits calculation cycles
- **Trade-off**: Stability vs accuracy

### Error Handling
- Validate timestep divides 60 evenly
- Check shadow frequency reasonableness
- Ensure valid algorithm selection
- Verify output frequency compatibility

### Best Practices
1. **Start Simple**: Use speed focus for initial runs
2. **Validate Early**: Check convergence warnings
3. **Increment Gradually**: Don't jump to maximum accuracy
4. **Monitor File Size**: Detailed output can be GB+
5. **Document Settings**: Track what settings were used

### Common Issues
1. **Non-convergence**: Too few iterations or too large timestep
2. **Slow Runs**: Unnecessary accuracy for purpose
3. **Huge Files**: Timestep output for annual runs
4. **Inaccurate Peaks**: Too large timesteps
5. **Shadow Artifacts**: Infrequent calculations