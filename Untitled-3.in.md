 this is the code thatother person was working on it, now  he quit at middle and gave to me. but now ineed to finalise it. but frst i need to understand what is done, what need to be done and modify when is needed. first i provide the overall view, then after you havig undertsnading we will work on the codes i provide. so give detailed and easy to understand steps to do.

Below is a **textual summary** of the workflow describing the loop from initial data through calibration, re-runs, and analysis:

ok. so first lets work on this part of creating df file.

so, we have this overriding:
1: that is for permenent replacing lookup tables with excel file, 2: then also we have this lookup overriding over memory. 3: then we have this partly overriding with user config

number 1 will be happen in our main py file, but for number 2 and 3 will be for idf creation part.

for now, i have the following code, i made it previously for idf creation.

so, now want to integrate with this main py file.

for some parts need to be as main create idf file, then some parts to be in main py file. so now lets do it.

first give full code for main creation idf file, then give full code of this main. py file

Below is a **step-by-step** guide to help you **understand, finalize, and integrate** all the pieces of this workflow. The goal is to ensure you can orchestrate IDF creation, simulation runs, validation, calibration, and scenario modifications in a coherent way. I’ve broken it into logical tasks, each explaining what is already done, what still needs to be done, and how it fits into the larger workflow.

---

## 1. **Understand the Big-Picture Workflow**

1. **Main Data & Lookup Tables**

   - You have CSV/Excel data (in `data/` and `lookup_xlx/`) describing buildings and default parameters (e.g., geometry, fenestration, HVAC, DHW, etc.).
   - **User configuration files** (`user_configs/`) can override default lookup data.
2. **Create IDF File**

   - For each building, use the base data + lookups + user overrides to generate an EnergyPlus IDF.
   - Output the parameter assignments (e.g., final WWR, infiltration rates) to CSV in `output/assigned/`.
3. **Run Simulations**

   - EnergyPlus runs these IDF files (`output_IDFs/` or similar directory) and produces CSV/HTML output in `Sim_Results/`.
4. **Validation**

   - Compare simulations with real data in `validation/`.
   - Generate metrics (MBE, CV(RMSE), etc.) in a validation report.
5. **Decision Point**

   - If results match thresholds, you can stop.
   - If not, you re-run with new/modified parameters (calibration, scenario generation, etc.).
6. **Generate More IDFs & Rerun**

   - Update parameters (based on either user rules, calibration methods, or scenario variations).
   - Regenerate IDFs, run again, produce new output.
7. **Analysis (Sensitivity / Surrogate / Optimization)**

   - Optionally, do deeper analyses (in `cal/`, `sensitive/`, `surrogate/`) to find which parameters matter most, build surrogate models, or do optimization.
8. **Reporting**

   - Keep track of assigned parameters, simulation results, validation outcomes.
   - Summaries go into `output/`, e.g. `validation_report.csv`, scenario param CSVs, or any optimization results.
9. **Update Post-Calibration Values**

   - Once satisfied, feed these “best-fit” or “tuned” values back into the default lookups or user configs for future runs.

---

## 2. **Set Up the Main Orchestration Script**

### **Task**: Create/Finalize `main.py`

- **Purpose**: This will be your high-level orchestrator that:
  1. Reads user configs and main data.
  2. Calls the IDF creation script (`main_create_idf.py` or a set of modules).
  3. Runs EnergyPlus simulations (via `epw/run_epw_sims.py` or a direct function call).
  4. Calls validation routines (in `validation/`).
  5. Checks if thresholds are met; if not, triggers scenario generation/calibration steps from `modification/` or `cal/`.
  6. Summarizes and saves final results.

**Steps to do**:

1. **Import** modules that parse user configs (`lookup_xlx` or JSON in `user_configs/`).
2. **Read** CSV data from `data/` (like `df_buildings.csv`, `df_focus.csv`).
3. **Invoke** the function(s) in `main_create_idf.py` to generate IDFs.
4. **Run** the simulation script from `epw/run_epw_sims.py`.
5. **Parse** results (using `postproc/merge_results.py`) and do validation (using `validation/validate_results.py`).
6. **Decide** if you repeat or move on. Possibly call calibration or scenario modifications if needed.
7. **Summarize** final outputs, or call the advanced modules in `cal/`, `sensitive/`, `surrogate/`.

**What’s left**:

- You likely need to define in `main.py` how you want each step triggered (e.g., command-line arguments, function calls, or a config parameter like `"mode": "calibrate"`).
- For user overrides, ensure you read JSON from `user_configs/` and pass the overrides down to the IDF creation modules.

---

## 3. **Linking User Configs & Lookup Tables**

- **Existing**: You have Excel lookups in `lookup_xlx/` and possible JSON configs in `user_configs/`.
- **Goal**: A code path that merges them (with user-config taking precedence) so that final parameter picks reflect any user-specified override or randomization range.

### **Task**: Build or Finalize a “Lookup Management” Module

- Could be in `main_create_idf.py` or a dedicated file like `lookup_manager.py`.
- **Responsibilities**:
  1. Read the Excel defaults (like `dhw_lookup.xlsx`, `hvac_lookup.xlsx`).
  2. Read user configs in JSON (like `dhw_lookup.json`, `hvac_lookup.json`).
  3. Merge/override them into final data structures.

**Steps to do**:

1. **Read** the default Excel data, parse them to Python dicts (some code might already exist in `dhw_overrides_from_excel.py`, `hvac_overrides_from_excel.py`, etc.).
2. **Read** the JSON user configs from `user_configs/`.
3. **Perform** merges/overrides (where JSON keys exist, they replace Excel).
4. **Pass** the final dictionary to the IDF creation step.

**What’s left**:

- Confirm the merges handle partial overrides (e.g., user only overrides infiltration rate, but leaves other fields as default).
- Possibly unify the “override” logic across all modules (DHW, HVAC, Fenestration, etc.) so it’s consistent.

---

## 4. **Creating the IDFs** (`main_create_idf.py`)

- **Existing**: `main_create_idf.py` imports many submodules (geometry, fenestration, lighting, etc.) and presumably has a `create_idf_for_building(...)` function.
- **Goal**: Ensure that user config overrides are applied properly, and that the assigned parameters are logged to CSV in `output/assigned/`.

### **Task**: Validate & Possibly Extend the IDF-Creation Steps

**Steps to do**:

1. **Check** each sub-module (e.g., `fenez/fenestration.py`, `DHW/water_heater.py`) to see if they can accept user override inputs or random picks from `user_configs/`.
2. **Confirm** that each assigned parameter is saved in the correct CSV (like `assigned_geometry.csv`, `assigned_dhw_params.csv`).
3. **Add** shading or other modules if they are not yet integrated (you mentioned shading code needs final hooking up).
4. **Ensure** the final IDF is saved to `output_IDFs/` or a user-specified folder.

**What’s left**:

- If you want the user config to define “pick infiltration from X to Y randomly,” you need to ensure that logic is present in the creation script.
- You might unify all “assignment logging” to a single function that writes to CSV, to keep it consistent across systems.

---

## 5. **Running Simulations** (`epw/run_epw_sims.py`)

- **Existing**: Code to run EnergyPlus in parallel, presumably using `simulate_all(...)`.
- **Goal**: Make sure it is triggered from `main.py` (or a similar orchestrator) and that you know where the results are stored.

### **Task**: Tie the Simulation Step into the Main Workflow

**Steps to do**:

1. In `main.py`, after IDFs are created, **call** `simulate_all(...)`.
2. **Ensure** the output path (like `output/Sim_Results/`) is correct.
3. Optionally **create** a function that checks if the simulation ran successfully (EnergyPlus error codes, presence of CSV output, etc.).

**What’s left**:

- Confirm if you want to parse or rename EnergyPlus outputs for clarity.
- Decide if the user can specify weather files from `epw_lookup`.

---

## 6. **Post-Processing** (`postproc/`)

- **Existing**: `merge_results.py` has `merge_all_results(...)` to aggregate CSV simulation outputs.
- **Goal**: Possibly unify post-processed results into a single “master CSV” for easy comparison to real data or for calibration input.

### **Task**: Integrate Post-Processing

**Steps to do**:

1. **After** simulations finish, call `merge_all_results(...)` from `main.py` or a dedicated script.
2. **Store** the merged result in `output/results/merged_*.csv`.
3. If needed, **append** building info or scenario info (so that you know which building/scenario each row belongs to).

**What’s left**:

- Confirm the merged data aligns with the structure of real data you’ll use for validation.
- Possibly allow user-specified time granularity (daily vs. hourly).

---

## 7. **Validation** (`validation/`)

- **Existing**:

  - `compare_sims_with_measured.py`, `metrics.py`, `validate_results.py`, `visualize.py`.
  - They compute MBE, CV(RMSE), NMBE, etc.
- **Goal**: Provide an automatic way to run these comparisons for each building or scenario that has “real” data.

### **Task**: Hook Validation into the Main Workflow

**Steps to do**:

1. **Check** if real data (in `output/real_data/`) is properly aligned in date/time with the simulation outputs.
2. In `main.py`, **call** a function from `validate_results.py` that:
   - Loads the simulated data from `merged_*.csv`.
   - Loads the measured data from `real_data_*.csv`.
   - Calculates validation metrics (MBE, CVRMSE, etc.).
   - Saves them to `output/validation_report.csv` or similar.
3. **Decide** how to handle partial or missing data.

**What’s left**:

- Possibly create your own “validation config” specifying the thresholds for pass/fail.
- Integrate a check: if pass < threshold => go to calibration.

---

## 8. **Calibration / Scenario Generation** (`cal/` and `modification/`)

- **Existing**:

  - `cal/` has modules for random search, GA, Bayesian (via scikit-optimize).
  - `modification/` has modules (`common_utils.py`, `hvac_functions.py`, etc.) to apply new parameters to IDFs or create new scenario CSVs.
- **Goal**: When validation is unsatisfactory, systematically change parameters and re-run.

### **Task**: Decide Your Calibration or Scenario Path

1. **Manual/Ad-hoc**: You create new scenarios in `modification/` by defining parameter ranges. You generate new IDFs, run them, see if it’s better.
2. **Automated**: Use the `CalibrationManager` or “scenario generator” in `cal/unified_calibration.py` to systematically propose new parameter sets.

**Steps to do**:

1. **Set** up a calibration “workflow” in `main.py`:
   - If fail: call `CalibrationManager.run_calibration(...)` or run the scenario-generation logic in `modification/main_modifi.py`.
2. **Use** `modification/common_utils.py` to create N new parameter sets, each set generating a new IDF.
3. **Run** simulations, do validation.
4. **Iterate** until thresholds are met or you reach iteration limit.

**What’s left**:

- Ensure you store the results of each scenario run (in `scenarios/` for param sets, and `scenario_idfs/` for IDFs).
- Make sure you track calibration/iteration steps in a “history log” or CSV.

---

## 9. **Advanced Analyses** (`sensitive/`, `surrogate/`, and `cal/` Extended)

- **Existing**:

  - `surrogate/` can build ML models from simulation data (e.g., using RandomForestRegressor).
  - `sensitive/` can run SALib-based sensitivity (Sobol, Morris).
  - `cal/` has more calibration approaches.
- **Goal**: Provide optional advanced workflows.

### **Task**: Wrap or Integrate into Main Orchestration (Optional)

1. **If** user wants a sensitivity analysis, run `unified_sensitivity.py` with relevant parameters.
2. **If** user wants surrogate-based calibration, let them build the surrogate (in `unified_surrogate.py`) and then optimize.
3. **If** user wants a direct Bayesian approach with scikit-optimize, call the relevant code in `unified_calibration.py`.

**What’s left**:

- Typically, these advanced features have their own “entry points.” You could unify them behind command-line arguments or function calls in `main.py` (e.g., `python main.py --mode=sensitivity`).

---

## 10. **Finalize Output Organization & Cleanup**

- **Existing**: You have `output/assigned/`, `output/results/`, `output/Sim_Results/`, etc.
- **Goal**: Consistent naming, logs, and the ability to clean up or archive old runs.

### **Task**: Standardize Folder & File Naming

1. **Decide** how you want scenario files named: e.g. `scenario_0_bldg_4136730.idf` or `building_4136730_scenario_0.idf`.
2. **Ensure** CSV logs in `assigned/` or `scenarios/` match the IDF names.
3. **Implement** a small utility to remove old simulation results or zip them if needed.

**What’s left**:

- Possibly rename some folders or files to be consistent.
- A final “housekeeping” script to manage old results is optional, but nice if you have many runs.

---

## 11. **Document & Verify**

1. **Document** each module:

   - Purpose, how it’s called, expected inputs, outputs.
   - This will help maintain the code once the original developer is gone.
2. **Create** a small “example flow” or “tutorial” with sample data to show new users how to run the pipeline.
3. **Check** each part in practice:

   - Manually run `main.py` for a single building.
   - Validate that the assigned CSVs, IDFs, simulation results, and final validations all appear.
   - If anything is missing or misaligned, fix it.

---

## 12. **Summary of To-Dos**

Below is a condensed list of action items you’ll want to tackle, in order:

1. **Main Orchestration (`main.py`)**

   - Write or update to orchestrate data reading, IDF creation, simulation, validation, iteration.
2. **User Config & Lookup Merging**

   - Confirm a single entry point merges Excel defaults + JSON overrides.
   - Ensure partial overrides are handled gracefully.
3. **IDF Creation**

   - Check each sub-module (geometry, fenestration, HVAC, shading, etc.) to ensure override logic is integrated.
   - Save assigned parameters to `output/assigned/`.
4. **Simulation Execution**

   - Ensure `epw/run_epw_sims.py` is invoked from `main.py`.
   - Double-check output paths and parallelization.
5. **Post-Processing**

   - Call `merge_results.py` after each simulation batch to unify outputs.
   - Store merged results in `output/results/`.
6. **Validation**

   - Implement or call existing validation code in `validation/`.
   - Generate a summary CSV with metrics (MBE, CV(RMSE), etc.).
7. **Calibration / Modification**

   - If validation fails, call `cal/` or `modification/` scripts to systematically vary parameters and re-run.
   - Record scenario logs and final outputs.
8. **Advanced Modules**

   - Integrate optional sensitivity, surrogate, optimization methods if needed.
9. **Output & Folder Organization**

   - Standardize naming conventions.
   - Possibly create a utility script for cleanup or archiving.
10. **Documentation**

- Write or finalize docstrings, README, or internal wiki.
- Create a small step-by-step usage example.

By following these steps, you can **finalize the code** in a cohesive manner. The main theme is to **unify** the existing modules under one controlling script or a small set of scripts (`main.py` or similar) that can direct the flow from “user data & config” all the way to “validation & calibration,” iterating as needed.

Below is a **fully fleshed-out example** of a `main.py` script that **ties together** all the major steps:

- **Reading user configs** and building data
- **Generating IDFs**
- **Running EnergyPlus simulations**
- **Validating results**
- **Iterating calibration or scenario updates**
- **Optionally** performing **sensitivity analysis**, **surrogate modeling**, or **optimization**

All of these steps are driven by **user configuration**, allowing for a **flexible** and **extensible** workflow.

> **Important**: This sample is still somewhat **pseudo-code**. You should **replace** the placeholder functions (`load_user_configs()`, `create_idfs_for_buildings()`, `simulate_all()`, etc.) with the **actual** function calls and module imports from **your** codebase. Also, adapt the user configuration keys (e.g., `{"paths": {...}, "simulation": {...}}`) to your actual JSON/YAML config structure.

---

## **Short Description of the Process**

1. **Load User Config & Data**

   - The script reads a JSON/YAML config file (or multiple files) and merges them.
   - Loads main building data from CSV or a database.
2. **Create Base IDFs & Run Simulations**

   - Uses modules like `main_create_idf.py` to generate EnergyPlus IDFs.
   - Calls `epw/run_epw_sims.py` (or your chosen function) to run simulations.
   - Merges results (`postproc/merge_results.py`) for further analysis.
3. **Validation**

   - Invokes modules in `validation/validate_results.py` to compare simulated data with real data.
   - Checks if results meet MBE/CVRMSE thresholds or another criterion.
4. **Calibration / Scenario Generation Loop**

   - If validation fails, the code generates new parameter sets (via `modification/`) or uses advanced approaches in `cal/` (GA, Bayesian, random search, etc.).
   - Regenerates IDFs, re-runs simulations, re-validates.
   - Continues until thresholds are met or the iteration limit is reached.
5. **Advanced Analysis**

   - **Sensitivity Analysis** (with `sensitive/`, e.g., SALib)
   - **Surrogate Modeling** (with `surrogate/`, e.g., building a RandomForest or XGBoost model)
   - **Optimization** (with `cal/` or a dedicated `optimization/` folder, possibly using the surrogate)
6. **Final Output**

   - Reports or CSV logs for **assigned parameters**, **validation metrics**, **scenario results**, etc.
   - Optionally updates default lookups with final “best-fit” or “optimized” values.

---

## **Adapting This Code**

1. **Replace Placeholder Dictionaries & Function Calls**

   - Where you see `user_config = {...}`, you’ll likely load this from a real JSON or YAML file.
   - Functions like `create_idfs_for_buildings()`, `simulate_all()`, `merge_all_results()`, `validate_data()` should be replaced with actual imports and calls from your code.
2. **Refine the Iterative Logic**

   - If you use a **genetic algorithm** or **Bayesian** approach for calibration, swap out the pseudo `generate_param_sets()` with calls to your calibration modules (`cal.unified_calibration.py`).
   - If you have **scenario rules** (like specifying occupant density in random ranges or infiltration step-changes), incorporate them.
3. **Add Error Handling & Parallelization**

   - Wrap calls in `try/except` if you expect file I/O or simulation errors.
   - If you want to run multiple E+ simulations in parallel, your `simulate_all` function or scripts can use `multiprocessing` or `joblib` to coordinate parallel runs.
   - You can expand logging to debug-level or add more detail around file paths, param sets, etc.
4. **More Detailed Logging**

   - Each step logs major activities. You can add debug statements (e.g., `logger.debug(...)`) inside deeper loops or function calls to trace your program flow more precisely.
5. **Structure**

   - The code is modular: each advanced analysis (sensitivity, surrogate, optimization) is in its own function.
   - This approach lets you easily **disable** or **enable** them from the user config, or break them out into separate orchestrator scripts if they get very large.

With these adaptations, you have a **central** `main.py` that can coordinate the entire building modeling workflow—**from initial IDF creation to advanced calibration and analysis—**all governed by user configs for maximum flexibility.

## **Full Code: `main.py`**

```python
  """
File: main.py

Purpose:
    1) Load user config, building data, default lookups
    2) Create base IDFs, run sims, validate
    3) (Optional) iterative calibration/scenario loops if thresholds not met
    4) (Optional) advanced modules: sensitivity, surrogate, optimization
    5) Produce final outputs/logs

Adaptation:
    - Replace placeholder dictionaries, function calls, and file paths
      with the real ones from your codebase.
    - Expand or refine the iterative logic to suit your calibration approach
      (random, genetic, Bayesian) or scenario generation rules
      (user-specified ranges, etc.).
    - Add error handling, parallelization, or more detailed logging if needed.
"""

import os
import logging
import pandas as pd

# ------------------------------------------------------------------------------
# Example placeholders for actual modules in your code:
# ------------------------------------------------------------------------------
# from user_config_manager import load_user_configs
# from lookup_manager import load_default_lookups, merge_user_overrides
# from main_create_idf import create_idfs_for_buildings
# from epw.run_epw_sims import simulate_all
# from postproc.merge_results import merge_all_results
# from validation.validate_results import validate_data
# from modification.main_modifi import generate_param_sets, apply_params_to_idf
# from cal.unified_calibration import CalibrationManager
# from sensitive.unified_sensitivity import run_sensitivity_analysis
# from surrogate.unified_surrogate import build_and_save_surrogate, load_surrogate_and_predict
# from optimization.ga_optimizer import run_genetic_optimization
# from optimization.bayesian_optimizer import run_bayesian_optimization
  
# ------------------------------------------------------------------------------
# 1. LOGGING SETUP
# ------------------------------------------------------------------------------
def setup_logging(log_level=logging.INFO):
    """
    Initialize logging with a standard format.
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 2. MAIN ORCHESTRATION
# ------------------------------------------------------------------------------
def main():
    logger = setup_logging()
    logger.info("==== Starting main.py ====")

    # --------------------------------------------------------------------------
    # A) LOAD USER CONFIG & DATA
    # --------------------------------------------------------------------------
    logger.info("Loading user configurations...")
    # user_config = load_user_configs("user_configs/config.json")
    # For demonstration, here's a mock config:
    user_config = {
        "paths": {
            "building_data": "data/df_buildings.csv",
            "lookup_folder": "lookup_xlx/",
            "base_idf_folder": "output/output_IDFs/",
            "scenario_idf_folder": "output/scenario_idfs/",
            "sim_results_folder": "output/Sim_Results/",
            "merged_results_folder": "output/results/",
            "real_data_folder": "output/real_data/"
        },
        "simulation": {
            "run_base_simulation": True,
            "parallel": True  # Possibly used for parallel E+ runs
        },
        "validation": {
            "perform_validation": True,
            "mbe_threshold": 5.0,
            "cvrmse_threshold": 15.0,
            "real_data_file": "real_data_1.csv"
        },
        "calibration": {
            "perform_calibration": True,
            "max_iterations": 5
        },
        "sensitivity": {
            "perform_sensitivity": False,
            "method": "sobol",
            "num_samples": 1000
        },
        "surrogate": {
            "perform_surrogate": False,
            "model_type": "RandomForest"
        },
        "optimization": {
            "perform_optimization": False,
            "method": "bayesian"
        }
    }

    logger.info("Loading building data from CSV/Database...")
    building_data_path = user_config["paths"]["building_data"]
    if os.path.exists(building_data_path):
        df_buildings = pd.read_csv(building_data_path)
    else:
        logger.warning(f"Could not find building data at {building_data_path}; using empty DataFrame.")
        df_buildings = pd.DataFrame()

    logger.info("Loading default lookups and merging user overrides...")
    # default_lookups = load_default_lookups(user_config["paths"]["lookup_folder"])
    # user_overrides = load_user_configs("user_configs/overrides.json")
    # final_lookups = merge_user_overrides(default_lookups, user_overrides)
    final_lookups = {}  # Placeholder

    # --------------------------------------------------------------------------
    # B) CREATE & SIMULATE BASE IDFs
    # --------------------------------------------------------------------------
    if user_config["simulation"].get("run_base_simulation", True):
        logger.info("Creating base IDFs for each building...")
        base_idf_folder = user_config["paths"]["base_idf_folder"]
        # create_idfs_for_buildings(
        #     df_buildings=df_buildings,
        #     lookups=final_lookups,
        #     output_folder=base_idf_folder
        # )

        logger.info("Running base simulations with EnergyPlus...")
        sim_output_folder = os.path.join(user_config["paths"]["sim_results_folder"], "base")
        # simulate_all(
        #     idf_folder=base_idf_folder,
        #     output_folder=sim_output_folder,
        #     parallel=user_config["simulation"]["parallel"]
        # )

        logger.info("Merging base simulation results...")
        merged_results_folder = user_config["paths"]["merged_results_folder"]
        base_merged_csv = os.path.join(merged_results_folder, "base_merged.csv")
        # base_merged_df = merge_all_results(sim_output_folder)
        # base_merged_df.to_csv(base_merged_csv, index=False)

        # ----------------------------------------------------------------------
        # C) VALIDATION (BASE CASE)
        # ----------------------------------------------------------------------
        if user_config["validation"].get("perform_validation", False):
            real_data_path = os.path.join(
                user_config["paths"]["real_data_folder"],
                user_config["validation"]["real_data_file"]
            )
            # base_metrics = validate_data(base_merged_csv, real_data_path)
            # logger.info(f"Base validation metrics: {base_metrics}")
            base_metrics = {"MBE": 12.0, "CVRMSE": 20.0}  # Example placeholder

            base_passes = (
                base_metrics["MBE"] <= user_config["validation"]["mbe_threshold"]
                and base_metrics["CVRMSE"] <= user_config["validation"]["cvrmse_threshold"]
            )
            if base_passes:
                logger.info("Base simulation meets validation thresholds.")
            else:
                logger.info("Base simulation fails thresholds. Calibration/Scenarios may be needed.")
        else:
            logger.info("Skipping base validation as per user config.")
            base_metrics = {}
            base_passes = False
    else:
        logger.info("Skipping base simulation as per user config.")
        base_metrics = {}
        base_passes = False

    # --------------------------------------------------------------------------
    # D) CALIBRATION / SCENARIO GENERATION
    # --------------------------------------------------------------------------
    if user_config["calibration"].get("perform_calibration", False) and not base_passes:
        logger.info("Starting iterative calibration/scenario loop...")
        iterative_calibration_loop(df_buildings, user_config, base_metrics)
    else:
        logger.info("Skipping calibration loop. (Either base passes or config turned off.)")

    # --------------------------------------------------------------------------
    # E) ADVANCED ANALYSIS: SENSITIVITY, SURROGATE, OPTIMIZATION
    # --------------------------------------------------------------------------
    # 1) SENSITIVITY
    if user_config["sensitivity"].get("perform_sensitivity", False):
        logger.info("Performing sensitivity analysis.")
        run_sensitivity_workflow(user_config)

    # 2) SURROGATE
    if user_config["surrogate"].get("perform_surrogate", False):
        logger.info("Creating or updating surrogate model.")
        run_surrogate_workflow(user_config)

    # 3) OPTIMIZATION
    if user_config["optimization"].get("perform_optimization", False):
        logger.info("Performing optimization workflow.")
        run_optimization_workflow(user_config)

    logger.info("==== End of main.py ===")

# ------------------------------------------------------------------------------
# 3. ITERATIVE CALIBRATION LOOP
# ------------------------------------------------------------------------------
def iterative_calibration_loop(df_buildings, user_config, base_metrics):
    """
    A loop for calibration or scenario generation:
      - Generate new param sets
      - Create scenario IDFs
      - Run simulations
      - Validate
      - Stop if thresholds met or max iterations reached
    """
    logger = logging.getLogger(__name__)
    logger.info("Entered iterative_calibration_loop.")

    max_iter = user_config["calibration"].get("max_iterations", 5)
    scenario_idf_folder = user_config["paths"]["scenario_idf_folder"]
    sim_results_folder = user_config["paths"]["sim_results_folder"]
    merged_results_folder = user_config["paths"]["merged_results_folder"]
    real_data_folder = user_config["paths"]["real_data_folder"]
    real_data_file = user_config["validation"]["real_data_file"]
    mbe_thresh = user_config["validation"]["mbe_threshold"]
    cvrmse_thresh = user_config["validation"]["cvrmse_threshold"]

    best_metrics = dict(base_metrics)  # copy for safety
    iteration = 0
    improved = False

    while iteration < max_iter:
        iteration += 1
        logger.info(f"--- Iteration {iteration}/{max_iter} ---")

        # 1) Generate param sets
        logger.info("Generating new parameter sets for scenarios/calibration...")
        # new_param_sets = generate_param_sets(best_metrics, iteration)
        # (Example placeholder):
        new_param_sets = [
            {"infiltration": 0.4},
            {"infiltration": 0.6}
        ]

        # 2) Create scenario IDFs
        for i, param_set in enumerate(new_param_sets):
            scenario_idf_path = os.path.join(scenario_idf_folder, f"iter_{iteration}_scen_{i}.idf")
            logger.info(f"Creating scenario IDF: {scenario_idf_path}")
            # apply_params_to_idf("output/output_IDFs/base.idf", param_set, scenario_idf_path)

        # 3) Run simulations
        iteration_sim_folder = os.path.join(sim_results_folder, f"iter_{iteration}")
        # simulate_all(
        #     idf_folder=scenario_idf_folder,
        #     output_folder=iteration_sim_folder,
        #     parallel=user_config["simulation"]["parallel"]
        # )
        logger.info("Simulations finished for iteration %d.", iteration)

        # 4) Merge & Validate
        # merged_iter_csv = os.path.join(merged_results_folder, f"merged_iter_{iteration}.csv")
        # iteration_merged_df = merge_all_results(iteration_sim_folder)
        # iteration_merged_df.to_csv(merged_iter_csv, index=False)

        # iteration_metrics = validate_data(
        #     simulated_data=merged_iter_csv,
        #     real_data=os.path.join(real_data_folder, real_data_file)
        # )
        # Placeholder example:
        iteration_metrics = {
            "MBE": best_metrics.get("MBE", 12.0) - 2,
            "CVRMSE": best_metrics.get("CVRMSE", 20.0) - 2
        }
        logger.info(f"Iteration {iteration} metrics: {iteration_metrics}")

        # 5) Check improvement
        if (iteration_metrics["MBE"] < best_metrics.get("MBE", float('inf')) and
                iteration_metrics["CVRMSE"] < best_metrics.get("CVRMSE", float('inf'))):
            logger.info("Metrics improved; updating best_metrics.")
            best_metrics = iteration_metrics
            improved = True

        # 6) Check threshold
        if best_metrics["MBE"] <= mbe_thresh and best_metrics["CVRMSE"] <= cvrmse_thresh:
            logger.info(f"Thresholds met at iteration {iteration}. Ending calibration loop.")
            break
        else:
            logger.info(f"Iteration {iteration} did not meet thresholds. Continuing...")

    logger.info("Calibration/scenario loop completed.")
    logger.info(f"Best final metrics: {best_metrics}")
    if improved:
        logger.info("Optionally update default lookups or user config with final best parameters.")

# ------------------------------------------------------------------------------
# 4. SENSITIVITY WORKFLOW
# ------------------------------------------------------------------------------
def run_sensitivity_workflow(user_config):
    """
    Demonstrates how you'd orchestrate a sensitivity analysis.
    Typically, you define a param space, run many sims or use a surrogate,
    then compute sensitivity indices (Sobol, Morris, etc.).
    """
    logger = logging.getLogger(__name__)
    logger.info("Running sensitivity analysis...")

    method = user_config["sensitivity"].get("method", "sobol")
    num_samples = user_config["sensitivity"].get("num_samples", 1000)

    # param_ranges = define_param_ranges(...)  # Example
    # run_sensitivity_analysis(param_ranges, method=method, samples=num_samples)

    logger.info(f"Sensitivity analysis complete with method={method}.")


# ------------------------------------------------------------------------------
# 5. SURROGATE WORKFLOW
# ------------------------------------------------------------------------------
def run_surrogate_workflow(user_config):
    """
    If the user wants to create/update a surrogate model from scenario data,
    you gather training data (params + outputs) and fit a regressor (RF, XGBoost, etc.).
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting surrogate modeling...")

    model_type = user_config["surrogate"].get("model_type", "RandomForest")
    # training_data = gather_scenario_data("output/results/")
    # build_and_save_surrogate(training_data, model_type=model_type, output_path="models/surrogate.pkl")

    # predicted = load_surrogate_and_predict("models/surrogate.pkl", new_param_set)
    logger.info(f"Surrogate modeling completed. Model={model_type}")


# ------------------------------------------------------------------------------
# 6. OPTIMIZATION WORKFLOW
# ------------------------------------------------------------------------------
def run_optimization_workflow(user_config):
    """
    Could be a GA, Bayesian, or other algorithm.
    Possibly uses a surrogate model for quick fitness evaluations,
    or calls the full E+ simulation for each candidate.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting optimization workflow...")

    method = user_config["optimization"].get("method", "genetic")
    if method == "genetic":
        logger.info("Using Genetic Algorithm approach.")
        # run_genetic_optimization(...)
    elif method == "bayesian":
        logger.info("Using Bayesian Optimization approach.")
        # run_bayesian_optimization(...)
    else:
        logger.warning(f"Unknown optimization method: {method}")

    logger.info("Optimization workflow completed.")

# ------------------------------------------------------------------------------
# 7. SCRIPT ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
```

---
