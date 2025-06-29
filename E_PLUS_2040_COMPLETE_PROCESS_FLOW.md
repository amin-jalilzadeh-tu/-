# E_Plus_2040_py Complete Process Flow Documentation

## Table of Contents
1. [Overview](#overview)
2. [Data Flow Architecture](#data-flow-architecture)
3. [Parameter Assignment Functions](#parameter-assignment-functions)
4. [Data Transformation Functions](#data-transformation-functions)
5. [Lookup Dictionaries and Data Structures](#lookup-dictionaries-and-data-structures)
6. [Validation and Error Handling](#validation-and-error-handling)
7. [Scheduling Logic](#scheduling-logic)
8. [EnergyPlus Objects Creation](#energyplus-objects-creation)
9. [Mathematical Formulas and Calculations](#mathematical-formulas-and-calculations)
10. [File I/O Operations](#file-io-operations)
11. [Database Operations and SQL Queries](#database-operations-and-sql-queries)
12. [Configuration Constants and Defaults](#configuration-constants-and-defaults)

---

## 1. Overview

The E_Plus_2040_py system is a comprehensive building energy simulation framework that:
- Creates EnergyPlus IDF files from building data
- Runs simulations with various scenarios
- Performs calibration, sensitivity analysis, and surrogate modeling
- Validates results against measured data

### Main Process Flow:
1. **IDF Creation** → 2. **Simulation** → 3. **Parsing** → 4. **Analysis** → 5. **Validation**

---

## 2. Data Flow Architecture

### Primary Data Pipeline:
```
Input Excel/CSV → Building Data Processing → IDF Creation → EnergyPlus Simulation → SQL Results → Parsing → Analysis
```

### Key Components:
- **Orchestrator**: Main workflow controller
- **IDF Objects**: Modular components for building elements
- **Parsers**: SQL and IDF data extractors
- **Analyzers**: Calibration, sensitivity, and surrogate model builders

---

## 3. Parameter Assignment Functions

### 3.1 Zone Sizing Parameters (setzone/assign_zone_sizing_values.py)

**Function**: `assign_zone_sizing_params()`
```python
def assign_zone_sizing_params(
    building_function: str,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None
):
```

**Parameter Selection Logic**:
- Strategy "A": Midpoint of range
- Strategy "B": Random uniform distribution
- Default: Minimum value

**Parameters Assigned**:
- `cooling_supply_air_temp`: Temperature of cooling supply air (°C)
- `heating_supply_air_temp`: Temperature of heating supply air (°C)
- `cooling_supply_air_hr`: Cooling supply air humidity ratio (kg/kg)
- `heating_supply_air_hr`: Heating supply air humidity ratio (kg/kg)
- `cooling_design_air_flow_method`: Method for calculating cooling airflow
- `heating_design_air_flow_method`: Method for calculating heating airflow

### 3.2 Geometry Parameters (geomz/assign_geometry_values.py)

**Function**: `assign_geometry_values()`
```python
def assign_geometry_values(
    building_row,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config=None,
    assigned_geom_log=None,
    excel_rules=None
):
```

**Key Calculations**:
1. **Perimeter Depth Selection**:
   ```python
   perimeter_depth = pick_val_with_range(
       rng_tuple=perimeter_depth_range,
       strategy=strategy,
       log_dict=log_dict,
       param_name="perimeter_depth"
   )
   ```

2. **Core Zone Determination**:
   - Residential buildings: Usually `has_core = False`
   - Non-residential: Usually `has_core = True`

### 3.3 DHW (Domestic Hot Water) Parameters (DHW/assign_dhw_values.py)

**Function**: `assign_dhw_parameters()`

**Complex Calculations**:

1. **Occupant Density Calculation** (for residential):
   ```python
   if area > 50:
       occupant_count += 0.01 * (area - 50)
   occupant_density = area / occupant_count
   ```

2. **NTA 8800-based Usage Calculation**:
   - Residential: 45 L/person/day at 60°C
   - Non-residential: Based on TABLE_13_1_KWH_PER_M2
   
   ```python
   # Non-residential calculation
   factor_kwh = dhw_lookup["TABLE_13_1_KWH_PER_M2"].get(nrtype, 1.4)
   annual_kwh = factor_kwh * area
   annual_liters = annual_kwh * 13.76  # Conversion factor
   daily_liters = annual_liters / 365.0
   ```

### 3.4 HVAC Parameters (HVAC/assign_hvac_values.py)

**Function**: `assign_hvac_ideal_parameters()`

**Parameters**:
- Heating/cooling setpoints (day/night)
- Supply air temperatures
- Schedule details for operation

**Override Logic**:
```python
def override_numeric_range(current_range, row):
    if "fixed_value" in row:
        v = row["fixed_value"]
        return (v, v)
    if "min_val" in row and "max_val" in row:
        return (row["min_val"], row["max_val"])
    return current_range
```

### 3.5 Fenestration (Windows) Parameters (fenez/assign_fenestration_values.py)

**Function**: `assign_fenestration_parameters()`

**WWR (Window-to-Wall Ratio) Calculation**:
```python
def compute_wwr_from_row(building_row, include_doors_in_wwr=False):
    ext_wall_area = building_row.get("exterior_wall_area_m2", 100.0)
    window_area = building_row.get("window_area_m2", 0.0)
    if include_doors_in_wwr:
        door_area = building_row.get("door_area_m2", 0.0)
        window_area += door_area
    return window_area / ext_wall_area
```

---

## 4. Data Transformation Functions

### 4.1 Time Series Aggregation (sql_data_manager.py)

**Hourly Aggregation**:
```python
def _aggregate_to_hourly(self, df: pd.DataFrame) -> pd.DataFrame:
    df['Hour'] = df['DateTime'].dt.floor('H')
    
    # Energy variables: SUM
    energy_vars = df[df['Variable'].str.contains('Energy|Consumption')]
    energy_agg = energy_vars.groupby(group_cols)['Value'].sum()
    
    # Other variables: MEAN
    other_vars = df[~df['Variable'].str.contains('Energy|Consumption')]
    other_agg = other_vars.groupby(group_cols)['Value'].mean()
```

**Daily Aggregation**:
```python
def _aggregate_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
    df['Date'] = df['DateTime'].dt.date
    # Similar logic with daily grouping
```

### 4.2 Semi-Wide Format Transformation

**Function**: `_convert_to_semi_wide()`
```python
def _convert_to_semi_wide(self, df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    # Create date string based on frequency
    if frequency == 'hourly':
        df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d_%H')
    elif frequency == 'daily':
        df['date_str'] = df['DateTime'].dt.strftime('%Y-%m-%d')
    
    # Pivot with dates as columns
    pivot_df = df.pivot_table(
        index=['building_id', 'variant_id', 'Variable', 'category', 'Zone', 'Units'],
        columns='date_str',
        values='Value',
        aggfunc='mean'
    )
```

---

## 5. Lookup Dictionaries and Data Structures

### 5.1 Zone Sizing Lookup (setzone/zone_sizing_lookup.py)

```python
zone_sizing_lookup = {
    "pre_calibration": {
        "residential": {
            "cooling_supply_air_temp_range": (13.5, 14.5),
            "heating_supply_air_temp_range": (48.0, 52.0),
            "cooling_supply_air_hr_range": (0.0085, 0.0095),
            "heating_supply_air_hr_range": (0.0035, 0.0045),
            "cooling_design_air_flow_method": "DesignDayWithLimit",
            "heating_design_air_flow_method": "DesignDay"
        },
        "non_residential": {
            "cooling_supply_air_temp_range": (12.0, 14.0),
            "heating_supply_air_temp_range": (40.0, 45.0),
            # ...
        }
    },
    "post_calibration": {
        # Fixed values after calibration
    }
}
```

### 5.2 Geometry Lookup (geomz/geometry_lookup.py)

```python
geometry_lookup = {
    "non_residential": {
        "Office Function": {
            "pre_calibration": {
                "has_core": True,
                "perimeter_depth_range": (2.5, 3.5)
            },
            "post_calibration": {
                "has_core": True,
                "perimeter_depth_range": (3.0, 3.0)  # Fixed
            }
        },
        # ... other building types
    },
    "residential": {
        "Apartment": {
            "pre_calibration": {
                "has_core": False,
                "perimeter_depth_range": (1.8, 2.3)
            }
        },
        # ...
    }
}
```

### 5.3 DHW Lookup with NTA 8800 Values (DHW/dhw_lookup.py)

```python
dhw_lookup = {
    "TABLE_13_1_KWH_PER_M2": {
        "Meeting Function": 2.8,      # kWh/m²/year
        "Office Function": 1.4,
        "Healthcare Function": 15.3,  # Hospitals use much more
        "Sport Function": 12.5,
        # ...
    },
    "pre_calibration": {
        "Apartment": {
            "occupant_density_m2_per_person_range": (25.0, 35.0),
            "liters_per_person_per_day_range": (45.0, 55.0),
            "default_tank_volume_liters_range": (900.0, 1100.0),
            "default_heater_capacity_w_range": (18000.0, 22000.0),
            "setpoint_c_range": (58.0, 60.0),
            # Schedule fractions
            "sched_morning_range": (0.5, 0.7),
            "sched_peak_range": (0.9, 1.1),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.5, 0.8)
        },
        # ...
    }
}
```

### 5.4 Ground Temperature Lookup (tempground/groundtemp_lookup.py)

```python
groundtemp_lookup = {
    "pre_calibration": {
        "January": (2.0, 3.0),
        "February": (3.5, 5.0),
        "March": (4.0, 6.0),
        # ... monthly values
    },
    "post_calibration": {
        "January": (2.61, 2.61),  # Fixed calibrated values
        # ...
    }
}
```

---

## 6. Validation and Error Handling

### 6.1 Calibration Objectives (cal/calibration_objectives.py)

**Error Metrics**:

1. **RMSE (Root Mean Square Error)**:
   ```python
   def _rmse(sim: np.ndarray, obs: np.ndarray) -> float:
       return np.sqrt(np.mean((sim - obs) ** 2))
   ```

2. **CVRMSE (Coefficient of Variation)**:
   ```python
   def _cvrmse(sim: np.ndarray, obs: np.ndarray) -> float:
       rmse = CalibrationObjective._rmse(sim, obs)
       mean_obs = np.mean(obs)
       if mean_obs == 0:
           return float('inf')
       return (rmse / mean_obs) * 100
   ```

3. **R² (Coefficient of Determination)**:
   ```python
   def _r2(sim: np.ndarray, obs: np.ndarray) -> float:
       ss_res = np.sum((obs - sim) ** 2)
       ss_tot = np.sum((obs - np.mean(obs)) ** 2)
       return 1 - (ss_res / ss_tot)
   ```

4. **MAPE (Mean Absolute Percentage Error)**:
   ```python
   def _mape(sim: np.ndarray, obs: np.ndarray) -> float:
       mask = obs != 0
       return np.mean(np.abs((obs[mask] - sim[mask]) / obs[mask])) * 100
   ```

### 6.2 ASHRAE Guideline 14 Criteria

```python
def create_ashrae_objectives(variables: List[str], 
                            hourly_cvrmse: float = 30.0,
                            monthly_nmbe: float = 10.0):
    # ASHRAE 14: Hourly CVRMSE < 30%, Monthly NMBE < 10%
```

---

## 7. Scheduling Logic

### 7.1 DHW Schedule Creation (DHW/schedules.py)

```python
def create_dhw_schedules(idf, schedule_name_suffix="DHW", setpoint_c=60.0,
                        morning_val=0.7, peak_val=1.0, 
                        afternoon_val=0.2, evening_val=0.8):
    
    # Usage fraction schedule
    frac_sched = idf.newidfobject("SCHEDULE:COMPACT")
    frac_sched.Field_3 = f"Until: 06:00, 0.0"
    frac_sched.Field_4 = f"Until: 08:00, {morning_val:.2f}"    # Morning
    frac_sched.Field_5 = f"Until: 10:00, {peak_val:.2f}"       # Peak
    frac_sched.Field_6 = f"Until: 17:00, {afternoon_val:.2f}"  # Afternoon
    frac_sched.Field_7 = f"Until: 21:00, {evening_val:.2f}"    # Evening
    frac_sched.Field_8 = f"Until: 24:00, {morning_val:.2f}"    # Night
```

### 7.2 Lighting Schedules (Elec/schedules.py)

```python
SCHEDULE_DEFINITIONS = {
    "Residential": {
        "Apartment": {
            "weekday": [
                (0, 6, 0.02),   # Night: 2% lighting
                (6, 8, 0.20),   # Morning: 20%
                (8, 18, 0.05),  # Day: 5% (people at work)
                (18, 23, 0.40), # Evening: 40%
                (23, 24, 0.02)  # Late night: 2%
            ],
            "weekend": [
                (0, 8, 0.04),   # Night/morning: 4%
                (8, 22, 0.30),  # Day: 30%
                (22, 24, 0.04)  # Night: 4%
            ],
        },
        # ...
    },
    "Non-Residential": {
        "Office Function": {
            "weekday": [
                (0, 7, 0.02),   # Unoccupied
                (7, 8, 0.15),   # Early arrivals
                (8, 12, 0.80),  # Morning peak
                (12, 13, 0.30), # Lunch
                (13, 17, 0.80), # Afternoon peak
                (17, 18, 0.25), # Late leavers
                (18, 24, 0.02)  # Unoccupied
            ],
            "weekend": [(0, 24, 0.02)],  # Minimal
        },
        # ...
    }
}
```

---

## 8. EnergyPlus Objects Creation

### 8.1 Zone Creation
- Uses perimeter/core zoning algorithm
- Core zone created if `has_core = True` and building is large enough
- Perimeter zones created based on `perimeter_depth` parameter

### 8.2 Material Properties Assignment

**Thermal Resistance Calculation**:
```python
# For known R-value, derive conductivity
if mat_opq["obj_type"] == "MATERIAL":
    thick = mat_opq["Thickness"]
    if r_val != 0:
        mat_opq["Conductivity"] = thick / r_val
elif mat_opq["obj_type"] == "MATERIAL:NOMASS":
    mat_opq["Thermal_Resistance"] = r_val
```

### 8.3 Water Heater Object
- Type: `WaterHeater:Mixed`
- Parameters: Volume, capacity, setpoint, schedules
- Connected to water use equipment

---

## 9. Mathematical Formulas and Calculations

### 9.1 Particle Swarm Optimization (PSO) Velocity Update

```python
# Velocity update equation
velocities[i, j] = (
    current_inertia * velocities[i, j] +
    self.cognitive * r1 * (pbest_positions[i, j] - positions[i, j]) +
    self.social * r2 * (gbest_position[j] - positions[i, j])
)

# Position update
positions[i, j] += velocities[i, j]
```

### 9.2 Differential Evolution Mutation

```python
# DE/best/1/bin strategy
mutant = best_individual + self.mutation_factor * (population[r1] - population[r2])

# DE/rand/2/bin strategy
mutant = population[r1] + self.mutation_factor * (
    (population[r2] - population[r3]) + (population[r4] - population[r5])
)
```

### 9.3 Shading Surface Creation
- Vertices defined in 3D space: `[x, y, z]`
- Polygon-based surfaces with transmittance schedules

---

## 10. File I/O Operations

### 10.1 Parquet File Format
- Used for efficient storage of time series data
- Compressed columnar format
- Schema preservation

### 10.2 File Naming Conventions

**Time Series Files**:
```
var_{variable_name}_{unit}_{frequency}_b{building_id}.parquet
```

**Base Data**:
```
base_all_{frequency}.parquet
```

### 10.3 Directory Structure
```
parsed_data/
├── timeseries/
│   ├── base_all_hourly.parquet
│   ├── base_all_daily.parquet
│   └── base_all_monthly.parquet
├── metadata/
│   └── schedules.parquet
└── comparisons/
    └── var_*.parquet
```

---

## 11. Database Operations and SQL Queries

### 11.1 Main Time Series Extraction Query

```sql
SELECT 
    t.TimeIndex,
    CASE 
        WHEN t.Hour = 24 THEN datetime(printf('%04d-%02d-%02d 00:00:00', 
            t.Year, t.Month, t.Day), '+1 day')
        ELSE datetime(printf('%04d-%02d-%02d %02d:%02d:00', 
            t.Year, t.Month, t.Day, t.Hour, t.Minute))
    END as DateTime,
    rdd.Name as Variable,
    rdd.KeyValue as Zone,
    rd.Value,
    rdd.Units,
    rdd.ReportingFrequency
FROM ReportData rd
JOIN Time t ON rd.TimeIndex = t.TimeIndex
JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
WHERE rdd.Name IN (?)
AND t.EnvironmentPeriodIndex IN (
    SELECT EnvironmentPeriodIndex 
    FROM EnvironmentPeriods 
    WHERE EnvironmentType = 3  -- Run period
)
```

### 11.2 Available Outputs Query

```sql
SELECT 
    rdd.ReportDataDictionaryIndex,
    rdd.Name as VariableName,
    rdd.KeyValue,
    rdd.Units,
    rdd.ReportingFrequency,
    COUNT(DISTINCT rd.TimeIndex) as DataPoints
FROM ReportDataDictionary rdd
LEFT JOIN ReportData rd ON rdd.ReportDataDictionaryIndex = rd.ReportDataDictionaryIndex
GROUP BY rdd.ReportDataDictionaryIndex, rdd.Name, rdd.KeyValue, rdd.Units, rdd.ReportingFrequency
```

### 11.3 Variable Categories Mapping

```python
SQL_CATEGORY_MAPPINGS = {
    'energy_meters': [
        'Electricity:Facility', 'Electricity:Building', 'Electricity:HVAC',
        'Gas:Facility', 'Cooling:EnergyTransfer', 'Heating:EnergyTransfer'
    ],
    'site_weather': [
        'Site Outdoor Air Drybulb Temperature', 'Site Wind Speed',
        'Site Diffuse Solar Radiation Rate per Area'
    ],
    'hvac': [
        'Zone Air System Sensible Cooling Energy',
        'Zone Air System Sensible Heating Energy',
        'Zone Thermostat Heating Setpoint Temperature'
    ],
    # ... more categories
}
```

---

## 12. Configuration Constants and Defaults

### 12.1 Simulation Constants

```python
# Time step
TIMESTEPS_PER_HOUR = 4  # 15-minute intervals

# Convergence criteria
LOAD_CONVERGENCE_TOLERANCE = 0.04  # 4%
TEMPERATURE_CONVERGENCE_TOLERANCE = 0.2  # 0.2°C

# Shadow calculation
SHADOW_CALCULATION_FREQUENCY = 30  # days
```

### 12.2 Default Values

```python
# Building defaults
DEFAULT_FLOOR_HEIGHT = 3.0  # meters
DEFAULT_WWR = 0.3  # 30% window-to-wall ratio

# HVAC defaults
DEFAULT_COOLING_COP = 3.0
DEFAULT_HEATING_EFFICIENCY = 0.8

# DHW defaults
DEFAULT_WATER_HEATER_EFFICIENCY = 0.8
DEFAULT_SETPOINT_TEMP = 60.0  # °C
```

### 12.3 Frequency Hierarchy

```python
freq_hierarchy = {
    'timestep': 0,
    'hourly': 1,
    'daily': 2,
    'monthly': 3,
    'yearly': 4,
    'runperiod': 5
}
```

### 12.4 Unit Conversions

```python
# Energy conversions
J_TO_KWH = 2.77778e-7
KWH_TO_J = 3.6e6

# DHW conversion (NTA 8800)
KWH_TO_LITERS_AT_60C = 13.76  # liters per kWh
```

---

## Summary

The E_Plus_2040_py system implements a comprehensive building energy simulation workflow with:

1. **Sophisticated parameter assignment** using ranges and strategies
2. **Complex data transformations** for different time frequencies
3. **Detailed lookup tables** based on building types and calibration stages
4. **Advanced optimization algorithms** (PSO, DE, CMA-ES, NSGA-II)
5. **Comprehensive error metrics** for validation
6. **Flexible scheduling systems** for all building services
7. **Efficient data storage** using Parquet format
8. **Robust SQL queries** for EnergyPlus output extraction
9. **Modular architecture** allowing easy extension

The system follows NTA 8800 standards for the Netherlands and implements ASHRAE Guideline 14 for measurement and verification.