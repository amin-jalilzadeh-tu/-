import streamlit as st

def main():
    st.set_page_config(page_title="E+ Builder & Calibrator", layout="wide")
    
    st.title("E+ Builder & Calibrator")
    st.markdown("_Automate EnergyPlus simulations, advanced scenarios, and calibrations—no coding required!_")

    # ------------------------------------------------------------------------------------
    # TABLE OF CONTENTS (Optional)
    # ------------------------------------------------------------------------------------
    with st.expander("Table of Contents", expanded=False):
        st.markdown("""
1. [Home / Landing](#home--landing)  
2. [Project / Simulation Setup](#project--simulation-setup)  
   1. [Project Metadata](#11-project-metadata-optional)  
   2. [Select Buildings](#12-select-buildings)  
   3. [Configure Overrides](#13-configure-overrides)  
   4. [Create IDFs & Run](#14-create-idfs--run)  
   5. [Post-Processing](#15-post-processing)  
3. [Advanced Analysis](#advanced-analysis-expert-or-unlocked)  
   1. [Scenario Modifications](#31-scenario-modifications)  
   2. [Validation](#32-validation)  
   3. [Sensitivity Analysis](#33-sensitivity-analysis)  
   4. [Surrogate Model](#34-surrogate-model)  
   5. [Calibration (Optimization)](#35-calibration-optimization)  
4. [Results & Visualization](#results--visualization)  
   1. [Runs Dashboard](#41-runs-dashboard)  
   2. [Time-Series / Aggregated Plots](#42-time-series--aggregated-plots)  
   3. [Scenario Comparison](#43-scenario-comparison)  
   4. [Validation Reports](#44-validation-reports)  
   5. [Calibration History & Best Fits](#45-calibration-history--best-fits)  
   6. [Sensitivity / Surrogate Visuals](#46-sensitivity--surrogate-visuals)  
5. [Settings / Administration](#settings--administration-optional)
        """)
        st.markdown("""
**Tip**: Click any section heading in the table of contents to jump there
(if you run this with `st.markdown` anchor tags). In a real app, 
you might prefer tabs or a sidebar for navigation.
        """)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 1) HOME / LANDING
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    st.header("1. Home / Landing")
    st.markdown("""
**Welcome to E+ Builder & Calibrator**

_Automate EnergyPlus simulations, advanced scenarios, and calibrations—no coding required!_

**Get Started** | **Documentation**
    
---
    
## Role Selection

**Select Your User Role**:
- ( ) **Non-Expert** (simple workflow, minimal overrides)
- ( ) **Moderate** (some advanced features)
- ( ) **Expert** (all features unlocked: scenarios, calibration, etc.)

[ **Confirm** ]
    
> **Tip**: If you prefer a single role for everyone, you could omit this step or move it to Settings.
    """)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 2) PROJECT / SIMULATION SETUP
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    st.header("2. Project / Simulation Setup")

    # 2.1 Project Metadata
    st.subheader("2.1 Project Metadata (Optional)")
    st.markdown("""
**Project Name**: [ ________________ ]  
*(If blank, defaults to "Untitled Project")*

**Description / Notes**:  
(Multi-line text area—could accept Markdown for rich formatting)

**Created By**: [auto-filled user, e.g. “admin”]

( ) **Save Project Info**

> **Usage Note**: Non-Expert users might skip this entirely.
> **Data**: This doesn’t directly map to EnergyPlus config, but can be stored for reference.
    """)

    # 2.2 Select Buildings
    st.subheader("2.2 Select Buildings")
    st.markdown("""
You can show two options:
1. **Use Database** (with bounding box, pand_id, etc.)
2. **Use CSV** (upload df_buildings.csv)

### 2.2.1 Database Approach

> **Filter Method**: pand_id, pand_ids, postcode, bbox_xy, bbox_latlon.  
> **Preview**: show matched buildings in a table, then confirm.

### 2.2.2 CSV Approach

> Upload `df_buildings.csv`. Show quick validation (e.g., # columns, sample rows).
    """)

    # 2.3 Configure Overrides
    st.subheader("2.3 Configure Overrides")
    st.markdown("""
**We present each override type in a sub-section.** 
In practice, you might use tabs or accordions for each override file 
(geometry.json, fenestration.json, shading.json, etc.).

#### 2.3.1 Geometry
*(Mapped to `geometry.json`)*

| building_id | building_type | param_name         | fixed_value | min_val | max_val |
|------------:|--------------:|-------------------:|-----------:|--------:|--------:|
| 101         | (blank)       | perimeter_depth    | 2.5        | (N/A)   | (N/A)   |

#### 2.3.2 Envelope (Fenestration)
*(Mapped to `fenestration.json`)*

Etc.

#### 2.3.3 Shading
*(Mapped to `shading.json`)*

#### 2.3.4 DHW
*(Mapped to `dhw.json`)*

#### 2.3.5 HVAC
*(Mapped to `hvac.json`)*

#### 2.3.6 Ventilation
*(Mapped to `vent.json`)*

#### 2.3.7 Lighting
*(Mapped to `lighting.json`)*

#### 2.3.8 EPW & Climate
*(Mapped to `epw.json`)*

*(**Locked**: Elec Equipment, Ground Temp, Sizing if not ready)* 
    """)

    # 2.4 Create IDFs & Run
    st.subheader("2.4 Create IDFs & Run")
    st.markdown("""
**Scenario Name**: [ scenario1 ]  
**Calibration Stage**: pre_calibration / post_calibration / none  
**Picking Strategy**: midpoint / random / manual, etc.  
**Random Seed**: [ 42 ]  

**EnergyPlus** Settings:  
- IDD file: [ EnergyPlus/Energy+.idd ]  
- Base IDF: [ EnergyPlus/Minimal.idf ]  
- Output directory: [ output_IDFs ]

[ **Generate IDF** ]

**Run Simulations Immediately?**  
- ( ) Yes  => **num_workers**? Force Overwrite?  
[ **Start Simulation** ]

_(Log/Console output shown here)_
    """)

    # 2.5 Post-processing
    st.subheader("2.5 Post-Processing")
    st.markdown("""
( ) perform_post_process ?  

**If yes**:
- Convert to Daily? aggregator: mean, sum, max, pick_first_hour  
- Convert to Monthly? aggregator?  
**Output CSV**: merged_as_is.csv, merged_daily_mean.csv, etc.

[ **Aggregate Results** ]
    """)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 3) ADVANCED ANALYSIS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    st.header("3. Advanced Analysis (Expert or Unlocked)")

    # 3.1 Scenario Modifications
    st.subheader("3.1 Scenario Modifications")
    st.markdown("""
( ) perform_modification ?  
**Focus**: building_id, num_scenarios, picking_method, scale_factor, etc.  
**Run simulations**? **Post-process**?

[ **Generate** ] [ **Run** ]
    """)

    # 3.2 Validation
    st.subheader("3.2 Validation")
    st.markdown("""
( ) perform_validation ?  

**real_data_csv** vs. **sim_data_csv**  
**variables_to_compare**, threshold_cv_rmse, skip_plots?

[ **Run Validation** ] => Outputs validation_report.csv
    """)

    # 3.3 Sensitivity
    st.subheader("3.3 Sensitivity Analysis")
    st.markdown("""
( ) perform_sensitivity ?

**Method**: correlation / morris / sobol  
**results_csv** / **target_variable(s)**  
**Morris** => n_trajectories, num_levels  
**Sobol** => n_sobol_samples  

[ **Analyze** ] => multi_corr_sensitivity.csv or similar
    """)

    # 3.4 Surrogate
    st.subheader("3.4 Surrogate Model")
    st.markdown("""
( ) perform_surrogate ?

scenario_folder, results_csv, target_variable, model_out, test_size, etc.

[ **Train Surrogate** ]
    """)

    # 3.5 Calibration
    st.subheader("3.5 Calibration (Optimization)")
    st.markdown("""
( ) perform_calibration ?

**scenario_files**: scenario_params_dhw.csv, scenario_params_elec.csv  
method: ga / bayes / random  
( ) use_surrogate?  
**real_data_csv**: [ data/mock_merged_daily_mean.csv ]  

**GA**: pop_size, generations, crossover_prob, mutation_prob  
**Bayes**: bayes_n_calls  
**Random**: random_n_iter

[ **Run Calibration** ] => calibration_history.csv, best_params_folder
    """)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 4) RESULTS & VISUALIZATION
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    st.header("4. Results & Visualization")

    # 4.1 Runs Dashboard
    st.subheader("4.1 Runs Dashboard")
    st.markdown("""
| Run Name   | Buildings    | Date/Time         | Status     |
|------------|------------:|-------------------|-----------:|
| scenario1  | 101,202     | 2025-03-10 14:23  | Completed  |
| base_run   | 10 bldgs    | 2025-03-09 10:00  | Completed  |

[ Refresh ] [ View Results ]
    """)

    # 4.2 Time-Series / Aggregated Plots
    st.subheader("4.2 Time-Series / Aggregated Plots")
    st.markdown("""
Select CSV: merged_as_is.csv, merged_daily_mean.csv, ...
Filter by building, scenario, variables => produce line/bar chart.

[ Generate Plot ]
    """)

    # 4.3 Scenario Comparison
    st.subheader("4.3 Scenario Comparison")
    st.markdown("""
**Which CSV**: merged_as_is_scenarios.csv or daily_mean_scenarios.csv  
Select scenarios => compare annual or monthly or time-series difference.
    """)

    # 4.4 Validation Reports
    st.subheader("4.4 Validation Reports")
    st.markdown("""
**Available**:
- validation_report_base.csv
- validation_report_scenarios.csv

| building_id | variable            | MBE%  | CV(RMSE)% | pass? |
|------------:|--------------------:|------:|----------:|-----:|
| 101         | Electricity:Facility|  3.2  |   28.0    | pass |
    """)

    # 4.5 Calibration History & Best Fits
    st.subheader("4.5 Calibration History & Best Fits")
    st.markdown("""
Example chart: iteration vs error.

| generation | best_error |
|-----------:|----------:|
|     1      |   4500    |
|     2      |   2800    |
|     3      |   2000    |
|     4      |   1800    |
|     5      |   1500    |

Outputs in `calibrated/`.
    """)

    # 4.6 Sensitivity / Surrogate Visuals
    st.subheader("4.6 Sensitivity / Surrogate Visuals")
    st.markdown("""
**Sensitivity**: 
- If correlation => param_name vs correlation
- If Morris => bar chart with mu* vs sigma

**Surrogate**:
- R², RMSE, predicted vs actual chart
    """)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 5) SETTINGS / ADMINISTRATION
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    st.header("5. Settings / Administration (Optional)")
    st.markdown("""
**5.1 User Management**  
If multi-user system: show table of users, roles, last login, etc.

**5.2 Global Defaults**  
- E+ Installation Folder:  
- Default aggregator: mean/sum  
- Notification Email:  

**5.3 Data/Storage Maintenance**  
- Output Directory, Clean old runs, Export config as ZIP, etc.
    """)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # END
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    st.markdown("---")
    st.markdown("**End of UI Structure** — All placeholders above can be replaced with real forms & logic.")

if __name__ == "__main__":
    main()
