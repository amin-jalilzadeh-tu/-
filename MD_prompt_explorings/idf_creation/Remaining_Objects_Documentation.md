# Documentation for Remaining IDF Objects

## 1. Geometry Object

### Overview
Creates the building's thermal zones and surfaces using geomeppy, including walls, floors, ceilings, and zone definitions based on building dimensions and characteristics.

### Input Data
- **area**: Building floor area (m²)
- **perimeter**: Building perimeter (m)
- **gem_hoogte**: Building height (m)
- **gem_bouwlagen**: Number of floors
- **building_function**: residential/non_residential
- **edge_types**: Wall adjacency types (Facade, SharedWall, etc.)

### Key Calculations
```python
# Rectangle dimensions from area/perimeter
width = (perimeter - sqrt(perimeter² - 16*area)) / 4
length = area / width

# Floor height adjustment
if total_height < min_height * num_floors:
    num_floors = max(1, floor(total_height / min_height))
```

### IDF Objects Created
- **ZONE**: Thermal zones (core and perimeter)
- **BUILDINGSURFACE:DETAILED**: Walls, floors, ceilings, roofs
- **Constructions**: Surface construction assignments

### Parameters Assigned
- Zone volumes and floor areas
- Surface vertices and orientations
- Boundary conditions (Ground, Outdoors, Zone)
- Construction references

---

## 2. Ventilation Object

### Overview
Creates infiltration and ventilation objects for natural air exchange and mechanical ventilation systems.

### Input Data
- **building_function**: Building category
- **vent_key**: Ventilation archetype identifier
- **building area**: Total floor area
- **age_range**: Construction period
- **zone details**: Areas and core/perimeter status

### Key Calculations
```python
# Infiltration at 1Pa
qv10_value = base_rate * year_factor
c = qv10_value * (1/10)^flow_exponent

# Ventilation flow rate
total_flow = f_ctrl * building_area
zone_flow = total_flow * (zone_area / total_building_area)

# Core zone infiltration reduction
if is_core_zone:
    infiltration *= 0.25
```

### IDF Objects Created
- **ZONEINFILTRATION:DESIGNFLOWRATE**: Air leakage
- **ZONEVENTILATION:DESIGNFLOWRATE**: Natural ventilation
- **DESIGNSPECIFICATION:OUTDOORAIR**: Mechanical ventilation
- **SCHEDULE:COMPACT**: Operation schedules

### Parameters Assigned
| Parameter | Typical Values |
|-----------|----------------|
| Infiltration flow/exterior area | 0.0001-0.001 m³/s/m² |
| Temperature coefficient | 0.02-0.12 |
| Wind coefficient | 0.10-0.50 |
| Ventilation flow/area | 0.0002-0.001 m³/s/m² |
| HRV effectiveness | 0.60-0.85 (System D) |

---

## 3. Shading Object

### Overview
Creates window shading devices (blinds) and associated control schedules.

### Input Data
- **fenestration surfaces**: Window names from geometry
- **shading_type_key**: Blind configuration identifier
- **strategy**: Parameter selection method
- **user_config_shading**: Override values

### Key Calculations
```python
# Slat angle selection
slat_angle = select_value_from_range(angle_range, strategy)

# Optical properties
solar_transmittance = select_value_from_range(trans_range, strategy)
solar_reflectance = select_value_from_range(refl_range, strategy)
```

### IDF Objects Created
- **WINDOWMATERIAL:BLIND**: Blind material properties
- **WINDOWSHADINGCONTROL**: Control logic
- **SHADING:BUILDING:DETAILED**: Fixed geometric shading (optional)

### Parameters Assigned
| Parameter | Typical Values |
|-----------|----------------|
| Slat width | 25-80 mm |
| Slat separation | 10-30 mm |
| Slat angle | 0-45 degrees |
| Solar reflectance | 0.2-0.8 |
| Control type | AlwaysOn, OnIfScheduleAllows |
| Position | Interior, Exterior |

---

## 4. Zone Sizing Object

### Overview
Configures zone-level HVAC sizing parameters and outdoor air requirements.

### Input Data
- **building_function**: residential/non_residential
- **calibration_stage**: pre/post calibration
- **strategy**: Value selection method

### Key Calculations
```python
# Temperature selection
cooling_temp = select_from_range([13, 14], strategy)
heating_temp = select_from_range([40, 52], strategy)

# Humidity ratio
cooling_humidity = select_from_range([0.008, 0.009], strategy)
```

### IDF Objects Created
- **SIZING:ZONE**: Zone sizing parameters
- **DESIGNSPECIFICATION:OUTDOORAIR**: Global outdoor air specification
- **DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION**: Global air distribution

### Parameters Assigned
| Parameter | Residential | Non-Residential |
|-----------|------------|-----------------|
| Cooling supply temp | 13-14°C | 13-14°C |
| Heating supply temp | 40-50°C | 45-52°C |
| Cooling humidity ratio | 0.008-0.009 | 0.008-0.009 |
| Heating humidity ratio | 0.0156 | 0.0156 |
| Air flow method | DesignDay | Flow/Area |

---

## 5. Ground Temperature Object

### Overview
Sets monthly ground temperatures for ground-contact heat transfer calculations.

### Input Data
- **calibration_stage**: pre/post calibration
- **strategy**: Value selection method

### Key Calculations
```python
# Monthly temperature selection
for month in range(12):
    if calibration_stage == "pre_calibration":
        temp = select_from_range(monthly_ranges[month], strategy)
    else:
        temp = fixed_monthly_values[month]
```

### IDF Objects Created
- **SITE:GROUNDTEMPERATURE:BUILDINGSURFACE**: Monthly ground temperatures

### Parameters Assigned
Pre-calibration ranges (°C):
| Month | Min-Max | Month | Min-Max |
|-------|---------|-------|---------|
| Jan | 2-3 | Jul | 17-19 |
| Feb | 2-3 | Aug | 18-20 |
| Mar | 3-5 | Sep | 17-19 |
| Apr | 6-8 | Oct | 14-16 |
| May | 10-12 | Nov | 10-11 |
| Jun | 14-16 | Dec | 6-7 |

Post-calibration: Fixed values (e.g., Jan: 2.61°C, Jul: 18.05°C)

---

## Common Features Across All Modules

### 1. Lookup Table Structure
Each module uses hierarchical lookups:
```
calibration_stage → building_category → building_type → parameter_ranges
```

### 2. Value Selection Strategies
- **Strategy A**: Midpoint = (min + max) / 2
- **Strategy B**: Random = uniform(min, max)
- **Default**: Minimum value

### 3. Override Mechanisms
1. Base lookup values
2. Excel-based overrides
3. JSON user configuration overrides

### 4. Logging
All modules support logging assigned values:
```python
assigned_log[building_id] = {
    "parameter_name": {
        "range": [min, max],
        "selected": value
    }
}
```

### 5. Building Type Differentiation
Parameters vary by:
- Primary function (residential/non-residential)
- Specific type (Apartment, Office, etc.)
- Age range (pre-1946 to 2015+)
- Calibration stage