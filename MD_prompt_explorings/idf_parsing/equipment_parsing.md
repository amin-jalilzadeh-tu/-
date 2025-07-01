# Equipment Parsing Documentation

## Overview
The equipment parsing module extracts internal equipment and plug load data from IDF files and SQL simulation results. This includes electric equipment, gas equipment, and other internal gains sources.

## IDF Objects Parsed

### 1. ELECTRICEQUIPMENT
Electric equipment and plug loads in zones.

**Parameters Extracted:**
- Equipment Name
- Zone or Space Name
- Schedule Name
- Design Level Calculation Method:
  - `design_level`: Equipment Level (W)
  - `watts_per_area`: Watts per Zone Floor Area (W/m²)
  - Watts per Person (W/person)
- `fraction_latent`: Fraction Latent (0-1)
- `fraction_radiant`: Fraction Radiant (0-1)
- `fraction_lost`: Fraction Lost (0-1)
- `end_use`: End-Use Subcategory

### 2. GASEQUIPMENT
Gas-fired equipment in zones.

**Parameters Extracted:**
- Equipment Name
- Zone or Space Name
- Schedule Name
- Design Level Calculation Method:
  - Design Level (W)
  - Watts per Zone Floor Area (W/m²)
  - Watts per Person (W/person)
- Fraction Latent
- Fraction Radiant
- Fraction Lost
- Carbon Dioxide Generation Rate (m³/s-W)
- End-Use Subcategory

### 3. HOTWATEREQUIPMENT
Equipment using hot water as energy source.

**Parameters Extracted:**
- Equipment Name
- Zone or Space Name
- Schedule Name
- Design Level Calculation Method
- Fraction Latent
- Fraction Radiant
- Fraction Lost
- End-Use Subcategory

### 4. STEAMEQUIPMENT
Equipment using steam as energy source.

**Parameters Extracted:**
- Equipment Name
- Zone or Space Name
- Schedule Name
- Design Level Calculation Method
- Fraction Latent
- Fraction Radiant
- Fraction Lost
- End-Use Subcategory

### 5. OTHEREQUIPMENT
Other fuel type equipment.

**Parameters Extracted:**
- Equipment Name
- Fuel Type
- Zone or Space Name
- Schedule Name
- Design Level Calculation Method
- Fraction Latent
- Fraction Radiant
- Fraction Lost
- Carbon Dioxide Generation Rate
- End-Use Subcategory

### 6. EXTERIOREQUIPMENT
Equipment located outside the building.

**Parameters Extracted:**
- Equipment Name
- Fuel Use Type
- Schedule Name
- Design Level (W)
- End-Use Subcategory

### 7. EXTERIOR:LIGHTS
Exterior lighting (parking, facade, etc.).

**Parameters Extracted:**
- Exterior Lights Name
- Schedule Name
- Design Level (W)
- Control Option (AstronomicalClock, ScheduleOnly)
- End-Use Subcategory

### 8. Refrigeration Equipment

#### REFRIGERATION:SYSTEM
Complete refrigeration system.

**Parameters Extracted:**
- System Name
- Refrigerated Case or Walk-in List
- Refrigeration Transfer Load List
- Refrigeration Condenser Name
- Compressor or Compressor List Name
- Minimum Condensing Temperature (°C)
- Refrigeration System Working Fluid Type
- Suction Temperature Control Type

#### REFRIGERATION:COMPRESSORRACK
Multiple compressors serving refrigeration loads.

**Parameters Extracted:**
- Compressor Rack Name
- Heat Rejection Location
- Design Compressor Rack COP
- Compressor Rack COP Function of Temperature Curve
- Design Condenser Fan Power (W)
- Condenser Type

## SQL Variables Extracted

1. **Zone Electric Equipment Electricity Rate** (W)
2. **Zone Electric Equipment Electricity Energy** (J)
3. **Zone Electric Equipment Total Heating Rate** (W)
4. **Zone Electric Equipment Total Heating Energy** (J)
5. **Zone Electric Equipment Radiant Heating Rate** (W)
6. **Zone Electric Equipment Radiant Heating Energy** (J)
7. **Zone Electric Equipment Convective Heating Rate** (W)
8. **Zone Electric Equipment Latent Gain Rate** (W)
9. **Zone Gas Equipment Gas Rate** (W)
10. **Zone Gas Equipment Gas Energy** (J)
11. **Zone Gas Equipment Total Heating Rate** (W)
12. **Zone Other Equipment [Fuel Type] Rate** (W)
13. **Zone Other Equipment [Fuel Type] Energy** (J)

## Key Metrics Calculated

1. **Total Equipment Power**
   - Sum of all equipment power across zones
   - Units: W or W/m²

2. **Peak Demand**
   - Maximum instantaneous power draw
   - Time of peak occurrence
   - Units: kW

3. **Annual Consumption**
   - Total energy consumption by equipment type
   - Units: kWh or therms (for gas)

4. **Equipment Load Profile**
   - Hourly/daily variation in equipment use
   - Diversity factors

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── equipment.parquet
```

**Columns in equipment.parquet:**
- building_id
- zone_name
- equipment_type
- equipment_name
- fuel_type
- schedule_name
- design_level
- watts_per_area
- watts_per_person
- heat_gain_fractions (latent, radiant, lost)
- end_use_subcategory
- carbon_dioxide_rate (if applicable)

### SQL Timeseries Output
```
parsed_data/
└── timeseries/
    └── base_all_daily.parquet (for base buildings)
    └── comparisons/
        └── comparison_{building_id}.parquet (for variants)
```

## Data Processing Notes

1. **Heat Gain Distribution**: Equipment heat is distributed as:
   - Convective (immediate impact on air temperature)
   - Radiant (delayed impact through surfaces)
   - Latent (moisture addition)
   - Lost (not affecting zone)

2. **Schedule Dependencies**: Actual power = Design Level × Schedule Value

3. **End-Use Tracking**: Subcategories allow detailed energy use breakdown.

4. **Fuel Diversity**: Different fuel types tracked separately for utility cost analysis.

5. **Density Metrics**: W/m² allows comparison across different building sizes.

## Common End-Use Subcategories

- General
- Computers
- Servers
- Office Equipment  
- Printers
- Refrigeration
- Cooking
- Elevators
- Process Equipment
- Laboratory Equipment
- Medical Equipment
- Workshop Equipment

## Special Considerations

1. **IT Equipment**: Often has high power density and special cooling needs.

2. **Process Loads**: Industrial equipment may have unique schedules and heat gain patterns.

3. **Standby Power**: Some equipment has continuous parasitic loads.

4. **Power Factor**: Not explicitly modeled but affects actual electricity use.

5. **Equipment Aging**: Design levels may not reflect actual degraded performance.

## Quality Checks

1. **Power Density Ranges**: Typical office 5-15 W/m², data center 500-2000 W/m².

2. **Heat Gain Fractions**: Must sum to ≤ 1.0 (remainder is convective).

3. **Schedule Coordination**: Equipment schedules should align with occupancy.

4. **Fuel Type Consistency**: Fuel type must match available utilities.

5. **Refrigeration Temperatures**: Must maintain proper temperature ranges for food safety.