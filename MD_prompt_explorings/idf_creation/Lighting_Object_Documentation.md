# Lighting (Elec) Object Documentation

## Overview
The Lighting module creates `LIGHTS` and `ELECTRICEQUIPMENT` (for parasitic loads) objects in EnergyPlus IDF files. It handles parameter lookup, assignment, schedule creation, and thermal fraction configuration based on building type and characteristics.

## Input Data

### Building Row Data
- **ogc_fid**: Unique building identifier
- **building_function**: Category ("residential", "non_residential", or specific type)
- **residential_type**: Subtype when building_function is "residential" (e.g., "Apartment", "Detached House")
- **non_residential_type**: Subtype when building_function is "non_residential" (e.g., "Office Function", "Retail Function")
- **age_range**: Building construction period (for override matching)

### User Configuration (Optional)
- Parameter overrides from user_configs/{job_id}/lighting.json
- Can target specific building IDs, building types, or age ranges
- Overrideable parameters: lights_wm2, parasitic_wm2, tD, tN, and fraction parameters

### Control Parameters
- **calibration_stage**: "pre_calibration" or "post_calibration"
- **strategy**: "A" (average), "B" (random), or default (minimum)
- **random_seed**: For reproducible random values

## Process Flow

### 1. Building Categorization

The system determines:
- **building_category**: "Residential" or "Non-Residential"
- **sub_type**: Specific building type within category

Fallback defaults:
- Residential → "Apartment"
- Non-Residential → "Other Use Function"

### 2. Lookup Process (lighting_lookup.py)

Hierarchical structure:
```
calibration_stage
  └── building_category
        └── sub_type
              └── parameters (with min/max ranges)
```

#### Residential Types
All residential types have 0.0 W/m² for lighting (likely handled elsewhere):
- Apartment
- Corner House
- Detached House
- Terrace or Semi-detached House
- Two-and-a-half-story House

#### Non-Residential Types with Power Densities

| Building Type | Pre-Calibration (W/m²) | Post-Calibration (W/m²) |
|--------------|------------------------|------------------------|
| Meeting Function | 10.8-20.8 | 14.5-17.4 |
| Healthcare Function | 9.6-16.8 | 14.5-17.4 |
| Sport Function | 7.4-12.6 | 8.7-10.9 |
| Cell Function | 8.5-14.5 | 8.7-10.9 |
| Retail Function | 7.0-12.0 | 24.0-30.8 |
| Industrial Function | 8.5-14.5 | 8.7-10.9 |
| Accommodation Function | 3.2-5.6 | 6.3-7.2 |
| Office Function | 3.2-5.6 | 9.5-11.5 |
| Education Function | 8.7-15.3 | 8.7-10.9 |
| Other Use Function | 8.5-14.5 | 8.7-10.9 |

### 3. Parameter Assignment (assign_lighting_values.py)

**Main Parameters**:
- **lights_wm2**: Lighting power density (W/m²)
- **parasitic_wm2**: Standby power density (W/m²)
- **tD**: Daytime burning hours (informational)
- **tN**: Nighttime burning hours (informational)

**LIGHTS Fraction Parameters**:
- **lights_fraction_radiant**: Heat gain as radiation (default: 0.7)
- **lights_fraction_visible**: Heat gain as visible light (default: 0.2)
- **lights_fraction_replaceable**: Replaceable fraction (default: 1.0)
- **lights_fraction_return_air**: Return air fraction (default: 0.0)

**ELECTRICEQUIPMENT Fraction Parameters** (for parasitic):
- **equip_fraction_radiant**: Radiant fraction (default: 0.0)
- **equip_fraction_lost**: Lost fraction (default: 1.0)

**Value Selection Strategy**:
- Strategy "A": value = (min + max) / 2
- Strategy "B": value = random.uniform(min, max)
- Default: value = min

### 4. Schedule Creation

#### Lighting Schedules (from schedule_def.py)

Complex patterns based on building type:

**Example - Office Function**:
```
Weekdays:
  0-8: 0.02-0.05 (early morning)
  8-9: 0.5 (ramp up)
  9-12: 0.95 (morning peak)
  12-13: 0.8 (lunch dip)
  13-17: 0.95 (afternoon peak)
  17-18: 0.7 (early evening)
  18-24: 0.3-0.02 (evening/night)

Weekends:
  All day: 0.05 (minimal usage)
```

**Healthcare Function** (24/7 operation):
- Higher nighttime usage (0.2-0.4)
- Full usage during day hours

#### Parasitic Schedule
- Always-on: 1.0 for 24/7
- Applied to standby/vampire loads

### 5. IDF Object Creation (lighting.py)

Creates two objects:

#### LIGHTS Object
```
Name: Lights_ALL_ZONES
Zone_or_ZoneList_Name: ALL_ZONES
Schedule_Name: LightsSchedule
Design_Level_Calculation_Method: Watts/Area
Watts_per_Zone_Floor_Area: [assigned lights_wm2]
Fraction_Radiant: [assigned fraction, typically 0.7]
Fraction_Visible: [assigned fraction, typically 0.2]
Fraction_Replaceable: [assigned fraction, typically 1.0]
Return_Air_Fraction: [assigned fraction, typically 0.0]
```

#### ELECTRICEQUIPMENT Object (Parasitic)
```
Name: Parasitic_ALL_ZONES
Zone_or_ZoneList_Name: ALL_ZONES
Schedule_Name: ParasiticSchedule
Design_Level_Calculation_Method: Watts/Area
Watts_per_Zone_Floor_Area: [assigned parasitic_wm2]
Fraction_Radiant: [assigned fraction, typically 0.0]
Fraction_Lost: [assigned fraction, typically 1.0]
```

## Output Parameters Assigned

### LIGHTS Object Parameters
1. **Power Density**: Watts_per_Zone_Floor_Area (3.2-30.8 W/m² for non-residential)
2. **Schedule**: Complex occupancy-based patterns
3. **Thermal Fractions**:
   - Radiant: 0.7 (70% of heat as radiation)
   - Visible: 0.2 (20% as visible light)
   - Replaceable: 1.0 (100% replaceable)
   - Return Air: 0.0 (0% through return air)

### ELECTRICEQUIPMENT Object Parameters (Parasitic)
1. **Power Density**: Watts_per_Zone_Floor_Area (typically small values)
2. **Schedule**: Always-on (24/7)
3. **Thermal Fractions**:
   - Radiant: 0.0 (no radiant heat)
   - Lost: 1.0 (100% lost/dissipated)

## Logging

All assigned values are logged to `assigned_values_log` dictionary:
```python
{
    building_id: {
        "building_category": "Residential" or "Non-Residential",
        "sub_type": specific_type,
        "lights_wm2": {
            "range": [min, max],
            "selected": value
        },
        "parasitic_wm2": {
            "range": [min, max],
            "selected": value
        },
        # ... all fraction parameters with ranges and selected values
    }
}
```

## Key Features

1. **Zero Lighting for Residential**: All residential types have 0.0 W/m² suggesting residential lighting may be included in equipment loads

2. **Energy Efficiency**: Pre-calibration values reflect modern energy-efficient lighting (e.g., Office: 3.2-5.6 W/m²)

3. **Occupancy-Based Schedules**: Sophisticated patterns reflecting real usage:
   - Lunch breaks
   - Early/late working hours
   - Weekend differences
   - 24/7 operations for healthcare

4. **Thermal Impact Modeling**: Detailed fraction parameters affect zone heat gains and cooling loads

5. **Parasitic Load Separation**: Standby power modeled as always-on equipment

6. **Override Flexibility**: User configs can override any parameter at multiple specificity levels