# fenestration.py
import os
import random
import pandas as pd

################################################################################
# 1) Example of a BASE FENESTRATION DICT
################################################################################
# You can store or load your default fenestration data by building function/age.
# Adjust these structures to match your real data. For demonstration:
BASE_FENESTRATION_DATA = {
    "residential": {
        "1992 - 2005": {
            "wwr": (0.20, 0.30),      # min, max
            "roof_R_value": (2.5, 3.0)
        },
        "2015 and later": {
            "wwr": (0.30, 0.35),
            "roof_R_value": (3.0, 4.0)
        }
    },
    "non_residential": {
        "1992 - 2005": {
            "wwr": (0.10, 0.20),
            "roof_R_value": (2.0, 2.5)
        },
        "2015 and later": {
            "wwr": (0.25, 0.40),
            "roof_R_value": (3.5, 4.5)
        }
    }
}


################################################################################
# 2) Loading Excel for Fenestration
################################################################################
def load_excel_fenez_overrides(excel_path):
    """
    Read fenestration overrides from an Excel file. Return a DataFrame or None.
    Expected columns:
      building_function, age_range, scenario, param_name, min_val, max_val, fixed_value
    """
    if not excel_path or (not os.path.isfile(excel_path)):
        return None
    
    df = pd.read_excel(excel_path)
    # Make sure all columns exist, or handle gracefully
    for col in ["building_function", "age_range", "scenario",
                "param_name", "min_val", "max_val", "fixed_value"]:
        if col not in df.columns:
            df[col] = None
    return df


def apply_excel_override_for_building(df_excel, building_function, age_range, scenario, param_name):
    """
    Given a single building's function, age_range, scenario, and a param_name,
    see if there's a row in df_excel that overrides min_val, max_val, or fixed_value.
    Return (min_val, max_val, fixed_val) or None if no match.
    """
    if df_excel is None:
        return None

    subset = df_excel[
        (df_excel["building_function"] == building_function) &
        (df_excel["age_range"] == age_range) &
        (df_excel["scenario"] == scenario) &
        (df_excel["param_name"] == param_name)
    ]
    if subset.empty:
        return None

    row = subset.iloc[0]  # If multiple matches, you can decide to take first or last
    return (row["min_val"], row["max_val"], row["fixed_value"])


################################################################################
# 3) Applying Partial JSON overrides (fenestration.json)
################################################################################
def find_partial_user_override_for_building(
    user_config_fenez,   # list of dicts from fenestration.json
    bldg_id,
    building_function,
    age_range,
    scenario,
    param_name
):
    """
    Return (min_val, max_val, fixed_val) for a building if found, else None.
    The fenestration.json might look like:
      [
        {
          "building_id": 4136730,
          "building_function": "residential",
          "age_range": "1992 - 2005",
          "scenario": "scenario1",
          "param_name": "wwr",
          "min_val": 0.25,
          "max_val": 0.30
        },
        ...
      ]
    If building_id is in the rule, it must match exactly; if not present, we ignore building_id.
    We also match building_function, age_range, scenario, param_name if they're present.
    """
    if not user_config_fenez:
        return None

    possible_matches = []
    for rule in user_config_fenez:
        # param_name
        if rule.get("param_name") != param_name:
            continue
        # building_id if present
        if "building_id" in rule:
            if rule["building_id"] != bldg_id:
                continue
        # function
        if rule.get("building_function") and rule["building_function"] != building_function:
            continue
        # age_range
        if rule.get("age_range") and rule["age_range"] != age_range:
            continue
        # scenario
        if rule.get("scenario") and rule["scenario"] != scenario:
            continue
        
        # If all checks pass, we have a match
        possible_matches.append(rule)
    
    if not possible_matches:
        return None
    
    # If multiple match, pick first or whichever logic you need
    first_match = possible_matches[0]
    return (
        first_match.get("min_val"),
        first_match.get("max_val"),
        first_match.get("fixed_value")
    )


################################################################################
# 4) The Final Value Picker
################################################################################
def pick_fenestration_value(min_val, max_val, fixed_val, strategy="B", random_seed=None):
    """
    If fixed_val is not None, return it (the user or Excel demanded a fixed override).
    Otherwise, pick from [min_val, max_val]:
      - strategy = "A" => midpoint
      - strategy = "B" => random uniform
      - else => min_val
    """
    if random_seed is not None:
        random.seed(random_seed)

    if fixed_val is not None:
        return fixed_val, "fixed_value"

    if min_val is None or max_val is None:
        return None, "no_range"  # fallback

    if strategy == "A":
        chosen = 0.5 * (min_val + max_val)
        note = f"range_{min_val}_{max_val}_mid"
    elif strategy == "B":
        chosen = random.uniform(min_val, max_val)
        note = f"range_{min_val}_{max_val}_random"
    else:
        chosen = min_val
        note = f"range_{min_val}_{max_val}_pick_min"

    return chosen, note


################################################################################
# 5) Main merge logic: assign_fenestration_values_for_building(...)
################################################################################
def assign_fenestration_values_for_building(
    building_row,
    scenario,
    excel_fenez_df,     # optional
    user_config_fenez,  # list from fenestration.json
    assigned_fenez_log, # dict for logging
    random_seed=42,
    strategy="B"
):
    """
    1) Identify building_function ("residential" or "non_residential").
    2) Identify age_range from building_row.
    3) Start from BASE_FENESTRATION_DATA => param_name => (base_min, base_max).
    4) Apply Excel override if found => (excel_min, excel_max, excel_fixed).
    5) Apply user_config JSON override => (user_min, user_max, user_fixed).
    6) pick_fenestration_value => final_value
    7) Save final_value + range_info into assigned_fenez_log[bldg_id][param_name].

    Return a dict of final params: e.g. {"wwr": 0.28, "roof_R_value": 2.9, ...}
    """
    bldg_id = building_row.get("ogc_fid")
    building_function = building_row.get("building_function", "residential").lower()
    age_range = building_row.get("age_range", "1992 - 2005")

    if bldg_id not in assigned_fenez_log:
        assigned_fenez_log[bldg_id] = {}

    final_params = {}

    # 1) Get the relevant base dictionary
    if building_function == "residential":
        base_data_for_age = BASE_FENESTRATION_DATA["residential"].get(age_range, {})
    else:
        base_data_for_age = BASE_FENESTRATION_DATA["non_residential"].get(age_range, {})

    # 2) For each fenestration param in that age_data
    #    For instance, "wwr", "roof_R_value", etc.
    for param_name, base_tuple in base_data_for_age.items():
        base_min, base_max = base_tuple if isinstance(base_tuple, tuple) else (None, None)
        base_fixed = None

        # 3) Apply Excel override
        excel_override = apply_excel_override_for_building(
            df_excel=excel_fenez_df,
            building_function=building_function,
            age_range=age_range,
            scenario=scenario,
            param_name=param_name
        )
        if excel_override:
            e_min, e_max, e_fixed = excel_override
            if e_fixed is not None:
                base_fixed = e_fixed
                base_min, base_max = None, None
            else:
                if e_min is not None: base_min = e_min
                if e_max is not None: base_max = e_max

        # 4) Apply user_config JSON override
        user_override = find_partial_user_override_for_building(
            user_config_fenez=user_config_fenez,
            bldg_id=bldg_id,
            building_function=building_function,
            age_range=age_range,
            scenario=scenario,
            param_name=param_name
        )
        if user_override:
            u_min, u_max, u_fixed = user_override
            if u_fixed is not None:
                base_fixed = u_fixed
                base_min, base_max = None, None
            else:
                if u_min is not None: base_min = u_min
                if u_max is not None: base_max = u_max

        # 5) Final pick
        chosen_val, range_info = pick_fenestration_value(
            min_val=base_min,
            max_val=base_max,
            fixed_val=base_fixed,
            strategy=strategy,
            random_seed=random_seed
        )

        # 6) Store in final_params
        final_params[param_name] = chosen_val

        # 7) Log in assigned_fenez_log
        assigned_fenez_log[bldg_id][param_name] = {
            "chosen_value": chosen_val,
            "range_info": range_info
        }

    return final_params


################################################################################
# 6) add_fenestration(...) => the function called by create_idf_for_building
################################################################################
def add_fenestration(
    idf,
    building_row,
    scenario,
    calibration_stage,
    strategy,
    random_seed,
    user_config_fenez,
    assigned_fenez_log,
    excel_fenez_df=None
):
    """
    1) Call assign_fenestration_values_for_building(...) to get final fenestration params
       (e.g. wwr, roof_R_value, etc.).
    2) Create windows in the IDF using the chosen WWR, or adjust roof materials by the chosen R-value, etc.
    3) Store results in assigned_fenez_log if needed (already done inside the function).
    """
    # 1) Merge + pick final fenestration parameters
    final_params = assign_fenestration_values_for_building(
        building_row=building_row,
        scenario=scenario,
        excel_fenez_df=excel_fenez_df,     # pass the DataFrame if you want
        user_config_fenez=user_config_fenez,
        assigned_fenez_log=assigned_fenez_log,
        random_seed=random_seed,
        strategy=strategy
    )
    
    wwr_val = final_params.get("wwr", 0.20)
    roof_r  = final_params.get("roof_R_value", 3.0)

    # 2) Actually modify the IDF
    # Example: for each exterior wall, add a window that is wwr_val * that wall’s area
    # If you want to reference surfaces in the IDF, you can do something like:
    for surface in idf.getsubsurfaces("WALL"):
        if surface.Outside_Boundary_Condition.lower() == "outdoors":
            # compute area, add a window object, etc.
            pass

    # Or if you have a separate code that sets roof R-value by adjusting the construction layers:
    #    you can pass "roof_r" to your materials code or do it here.

    # This function can just modify the IDF in-place. No return needed.
    return
