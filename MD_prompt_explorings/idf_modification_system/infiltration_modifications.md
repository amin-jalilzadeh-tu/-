# Infiltration Modifications System

## Overview
The infiltration modification system handles air leakage parameters in EnergyPlus IDF files. Infiltration represents uncontrolled air exchange between the building interior and exterior, significantly impacting heating and cooling loads. This system allows modeling of various air sealing improvements and construction standards.

## Modified Object Types
- `ZONEINFILTRATION:DESIGNFLOWRATE` - Primary infiltration modeling object
- `ZONEINFILTRATION:EFFECTIVELEAKAGEAREA` - Effective leakage area method
- `ZONEINFILTRATION:FLOWCOEFFICIENT` - Flow coefficient method

## Parameters Modified

### ZONEINFILTRATION:DESIGNFLOWRATE Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `design_flow_rate` | Design Flow Rate | 4 | float | m³/s | - | infiltration_loads |
| `flow_per_zone_area` | Flow per Zone Floor Area | 5 | float | m³/s-m² | 0.0-0.01 | infiltration_loads |
| `flow_per_exterior_area` | Flow per Exterior Surface Area | 6 | float | m³/s-m² | 0.0-0.01 | infiltration_loads |
| `air_changes_per_hour` | Air Changes per Hour | 7 | float | 1/hr | 0.0-5.0 | infiltration_loads |
| `constant_coefficient` | Constant Term Coefficient | 8 | float | - | 0.0-1.0 | infiltration_model |
| `temperature_coefficient` | Temperature Term Coefficient | 9 | float | - | 0.0-0.05 | infiltration_model |
| `velocity_coefficient` | Velocity Term Coefficient | 10 | float | - | 0.0-0.5 | infiltration_model |
| `velocity_squared_coefficient` | Velocity Squared Term Coefficient | 11 | float | - | 0.0-0.1 | infiltration_model |

### Infiltration Model Coefficients
The actual infiltration rate is calculated as:
```
Infiltration = (DesignFlowRate) × [A + B×|Tzone-Toutdoor| + C×WindSpeed + D×WindSpeed²]
```
Where A, B, C, D are the coefficients defined above.

## Modification Strategies

### 1. Air Sealing (`air_sealing`)
- **Purpose**: Simulate general air sealing improvements
- **Modifications**:
  - Reduces infiltration rates by 20-40%
  - Maximum reduction capped at 90% to maintain minimum ventilation
  - Applied based on calculation method:
    - Flow/Zone: Modifies Design Flow Rate
    - Flow/Area: Modifies Flow per Zone Floor Area
    - AirChanges/Hour: Modifies Air Changes per Hour
  - Maintains proportional relationships

### 2. Tight Construction (`tight_construction`)
- **Purpose**: Apply tight construction standards
- **Modifications**:
  - Sets Air Changes per Hour to 0.1-0.3 ACH
  - Reduces Constant Term Coefficient by 50%
  - Represents modern construction techniques:
    - Continuous air barriers
    - Sealed penetrations
    - Quality construction practices
  - Typical of energy-efficient new construction

### 3. Passive House Standard (`passive_house`)
- **Purpose**: Apply Passive House infiltration requirements
- **Modifications**:
  - Sets Air Changes per Hour to 0.05 ACH
    - Based on 0.6 ACH at 50 Pa pressure test
    - Converted to natural conditions
  - Sets very low coefficients:
    - Constant Term: 0.1
    - Temperature Term: 0.001
    - Velocity Term: 0.001
    - Velocity Squared Term: 0.0001
  - Represents ultra-tight construction with:
    - Meticulous air sealing
    - Continuous air barrier
    - Certified blower door testing

## Process Flow

### 1. Parameter Identification
```
Infiltration Object → Identify Calculation Method (Field 3)
                   → Locate Active Flow Parameter
                   → Find Coefficient Parameters
```

### 2. Strategy Application
```
Current Values → Apply Strategy Rules → New Values
               → Validate Ranges
               → Update Parameters
               → Create Modification Records
```

### 3. Calculation Method Logic
- **Flow/Zone**: Direct flow rate in m³/s
- **Flow/Area**: Flow per unit floor area
- **Flow/ExteriorArea**: Flow per unit exterior surface area
- **AirChanges/Hour**: Complete air volume changes per hour

## Integration Notes

### Relationship with Other Systems
- **Ventilation**: Infiltration affects total outdoor air
- **HVAC**: Infiltration impacts heating/cooling loads
- **Schedules**: May vary by time (though coefficients handle this)
- **Building Envelope**: Tightness depends on construction quality

### Common Use Cases
1. **Existing Building Retrofits**: Air sealing improvements
2. **New Construction**: Meeting energy codes
3. **High-Performance Buildings**: Passive House certification
4. **Climate Studies**: Impact of infiltration on energy use

### Performance Impact
- **Heating Energy**: Major reduction (20-80%)
- **Cooling Energy**: Moderate reduction (10-40%)
- **Peak Loads**: Significant reduction in extreme weather
- **Indoor Air Quality**: May require mechanical ventilation

## Technical Implementation Details

### Field Index Reference
- Field 0: Name
- Field 1: Zone or Zone List Name
- Field 2: Schedule Name
- Field 3: Design Flow Rate Calculation Method
- Fields 4-7: Flow rate parameters (only one active)
- Fields 8-11: Model coefficients

### Validation Requirements
- Ensure minimum infiltration for indoor air quality
- Verify calculation method matches modified parameter
- Check coefficient values remain in valid ranges
- Validate total of all heat fractions ≤ 1.0

### Building Standards Reference
| Standard | Typical ACH | Notes |
|----------|------------|--------|
| Old/Leaky | 1.0-3.0 | Pre-1980s construction |
| Standard | 0.5-1.0 | Current code minimum |
| Energy Efficient | 0.2-0.5 | Above-code construction |
| Tight Construction | 0.1-0.3 | High-performance |
| Passive House | 0.05 | Ultra-tight standard |

### Error Handling
- Prevent reduction below minimum safe levels
- Handle missing calculation method gracefully
- Validate numeric values before modification
- Log all modifications for debugging

### Special Considerations
1. **Minimum Ventilation**: Never reduce to zero
2. **Pressure Effects**: Coefficients model stack and wind effects
3. **Seasonal Variation**: Temperature coefficient captures seasonal changes
4. **Building Height**: Wind coefficients more important for tall buildings