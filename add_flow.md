FileDoes it need updates?Why?**`main_modifi.py`****Yes**Needs to be taught how to load, create scenarios for, and apply the new parameter types (e.g., shading).**`modification/*_functions.py`** **Yes (New Files)** You must create a new function file for each new parameter type (`shading_functions.py`, etc.).**`orchestrator.py`****Yes**The **structuring** step needs to be updated to call your new structuring scripts (e.g., `shading_structuring.py`). The part calling the modification workflow does **not** need to be changed. **`idf_objects/structuring/*`**  **Yes (New Files)** You should create new structuring scripts to prepare your assigned data for scenario generation, especially for adding `min_val` and `max_val` ranges.**`combined.json`****Yes**Must be updated to define the file paths for the new parameters under both the `modification` and `structuring` sections.



| **File**                             | **Does it Need Updates?** | **Why?**                                                                                                                                                                                                                                                               |
| ------------------------------------------ | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`main_modifi.py`**               | Yes                             | - Must load**new scenario CSVs**(e.g. shading, geometry) in the same way as HVAC, DHW, etc.- Must call**`apply_shading_params_to_idf(...)`**or `apply_geometry_params_to_idf(...)`in the scenario loop to apply changes.                                           |
| **`modification/\*_functions.py`** | Yes (new files too)             | - For each new domain you want to param (shading, geometry, infiltration), create a new “functions” file (e.g.`shading_functions.py`).- That file contains `apply_shading_params_to_idf(...)`for scenario application, optionally `create_shading_scenarios(...)`.   |
| **`orchestrator.py`**              | Yes                             | - In the**structuring step** : add calls to your new flatten/structuring scripts (`flatten_shading_data(...)`, etc.) if you want them automatically done when `perform_structuring`is true.- The**modification**step: you might pass new scenario CSV paths. |
| **`idf_objects/structuring/*`**    | Yes (new files too)             | - Create new flattening scripts for shading/geometry, e.g.`flatten_shading.py`, if you want a separate building-level vs. zone-level CSV.- If you store param_min/param_max differently, parse them similarly to how `flatten_hvac.py`does.                              |
| **`combined.json`**                | Yes                             | - You need new references for shading or geometry assigned CSVs under `structuring`(like you do with HVAC).- You also need new references in `modification -> scenario_csv -> shading`, so the modification code knows which CSV to read for shading.                    |




It's understandable that integrating the new pieces into main_modifi.py can be tricky. The key is to systematically add the new parameter set (shading in this case) to each stage of the workflow: loading, filtering, scenario creation, and application.

# an example:

Of course. Let's get the `assigned_shading_params.csv` integrated into your workflow.

Based on the CSV format you've provided, we need to create two key processes:

1.  **Structuring**: A script that reads `assigned_shading_params.csv` and applies `min_val`/`max_val` ranges based on rules you define. This will produce a new `structured_shading_params.csv`.
2.  **Modification**: A set of functions that use the structured file to generate scenarios and then apply those new values to the `Material:WindowBlind` and `ShadingControl` objects in the IDF.

Here is the code and the integration steps.

---

### Step 1: Define Your Shading Rules in `combined.json`

First, you need to provide the rules for how scenarios should be generated. Which parameters do you want to vary, and within what range? Add these rules to the `shading` array in your `combined.json` file.

**File to Update**: `combined.json`

```json
{
  "shading": [
    {
      "param_name": "slat_angle_deg",
      "min_val": 30.0,
      "max_val": 60.0
    },
    {
      "param_name": "slat_beam_solar_reflectance",
      "min_val": 0.6,
      "max_val": 0.8
    },
    {
      "param_name": "blind_to_glass_distance",
      "fixed_value": 0.075
    },
    {
      "param_name": "slat_width",
      "min_val": 0.020,
      "max_val": 0.030
    }
  ],
  "main_config": {
    "structuring": {
      "perform_structuring": true,
      "shading": {
        "csv_in": "assigned/assigned_shading_params.csv",
        "csv_out": "assigned/structured_shading_params.csv"
      }
    },
    "modification": {
        "perform_modification": true,
        "modify_config": {
            "assigned_csv": {
                "shading": "assigned/structured_shading_params.csv"
            },
            "scenario_csv": {
                "shading": "scenarios/scenario_params_shading.csv"
            }
        }
    }
  }
}
```

### Step 2: Create the Structuring Script

This script will read your `assigned_shading_params.csv`, apply the rules from `combined.json`, and write `structured_shading_params.csv`.

**New File to Create**: `D:\Documents\E_Plus_2030_py\idf_objects\structuring\shading_structuring.py`

```python
"""
shading_structuring.py

Transforms the assigned shading log into a structured format with min/max ranges
for sensitivity analysis and modification.
"""
import pandas as pd
import os

def transform_shading_log_to_structured(csv_input, csv_output, user_shading_rules):
    """
    Reads the assigned shading log and adds min/max value columns based on user rules.

    Args:
        csv_input (str): Path to assigned_shading_params.csv
        csv_output (str): Path to write structured_shading_params.csv
        user_shading_rules (list): A list of dictionaries with shading rules.
    """
    if not os.path.exists(csv_input):
        print(f"[ERROR] Shading structuring input not found: {csv_input}")
        return

    df = pd.read_csv(csv_input)
    
    df['min_val'] = pd.NA
    df['max_val'] = pd.NA

    # Create a dictionary for quick rule lookup
    rules_map = {rule['param_name']: rule for rule in user_shading_rules}

    for index, row in df.iterrows():
        param_name = row['param_name']
        if param_name in rules_map:
            rule = rules_map[param_name]
            if 'fixed_value' in rule:
                # If fixed, assigned_value is overwritten and no range is set
                df.loc[index, 'assigned_value'] = rule['fixed_value']
            else:
                df.loc[index, 'min_val'] = rule.get('min_val')
                df.loc[index, 'max_val'] = rule.get('max_val')

    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    df.to_csv(csv_output, index=False)
    print(f"[INFO] Wrote structured shading params to {csv_output} ({len(df)} rows)")

```

### Step 3: Create the Modification Functions

This module will use the `structured_shading_params.csv` to generate and apply scenarios.

**New File to Create**: `D:\Documents\E_Plus_2030_py\modification\shading_functions.py`

```python
"""
shading_functions.py

Functions for creating and applying shading parameter scenarios.
"""
import pandas as pd
from modification.common_utils import generate_multiple_param_sets, save_param_scenarios_to_csv

# This dictionary maps the CSV param_name to the actual EnergyPlus field name.
PARAM_TO_EP_FIELD_MAP = {
    # Material:WindowBlind fields
    "slat_orientation": "Slat_Orientation",
    "slat_width": "Slat_Width",
    "slat_separation": "Slat_Separation",
    "slat_thickness": "Slat_Thickness",
    "slat_angle_deg": "Slat_Angle",
    "slat_conductivity": "Slat_Conductivity",
    "slat_beam_solar_transmittance": "Slat_Beam_Solar_Transmittance",
    "slat_beam_solar_reflectance": "Slat_Beam_Solar_Reflectance",
    "slat_diffuse_solar_transmittance": "Slat_Diffuse_Solar_Transmittance",
    "slat_diffuse_solar_reflectance": "Slat_Diffuse_Solar_Reflectance",
    "slat_beam_visible_transmittance": "Slat_Beam_Visible_Transmittance",
    "slat_beam_visible_reflectance": "Front_Side_Slat_Beam_Visible_Reflectance", # Note: E+ has front/back
    "slat_diffuse_visible_transmittance": "Slat_Diffuse_Visible_Transmittance",
    "slat_diffuse_visible_reflectance": "Front_Side_Slat_Diffuse_Visible_Reflectance", # Note: E+ has front/back
    "slat_ir_transmittance": "Slat_Infrared_Transmittance",
    "slat_ir_emissivity": "Front_Side_Slat_Infrared_Emissivity", # Note: E+ has front/back
    "blind_to_glass_distance": "Blind_to_Glass_Distance",
    "slat_opening_multiplier": "Slat_Opening_Multiplier",
    # ShadingControl fields could be added here if needed
}

def create_shading_scenarios(df_shading_input, building_id, num_scenarios, picking_method, random_seed, scenario_csv_out):
    """Generates scenarios for shading parameters from a structured CSV."""
    shading_scenarios = generate_multiple_param_sets(
        df_main_sub=df_shading_input,
        num_sets=num_scenarios,
        picking_method=picking_method
    )
    # The common util `save_param_scenarios_to_csv` doesn't preserve all columns,
    # so we build the dataframe manually here.
    rows = []
    for i, scenario_dict in enumerate(shading_scenarios):
        # We need to map the scenario values back to the original rows
        for _, row in df_shading_input.iterrows():
            param_name = row['param_name']
            if param_name in scenario_dict:
                new_row = row.to_dict()
                new_row['scenario_index'] = i
                new_row['ogc_fid'] = building_id
                new_row['assigned_value'] = scenario_dict[param_name]
                rows.append(new_row)

    df_out = pd.DataFrame(rows)
    df_out.to_csv(scenario_csv_out, index=False)
    print(f"[INFO] Wrote scenario shading params to {scenario_csv_out}")
    return df_out


def apply_shading_params_to_idf(idf, df_shading_scen):
    """Applies shading parameters to the IDF by modifying Material:WindowBlind objects."""
    if df_shading_scen.empty:
        return

    print(f"[INFO] Applying {len(df_shading_scen)} shading parameter modifications...")
    
    # Group by the blind material name to modify each object once
    grouped = df_shading_scen.groupby('blind_material_name')

    for blind_name, group_df in grouped:
        try:
            # Find the blind material object
            blind_obj = idf.getobject("MATERIAL:WINDOWBLIND", blind_name)
            if not blind_obj:
                print(f"[WARN] Could not find MATERIAL:WINDOWBLIND named '{blind_name}'. Skipping.")
                continue

            print(f"  - Modifying MATERIAL:WINDOWBLIND '{blind_name}':")
            for row in group_df.itertuples():
                param_name = row.param_name
                param_value = row.assigned_value
                
                if param_name in PARAM_TO_EP_FIELD_MAP:
                    ep_field = PARAM_TO_EP_FIELD_MAP[param_name]
                    # Set the attribute on the eppy/geomeppy object
                    setattr(blind_obj, ep_field, param_value)
                    print(f"    - Set {ep_field} = {param_value}")

        except Exception as e:
            print(f"[ERROR] Failed to modify blind material '{blind_name}': {e}")
```

### Step 4: Update and Integrate the Orchestrator and Modification Scripts

Finally, update `orchestrator.py` to run the new structuring script and `main_modifi.py` to run the modification.

**File to Update**: `D:\Documents\E_Plus_2030_py\orchestrator.py` (add the **shading** block inside the `structuring` section)

```python
# In orchestrator.py, inside the `if structuring_cfg.get("perform_structuring", False):` block

# ... after the DHW block ...
            # --- Shading ----------------------------------------------------
            from idf_objects.structuring.shading_structuring import transform_shading_log_to_structured
            shading_conf = structuring_cfg.get("shading", {})
            user_shading_rules = safe_load_subjson("shading.json", "shading") or []
            
            if shading_conf:
                shading_in = patch_if_relative(shading_conf.get("csv_in"))
                shading_out = patch_if_relative(shading_conf.get("csv_out"))

                transform_shading_log_to_structured(
                    csv_input=shading_in,
                    csv_output=shading_out,
                    user_shading_rules=user_shading_rules
                )
            else:
                logger.warning("[STRUCTURING] 'shading' configuration not found in structuring settings.")

# ... before the HVAC block ...
```

**File to Update**: `D:\Documents\E_Plus_2030_py\modification\main_modifi.py` (The changes from the previous response are correct, just ensure you are using the `structured` csv as input).

```python
# In main_modifi.py

# Add the import at the top
from modification.shading_functions import create_shading_scenarios, apply_shading_params_to_idf

# In run_modification_workflow function:
# 1. Load the structured data
df_shading_all = load_assigned_csv(assigned_csvs["shading"])
df_shading_sub = df_shading_all[df_shading_all["ogc_fid"] == building_id].copy()

# 2. Create scenarios
df_scen_shading = create_shading_scenarios(
    df_shading_input=df_shading_sub,
    #... other params
)

# 3. Load scenario CSVs
df_shading_scen = load_scenario_csv(scenario_csvs["shading"]) #...
shading_groups = df_shading_scen.groupby("scenario_index") #...

# 4. Inside the `for i in range(num_scenarios):` loop, get and apply the scenario
shading_df = shading_groups.get_group(i) #...
apply_shading_params_to_idf(idf, shading_df)
```

With these new files and updates, your workflow is now equipped to handle parametric analysis of window shading systems. You can follow this exact pattern for the other missing parameter sets.