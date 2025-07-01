# HVAC Parsing Documentation

## Overview
The HVAC parsing module extracts heating, ventilation, and air conditioning system data from IDF files and SQL simulation results. This includes zone equipment, air loops, coils, fans, thermostats, and control systems.

## IDF Objects Parsed

### 1. Zone HVAC Equipment

#### ZONEHVAC:IDEALLOADSAIRSYSTEM
Ideal air system for load calculations.

**Parameters Extracted:**
- `cooling_capacity`: Maximum Total Cooling Capacity (W)
- `heating_capacity`: Maximum Sensible Heating Capacity (W)
- Cooling/Heating Limit types
- Dehumidification/Humidification Control Types
- Outdoor Air Economizer Type
- Heat Recovery Type
- Sensible/Latent Heat Recovery Effectiveness

#### ZONEHVAC:EQUIPMENTLIST
List of equipment serving a zone.

**Parameters Extracted:**
- Zone Name
- Equipment Object Type and Name
- Cooling/Heating Sequence
- Sequential Cooling/Heating Load Fractions

#### ZONEHVAC:EQUIPMENTCONNECTIONS
Zone air distribution connections.

**Parameters Extracted:**
- Zone Name
- Zone Air Inlet/Outlet/Exhaust Node Names
- Zone Return Air Node Name

### 2. Cooling Coils

#### COIL:COOLING:DX:SINGLESPEED
Single-speed DX cooling coil.

**Parameters Extracted:**
- Gross Rated Total Cooling Capacity (W)
- Gross Rated Sensible Heat Ratio
- `cooling_cop`: Gross Rated Cooling COP
- Rated Air Flow Rate (m³/s)
- Rated Evaporator Fan Power Per Volume Flow Rate (W/(m³/s))

#### COIL:COOLING:DX:TWOSPEED
Two-speed DX cooling coil.

**Parameters Extracted:**
- High/Low Speed Gross Rated Total Cooling Capacity (W)
- High/Low Speed Gross Rated COP
- High/Low Speed Rated Air Flow Rate (m³/s)

#### COIL:COOLING:DX:VARIABLESPEED
Variable-speed DX cooling coil.

**Parameters Extracted:**
- Speed Level Data (up to 10 speeds)
- Reference Unit Gross Rated Total Cooling Capacity (W)
- Reference Unit Rated Air Flow Rate (m³/s)

### 3. Heating Coils

#### COIL:HEATING:ELECTRIC
Electric heating coil.

**Parameters Extracted:**
- Nominal Capacity (W)
- `heating_efficiency`: Efficiency (default 1.0)

#### COIL:HEATING:GAS
Gas heating coil.

**Parameters Extracted:**
- Nominal Capacity (W)
- `heating_efficiency`: Gas Burner Efficiency
- Parasitic Electric Load (W)
- Parasitic Gas Load (W)

#### COIL:HEATING:WATER
Hot water heating coil.

**Parameters Extracted:**
- U-Factor Times Area Value (W/K)
- Maximum Water Flow Rate (m³/s)
- Water Inlet/Outlet Node Names

### 4. Fans

#### FAN:SYSTEMMODEL
System model fan with detailed performance curves.

**Parameters Extracted:**
- `design_supply_air_flow`: Design Maximum Air Flow Rate (m³/s)
- Design Pressure Rise (Pa)
- `fan_efficiency`: Fan Total Efficiency
- Motor Efficiency
- Motor In Air Stream Fraction
- Fan Power Coefficients

#### FAN:CONSTANTVOLUME
Constant volume fan.

**Parameters Extracted:**
- Maximum Flow Rate (m³/s)
- Pressure Rise (Pa)
- Fan Total Efficiency
- Motor Efficiency

#### FAN:VARIABLEVOLUME
Variable volume fan.

**Parameters Extracted:**
- Maximum Flow Rate (m³/s)
- Pressure Rise (Pa)
- Fan Total Efficiency
- Motor Efficiency
- Fan Power Coefficients

### 5. Thermostats and Controls

#### THERMOSTATSETPOINT:DUALSETPOINT
Dual setpoint thermostat.

**Parameters Extracted:**
- `heating_setpoint`: Heating Setpoint Temperature Schedule Name
- `cooling_setpoint`: Cooling Setpoint Temperature Schedule Name

#### ZONECONTROL:THERMOSTAT
Zone thermostat control.

**Parameters Extracted:**
- Zone Name
- Control Type Schedule Name
- Thermostat Type and Name

### 6. Air Loops and Systems

#### AIRLOOPHVAC
Main air loop definition.

**Parameters Extracted:**
- Design Supply Air Flow Rate (m³/s)
- Controller List Name
- Availability Manager List Name
- Supply/Demand Side configurations

#### CONTROLLER:OUTDOORAIR
Outdoor air controller.

**Parameters Extracted:**
- `minimum_outdoor_air`: Minimum Outdoor Air Flow Rate (m³/s)
- Maximum Outdoor Air Flow Rate (m³/s)
- Economizer Control Type
- Economizer Maximum/Minimum Limit Temperatures

### 7. Sizing

#### SIZING:ZONE
Zone sizing parameters.

**Parameters Extracted:**
- Zone Cooling/Heating Design Supply Air Temperatures (°C)
- Zone Cooling/Heating Design Supply Air Humidity Ratios
- Design Outdoor Air Flow Rate (m³/s)
- Cooling/Heating Design Air Flow Methods

#### SIZING:SYSTEM
System sizing parameters.

**Parameters Extracted:**
- Type of Load to Size On
- Design Outdoor Air Flow Rate (m³/s)
- Central Cooling/Heating Design Supply Air Temperatures

## SQL Variables Extracted

1. **Zone Air System Sensible Cooling Rate** (W)
2. **Zone Air System Sensible Cooling Energy** (J)
3. **Zone Air System Sensible Heating Rate** (W)
4. **Zone Air System Sensible Heating Energy** (J)
5. **Zone Air System Total Cooling Rate** (W)
6. **Zone Air System Total Cooling Energy** (J)
7. **Zone Air System Total Heating Rate** (W)
8. **Zone Air System Total Heating Energy** (J)
9. **Cooling Coil Total Cooling Rate** (W)
10. **Heating Coil Heating Rate** (W)
11. **Fan Electricity Rate** (W)
12. **Fan Electricity Energy** (J)
13. **System Node Temperature** (°C)
14. **System Node Mass Flow Rate** (kg/s)
15. **Zone Mean Air Temperature** (°C)
16. **Zone Thermostat Cooling Setpoint Temperature** (°C)
17. **Zone Thermostat Heating Setpoint Temperature** (°C)
18. **Zone Predicted Sensible Load to Cooling Setpoint Heat Transfer Rate** (W)
19. **Zone Predicted Sensible Load to Heating Setpoint Heat Transfer Rate** (W)

## Key Metrics Calculated

1. **Total Cooling Load**
   - Sum of sensible and latent cooling loads
   - Units: kWh

2. **Total Heating Load**
   - Total heating energy consumption
   - Units: kWh

3. **System COP**
   - Coefficient of Performance for cooling/heating
   - Ratio of useful energy to input energy

4. **Unmet Hours**
   - Hours when zone temperature is outside setpoint range
   - Units: hours

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        ├── hvac_equipment.parquet
        ├── hvac_systems.parquet
        └── hvac_thermostats.parquet
```

**Columns include:**
- building_id
- zone_name
- object_type
- object_name
- equipment_specifications
- capacity_ratings
- efficiency_values
- control_parameters
- node_connections
- setpoint_schedules

### SQL Timeseries Output
```
parsed_data/
└── timeseries/
    └── base_all_daily.parquet (for base buildings)
    └── comparisons/
        └── comparison_{building_id}.parquet (for variants)
```

## Data Processing Notes

1. **Node Connections**: HVAC systems use node names to connect components - these must be tracked for system topology.

2. **Capacity Auto-sizing**: Many capacities can be autosized by EnergyPlus - actual values appear in SQL results.

3. **Control Hierarchies**: Multiple control layers (thermostats, setpoint managers, availability managers).

4. **Performance Curves**: Many components use performance curves that modify rated performance.

5. **Multi-Zone Systems**: Central systems serving multiple zones require careful allocation of energy use.

## Special Considerations

1. **Ideal Loads Systems**: Used for load calculations but don't represent real equipment.

2. **Part Load Performance**: Actual efficiency varies with load - tracked through performance curves.

3. **Simultaneous Heating/Cooling**: Some systems can provide both - requires careful accounting.

4. **Outdoor Air Integration**: Ventilation requirements affect HVAC energy consumption.

5. **Control Strategies**: Advanced controls (economizers, demand control ventilation) significantly impact performance.