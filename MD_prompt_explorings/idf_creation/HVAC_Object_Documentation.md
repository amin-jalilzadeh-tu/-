# HVAC Object Documentation

## Overview
The HVAC module creates Ideal Loads Air System objects in EnergyPlus IDF files to simulate heating, ventilation, and air conditioning. It uses a comprehensive lookup system with building type, age, and scenario-specific parameters, creating thermostats, schedules, and zone equipment connections.

## Input Data

### Building Row Data
- **ogc_fid**: Unique building identifier
- **building_function**: "residential" or "non_residential"
- **residential_type**: Specific type (e.g., "Corner House", "Apartment")
- **non_residential_type**: Specific type (e.g., "Office Function", "Healthcare Function")
- **age_range**: Building construction period (e.g., "1992 - 2005", "2015 and later")
- **scenario**: Simulation scenario name

### User Configuration (Optional)
- Parameter overrides from user_config_hvac
- Can override individual parameters or entire schedules
- Supports fixed values or min/max range modifications

### Control Parameters
- **calibration_stage**: "pre_calibration" or "post_calibration"
- **strategy**: "A" (midpoint), "B" (random), or default (minimum)
- **random_seed**: For reproducible random values

## Process Flow

### 1. Lookup Structure (hvac_lookup.py)

Multi-level hierarchy:
```
calibration_stage
  └── scenario
        └── building_function
              └── building_subtype
                    └── age_range
                          └── parameters
```

### 2. Parameters Stored

#### Temperature Setpoints (°C)
- **heating_day_setpoint_range**: Daytime heating setpoint (typical: 19-21°C)
- **heating_night_setpoint_range**: Nighttime heating setpoint (typical: 16-18°C)
- **cooling_day_setpoint_range**: Daytime cooling setpoint (typical: 24-26°C)
- **cooling_night_setpoint_range**: Nighttime cooling setpoint (typical: 26-28°C)

#### Supply Air Temperatures (°C)
- **max_heating_supply_air_temp_range**: Maximum heating supply air (typical: 40-50°C)
- **min_cooling_supply_air_temp_range**: Minimum cooling supply air (typical: 12-14°C)

#### Schedule Details
Complex schedule patterns for:
- **hvac_availability**: System on/off times
- **setpoints**: Day/night switching times
- **occupancy_schedule**: Building occupancy patterns

### 3. Parameter Assignment (assign_hvac_values.py)

1. **Navigate Lookup Table**: Find parameters based on building characteristics
2. **Apply User Overrides**: 
   - Fixed values: `{"param_name": "heating_day_setpoint", "fixed_value": 20.5}`
   - Range modifications: `{"param_name": "heating_day_setpoint", "min_val": 19, "max_val": 22}`
   - Schedule overrides: `{"param_name": "hvac_availability_weekday", "override_blocks": [...]}`
3. **Select Values**:
   - Strategy "A": value = (min + max) / 2
   - Strategy "B": value = random.uniform(min, max)
   - Default: value = min

### 4. Schedule Creation (schedule_creation.py)

Creates SCHEDULE:COMPACT objects:

#### HVAC Availability Schedule
Controls when system operates:
```
Schedule:Compact,
    HVACAvailSchedule_ZoneName,
    ControlType,
    Through: 12/31,
    For: Weekdays,
    Until: 07:00, 0,
    Until: 19:00, 1,
    Until: 24:00, 0,
    For: AllOtherDays,
    Until: 24:00, 0;
```

#### Heating/Cooling Setpoint Schedules
Temperature setpoints with day/night variations:
```
Schedule:Compact,
    HeatingSetpointSchedule_ZoneName,
    Temperature,
    Through: 12/31,
    For: AllDays,
    Until: 07:00, 18.0,  ! Night setpoint
    Until: 19:00, 20.0,  ! Day setpoint
    Until: 24:00, 18.0;  ! Night setpoint
```

### 5. IDF Object Creation (custom_hvac.py)

For each zone, creates:

#### Control Infrastructure
1. **SCHEDULETYPELIMITS**: Define valid ranges for schedules
2. **SCHEDULE:COMPACT**: Multiple schedules for control and setpoints

#### Thermostat Objects
3. **ZONECONTROL:THERMOSTAT**
   ```
   Zone_or_ZoneList_Name: ZoneName
   Control_Type_Schedule_Name: Zone_Control_Type_Sched
   Control_1_Name: DualSetpoint_ZoneName
   ```

4. **THERMOSTATSETPOINT:DUALSETPOINT**
   ```
   Heating_Setpoint_Temperature_Schedule_Name: HeatingSetpointSchedule_ZoneName
   Cooling_Setpoint_Temperature_Schedule_Name: CoolingSetpointSchedule_ZoneName
   ```

#### Equipment Connections
5. **ZONEHVAC:EQUIPMENTCONNECTIONS**
   ```
   Zone_Name: ZoneName
   Zone_Air_Inlet_Node_Name: ZoneName Supply Inlet
   Zone_Air_Node_Name: ZoneName Zone Air Node
   Zone_Return_Air_Node_Name: ZoneName Return Outlet
   ```

6. **ZONEHVAC:EQUIPMENTLIST**
   ```
   Zone_Equipment_1_Name: IdealLoadsSystem_ZoneName
   Zone_Equipment_1_Cooling_Sequence: 1
   Zone_Equipment_1_Heating_Sequence: 1
   ```

#### Ideal Loads System
7. **ZONEHVAC:IDEALLOADSAIRSYSTEM**
   ```
   Name: IdealLoadsSystem_ZoneName
   Availability_Schedule_Name: HVACAvailSchedule_ZoneName
   Zone_Supply_Air_Node_Name: ZoneName Supply Inlet
   Maximum_Heating_Supply_Air_Temperature: [from lookup]
   Minimum_Cooling_Supply_Air_Temperature: [from lookup]
   Maximum_Heating_Supply_Air_Humidity_Ratio: 0.0156
   Minimum_Cooling_Supply_Air_Humidity_Ratio: 0.0077
   Heating_Limit: NoLimit
   Cooling_Limit: NoLimit
   Dehumidification_Control_Type: None
   Humidification_Control_Type: None
   Demand_Controlled_Ventilation_Type: None
   Outdoor_Air_Economizer_Type: NoEconomizer
   ```

8. **NODELIST**: For zone air inlet nodes

## Output Parameters Assigned

### Temperature Control Parameters
- Heating setpoints: Day (19-21°C) and Night (16-18°C)
- Cooling setpoints: Day (24-26°C) and Night (26-28°C)
- Supply air temperatures: Heating max (40-50°C), Cooling min (12-14°C)

### Schedule Parameters
- HVAC availability: Typically 07:00-19:00 weekdays, off weekends
- Setpoint switching: Day/night transitions at 07:00 and 19:00
- Occupancy patterns: Building-type specific

### System Configuration
- Ideal loads with unlimited heating/cooling capacity
- No humidity control (dehumidification/humidification = None)
- No economizer or demand-controlled ventilation
- Fixed supply air humidity ratios

## Logging

Detailed logging in `assigned_hvac_log`:
```python
{
    building_id: {
        "params": {
            "heating_day_setpoint": {"range": [min, max], "selected": value},
            "heating_night_setpoint": {"range": [min, max], "selected": value},
            # ... all other parameters
        },
        "zones": {
            zone_name: {
                "hvac_objects": {
                    "ideal_loads": "IdealLoadsSystem_ZoneName",
                    "thermostat": "ZoneName Thermostat",
                    # ... all created objects
                }
            }
        }
    }
}
```

## Key Features

1. **Ideal Loads Simplification**: Uses EnergyPlus's ideal loads system for simplified HVAC modeling
2. **Comprehensive Scheduling**: Separate schedules for availability, heating, and cooling
3. **Building-Type Specific**: Parameters vary by residential/non-residential type and age
4. **Zone-Level Application**: Creates individual HVAC systems for each thermal zone
5. **Override Flexibility**: User can override any parameter or schedule
6. **Calibration Support**: Different values for pre/post calibration scenarios