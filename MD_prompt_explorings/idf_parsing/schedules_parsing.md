# Schedules Parsing Documentation

## Overview
The schedules parsing module extracts time-varying control schedules from IDF files. Schedules control virtually all building operations including occupancy, lighting, equipment, HVAC setpoints, and operational patterns.

## IDF Objects Parsed

### 1. SCHEDULETYPELIMITS
Defines value limits and type for schedules.

**Parameters Extracted:**
- Type Limits Name
- Lower Limit Value
- Upper Limit Value
- Numeric Type (Continuous, Discrete)
- Unit Type (Dimensionless, Temperature, etc.)

### 2. SCHEDULE:CONSTANT
Simple constant value schedule.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- Hourly Value (constant for all hours)

### 3. SCHEDULE:COMPACT
Compact format for complex schedules.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- Field entries defining:
  - Through: dates
  - For: day types (Weekdays, Weekends, AllDays, specific days)
  - Until: times
  - Values at each time period

**Example Structure:**
```
Through: 12/31,
For: Weekdays,
Until: 8:00, 0.0,
Until: 18:00, 1.0,
Until: 24:00, 0.0,
For: Weekends,
Until: 24:00, 0.0
```

### 4. SCHEDULE:DAY:HOURLY
Hourly values for a single day.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- Hour 1 through Hour 24 values

### 5. SCHEDULE:DAY:INTERVAL
Variable interval schedule for a day.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- Interpolate to Timestep (Yes/No)
- Time/Value pairs:
  - Time 1, Value 1
  - Time 2, Value 2
  - etc.

### 6. SCHEDULE:DAY:LIST
List of values with specified minutes per item.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- Interpolate to Timestep (Yes/No)
- Minutes per Item
- List of values

### 7. SCHEDULE:WEEK:DAILY
Weekly schedule referencing day schedules.

**Parameters Extracted:**
- Schedule Name
- Sunday Schedule:Day Name
- Monday Schedule:Day Name
- Tuesday Schedule:Day Name
- Wednesday Schedule:Day Name
- Thursday Schedule:Day Name
- Friday Schedule:Day Name
- Saturday Schedule:Day Name
- Holiday Schedule:Day Name
- SummerDesignDay Schedule:Day Name
- WinterDesignDay Schedule:Day Name
- CustomDay1 Schedule:Day Name
- CustomDay2 Schedule:Day Name

### 8. SCHEDULE:WEEK:COMPACT
Compact weekly schedule format.

**Parameters Extracted:**
- Schedule Name
- DayType List pairs:
  - Day Type (Weekdays, Weekend, AllDays, etc.)
  - Schedule:Day Name

### 9. SCHEDULE:YEAR
Annual schedule referencing week schedules.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- Schedule Week Name/Start Date pairs:
  - Schedule:Week Name 1, Start Month 1, Start Day 1
  - Schedule:Week Name 2, Start Month 2, Start Day 2
  - etc.

### 10. SCHEDULE:FILE
External file-based schedule.

**Parameters Extracted:**
- Schedule Name
- Schedule Type Limits Name
- File Name (path to CSV file)
- Column Number
- Rows to Skip at Top
- Number of Hours of Data
- Column Separator
- Interpolate to Timestep (Yes/No)
- Minutes per Item

## Key Schedule Types and Uses

### Occupancy Schedules
- Range: 0 to 1 (fraction of peak occupancy)
- Controls: People objects, ventilation rates
- Typical: 0 at night, 1 during occupied hours

### Lighting Schedules
- Range: 0 to 1 (fraction of design power)
- Controls: Lights objects
- May include dimming profiles

### Equipment Schedules
- Range: 0 to 1 (fraction of design power)
- Controls: ElectricEquipment, GasEquipment objects
- Varies by equipment type

### Thermostat Schedules
- Range: Temperature values (°C)
- Controls: Heating and cooling setpoints
- Includes setback/setup periods

### Availability Schedules
- Range: 0 or 1 (off/on)
- Controls: HVAC system operation
- Binary on/off control

### Activity Schedules
- Range: Metabolic rate (W/person)
- Controls: People heat gain
- Varies with activity level

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── schedules.parquet
```

**Columns in schedules.parquet:**
- building_id
- schedule_name
- schedule_type
- type_limits_name
- schedule_structure (JSON with full definition)
- annual_profile (simplified 8760 hourly values if computed)
- min_value
- max_value
- average_value

## Data Processing Notes

1. **Schedule Hierarchy**: Year → Week → Day → Hour/Interval structure.

2. **Day Types**: Different profiles for weekdays, weekends, holidays, design days.

3. **Interpolation**: Some schedules interpolate between specified times.

4. **Reference Resolution**: Schedules reference each other requiring recursive parsing.

5. **Time Formats**: Various formats (decimal hours, HH:MM, minutes from midnight).

## Schedule Analysis

### Profile Extraction
Convert complex schedule definitions to 8760 hourly values for analysis.

### Operating Hours Calculation
```python
operating_hours = sum(1 for value in hourly_values if value > threshold)
```

### Peak Period Identification
Identify when schedules reach maximum values.

### Diversity Factors
Ratio of average to peak values indicates usage diversity.

## Common Schedule Patterns

### Office Occupancy
```
Weekdays: 0 (midnight-7am), ramp up (7-9am), 1.0 (9am-5pm), ramp down (5-7pm), 0 (7pm-midnight)
Weekends: 0 all day
```

### Retail Lighting
```
All days: 0 (midnight-6am), 0.5 (6-8am), 1.0 (8am-9pm), 0.5 (9-10pm), 0 (10pm-midnight)
```

### Residential Thermostat
```
Heating: 20°C (night), 22°C (morning/evening), 18°C (day when unoccupied)
Cooling: 26°C (night), 24°C (when occupied), 28°C (when unoccupied)
```

### School Availability
```
Weekdays during school year: 1
Weekends and summer: 0
```

## Special Considerations

1. **Daylight Saving Time**: Schedules typically ignore DST unless specifically modeled.

2. **Holidays**: Require special day assignments in RunPeriodControl:SpecialDays.

3. **Schedule Conflicts**: Multiple schedules may control same parameter - last one wins.

4. **Design Days**: Separate profiles for sizing calculations.

5. **Leap Years**: 8784 hours instead of 8760.

## Quality Checks

1. **Value Ranges**: Verify schedules stay within type limits.

2. **Completeness**: Ensure all time periods are covered (sum to 24 hours).

3. **Referenced Objects**: All referenced day/week schedules must exist.

4. **Realistic Patterns**: Check for reasonable occupancy/operation patterns.

5. **Synchronization**: Related schedules (occupancy, lighting, equipment) should align.

## Schedule Optimization

### Load Shifting
Modify schedules to shift loads to off-peak periods.

### Setpoint Optimization
Adjust temperature setpoints for energy savings.

### Occupancy-Based Control
Align all schedules with actual occupancy patterns.

### Seasonal Adjustments
Different profiles for heating/cooling seasons.

## Integration Notes

1. **People Objects**: Reference occupancy, activity, clothing schedules.

2. **HVAC Systems**: Reference availability and setpoint schedules.

3. **Internal Gains**: All internal gain objects reference operation schedules.

4. **Controls**: Advanced controls may override basic schedules.

5. **Utility Rates**: Time-of-use rates need synchronized schedules.