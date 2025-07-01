# DHW (Domestic Hot Water) Parsing Documentation

## Overview
The DHW parsing module extracts domestic hot water system data from IDF files and SQL simulation results. This includes water heaters, water use equipment, pumps, pipes, and plant loops.

## IDF Objects Parsed

### 1. WATERHEATER:MIXED
Mixed (single node) water heater model.

**Parameters Extracted:**
- `tank_volume`: Tank Volume (m³)
- `heater_capacity`: Heater Maximum Capacity (W)
- `setpoint_schedule`: Setpoint Temperature Schedule Name
- `thermal_efficiency`: Heater Thermal Efficiency (0-1)
- `fuel_type`: Heater Fuel Type
- Deadband Temperature Difference (°C)
- Ambient Temperature Zone Name
- Heat Loss Coefficient to Ambient (W/K)
- Use Side Inlet/Outlet Node Names
- Source Side Inlet/Outlet Node Names

### 2. WATERHEATER:STRATIFIED
Stratified (multi-node) water heater model.

**Parameters Extracted:**
- Tank Volume (m³)
- Tank Height (m)
- Tank Shape
- Maximum Heater Capacity (W)
- Heater Priority Control
- Number of Nodes
- Heater Thermal Efficiency
- Off Cycle Parasitic Fuel Type
- Node Additional Loss Coefficients

### 3. WATERUSE:EQUIPMENT
Equipment that uses hot water.

**Parameters Extracted:**
- `flow_rate`: Peak Flow Rate (m³/s)
- End-Use Subcategory
- Hot Water Supply Temperature Schedule
- Target Temperature Schedule
- Sensible Fraction Schedule
- Latent Fraction Schedule
- Flow Rate Fraction Schedule

### 4. WATERUSE:CONNECTIONS
Connections between water use equipment and supply.

**Parameters Extracted:**
- Inlet Node Name
- Outlet Node Name
- Hot Water Supply Temperature Schedule
- Cold Water Supply Temperature Schedule
- Number of Water Use Equipment objects

### 5. PLANTLOOP
Plant loop definitions for hot water systems.

**Parameters Extracted:**
- Loop Name
- Fluid Type
- Maximum/Minimum Loop Temperature (°C)
- Maximum/Minimum Loop Flow Rate (m³/s)
- Plant Equipment Operation Scheme

### 6. Pumps
- **PUMP:VARIABLESPEED**
  - Rated Flow Rate (m³/s)
  - Rated Pump Head (Pa)
  - Rated Power Consumption (W)
  - Motor Efficiency
  - Pump Control Type
  
- **PUMP:CONSTANTSPEED**
  - Rated Flow Rate (m³/s)
  - Rated Pump Head (Pa)
  - Rated Power Consumption (W)
  - Motor Efficiency

### 7. Pipes
- **PIPE:ADIABATIC**: No heat loss pipes
- **PIPE:INDOOR**: Indoor pipes with heat loss
- **PIPE:OUTDOOR**: Outdoor pipes with heat loss

**Parameters Extracted:**
- Pipe Inside/Outside Diameter (m)
- Pipe Length (m)
- Pipe Thermal Conductivity (W/m-K)
- Pipe Heat Loss Coefficient (W/m²-K)

## SQL Variables Extracted

The following variables are extracted from SQL simulation results:

1. **Water Heater Heating Energy** (J)
2. **Water Heater Heating Rate** (W)
3. **Water Heater Tank Temperature** (°C)
4. **Water Heater Heat Loss Energy** (J)
5. **Water Heater Heat Loss Rate** (W)
6. **Water Use Equipment Hot Water Volume Flow Rate** (m³/s)
7. **Water Use Equipment Hot Water Volume** (m³)
8. **Water Use Equipment Total Volume Flow Rate** (m³/s)
9. **Water Use Equipment Mains Water Volume** (m³)

## Key Metrics Calculated

1. **Total Hot Water Use**
   - Sum of all hot water consumption across equipment
   - Units: m³ or gallons

2. **Water Heating Energy**
   - Total energy used for water heating
   - Units: kWh

3. **System Efficiency**
   - Ratio of useful hot water energy to input energy
   - Accounts for tank losses and distribution losses

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── dhw.parquet
```

**Columns in dhw.parquet:**
- building_id
- zone_name (if applicable)
- object_type
- object_name
- parameter_name
- parameter_value
- units
- tank_specifications (volume, capacity, efficiency)
- flow_rates
- temperature_setpoints
- fuel_type
- node_connections

### SQL Timeseries Output
```
parsed_data/
└── timeseries/
    └── base_all_daily.parquet (for base buildings)
    └── comparisons/
        └── comparison_{building_id}.parquet (for variants)
```

**DHW-related columns:**
- Date columns (YYYY-MM-DD format)
- building_id
- VariableName (DHW-related variables)
- KeyValue (water heater/equipment names)
- Units
- Daily aggregated values

## Data Processing Notes

1. **Plant Loop Integration**: DHW systems are often part of larger plant loops, requiring cross-reference with HVAC systems.

2. **Temperature Schedules**: Multiple temperature schedules control setpoints and supply temperatures.

3. **Flow Rate Variations**: Flow rates can vary based on schedules and demand patterns.

4. **Energy Tracking**: Both fuel input and heat loss are tracked for efficiency calculations.

5. **Multi-Zone Systems**: Some DHW systems serve multiple zones and require proper allocation.

6. **Recirculation Loops**: Some systems include recirculation pumps and associated losses.

## Special Considerations

1. **Fuel Types**: Different fuel types (electricity, natural gas, etc.) require different efficiency calculations.

2. **Solar Water Heating**: Solar-assisted systems have additional components not listed here.

3. **Heat Recovery**: Some systems include heat recovery from other sources.

4. **Tankless Systems**: Instantaneous water heaters have different parameters than storage systems.

5. **Distribution Losses**: Pipe heat losses can significantly impact system efficiency.