# Ventilation and HVAC Generation Fixes

## Critical Issues Found

### Ventilation/Infiltration Issues:

1. **Core Zone Infiltration (VENT_001)**
   - Problem: Core zones were getting zero infiltration
   - Fix: Apply 25% reduction factor instead of zero
   - Status: Fixed in add_ventilation.py line 386

2. **Extreme Value Validation (VENT_002)**
   - Problem: No validation for unrealistic ventilation rates
   - Fix: Add warnings for extreme values in calc_functions.py
   - Status: Partially fixed with warnings

3. **Unit Conversion Tracking (VENT_004)**
   - Problem: Confusing conversions between L/s/m², m³/h, and m³/s
   - Fix: Add explicit unit tracking in logs
   - Status: Fixed with unit tracking logs

4. **Zone Area Fallback (VENT_011)**
   - Problem: Equal split doesn't consider core vs perimeter zones
   - Fix: Use intelligent fallback (25% core, 75% perimeter)
   - Status: Fixed in add_ventilation.py lines 300-328

5. **DSOA Method Error (VENT_012)**
   - Problem: Using "Sum" instead of "Flow/Area" for outdoor air
   - Fix: Change to "Flow/Area" method
   - Status: Fixed in add_ventilation.py line 216

6. **Minimum Ventilation (VENT_015)**
   - Problem: Small zones could get near-zero ventilation
   - Fix: Enforce 10 L/s (0.01 m³/s) minimum per zone
   - Status: Fixed in add_ventilation.py lines 403-406

### HVAC Issues:

1. **Cooling Setpoints Too High (HVAC_001)**
   - Problem: Residential cooling setpoints are 32-34°C
   - Solution: Reduce to realistic 24-26°C range
   - File: hvac_lookup.py

2. **Missing Humidity Control (HVAC_002)**
   - Problem: No humidity limits in ideal loads system
   - Solution: Add humidity ratio limits (0.012 max, 0.008 min)
   - File: custom_hvac.py lines 274-275

3. **No Outdoor Air Integration (HVAC_003)**
   - Problem: System D ventilation not connected to HVAC
   - Solution: Link DSOA object to ideal loads system
   - File: custom_hvac.py line 290

4. **Schedule Type Limits (HVAC_004)**
   - Problem: Missing "Fraction" schedule type limits
   - Status: Fixed in custom_hvac.py lines 110-118

5. **Control Schedule Syntax (HVAC_005)**
   - Problem: Incorrect field format in control schedule
   - Status: Fixed in custom_hvac.py lines 130-134

## Recommended Additional Fixes

### 1. Update Cooling Setpoints in hvac_lookup.py
Change all residential cooling setpoints from 32-34°C to 24-26°C:
```python
'cooling_day_setpoint_range': ( 24.0, 26.0 ),
'cooling_night_setpoint_range': ( 25.0, 27.0 ),
```

### 2. Add Humidity Control to custom_hvac.py
After line 273, add:
```python
ideal.Maximum_Heating_Supply_Air_Humidity_Ratio = 0.012  # 12 g/kg
ideal.Minimum_Cooling_Supply_Air_Humidity_Ratio = 0.008  # 8 g/kg
```

### 3. Connect DSOA for System D in custom_hvac.py
After line 289, add:
```python
if system_type == "D" and dsoa_object_name_global:
    ideal.Design_Specification_Outdoor_Air_Object_Name = dsoa_object_name_global
```

### 4. Add Validation for Extreme Values
In assign_ventilation_values.py, add checks for:
- Infiltration rates > 5.0 L/s/m² @ 10Pa
- Ventilation rates > 10.0 L/s/m²
- Year factors > 3.0 or < 0.5

### 5. Improve Integration Between Systems
- Ensure ventilation schedules align with HVAC schedules
- Consider thermal comfort when setting ventilation rates
- Add zone multipliers for special spaces (kitchens, bathrooms)

## Testing Recommendations

1. Run simulations with the fixes and check:
   - Total ventilation rates per building type
   - Zone air change rates (should be 0.3-1.5 ACH typically)
   - Indoor temperatures stay within comfort range
   - Energy consumption is reasonable

2. Validate against Dutch standards:
   - NTA 8800 ventilation requirements
   - BENG energy performance indicators
   - Indoor air quality standards

3. Compare before/after results for:
   - Annual energy use
   - Peak heating/cooling loads
   - Hours outside comfort range