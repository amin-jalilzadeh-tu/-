```md
# E+ Builder & Calibrator: Ultra-Extended Markdown UI Design

Below is a **single Markdown document** that shows a highly detailed, step-by-step UI layout.  
It covers everything from a **Home/Landing** screen to **Advanced Analysis** and **Settings**,  
with extended notes for each step, potential error handling, and role-based functionality.

---

## Table of Contents

1. [Home / Landing](#home--landing)  
2. [Project / Simulation Setup](#2-project--simulation-setup)  
   1. [Project Metadata](#21-project-metadata-optional)  
   2. [Select Buildings](#22-select-buildings)  
   3. [Configure Overrides](#23-configure-overrides)  
   4. [Create IDFs & Run](#24-create-idfs--run)  
   5. [Post-Processing](#25-post-processing)  
3. [Advanced Analysis (Expert)](#3-advanced-analysis-expert)  
   1. [Scenario Modifications](#31-scenario-modifications)  
   2. [Validation](#32-validation)  
   3. [Sensitivity Analysis](#33-sensitivity-analysis)  
   4. [Surrogate Model](#34-surrogate-model)  
   5. [Calibration (Optimization)](#35-calibration-optimization)  
4. [Results & Visualization](#4-results--visualization)  
   1. [Runs Dashboard](#41-runs-dashboard)  
   2. [Time-Series / Aggregated Plots](#42-time-series--aggregated-plots)  
   3. [Scenario Comparison](#43-scenario-comparison)  
   4. [Validation Reports](#44-validation-reports)  
   5. [Calibration History & Best Fits](#45-calibration-history--best-fits)  
   6. [Sensitivity / Surrogate Visuals](#46-sensitivity--surrogate-visuals)  
5. [Settings / Administration (Optional)](#5-settings--administration-optional)

---

## Home / Landing

```md
# Welcome to E+ Builder & Calibrator

_A powerful tool to automate EnergyPlus simulations and optionally perform advanced scenario analyses or calibration._

[ **Get Started** ]
[ **View Documentation** ]

---

## User Role Selection (Optional)

If you have role-based features:

**Choose Your Access Level**:
- ( ) **Non-Expert**  
  Minimal override sections; advanced features hidden or locked.  
- ( ) **Moderate**  
  Some advanced overrides; scenario analysis partially available.  
- ( ) **Expert**  
  Full system unlocked (scenario generation, sensitivity, calibration, etc.).

[ **Confirm Role Selection** ]
```

- After confirming, the UI may hide or disable advanced modules for Non-experts.

---

## 2. Project / Simulation Setup

This section is the main workflow for selecting buildings, configuring overrides, generating IDFs, running simulations, and optionally post-processing the results.

---

### 2.1 Project Metadata (Optional)

```md
# Project Metadata

**Project Name**: [ ___________________ ]  
*If blank, defaults to "Untitled Project"*

**Description / Notes**:
```
(multi-line text area)
```
**Created By**: ( auto-filled user? e.g. “admin” )  

( ) **Save Project Info**  
```

- **Where to Store**: This data does not directly feed into EnergyPlus, but could be part of a `project_config.json`.

---

### 2.2 Select Buildings

Users can choose to retrieve buildings from a **database** or upload a **CSV**.  
In a real UI, you might have radio buttons or toggles:

```
Use Database?  ( x ) Yes   (  ) No
```

#### 2.2.1 Database Approach

```md
# Select Buildings (Database)

( x ) **Use Database**  

**filter_by**:
- ( ) pand_id
- ( ) pand_ids
- ( ) meestvoorkomendepostcode
- ( ) bbox_xy
- ( ) bbox_latlon

**Filter Criteria**:
(e.g. "pand_id": ["0383100000001369"])

[ **Preview Buildings** ]

Preview Table:
| building_id         | function    | area (m²) |
|---------------------|------------:|----------:|
| 0383100000001369    | Residential |  85       |
| 0383100000001370    | Residential | 120       |

[ **Confirm Selection** ]
```

- If bounding box is chosen, user enters `[minx, miny, maxx, maxy]` or uses a map.

#### 2.2.2 CSV Approach

```md
# Select Buildings (CSV)

(  ) **Use Database**  
( x ) **Use CSV**  

Upload **df_buildings.csv**:  
[ **Choose File** ]

Validation:  
- Found columns: `["building_id","function","area","lat","lon"]`  
- Row count: 212  
- Sample Rows:

| building_id | function       | area | lat   | lon   |
|------------:|---------------:|-----:|------:|------:|
| 100         | Residential    | 95   | 52.35 | 4.88  |
| 101         | Non-Residential| 300  | 52.36 | 4.90  |

[ **Confirm** ]
```

**Error Handling**:  
If columns are missing, display a red error:  
```
**Error**: CSV must contain "building_id" column. Found: ...
```

---

### 2.3 Configure Overrides

In the real UI, these would likely be tabs or an accordion. Here, we list them as sub-sections.

#### 2.3.1 Geometry

```md
# Geometry Overrides
*(mapped to geometry.json or user_config_geometry)*

**Possible param_name**: perimeter_depth, has_core

| building_id | building_type | param_name         | fixed_value | min_val | max_val |
|------------:|--------------:|-------------------:|-----------:|--------:|--------:|
| 101         | ( blank )     | ( ) perimeter_depth
                                 ( ) has_core       |    2.5     |  (N/A)  |  (N/A)  |

[ + Add Row ]

**Rules**:
- If `param_name = has_core`, `fixed_value` must be true/false.
- If using `fixed_value`, do not specify min_val/max_val.
```

#### 2.3.2 Envelope (Fenestration)

```md
# Envelope / Fenestration
*(mapped to fenestration.json)*

**Common param_name**: wwr, wall_u_value, roof_r_value, infiltration, etc.

| building_function | building_type | age_range    | scenario   | calibration_stage | building_id | param_name  | fixed_value | min_val | max_val |
|-------------------|--------------:|-------------:|-----------:|------------------:|------------:|------------:|-----------:|--------:|--------:|
| "residential"     | "Apartment"   | 1975-1991    | scenario1  | pre_calibration   | (blank)     | wwr         |            | 0.25    | 0.30    |
| (blank)           | "Apartment"   | (blank)      | scenario1  | (blank)           | 555         | wall_u_value|  1.2       | (N/A)   | (N/A)   |

[ + Add Row ]
```

#### 2.3.3 Shading

```md
# Shading Overrides
*(mapped to shading.json)*

| building_id | shading_type                | trans_schedule_name | Comments      |
|------------:|----------------------------:|---------------------:|--------------:|
| (blank)     | SHADING:BUILDING:DETAILED  | TreeTransSchedule   | for trees
|  333        | SHADING:SITE:DETAILED      | null                | site shading

[ + Add Row ]

**Possible shading_type**: SHADING:BUILDING:DETAILED, SHADING:SITE:DETAILED, etc.
```

#### 2.3.4 DHW

```md
# DHW Overrides
*(mapped to dhw.json)*

| building_id | dhw_key    | building_function | age_range      | param_name                        | fixed_value | min_val | max_val |
|------------:|-----------:|------------------:|---------------:|----------------------------------:|-----------:|--------:|--------:|
| 4136730     | "Apartment"| "Residential"     | "1992 - 2005"  | setpoint_c                        | 58.0       | (N/A)   | (N/A)   |
| (blank)     | (blank)    | "residential"     | (blank)        | occupant_density_m2_per_person    | (N/A)      | 30.0    | 40.0    |

[ + Add Row ]
```

#### 2.3.5 HVAC

```md
# HVAC Overrides
*(mapped to hvac.json)*

**param_name**: heating_day_setpoint, cooling_day_setpoint, etc.

| building_id | building_function | scenario    | calibration_stage | param_name                   | fixed_value | min_val | max_val |
|------------:|------------------:|------------:|------------------:|-----------------------------:|-----------:|--------:|--------:|
| (blank)     | "residential"     | scenario1   | pre_calibration   | heating_day_setpoint         |            | 19.0    | 20.0    |
| 10125       | "non_residential" | scenario2   | post_calibration  | max_heating_supply_air_temp  | 52.0       | (N/A)   | (N/A)   |

[ + Add Row ]
```

#### 2.3.6 Ventilation

```md
# Ventilation Overrides
*(mapped to vent.json)*

| building_id | building_function | scenario   | param_name        | fixed_value  | min_val | max_val |
|------------:|------------------:|----------:|------------------:|-------------:|--------:|--------:|
| (blank)     | "residential"     | scenario1 | infiltration_base |             | 1.2     | 1.5     |
| 111222      | "residential"     | scenario1 | system_type       | "D"         | (N/A)   | (N/A)   |

[ + Add Row ]

Example error check: if infiltration_base < 0, show "Invalid infiltration".
```

#### 2.3.7 Lighting

```md
# Lighting Overrides
*(mapped to lighting.json)*

**param_name**: lights_wm2, parasitic_wm2, td/tn for hours, fraction_radiant, etc.

| building_id | building_type     | age_range   | param_name                | fixed_value | min_val | max_val |
|------------:|------------------:|-----------:|--------------------------:|-----------:|--------:|--------:|
| 777         | "Healthcare"      | (blank)    | lights_wm2               |           | 18.5    | 20.0    |
| (blank)     | "Retail Function" | Pre-1980   | td                       | 3000       | (N/A)   | (N/A)   |

[ + Add Row ]
```

#### 2.3.8 EPW & Climate

```md
# EPW & Climate
*(mapped to epw.json)*

| building_id | desired_year | fixed_epw_path               | override_year_to | epw_lat | epw_lon |
|------------:|------------:|-----------------------------:|-----------------:|--------:|--------:|
| 101         | (blank)     | "C:/EPWs/Rotterdam2030.epw"  | (N/A)            | (N/A)   | (N/A)   |
| (blank)     | 2020        | (blank)                      | 2050             | 52.0    | 4.5     |

[ + Add Row ]
```

#### 2.3.9 (Locked) Elec Equipment, Ground Temp, Sizing

```md
# Elec Equipment / Ground Temp / Sizing (Placeholder)

**Locked** or “Coming Soon.” 
- If user is Expert and code is ready, these might be partially available. 
```

---

### 2.4 Create IDFs & Run

```md
# Create IDFs

**Scenario Name**: [ scenario1 ]  
**Calibration Stage**: ( ) pre_calibration  ( ) post_calibration  ( ) none  

**Picking Strategy**:
( ) midpoint   ( ) random_uniform   ( ) manual  
**Random Seed**: [ 42 ]

**EnergyPlus**:
- IDD File: [ "EnergyPlus/Energy+.idd" ]
- Base IDF File: [ "EnergyPlus/Minimal.idf" ]
- Output IDF Dir: [ "output_IDFs" ]

[ Generate IDF ]

---

( ) **Run Simulation immediately** after IDF creation?  
  - num_workers: [ 8 ]  
  - ( ) Force Overwrite?  

[ Start Simulation ]

**Progress Log**:
```
IDF creation for building 101...
IDF creation done.
Running E+...
Simulation complete. Output in "Sim_Results/..."
```
```

---

### 2.5 Post-Processing

```md
# Post-Processing

( ) perform_post_process ?

**Aggregation**:
- Convert to Daily? ( ) yes
  daily_aggregator: ( ) mean ( ) sum ( ) max ...
- Convert to Monthly? ( ) yes
  monthly_aggregator: ( ) mean ( ) sum ( ) max ...

**Output CSV**:
- "merged_as_is.csv" 
- "merged_daily_mean.csv"

[ Aggregate Results ]
```

---

## 3. Advanced Analysis (Expert)

If user is Non-expert, these may be hidden or greyed out.

### 3.1 Scenario Modifications

```md
# Scenario Modifications

( ) perform_modification ?

**building_id**: [ 4136730 ]  
**num_scenarios**: [ 5 ]  

**picking_method**: 
- ( ) random_uniform 
- ( ) scale_around_base 
- ( ) offset_half  
**picking_scale_factor**: [ 0.5 ]

( ) run_simulations ?  
( ) perform_post_process ?

**Scenario CSV** references:
- scenario_params_hvac.csv
- scenario_params_dhw.csv
...

[ Generate Multi-Scenario ]
```

### 3.2 Validation

```md
# Validation

( ) perform_validation ?

**Validation Config**:
- real_data_csv: [ data/mock_merged_daily_mean.csv ]
- sim_data_csv:  [ results/merged_daily_mean.csv ]
- threshold_cv_rmse: [ 30.0 ]
- variables_to_compare: 
  - [ ] Electricity:Facility 
  - [ ] Heating:EnergyTransfer 
  ...
( ) skip_plots ?

[ Run Validation ]

(Output => validation_report_base.csv or scenario version)
```

### 3.3 Sensitivity Analysis

```md
# Sensitivity Analysis

( ) perform_sensitivity ?

**method**: 
( ) correlation  ( ) morris  ( ) sobol

**results_csv**: [ results_scenarioes/merged_daily_mean_scenarios.csv ]
**target_variable**: [ "Heating:EnergyTransfer [J](Hourly)" ]

If morris:
- n_morris_trajectories: [10]
- num_levels: [4]

If sobol:
- n_sobol_samples: [1000]

[ Analyze Sensitivity ]
```

### 3.4 Surrogate Model

```md
# Surrogate Model

( ) perform_surrogate ?

- scenario_folder: [ scenarios ]
- results_csv: [ results_scenarioes/merged_daily_mean_scenarios.csv ]
- target_variable: [ "Heating:EnergyTransfer [J](Hourly)" ]
- model_out: [ "heating_surrogate_model.joblib" ]
- cols_out:  [ "heating_surrogate_columns.joblib" ]
- test_size: [ 0.3 ]

[ Train Surrogate ]

(Output => R², MSE, etc.)
```

### 3.5 Calibration (Optimization)

```md
# Calibration

( ) perform_calibration ?

- scenario_folder: [ scenarios ]
- scenario_files: [ "scenario_params_dhw.csv", "scenario_params_elec.csv" ]
- method: ( ) ga  ( ) bayes  ( ) random
- ( ) use_surrogate ?

**GA**:
 - ga_pop_size: [10]
 - ga_generations: [5]
 - crossover_prob: [0.7]
 - mutation_prob: [0.2]

**Bayes**:
 - bayes_n_calls: [15]

**Random**:
 - random_n_iter: [20]

real_data_csv: [ data/mock_merged_daily_mean.csv ]

output_history_csv: [ "calibration_history.csv" ]
best_params_folder: [ "calibrated" ]

[ Run Calibration ]
```

---

## 4. Results & Visualization

### 4.1 Runs Dashboard

```md
# Runs Dashboard

| Run Name    | Buildings    | Date/Time        | Status     |
|-------------|------------:|------------------|-----------:|
| scenario1   | 101, 202    | 2025-03-10 14:23 | Completed  |
| base_run    | 10 bldgs    | 2025-03-09 10:00 | Completed  |

[ Refresh ]  
[ View Results -> ] leads to next screens
```

### 4.2 Time-Series / Aggregated Plots

```md
# Time-Series / Aggregated Plots

**Select CSV**:
( ) merged_as_is.csv  
( ) merged_daily_mean.csv  
( ) merged_as_is_scenarios.csv  
( ) merged_daily_mean_scenarios.csv  

**Filter**:
- building_id: [   ]  
- scenario: [ scenario1 ]  

**Variables**:
- [x] Electricity:Facility
- [ ] Heating:EnergyTransfer

**Chart Type**:
( ) Line   ( ) Area   ( ) Bar

[ Generate Plot ]

-- Chart Display --

[ Download PNG ]  [ Export CSV Subset ]
```

### 4.3 Scenario Comparison

```md
# Scenario Comparison

**Which CSV**?
( ) merged_as_is_scenarios.csv  
( ) merged_daily_mean_scenarios.csv  

**Select Scenarios**:
- [ scenario1 ]
- [ scenario2 ]
- [ scenario3 ]

**Metric**:
( ) total annual usage  
( ) monthly average  
( ) time-series overlay  

[ Compare ]

-- Graph or table comparing selected scenarios --
```

### 4.4 Validation Reports

```md
# Validation Reports

**Available**:
- validation_report_base.csv
- validation_report_scenarios.csv

Choose: ( ) validation_report_scenarios.csv

| building_id | variable                              | MBE% | CV(RMSE)% | pass/fail |
|------------:|---------------------------------------:|-----:|----------:|----------:|
| 101         | Electricity:Facility [J](Hourly)       | 3.2  | 28.0      | pass      |
| 101         | Heating:EnergyTransfer [J](Hourly)     | -1.3 | 35.0      | fail      |

[ Download CSV ]  

If skip_plots=false, show “Compare Real vs Sim Plot?”
```

### 4.5 Calibration History & Best Fits

```md
# Calibration History & Best Fits

**calibration_history.csv**:

| generation | best_error |
|-----------:|----------:|
| 1          | 4500      |
| 2          | 2800      |
| 3          | 2000      |
| 4          | 1800      |
| 5          | 1500      |

( Plot: generation vs error )

**Best Parameters** located in "calibrated/" folder:
- scenario_params_dhw.csv
- scenario_params_elec.csv

[ Apply Best-Fit to Default Overrides? ] 
```

### 4.6 Sensitivity / Surrogate Visuals

```md
# Sensitivity & Surrogate Visuals

## Sensitivity
If we have e.g. morris or sobol outputs:

| param_name        | mu* or index | ranking |
|------------------:|-------------:|--------:|
| infiltration_base | 0.75         |  1      |
| occupant_density  | 0.55         |  2      |

( ) Show bar chart for param influence.

## Surrogate
If a model was trained:
- R² = 0.92, MSE=300
- ( ) Plot predicted vs. actual

[ Export Chart ]
```

---

## 5. Settings / Administration (Optional)

```md
# Settings / Administration

## 5.1 User Management
(If multi-user environment)

| Username | Role       | Last Login         |
|----------|-----------:|--------------------|
| admin    | Expert     | 2025-03-10 14:00   |
| staff1   | Moderate   | 2025-03-09 16:32   |

[ Add User ]  [ Edit Role ]  [ Remove User ]

## 5.2 Global Defaults
- EnergyPlus Folder: [ C:\EnergyPlus22.2\ ]
- Default aggregator: ( ) mean ( ) sum
- Email notifications: ( ) On  ( ) Off

[ Save Settings ]

## 5.3 Data / Storage Maintenance
- Output directory: [ D:\E_Plus_2030_py\output ]
- [ Clean old runs older than X days ]
- [ Export entire config as ZIP ]
```

---

## Additional Notes

1. **Wizard vs. Tabs**  
   - You may implement these sections as a step-by-step wizard (Next/Back) or separate tabs.  
2. **Role-Based Hiding**  
   - Non-expert sees only a portion of these steps. For instance, they might skip advanced overrides or scenario analysis.  
3. **Validation**  
   - Show inline errors if fixed_value or min_val/max_val are invalid (e.g., negative infiltration_base).  
4. **Backend**  
   - Each sub-section (e.g., “HVAC Overrides”) corresponds to a JSON array that merges into the final config.  
5. **Progress / Logs**  
   - “Generate IDF” and “Run Simulations” typically trigger asynchronous tasks; a progress bar or job queue can be displayed.  
6. **File Download**  
   - CSV and output files (like “merged_as_is.csv”) can be downloaded or previewed.  
7. **User Experience**  
   - For large sets of overrides, a table-based approach with “+Add Row” is crucial. Possibly an option to **import** overrides from CSV or **export** them for reuse.

This single Markdown code block acts as a **complete reference** for building a front-end or a user guide. You can trim or rearrange sections to fit your specific project needs. 
```