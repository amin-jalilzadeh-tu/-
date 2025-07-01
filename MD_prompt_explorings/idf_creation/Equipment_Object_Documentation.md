# Equipment (Electric Equipment) Object Documentation

## Overview
The Equipment module creates `ELECTRICEQUIPMENT` objects in EnergyPlus IDF files to simulate plug loads and miscellaneous electric equipment. It handles parameter lookup, assignment, schedule creation, and heat gain distribution based on building type and characteristics.

## Input Data

### Building Row Data
- **ogc_fid**: Unique building identifier
- **building_function**: Category ("residential" or "non_residential")
- **residential_type**: Subtype when residential (e.g., "Apartment", "Detached House")
- **non_residential_type**: Subtype when non-residential (e.g., "Office Function", "Retail Function")
- **age_range**: Building construction period (for override matching)

### User Configuration (Optional)
- Parameter overrides from user_config
- Can target specific building IDs, building types, or age ranges
- Overrideable parameters: equip_wm2 and heat fraction parameters

### Control Parameters
- **calibration_stage**: "pre_calibration" or "post_calibration"
- **strategy**: "A" (average), "B" (random), or default (minimum)
- **random_seed**: For reproducible random values
- **zonelist_name**: Zone list to apply equipment to (default: "ALL_ZONES")

## Process Flow

### 1. Building Categorization

Determines:
- **building_category**: "Residential" or "Non-Residential"
- **sub_type**: Specific building type within category

Fallback defaults:
- Residential → "Apartment"
- Non-Residential → "Other Use Function"

### 2. Lookup Process (equip_lookup.py)

Structure:
```
calibration_stage
  └── building_category
        └── sub_type
              └── parameters (with min/max ranges)
```

#### Equipment Power Densities by Type

**Residential Types** (W/m²):
| Building Type | Pre-Calibration | Post-Calibration |
|--------------|-----------------|------------------|
| Corner House | 3.0-4.8 | 3.0-4.8 |
| Apartment | 1.8-3.6 | 1.8-3.6 |
| Terrace/Semi-detached | 3.0-4.8 | 3.0-4.8 |
| Detached House | 3.6-6.0 | 3.6-6.0 |
| Two-and-a-half-story | 3.6-6.0 | 3.6-6.0 |

**Non-Residential Types** (W/m²):
| Building Type | Pre-Calibration | Post-Calibration |
|--------------|-----------------|------------------|
| Office Function | 4.8-8.4 | 4.8-8.4 |
| Retail Function | 3.6-8.4 | 3.6-8.4 |
| Education Function | 3.0-6.0 | 3.0-6.0 |
| Healthcare Function | 4.8-9.6 | 4.8-9.6 |
| Meeting Function | 2.4-6.0 | 2.4-6.0 |
| Sport Function | 1.8-4.8 | 1.8-4.8 |
| Cell Function | 1.2-3.0 | 1.2-3.0 |
| Industrial Function | 3.6-7.2 | 3.6-7.2 |
| Accommodation Function | 2.4-4.8 | 2.4-4.8 |
| Other Use Function | 3.6-7.2 | 3.6-7.2 |

### 3. Parameter Assignment (assign_equip_values.py)

**Main Parameters**:
- **equip_wm2**: Equipment power density (W/m²)
- **tD**: Daytime hours (informational)
- **tN**: Nighttime hours (informational)

**Heat Fraction Parameters**:
- **equip_fraction_latent**: Moisture heat gain (default: 0.0)
- **equip_fraction_radiant**: Radiant heat gain (default: 0.1)
- **equip_fraction_lost**: Heat lost/removed (default: 0.8)

Note: Convective fraction = 1 - (latent + radiant + lost) = 0.1

**Value Selection Strategy**:
- Strategy "A": value = (min + max) / 2
- Strategy "B": value = random.uniform(min, max)
- Default: value = min

### 4. Schedule Creation (schedules.py)

Creates usage schedules based on building type:

**Example - Office Equipment Schedule**:
```
Weekdays:
  0-8: 0.05 (5% - standby/vampire loads)
  8-9: 0.5 (50% - ramp up)
  9-12: 0.75 (75% - morning peak)
  12-13: 0.65 (65% - lunch dip)
  13-17: 0.75 (75% - afternoon peak)
  17-18: 0.5 (50% - ramp down)
  18-24: 0.05 (5% - standby)

Weekends:
  All day: 0.05 (5% - minimal usage)
```

**Residential Schedule**:
- Lower daytime usage (people at work)
- Higher evening usage
- Weekend patterns differ from weekdays

### 5. IDF Object Creation (equipment.py)

Creates ELECTRICEQUIPMENT object:
```
ElectricEquipment,
    Equip_ALL_ZONES,                    ! Name
    ALL_ZONES,                          ! Zone or ZoneList Name
    EquipSchedule,                      ! Schedule Name
    Watts/Area,                         ! Design Level Calculation Method
    ,                                   ! Design Level {W}
    [assigned equip_wm2],               ! Watts per Zone Floor Area {W/m2}
    ,                                   ! Watts per Person {W/person}
    [assigned fraction_latent],         ! Fraction Latent
    [assigned fraction_radiant],        ! Fraction Radiant
    [assigned fraction_lost];           ! Fraction Lost
```

## Output Parameters Assigned

### Power Parameters
- **Watts_per_Zone_Floor_Area**: 1.2-9.6 W/m² depending on building type
- **Design_Level_Calculation_Method**: Always "Watts/Area"

### Heat Distribution
- **Fraction_Latent**: 0.0 (no moisture from equipment)
- **Fraction_Radiant**: 0.1 (10% as thermal radiation)
- **Fraction_Lost**: 0.8 (80% removed/exhausted)
- **Fraction_Convective**: 0.1 (10% - implicit, not specified)

### Schedule
- Complex occupancy-based patterns
- Accounts for work hours, lunch breaks, weekends
- Standby power during off hours

## Logging

All assigned values logged to `assigned_values_log`:
```python
{
    building_id: {
        "building_category": "Residential" or "Non-Residential",
        "sub_type": specific_type,
        "equip_wm2": {
            "range": [min, max],
            "selected": value
        },
        "equip_fraction_latent": {
            "range": [min, max],
            "selected": value
        },
        # ... other fraction parameters
    }
}
```

## Key Features

1. **Realistic Power Densities**: Based on building type and usage patterns
   - Residential: 1.8-6.0 W/m²
   - Non-residential: 1.2-9.6 W/m²

2. **Heat Gain Distribution**: 
   - Most heat is "lost" (removed by ventilation/cooling)
   - Small radiant and convective components affect zone loads

3. **Occupancy-Based Schedules**: 
   - Reflect actual usage patterns
   - Include standby/vampire loads
   - Different weekday/weekend profiles

4. **Building Type Specificity**:
   - Healthcare has highest loads (medical equipment)
   - Cell/Sport have lowest loads (minimal equipment)
   - Office/Education have typical plug loads

5. **Override Flexibility**: User configs can override any parameter

6. **Zone List Application**: Equipment applied to all zones via zone list