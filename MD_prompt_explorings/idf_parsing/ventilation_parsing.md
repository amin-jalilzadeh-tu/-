# Ventilation Parsing Documentation

## Overview
The ventilation parsing module extracts mechanical and natural ventilation data from IDF files and SQL simulation results. This includes outdoor air requirements, ventilation controls, and air distribution systems.

## IDF Objects Parsed

### 1. Zone Ventilation

#### ZONEVENTILATION:DESIGNFLOWRATE
Simple ventilation model for zones.

**Parameters Extracted:**
- Ventilation Name
- Zone Name
- Schedule Name
- Design Flow Rate Calculation Method:
  - `design_flow_rate`: Flow Rate (m³/s)
  - `flow_per_area`: Flow Rate per Zone Floor Area (m³/s-m²)
  - `flow_per_person`: Flow Rate per Person (m³/s-person)
  - `air_changes`: Air Changes per Hour (ACH)
- `ventilation_type`: Ventilation Type (Natural, Exhaust, Intake, Balanced)
- `fan_efficiency`: Fan Total Efficiency
- Fan Pressure Rise (Pa)
- `minimum_outdoor_air`: Minimum Indoor Temperature (°C)
- Maximum Indoor Temperature (°C)
- Delta Temperature (°C)
- Minimum Outdoor Temperature (°C)
- Maximum Outdoor Temperature (°C)
- Maximum Wind Speed (m/s)

#### ZONEVENTILATION:WINDANDSTACKDRIVENFLOW
Natural ventilation through openings.

**Parameters Extracted:**
- Ventilation Name
- Zone Name
- Opening Area (m²)
- Opening Schedule Name
- Opening Effectiveness
- Effective Angle (degrees)
- Height Difference (m)
- Discharge Coefficient for Opening
- Minimum Indoor Temperature (°C)
- Maximum Indoor Temperature (°C)
- Delta Temperature (°C)
- Minimum Outdoor Temperature (°C)
- Maximum Outdoor Temperature (°C)
- Maximum Wind Speed (m/s)

### 2. Zone Air Balance

#### ZONEAIRBALANCE:OUTDOORAIR
Balanced outdoor air ventilation.

**Parameters Extracted:**
- Zone Name
- Air Balance Method
- Induced Outdoor Air Due to Unbalanced Duct Leakage (m³/s)
- Induced Outdoor Air Schedule Name

### 3. Zone Mixing

#### ZONEMIXING
Air transfer from one zone to another.

**Parameters Extracted:**
- Mixing Name
- Zone Name
- Schedule Name
- Design Flow Rate Calculation Method
- Source Zone Name
- Delta Temperature (°C)
- Delta Temperature Schedule Name
- Minimum Source Zone Temperature Schedule Name
- Maximum Source Zone Temperature Schedule Name
- Minimum Outdoor Temperature Schedule Name
- Maximum Outdoor Temperature Schedule Name

#### ZONECROSSMIXING
Bi-directional air transfer between zones.

**Parameters Extracted:**
- Cross Mixing Name
- Zone Name
- Schedule Name
- Design Flow Rate Calculation Method
- Source Zone Name
- Delta Temperature (°C)

### 4. Design Specifications

#### DESIGNSPECIFICATION:OUTDOORAIR
Outdoor air requirements specification.

**Parameters Extracted:**
- Specification Name
- Outdoor Air Method (Flow/Person, Flow/Area, Flow/Zone, Sum, Maximum)
- `flow_per_person`: Outdoor Air Flow per Person (m³/s-person)
- `flow_per_area`: Outdoor Air Flow per Zone Floor Area (m³/s-m²)
- Outdoor Air Flow per Zone (m³/s)
- Outdoor Air Flow Air Changes per Hour
- Schedule Name

#### DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION
Air distribution effectiveness.

**Parameters Extracted:**
- Distribution Name
- Zone Air Distribution Effectiveness in Cooling Mode
- Zone Air Distribution Effectiveness in Heating Mode
- Zone Air Distribution Effectiveness Schedule Name
- Zone Secondary Recirculation Fraction

### 5. Mechanical Ventilation Control

#### CONTROLLER:MECHANICALVENTILATION
Demand controlled ventilation.

**Parameters Extracted:**
- Controller Name
- Availability Schedule Name
- Demand Controlled Ventilation (Yes/No)
- System Outdoor Air Method
- Zone Maximum Outdoor Air Fraction
- Zone/Space Names and their Design Specifications

#### CONTROLLER:OUTDOORAIR
Outdoor air economizer control.

**Parameters Extracted:**
- Controller Name
- Relief Air Outlet Node Name
- Return Air Node Name
- Mixed Air Node Name
- Actuator Node Name
- `minimum_outdoor_air`: Minimum Outdoor Air Flow Rate (m³/s)
- Maximum Outdoor Air Flow Rate (m³/s)
- Economizer Control Type
- Economizer Control Action Type
- Economizer Maximum/Minimum Limit Temperatures
- Electronic Enthalpy Limit Curve Name
- Economizer Minimum Limit Dewpoint Temperature
- Supply Air Flow Rate When No Cooling or Heating Needed

### 6. Air Mixing Components

#### OUTDOORAIR:MIXER
Mixing box for outdoor and return air.

**Parameters Extracted:**
- Mixer Name
- Mixed Air Node Name
- Outdoor Air Stream Node Name
- Relief Air Stream Node Name
- Return Air Stream Node Name

#### OUTDOORAIR:NODE
Outdoor air inlet conditions.

**Parameters Extracted:**
- Node Name
- Height Above Ground (m)
- Drybulb Temperature Schedule Name
- Wetbulb Temperature Schedule Name
- Wind Speed Schedule Name
- Wind Direction Schedule Name

### 7. Air Flow Network (if used)

#### AIRFLOWNETWORK:SIMULATIONCONTROL
AFN simulation parameters.

**Parameters Extracted:**
- AFN Control
- Wind Pressure Coefficient Type
- Building Type
- Maximum Number of Iterations
- Convergence Tolerance

## SQL Variables Extracted

1. **Zone Ventilation Sensible Heat Gain Energy** (J)
2. **Zone Ventilation Sensible Heat Loss Energy** (J)
3. **Zone Ventilation Latent Heat Gain Energy** (J)
4. **Zone Ventilation Latent Heat Loss Energy** (J)
5. **Zone Ventilation Total Heat Gain Energy** (J)
6. **Zone Ventilation Total Heat Loss Energy** (J)
7. **Zone Ventilation Current Density Volume Flow Rate** (m³/s)
8. **Zone Ventilation Standard Density Volume Flow Rate** (m³/s)
9. **Zone Ventilation Mass Flow Rate** (kg/s)
10. **Zone Ventilation Air Change Rate** (ACH)
11. **Zone Ventilation Fan Electricity Energy** (J)
12. **Zone Mechanical Ventilation Current Density Volume Flow Rate** (m³/s)
13. **Zone Mechanical Ventilation Standard Density Volume Flow Rate** (m³/s)
14. **Zone Mechanical Ventilation Mass Flow Rate** (kg/s)
15. **Zone Mechanical Ventilation Air Change Rate** (ACH)

## Key Metrics Calculated

1. **Average Ventilation Rate**
   - Time-weighted average outdoor air flow
   - Units: m³/s or ACH

2. **Ventilation Energy Loss**
   - Sensible and latent energy impact of ventilation
   - Units: kWh

3. **Air Change Effectiveness**
   - Ratio of ventilation air reaching breathing zone
   - Units: fraction (0-1)

4. **Outdoor Air Fraction**
   - Percentage of supply air that is outdoor air
   - Units: %

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── ventilation.parquet
```

**Columns in ventilation.parquet:**
- building_id
- zone_name
- ventilation_type
- object_name
- control_method
- design_flow_specifications
- temperature_controls
- schedule_name
- fan_properties
- outdoor_air_requirements

### SQL Timeseries Output
Ventilation-related variables in timeseries files include air flow rates and associated energy impacts.

## Data Processing Notes

1. **Flow Rate Methods**: Multiple ways to specify flow (absolute, per area, per person, ACH).

2. **Control Conditions**: Temperature and wind speed limits control natural ventilation.

3. **Fan Energy**: Only simple fan model - detailed fan energy in HVAC systems.

4. **Heat Recovery**: Not modeled in simple ventilation objects.

5. **Demand Control**: DCV adjusts ventilation based on occupancy or CO2.

## Ventilation Strategies

### Natural Ventilation
- Wind-driven flow
- Stack effect (buoyancy)
- Controlled by temperature and wind conditions

### Mechanical Ventilation
- Constant volume
- Variable volume with controls
- Energy recovery ventilation

### Hybrid Ventilation
- Combination of natural and mechanical
- Mode switching based on conditions

## Special Considerations

1. **Code Requirements**: Minimum outdoor air often driven by ASHRAE 62.1 or local codes.

2. **IAQ Concerns**: Ventilation rates affect indoor air quality beyond just temperature.

3. **Infiltration Interaction**: Mechanical ventilation affects building pressure and infiltration.

4. **Economizer Operation**: "Free cooling" when outdoor conditions favorable.

5. **Wind Data**: Natural ventilation highly sensitive to local wind patterns.

## Quality Checks

1. **Minimum Rates**: Verify meets code requirements (typically 0.3-0.5 ACH residential, higher commercial).

2. **Temperature Limits**: Natural ventilation controls should prevent overcooling.

3. **Fan Power**: Check fan efficiency and pressure rise are reasonable.

4. **Schedule Alignment**: Ventilation schedules should match occupancy patterns.

5. **Zone Pressure**: Balanced ventilation maintains neutral pressure.