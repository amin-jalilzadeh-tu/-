# Schedules Modifications System

## Overview
The schedules modification system handles time-based control parameters in EnergyPlus IDF files. Schedules define when and how building systems operate, directly impacting energy consumption patterns. This system can modify occupancy schedules, temperature setpoints, equipment operation, and other time-varying parameters.

## Modified Object Types
- `SCHEDULETYPELIMITS` - Defines valid ranges for schedule values
- `SCHEDULE:COMPACT` - Compact format for complex schedules
- `SCHEDULE:CONSTANT` - Constant value schedules
- `SCHEDULE:DAY:HOURLY` - Hourly schedule values
- `SCHEDULE:DAY:INTERVAL` - Interval-based daily schedules
- `SCHEDULE:DAY:LIST` - List format daily schedules
- `SCHEDULE:WEEK:DAILY` - Weekly schedule referencing daily schedules
- `SCHEDULE:WEEK:COMPACT` - Compact weekly schedules
- `SCHEDULE:YEAR` - Annual schedules
- `SCHEDULE:FILE` - External file-based schedules

## Parameters Modified

### SCHEDULE:CONSTANT Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `constant_value` | Hourly Value | 2 | float | varies | - | schedule_values |

### SCHEDULETYPELIMITS Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `lower_limit` | Lower Limit Value | 1 | float | varies | - | schedule_bounds |
| `upper_limit` | Upper Limit Value | 2 | float | varies | - | schedule_bounds |

### SCHEDULE:COMPACT Parameters
Schedule:Compact uses variable fields after index 2, containing:
- Day type specifications (e.g., "Weekdays", "Saturday", "Sunday")
- Time specifications (e.g., "Until: 8:00", "Until: 18:00")
- Values for each time period

## Modification Strategies

### 1. Occupancy Optimization (`occupancy_optimization`)
- **Purpose**: Adjust occupancy schedules for realistic patterns
- **Modifications**:
  - Reduces occupancy-related schedules by 10%
  - Applies to schedules with names containing:
    - OCCUPANCY
    - PEOPLE
    - OCC
  - Represents:
    - More accurate occupancy data
    - Partial remote work scenarios
    - Actual vs. design occupancy
  - Impact: Reduces internal gains and ventilation loads

### 2. Setback/Setup Setpoints (`setback_setpoint`)
- **Purpose**: Implement temperature setbacks during unoccupied hours
- **Modifications**:
  - Heating schedules: -2°C during unoccupied times
  - Cooling schedules: +2°C during unoccupied times
  - Identifies schedules containing:
    - SETPOINT
    - HEATING
    - COOLING
    - TEMP
  - Unoccupied hours: Before 7 AM and after 6 PM
  - Typical savings: 5-15% HVAC energy

### 3. Equipment Scheduling (`equipment_scheduling`)
- **Purpose**: Optimize equipment operation schedules
- **Modifications**:
  - Reduces equipment operation by 20% during all hours
  - Targets schedules containing:
    - EQUIPMENT
    - ELEC
    - PLUG
  - Represents:
    - Better equipment management
    - Standby power elimination
    - Automated shutoffs
  - Works with plug load reduction strategies

### 4. Extended Hours (`extended_hours`)
- **Purpose**: Extend HVAC availability for improved comfort
- **Modifications**:
  - Changes availability schedules from 0 to 1
  - 30% probability of extending operation
  - Targets schedules containing:
    - AVAILABILITY
    - FAN
    - HVAC
  - Use cases:
    - Overtime work accommodation
    - Event hosting
    - Improved morning warm-up/cool-down

## Process Flow

### 1. Schedule Type Detection
```
Schedule Object → Parse Schedule Name
               → Identify Schedule Purpose
               → Determine Modification Strategy
```

### 2. Compact Schedule Processing
```
Schedule:Compact → Parse Fields Sequentially
                → Identify Time/Value Pairs
                → Apply Modifications to Values
                → Preserve Time Structure
```

### 3. Time-Based Logic
```
Time String → Extract Hour
           → Determine Occupied/Unoccupied
           → Apply Appropriate Modification
           → Update Value Field
```

## Integration Notes

### Relationship with Other Systems
- **HVAC**: Temperature setpoint schedules control system operation
- **Lighting**: Lighting schedules follow occupancy patterns
- **Equipment**: Equipment schedules define plug load profiles
- **Ventilation**: Minimum outdoor air often follows occupancy

### Common Schedule Types and Uses
1. **Occupancy Schedules**:
   - Controls: People objects, ventilation rates
   - Typical: 0-1 fractional, peaks during work hours
   
2. **Temperature Setpoints**:
   - Controls: Zone thermostats
   - Typical: 20-24°C heating, 24-28°C cooling
   
3. **Equipment Schedules**:
   - Controls: Electric equipment, plug loads
   - Typical: 0-1 fractional, follows occupancy
   
4. **Lighting Schedules**:
   - Controls: Interior lighting
   - Typical: 0-1 fractional, may extend beyond occupancy
   
5. **HVAC Availability**:
   - Controls: System on/off
   - Typical: Binary 0/1

### Performance Impact
- **Schedule Optimization**: 10-30% energy savings potential
- **Setback/Setup**: 5-15% HVAC savings
- **Equipment Scheduling**: 10-25% plug load reduction
- **Occupancy Accuracy**: 5-20% overall savings

## Technical Implementation Details

### Schedule:Compact Format Example
```
Schedule:Compact,
  Office Occupancy,          ! Name
  Fraction,                  ! Schedule Type Limits
  Through: 12/31,           ! Date range
  For: Weekdays,            ! Day type
  Until: 7:00,   0.0,       ! Early morning
  Until: 8:00,   0.1,       ! Arrival
  Until: 12:00,  0.95,      ! Morning
  Until: 13:00,  0.5,       ! Lunch
  Until: 17:00,  0.95,      ! Afternoon
  Until: 18:00,  0.3,       ! Departure
  Until: 24:00,  0.05,      ! Evening
  For: AllOtherDays,        ! Weekends
  Until: 24:00,  0.0;       ! Unoccupied
```

### Time Field Recognition Patterns
1. `HH:MM` - Simple time format
2. `Until: HH:MM` - EnergyPlus standard
3. `HH:MM:SS` - Time with seconds

### Schedule Modification Best Practices
1. **Preserve Structure**: Don't modify time specifications
2. **Respect Limits**: Check ScheduleTypeLimits constraints
3. **Maintain Logic**: Ensure modified values make sense
4. **Document Changes**: Track what was modified and why

### Error Handling
- Validate schedule type before modification
- Check for numeric vs. non-numeric fields
- Preserve schedule continuity
- Handle variable field counts in Compact schedules

### Special Considerations
1. **Holiday Schedules**: May need separate handling
2. **Seasonal Variations**: Some schedules change by season
3. **Special Events**: Consider atypical operation days
4. **Daylight Saving**: Time zone considerations
5. **Ramp Rates**: Gradual transitions vs. step changes

### Common Pitfalls to Avoid
1. Modifying time fields instead of values
2. Breaking schedule continuity
3. Creating unrealistic patterns
4. Ignoring schedule type limits
5. Over-aggressive setbacks causing comfort issues