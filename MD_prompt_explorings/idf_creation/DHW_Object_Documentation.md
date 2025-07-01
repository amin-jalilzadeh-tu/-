# DHW (Domestic Hot Water) Object Documentation

## Overview
The DHW module creates `WATERHEATER:MIXED` objects in EnergyPlus IDF files to simulate domestic hot water systems. It handles parameter lookup, assignment, calculation, and schedule creation based on building type and characteristics.

## Input Data

### Building Row Data
- **dhw_key**: Building type identifier (e.g., "Apartment", "Office Function")
- **building_function**: General category ("residential" or specific non-residential type)
- **age_range**: Building construction period (e.g., "1992 - 2005")
- **floor_area_m2** or **area**: Building floor area in square meters
- **occupant_count**: Number of occupants (optional)
- **ogc_fid**: Unique building identifier

### User Configuration (Optional)
- Parameter overrides by building_id, dhw_key, building_function, or age_range
- Fixed values or min/max ranges for any parameter

### Control Parameters
- **calibration_stage**: "pre_calibration" or "post_calibration"
- **strategy**: "A" (midpoint) or "B" (random within range)
- **use_nta**: Boolean for NTA 8800 standard calculations
- **random_seed**: For reproducible random values

## Process Flow

### 1. Lookup Process (dhw_lookup.py)

Parameter ranges stored for each building type:

#### Residential Types
- Corner House
- Apartment
- Terrace or Semi-detached House
- Detached House
- Two-and-a-half-story House

#### Non-Residential Types
- Meeting Function
- Healthcare Function
- Sport Function
- Cell Function
- Retail Function
- Industrial Function
- Accommodation Function
- Office Function
- Education Function
- Other Use Function

#### Parameters per Type
| Parameter | Typical Range | Units |
|-----------|--------------|-------|
| occupant_density_m2_per_person | 25-75 (res), 10-100 (non-res) | m²/person |
| liters_per_person_per_day | 45-65 (res), 4-70 (non-res) | L/person/day |
| default_tank_volume_liters | 80-200 (res), 50-300 (non-res) | liters |
| default_heater_capacity_w | 3000-8000 | watts |
| setpoint_c | 58-65 | °C |
| usage_split_factor | 0.2-0.8 | fraction |
| peak_hours | 2-6 | hours |
| morning_val | 0.05-0.20 | fraction |
| peak_val | 0.15-0.60 | fraction |
| afternoon_val | 0.05-0.25 | fraction |
| evening_val | 0.10-0.30 | fraction |

### 2. Parameter Assignment (assign_dhw_values.py)

1. **Range Selection**:
   - Retrieves ranges from dhw_lookup based on dhw_key and calibration_stage
   - Applies user config overrides if matches found
   - For residential without occupant_density, calculates from floor area

2. **Value Selection**:
   - Strategy "A": midpoint = (min + max) / 2
   - Strategy "B": random.uniform(min, max)

3. **NTA 8800 Calculations** (if use_nta=True):
   
   **Residential**:
   ```python
   if area > 50:
       occupants = 1 + 0.01 * (area - 50)
   else:
       occupants = 1
   daily_liters = occupants * 45
   ```
   
   **Non-Residential**:
   - Uses TABLE_13_1_KWH_PER_M2 factors
   - annual_kWh = area * factor
   - daily_liters = annual_kWh * 13.76 / 365

### 3. Parameter Calculations (parameters.py)

**Calculated Values**:
```python
occupant_count = floor_area / occupant_density
daily_liters = occupant_count * liters_per_person_per_day
daily_m3 = daily_liters / 1000
peak_flow_m3s = (daily_m3 * usage_split_factor) / (peak_hours * 3600)
tank_volume_m3 = tank_volume_liters / 1000
```

### 4. Schedule Creation (schedules.py)

Creates two schedules:

**Use Fraction Schedule** (24-hour pattern):
- 00:00-06:00: 0.0
- 06:00-08:00: morning_val
- 08:00-10:00: peak_val
- 10:00-17:00: afternoon_val
- 17:00-21:00: evening_val
- 21:00-24:00: morning_val

**Setpoint Schedule**: Constant temperature (typically 60°C)

### 5. IDF Object Creation (water_heater.py)

Creates `WATERHEATER:MIXED` with:

| Parameter | Value/Source |
|-----------|--------------|
| Name | DHW_{name_suffix} |
| Tank Volume | Calculated tank_volume_m3 |
| Setpoint Temperature Schedule | Created setpoint schedule |
| Deadband Temperature Difference | 2°C |
| Maximum Temperature Limit | 80°C |
| Heater Control Type | CYCLE |
| Heater Maximum Capacity | Calculated heater_capacity_w |
| Heater Fuel Type | NaturalGas |
| Heater Thermal Efficiency | 0.9 (res), 0.8 (non-res) |
| Off/On Cycle Loss Coefficient | 5.0 W/K |
| Ambient Temperature Schedule | Always22C |
| Peak Use Flow Rate | Calculated peak_flow_m3s |
| Use Flow Rate Fraction Schedule | Created use fraction schedule |

## Output Parameters Assigned

The module assigns values to the following IDF parameters:

1. **Tank Properties**:
   - Tank_Volume: Based on building size and type
   - Setpoint_Temperature_Schedule_Name: Typically 60°C constant
   - Maximum_Temperature_Limit: 80°C

2. **Heater Properties**:
   - Heater_Maximum_Capacity: 3000-8000W based on building
   - Heater_Thermal_Efficiency: 0.8-0.9 based on type

3. **Usage Properties**:
   - Peak_Use_Flow_Rate: Calculated from daily usage
   - Use_Flow_Rate_Fraction_Schedule_Name: 24-hour usage pattern

4. **Loss Properties**:
   - Off_Cycle_Loss_Coefficient_to_Ambient_Temperature: 5.0 W/K
   - On_Cycle_Loss_Coefficient_to_Ambient_Temperature: 5.0 W/K

## Logging

All assigned values are logged to `assigned_dhw_log` dictionary with structure:
```python
{
    building_id: {
        "dhw_key": selected_key,
        "occupant_density_range": [min, max],
        "occupant_density_selected": value,
        "liters_per_person_per_day_range": [min, max],
        "liters_per_person_per_day_selected": value,
        # ... all other parameters
        "occupant_count": calculated_value,
        "daily_liters": calculated_value,
        "peak_flow_m3s": calculated_value,
        "object_names": {
            "water_heater": "DHW_suffix",
            "setpoint_schedule": "DHW_suffix_Setpoint",
            "use_fraction_schedule": "DHW_suffix_UseFraction"
        }
    }
}
```