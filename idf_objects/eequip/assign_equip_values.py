# File: D:\Documents\E_Plus_2030_py\idf_objects\eequip\assign_equip_values.py

import random
from .equip_lookup import equip_lookup
from .overrides_helper import find_applicable_overrides # if you use override logic

def assign_equipment_parameters(
    building_id: int,
    building_category: str,
    sub_type: str,
    age_range=None, # Passed to find_applicable_overrides
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: int = None,
    user_config: list = None, # override table (list of dicts)
    assigned_log: dict = None # optional dictionary to store final picks
):
    """
    Returns a dict with ``equip_wm2``, ``tD`` and ``tN`` picks for electric
    equipment. (Docstring from original file)
    """
    print(f"\n--- [DEBUG assign_equipment_parameters for bldg_id {building_id}] ---")
    print(f"[DEBUG assign_equip_params] INPUTS: building_category='{building_category}', sub_type='{sub_type}', calibration_stage='{calibration_stage}', strategy='{strategy}'")
    print(f"[DEBUG assign_equip_params]          age_range='{age_range}', user_config is {'Provided' if user_config else 'None'}")

    if random_seed is not None:
        random.seed(random_seed)
        print(f"[DEBUG assign_equip_params] Random seed set to: {random_seed}")

    # Normalize category strings so that lookups are consistent
    _original_building_category = building_category
    if building_category: # Check if building_category is not None or empty
        bt_low = building_category.lower()
        if bt_low == "residential":
            building_category = "Residential"
        elif bt_low == "non_residential": # Corrected from "non_residential" to match potential input casing
            building_category = "Non-Residential"
    print(f"[DEBUG assign_equip_params] Category after normalization: '{building_category}' (was '{_original_building_category}')")

    _original_sub_type = sub_type
    sub_type = sub_type.strip() if sub_type else ""
    print(f"[DEBUG assign_equip_params] Sub_type after strip: '{sub_type}' (was '{_original_sub_type}') (len: {len(sub_type)})")

    # Initialize ranges with minimal fallbacks, to be updated if lookups succeed
    equip_rng_default = (3.0, 3.0)
    tD_rng_default    = (500, 500)
    tN_rng_default    = (200, 200)

    equip_rng = equip_rng_default
    tD_rng    = tD_rng_default
    tN_rng    = tN_rng_default
    
    lookup_successful = False

    # 1) Grab the stage dictionary or fallback
    _original_calibration_stage = calibration_stage
    if calibration_stage not in equip_lookup:
        print(f"[DEBUG assign_equip_params] WARNING: calibration_stage '{calibration_stage}' not in equip_lookup keys: {list(equip_lookup.keys()) if isinstance(equip_lookup, dict) else 'Not a dict'}. Defaulting to 'pre_calibration'.")
        calibration_stage = "pre_calibration"
    
    if calibration_stage not in equip_lookup:
        print(f"[DEBUG assign_equip_params] CRITICAL FALLBACK (Stage): calibration_stage '{calibration_stage}' (even after potential default) is NOT in equip_lookup. Using hardcoded minimal fallback for ALL parameters.")
        # Ranges already initialized to minimal fallbacks
    else:
        stage_dict = equip_lookup[calibration_stage]
        print(f"[DEBUG assign_equip_params] Using calibration_stage: '{calibration_stage}'. Stage_dict keys: {list(stage_dict.keys()) if isinstance(stage_dict, dict) else 'Not a dict'}")

        # 2) Navigate to the sub-type dictionary or fallback
        if not isinstance(stage_dict, dict) or building_category not in stage_dict:
            print(f"[DEBUG assign_equip_params] FALLBACK (A - category): building_category '{building_category}' not in stage_dict for stage '{calibration_stage}' (or stage_dict is not a dict: {type(stage_dict)}). Using minimal fallback.")
            # Ranges already initialized to minimal fallbacks
        else:
            cat_dict = stage_dict[building_category]
            print(f"[DEBUG assign_equip_params] Found cat_dict for '{building_category}'. Sub-type keys in cat_dict: {list(cat_dict.keys()) if isinstance(cat_dict, dict) else 'Not a dict'}")
            
            if not isinstance(cat_dict, dict) or sub_type not in cat_dict:
                print(f"[DEBUG assign_equip_params] FALLBACK (B - sub_type): sub_type '{sub_type}' not in cat_dict for category '{building_category}' (or cat_dict is not a dict: {type(cat_dict)}). Using minimal fallback.")
                if isinstance(cat_dict, dict): print(f"   Available sub_types in cat_dict: {list(cat_dict.keys())}")
                # Ranges already initialized to minimal fallbacks
            else:
                param_dict = cat_dict[sub_type]
                if not isinstance(param_dict, dict):
                    print(f"[DEBUG assign_equip_params] FALLBACK (C - param_dict type): param_dict for '{sub_type}' is not a dictionary (type: {type(param_dict)}). Using minimal fallback.")
                    # Ranges already initialized to minimal fallbacks
                else:
                    print(f"[DEBUG assign_equip_params] SUCCESS: Found param_dict for sub_type '{sub_type}'. Keys: {list(param_dict.keys())}")
                    lookup_successful = True
                    # Get parameters with their own fallbacks if specific keys are missing
                    equip_rng = param_dict.get("EQUIP_WM2_range", equip_rng_default)
                    tD_rng    = param_dict.get("tD_range", tD_rng_default)
                    tN_rng    = param_dict.get("tN_range", tN_rng_default)
                    
                    if "EQUIP_WM2_range" not in param_dict: print(f"   [DEBUG assign_equip_params] Note: EQUIP_WM2_range missing in param_dict for '{sub_type}', used default {equip_rng_default}.")
                    if "tD_range" not in param_dict: print(f"   [DEBUG assign_equip_params] Note: tD_range missing in param_dict for '{sub_type}', used default {tD_rng_default}.")
                    if "tN_range" not in param_dict: print(f"   [DEBUG assign_equip_params] Note: tN_range missing in param_dict for '{sub_type}', used default {tN_rng_default}.")

    print(f"[DEBUG assign_equip_params] Ranges status after lookup (lookup_successful={lookup_successful}):")
    print(f"  equip_rng: {equip_rng}")
    print(f"  tD_rng: {tD_rng}")
    print(f"  tN_rng: {tN_rng}")

    # 3) Find override rows
    matches = [] # Ensure matches is defined
    if user_config is not None:
        # Assuming find_applicable_overrides exists and works correctly.
        # Add try-except if it's a source of potential errors.
        try:
            matches = find_applicable_overrides(building_id, sub_type, age_range, user_config)
            print(f"[DEBUG assign_equip_params] Found {len(matches)} applicable overrides for bldg_id={building_id}, sub_type='{sub_type}', age_range='{age_range}'.")
            if matches: print(f"   Overrides data: {matches}")
        except Exception as e:
            print(f"[DEBUG assign_equip_params] ERROR in find_applicable_overrides: {e}")
            matches = [] # Reset to empty list on error
    else:
        print(f"[DEBUG assign_equip_params] No user_config provided for overrides.")
        matches = []

    # 4) Apply overrides
    if matches:
        print(f"[DEBUG assign_equip_params] Applying {len(matches)} overrides...")
    for row_idx, row in enumerate(matches):
        # Defensive get for keys in override rows
        pname = row.get("param_name")
        mn = row.get("min_val")
        mx = row.get("max_val")

        if pname is None or mn is None or mx is None:
            print(f"  [DEBUG assign_equip_params] Override {row_idx+1} skipped: malformed row (missing param_name, min_val, or max_val): {row}")
            continue
            
        pname = pname.strip() # Ensure no leading/trailing spaces

        print(f"  [DEBUG assign_equip_params] Override {row_idx+1}: param='{pname}', min_val={mn}, max_val={mx}")
        if pname == "equip_wm2":
            equip_rng = (float(mn), float(mx))
            print(f"    Updated equip_rng to: {equip_rng}")
        elif pname == "tD":
            tD_rng = (float(mn), float(mx))
            print(f"    Updated tD_rng to: {tD_rng}")
        elif pname == "tN":
            tN_rng = (float(mn), float(mx))
            print(f"    Updated tN_rng to: {tN_rng}")
        else:
            print(f"    [DEBUG assign_equip_params] Unrecognized param_name '{pname}' in override row.")
    
    if matches: print(f"[DEBUG assign_equip_params] Ranges after potential overrides: equip_rng={equip_rng}, tD_rng={tD_rng}, tN_rng={tN_rng}")

    # 5) Strategy to pick final values
    def pick_val(param_name, r, current_strategy): # Added param_name and strategy for better logging
        val = None
        # Ensure r is a tuple of two numbers
        if not (isinstance(r, (tuple, list)) and len(r) == 2 and all(isinstance(n, (int, float)) for n in r)):
            print(f"  [DEBUG assign_equip_params] pick_val for '{param_name}': Invalid range format {r}. Using default 0.0.")
            return 0.0 # Or handle error appropriately
            
        if current_strategy == "A": # midpoint
            val = (r[0] + r[1]) / 2.0
        elif current_strategy == "B": # random
            val = random.uniform(r[0], r[1])
        else: # fallback => pick min
            val = r[0]
        print(f"  [DEBUG assign_equip_params] pick_val for '{param_name}': range={r}, strategy='{current_strategy}', picked={val}")
        return val

    assigned_equip = max(0.0, float(pick_val("equip_wm2", equip_rng, strategy)))
    assigned_tD    = max(0.0, float(pick_val("tD", tD_rng, strategy)))
    assigned_tN    = max(0.0, float(pick_val("tN", tN_rng, strategy)))

    assigned = {
        "equip_wm2": {"assigned_value": assigned_equip, "min_val": equip_rng[0], "max_val": equip_rng[1], "object_name": "ELECTRICEQUIPMENT"},
        "tD": {"assigned_value": assigned_tD, "min_val": tD_rng[0], "max_val": tD_rng[1], "object_name": "ELECTRICEQUIPMENT_SCHEDULE"},
        "tN": {"assigned_value": assigned_tN, "min_val": tN_rng[0], "max_val": tN_rng[1], "object_name": "ELECTRICEQUIPMENT_SCHEDULE"}
    }
    print(f"[DEBUG assign_equip_params] Final assigned values: {assigned}")

    # 6) Optional logging of both the picks and underlying ranges
    if assigned_log is not None:
        log_data = {
            "assigned": assigned,
            "ranges": {
                "equip_wm2": equip_rng,
                "tD": tD_rng,
                "tN": tN_rng,
            },
            "lookup_successful": lookup_successful, # Added for insight
            "overrides_applied_count": len(matches) # Added for insight
        }
        assigned_log[building_id] = log_data
        print(f"[DEBUG assign_equip_params] Logged data for building_id {building_id}: {log_data}")

    print(f"--- [END DEBUG assign_equipment_parameters for bldg_id {building_id}] ---")
    return assigned