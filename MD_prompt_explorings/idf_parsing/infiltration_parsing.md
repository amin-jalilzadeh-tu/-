# Infiltration Parsing Documentation

## Overview
The infiltration parsing module extracts uncontrolled air leakage data from IDF files and SQL simulation results. This includes design flow rates, leakage areas, and flow coefficients for modeling air infiltration through the building envelope.

## IDF Objects Parsed

### 1. ZONEINFILTRATION:DESIGNFLOWRATE
Basic infiltration model using design flow rate.

**Parameters Extracted:**
- Infiltration Name
- Zone or Space Name
- Schedule Name
- Design Flow Rate Calculation Method:
  - `design_flow_rate`: Flow Rate (m³/s)
  - `flow_per_area`: Flow per Exterior Surface Area (m³/s-m²)
  - `air_changes`: Air Changes per Hour (ACH)
  - Flow per Exterior Wall Area (m³/s-m²)
- `constant_coef`: Constant Term Coefficient (A)
- `temp_coef`: Temperature Term Coefficient (B)
- `velocity_coef`: Velocity Term Coefficient (C)
- `velocity_squared_coef`: Velocity Squared Term Coefficient (D)

**Infiltration Equation:**
```
Infiltration = (Design Flow Rate) × (Schedule) × [A + B|Tzone - Toutdoor| + C(WindSpeed) + D(WindSpeed²)]
```

### 2. ZONEINFILTRATION:EFFECTIVELEAKAGEAREA
Sherman-Grimsrud infiltration model.

**Parameters Extracted:**
- Infiltration Name
- Zone Name
- Schedule Name
- Effective Air Leakage Area (m²)
- Stack Coefficient
- Wind Coefficient

**Model Equation:**
```
Infiltration = (Schedule) × √[(Stack Coefficient × |Tzone - Toutdoor|) + (Wind Coefficient × WindSpeed²)]
```

### 3. ZONEINFILTRATION:FLOWCOEFFICIENT
AIM-2 infiltration model.

**Parameters Extracted:**
- Infiltration Name
- Zone Name
- Schedule Name
- Flow Coefficient (m³/s)
- Stack Coefficient
- Pressure Exponent
- Wind Coefficient
- Shelter Factor

### 4. Space Infiltration Objects
Equivalent to zone infiltration but applied at space level:

#### SPACEINFILTRATION:DESIGNFLOWRATE
#### SPACEINFILTRATION:EFFECTIVELEAKAGEAREA
#### SPACEINFILTRATION:FLOWCOEFFICIENT

Same parameters as zone equivalents but for individual spaces.

### 5. ZONEAIRBALANCE:OUTDOORAIR
Can also model infiltration effects when used with unbalanced systems.

**Parameters Extracted:**
- Zone Name
- Air Balance Method
- Induced Outdoor Air Due to Unbalanced Duct Leakage (m³/s)
- Induced Outdoor Air Schedule Name

## SQL Variables Extracted

1. **Zone Infiltration Sensible Heat Gain Energy** (J)
2. **Zone Infiltration Sensible Heat Loss Energy** (J)
3. **Zone Infiltration Latent Heat Gain Energy** (J)
4. **Zone Infiltration Latent Heat Loss Energy** (J)
5. **Zone Infiltration Total Heat Gain Energy** (J)
6. **Zone Infiltration Total Heat Loss Energy** (J)
7. **Zone Infiltration Current Density Volume Flow Rate** (m³/s)
8. **Zone Infiltration Standard Density Volume Flow Rate** (m³/s)
9. **Zone Infiltration Mass Flow Rate** (kg/s)
10. **Zone Infiltration Air Change Rate** (ACH)
11. **Zone Infiltration Volume** (m³)
12. **AFN Zone Infiltration Sensible Heat Gain Energy** (J) - if using AirflowNetwork
13. **AFN Zone Infiltration Sensible Heat Loss Energy** (J) - if using AirflowNetwork

## Key Metrics Calculated

1. **Average Infiltration Rate**
   - Annual average air change rate due to infiltration
   - Units: ACH or m³/s

2. **Infiltration Energy Impact**
   - Total sensible and latent energy loss/gain from infiltration
   - Units: kWh

3. **Peak Infiltration**
   - Maximum infiltration rate and when it occurs
   - Typically during extreme temperature differences or high winds

4. **Effective Leakage Area**
   - Total equivalent leakage area at reference pressure
   - Units: m² at specified pressure difference

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── infiltration.parquet
```

**Columns in infiltration.parquet:**
- building_id
- zone_name
- infiltration_model_type
- object_name
- schedule_name
- design_flow_parameters
- model_coefficients (A, B, C, D)
- effective_leakage_area
- reference_conditions

### SQL Timeseries Output
```
parsed_data/
└── timeseries/
    └── base_all_daily.parquet (for base buildings)
    └── comparisons/
        └── comparison_{building_id}.parquet (for variants)
```

## Data Processing Notes

1. **Model Selection**: Different models suit different analysis needs:
   - DesignFlowRate: Simple, good for preliminary analysis
   - EffectiveLeakageArea: Based on blower door tests
   - FlowCoefficient: Most detailed, requires more inputs

2. **Weather Sensitivity**: Infiltration varies with temperature difference and wind speed.

3. **Building Pressure**: Infiltration affected by mechanical ventilation and stack effect.

4. **Scheduling**: Can model reduced infiltration during occupied hours due to pressurization.

5. **Surface Area Calculation**: "Exterior Surface Area" includes walls, roofs, and floors.

## Infiltration Modeling Approaches

### Constant Infiltration
- Fixed ACH value
- Simple but unrealistic
- Coefficients: A=1, B=C=D=0

### Temperature-Driven
- Stack effect dominant
- High-rise buildings
- Large B coefficient

### Wind-Driven
- Exposed locations
- Low-rise buildings
- Large C or D coefficients

### Combined Effects
- Most realistic
- All coefficients non-zero
- Varies with weather

## Typical Coefficient Values

### Residential Buildings
- A = 0.10 - 0.30
- B = 0.15 - 0.30
- C = 0.10 - 0.25
- D = 0.00 - 0.10

### Commercial Buildings
- A = 0.05 - 0.20
- B = 0.10 - 0.25
- C = 0.05 - 0.20
- D = 0.00 - 0.05

## Special Considerations

1. **Air Tightness Standards**: Modern codes require specific leakage rates (e.g., 3 ACH50 for Passive House).

2. **Blower Door Testing**: Effective leakage area derived from pressurization tests.

3. **Terrain Effects**: Wind exposure varies with building height and surroundings.

4. **Compartmentalization**: Multi-zone buildings have internal air leakage too.

5. **Seasonal Variation**: Some models account for changes in envelope tightness.

## Quality Checks

1. **Reasonable Rates**: Typical 0.1-0.5 ACH for new buildings, 0.5-2.0 ACH for older.

2. **Coefficient Sums**: For DesignFlowRate, coefficients typically sum to ~1.0.

3. **Energy Impact**: Infiltration often 20-40% of space conditioning load.

4. **Peak Conditions**: Check infiltration during design day conditions.

5. **Zone Pressure**: Excessive infiltration may indicate pressure imbalances.

## Integration with Other Systems

1. **Ventilation**: Mechanical ventilation affects building pressure and infiltration.

2. **Wind Pressure**: Detailed models use surface-specific wind pressure coefficients.

3. **Stack Effect**: Tall buildings need multi-zone infiltration modeling.

4. **Duct Leakage**: Return air leaks can induce additional infiltration.

5. **Exhaust Systems**: Kitchen/bathroom exhausts increase infiltration.