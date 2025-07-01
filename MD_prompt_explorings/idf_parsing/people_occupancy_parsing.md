# People and Occupancy Parsing Documentation

## Overview
The people and occupancy parsing module extracts occupant-related data from IDF files and SQL simulation results. This includes occupancy levels, activity schedules, clothing insulation, and associated heat gains.

## IDF Objects Parsed

### 1. PEOPLE
Occupant load definitions for zones.

**Parameters Extracted:**
- People Name
- Zone or Zone List Name
- Number of People Schedule Name
- Number of People Calculation Method:
  - Number of People
  - People per Zone Floor Area (people/m²)
  - Zone Floor Area per Person (m²/person)
- Number of People
- Fraction Radiant (0-1)
- Sensible Heat Fraction (autocalculate or 0-1)
- Activity Level Schedule Name
- Carbon Dioxide Generation Rate (m³/s-W)
- Enable ASHRAE 55 Comfort Warnings (Yes/No)
- Mean Radiant Temperature Calculation Type
- Surface Name/Angle Factors (for MRT calculation)
- Work Efficiency Schedule Name
- Clothing Insulation Calculation Method
- Clothing Insulation Schedule Name
- Air Velocity Schedule Name
- Thermal Comfort Model Types (1-6)

### 2. Associated Schedules

#### Occupancy Schedule
Controls fraction of peak occupancy:
- Range: 0 to 1
- 0 = unoccupied, 1 = fully occupied

#### Activity Level Schedule
Metabolic rate per person:
- Units: W/person
- Typical values:
  - Seated, quiet: 108 W
  - Seated, light work: 126 W
  - Standing, relaxed: 126 W
  - Walking: 207 W
  - Heavy work: 315 W

#### Clothing Insulation Schedule
Thermal resistance of clothing:
- Units: clo (1 clo = 0.155 m²·K/W)
- Typical values:
  - Summer clothing: 0.5 clo
  - Winter clothing: 1.0 clo
  - Business suit: 1.0 clo

#### Air Velocity Schedule
Local air speed for comfort calculations:
- Units: m/s
- Typical: 0.1-0.2 m/s for still air

## SQL Variables Extracted

1. **Zone People Occupant Count** (-)
2. **Zone People Total Heating Energy** (J)
3. **Zone People Total Heating Rate** (W)
4. **Zone People Sensible Heating Energy** (J)
5. **Zone People Sensible Heating Rate** (W)
6. **Zone People Latent Gain Energy** (J)
7. **Zone People Latent Gain Rate** (W)
8. **Zone People Radiant Heating Energy** (J)
9. **Zone People Radiant Heating Rate** (W)
10. **Zone People Convective Heating Energy** (J)
11. **Zone People Convective Heating Rate** (W)
12. **Zone Thermal Comfort Mean Radiant Temperature** (°C)
13. **Zone Thermal Comfort Operative Temperature** (°C)
14. **Zone Thermal Comfort Fanger Model PMV** (-)
15. **Zone Thermal Comfort Fanger Model PPD** (%)
16. **Zone Thermal Comfort ASHRAE 55 Simple Model Summer Clothes Not Comfortable Time** (hr)
17. **Zone Thermal Comfort ASHRAE 55 Simple Model Winter Clothes Not Comfortable Time** (hr)

## Key Metrics Calculated

1. **Occupancy Density**
   - People per unit area (people/m²)
   - Area per person (m²/person)

2. **Peak Occupancy**
   - Maximum number of occupants
   - Time of peak occupancy

3. **Occupancy Hours**
   - Total occupied hours per year
   - Occupancy patterns by day type

4. **Heat Gain Summary**
   - Sensible heat gain from occupants
   - Latent heat gain (moisture)
   - Total metabolic heat generation

5. **Comfort Metrics**
   - PMV (Predicted Mean Vote): -3 to +3 scale
   - PPD (Predicted Percentage Dissatisfied): 5-100%
   - Unmet comfort hours

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── people.parquet
```

**Columns in people.parquet:**
- building_id
- zone_name
- people_name
- calculation_method
- number_of_people
- people_per_area
- area_per_person
- occupancy_schedule
- activity_schedule
- clothing_schedule
- air_velocity_schedule
- fraction_radiant
- sensible_heat_fraction
- comfort_model_types

### SQL Timeseries Output
People-related variables in timeseries files track occupancy counts and heat gains.

## Data Processing Notes

1. **Heat Gain Calculation**:
   ```
   Total Heat = Activity Level × Number of People
   Sensible Heat = Total Heat × Sensible Fraction
   Latent Heat = Total Heat × (1 - Sensible Fraction)
   ```

2. **Radiant/Convective Split**:
   ```
   Radiant = Sensible Heat × Fraction Radiant
   Convective = Sensible Heat × (1 - Fraction Radiant)
   ```

3. **Comfort Calculations**: Based on ASHRAE 55 or ISO 7730 standards

4. **CO2 Generation**: Used for demand-controlled ventilation

5. **Schedule Interactions**: Multiple schedules affect occupant impact

## Typical Values

### Office Building
- Density: 0.05-0.1 people/m² (10-20 m²/person)
- Activity: 126 W/person (seated, light work)
- Schedule: 0% nights/weekends, 90-100% weekdays
- Clothing: 0.5 clo summer, 1.0 clo winter

### Residential
- Number: 2-4 people per dwelling unit
- Activity: Variable by room and time
- Schedule: Higher mornings/evenings, lower midday
- Clothing: 0.5-1.0 clo typical

### Retail
- Density: 0.15-0.3 people/m²
- Activity: 126-207 W/person (standing/walking)
- Schedule: Matches store hours
- Clothing: 0.5-1.0 clo

## Special Considerations

1. **Diversity**: Peak occupancy rarely equals sum of zone peaks

2. **Latent Loads**: Occupants add moisture affecting HVAC sizing

3. **Comfort Models**: Different models suit different applications:
   - Fanger PMV/PPD: Office environments
   - Adaptive: Naturally ventilated buildings
   - ASHRAE 55 Simple: Quick assessments

4. **MRT Calculation**: Important for radiant system evaluation

5. **CO2 Tracking**: Links to ventilation control strategies

## Quality Checks

1. **Reasonable Densities**: Check against building type standards

2. **Schedule Alignment**: Occupancy should match operating hours

3. **Activity Levels**: Verify metabolic rates match space use

4. **Total Occupancy**: Sum should match expected building population

5. **Comfort Limits**: PMV typically -0.5 to +0.5 for comfort

## Integration with Other Systems

1. **Ventilation**: Occupancy drives outdoor air requirements

2. **Lighting**: Occupancy sensors may control lighting

3. **Equipment**: Some equipment tracks with occupancy

4. **HVAC**: Occupancy affects cooling loads and setpoints

5. **Energy**: People heat gains offset heating, add to cooling loads