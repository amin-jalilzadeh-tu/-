# File: D:\Documents\E_Plus_2030_py\idf_objects\Elec\assign_lighting_values.py

import random
from .lighting_lookup import lighting_lookup
from .constants import ( # Ensure all DEFAULT constants are imported
    DEFAULT_LIGHTING_WM2, DEFAULT_PARASITIC_WM2, DEFAULT_TD, DEFAULT_TN,
    DEFAULT_LIGHTS_FRACTION_RADIANT, DEFAULT_LIGHTS_FRACTION_VISIBLE,
    DEFAULT_LIGHTS_FRACTION_REPLACEABLE, DEFAULT_EQUIP_FRACTION_RADIANT,
    DEFAULT_EQUIP_FRACTION_LOST
)
from .overrides_helper import find_applicable_overrides # Assuming this helper function exists and is correct


def assign_lighting_parameters(
    building_id: int,
    building_category: str,
    sub_type: str,
    age_range=None,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: int = None,
    user_config: list = None, # list of override dicts from lighting.json
    assigned_log: dict = None # optional dictionary to store final picks
):
    """
    Determines final lighting parameters for a given building,
    merging any user overrides from ``lighting.json`` with defaults
    stored under ``lighting_lookup[calibration_stage][building_category][sub_type]``.
    """
    print(f"\n--- [DEBUG assign_lighting_parameters for bldg_id {building_id}] ---")
    print(f"[DEBUG assign_light_params] INPUTS: building_category='{building_category}', sub_type='{sub_type}', calibration_stage='{calibration_stage}', strategy='{strategy}'")

    # (A) Set random seed if specified
    if random_seed is not None:
        random.seed(random_seed)
        print(f"[DEBUG assign_light_params] Random seed set to: {random_seed}")

    # (B) Get the "stage_dict" for the given calibration_stage
    _original_calibration_stage = calibration_stage
    if calibration_stage not in lighting_lookup:
        print(f"[DEBUG assign_light_params] WARNING: calibration_stage '{calibration_stage}' not in lighting_lookup keys: {list(lighting_lookup.keys())}. Defaulting to 'pre_calibration'.")
        calibration_stage = "pre_calibration"
    
    # Define the comprehensive fallback structure (as in your original code for this file)
    # This is used if category or sub_type lookups fail at a high level.
    FULL_FALLBACK_DICT = {
        "lights_wm2": {"assigned_value": DEFAULT_LIGHTING_WM2, "min_val": DEFAULT_LIGHTING_WM2, "max_val": DEFAULT_LIGHTING_WM2, "object_name": "LIGHTS"},
        "parasitic_wm2": {"assigned_value": DEFAULT_PARASITIC_WM2, "min_val": DEFAULT_PARASITIC_WM2, "max_val": DEFAULT_PARASITIC_WM2, "object_name": "ELECTRICEQUIPMENT"},
        "tD": {"assigned_value": DEFAULT_TD, "min_val": DEFAULT_TD, "max_val": DEFAULT_TD, "object_name": "LIGHTS_SCHEDULE"},
        "tN": {"assigned_value": DEFAULT_TN, "min_val": DEFAULT_TN, "max_val": DEFAULT_TN, "object_name": "LIGHTS_SCHEDULE"},
        "lights_fraction_radiant": {"assigned_value": DEFAULT_LIGHTS_FRACTION_RADIANT, "min_val": DEFAULT_LIGHTS_FRACTION_RADIANT, "max_val": DEFAULT_LIGHTS_FRACTION_RADIANT, "object_name": "LIGHTS.Fraction_Radiant"},
        "lights_fraction_visible": {"assigned_value": DEFAULT_LIGHTS_FRACTION_VISIBLE, "min_val": DEFAULT_LIGHTS_FRACTION_VISIBLE, "max_val": DEFAULT_LIGHTS_FRACTION_VISIBLE, "object_name": "LIGHTS.Fraction_Visible"},
        "lights_fraction_replaceable": {"assigned_value": DEFAULT_LIGHTS_FRACTION_REPLACEABLE, "min_val": DEFAULT_LIGHTS_FRACTION_REPLACEABLE, "max_val": DEFAULT_LIGHTS_FRACTION_REPLACEABLE, "object_name": "LIGHTS.Fraction_Replaceable"},
        "equip_fraction_radiant": {"assigned_value": DEFAULT_EQUIP_FRACTION_RADIANT, "min_val": DEFAULT_EQUIP_FRACTION_RADIANT, "max_val": DEFAULT_EQUIP_FRACTION_RADIANT, "object_name": "ELECTRICEQUIPMENT.Fraction_Radiant"},
        "equip_fraction_lost": {"assigned_value": DEFAULT_EQUIP_FRACTION_LOST, "min_val": DEFAULT_EQUIP_FRACTION_LOST, "max_val": DEFAULT_EQUIP_FRACTION_LOST, "object_name": "ELECTRICEQUIPMENT.Fraction_Lost"}
    }

    if calibration_stage not in lighting_lookup: # Should have been caught by the default, but defensive check
        print(f"[DEBUG assign_light_params] CRITICAL FALLBACK (Stage): calibration_stage '{calibration_stage}' (even after potential default) is NOT in lighting_lookup. Using FULL_FALLBACK_DICT.")
        if assigned_log is not None: assigned_log[building_id] = FULL_FALLBACK_DICT
        print(f"--- [END DEBUG assign_lighting_parameters for bldg_id {building_id} - CRITICAL STAGE FALLBACK] ---")
        return FULL_FALLBACK_DICT
        
    stage_dict = lighting_lookup[calibration_stage]
    print(f"[DEBUG assign_light_params] Using calibration_stage: '{calibration_stage}'. Stage_dict keys: {list(stage_dict.keys()) if isinstance(stage_dict, dict) else 'Not a dict'}")

    # Normalise and strip inputs (as per your original file)
    _original_building_category = building_category
    if building_category.lower() == "residential": # Note: your original file had `if building_category.lower() == ...` which could error if building_category is None
        building_category = "Residential"
    elif building_category.lower() == "non_residential": # Same potential error if None
        building_category = "Non-Residential"
    # Safer normalization:
    # if building_category: # Check if building_category is not None or empty
    #     if building_category.lower() == "residential":
    #         building_category = "Residential"
    #     elif building_category.lower() == "non_residential":
    #         building_category = "Non-Residential"
    # For now, using your structure, assuming building_category is a valid string from get_building_category_and_subtype
    print(f"[DEBUG assign_light_params] Category after normalization: '{building_category}' (was '{_original_building_category}')")
    
    _original_sub_type = sub_type
    sub_type = sub_type.strip() if sub_type else "" # This is good
    print(f"[DEBUG assign_light_params] Sub_type after strip: '{sub_type}' (was '{_original_sub_type}') (len: {len(sub_type)})")

    # (C) Navigate to the sub_type dictionary or fallback
    param_dict = None # Initialize to be safe
    if not isinstance(stage_dict, dict) or building_category not in stage_dict:
        print(f"[DEBUG assign_light_params] FALLBACK (C1 - category): building_category '{building_category}' not in stage_dict for stage '{calibration_stage}' (or stage_dict is not a dict: {type(stage_dict)}). Returning FULL_FALLBACK_DICT.")
        if assigned_log is not None: assigned_log[building_id] = FULL_FALLBACK_DICT
        print(f"--- [END DEBUG assign_lighting_parameters for bldg_id {building_id} - FALLBACK C1] ---")
        return FULL_FALLBACK_DICT
    
    cat_dict = stage_dict[building_category]
    print(f"[DEBUG assign_light_params] Found cat_dict for '{building_category}'. Sub-type keys in cat_dict: {list(cat_dict.keys()) if isinstance(cat_dict, dict) else 'Not a dict'}")

    if not isinstance(cat_dict, dict) or sub_type not in cat_dict:
        print(f"[DEBUG assign_light_params] FALLBACK (C2 - sub_type): sub_type '{sub_type}' not in cat_dict for category '{building_category}' (or cat_dict is not a dict: {type(cat_dict)}). Returning FULL_FALLBACK_DICT.")
        if isinstance(cat_dict, dict): print(f"   Expected one of: {list(cat_dict.keys())}")
        if assigned_log is not None: assigned_log[building_id] = FULL_FALLBACK_DICT
        print(f"--- [END DEBUG assign_lighting_parameters for bldg_id {building_id} - FALLBACK C2] ---")
        return FULL_FALLBACK_DICT
        
    param_dict = cat_dict[sub_type]
    if not isinstance(param_dict, dict):
        print(f"[DEBUG assign_light_params] FALLBACK (C3 - param_dict type): param_dict for '{sub_type}' is not a dictionary (type: {type(param_dict)}). Returning FULL_FALLBACK_DICT.")
        if assigned_log is not None: assigned_log[building_id] = FULL_FALLBACK_DICT
        print(f"--- [END DEBUG assign_lighting_parameters for bldg_id {building_id} - FALLBACK C3] ---")
        return FULL_FALLBACK_DICT

    print(f"[DEBUG assign_light_params] SUCCESS: Found param_dict for sub_type '{sub_type}'. Keys: {list(param_dict.keys())}")

    # (D) Extract default ranges from found param_dict or constants if key missing in param_dict
    # These will be the starting point before overrides.
    lights_rng      = param_dict.get("LIGHTS_WM2_range", (DEFAULT_LIGHTING_WM2, DEFAULT_LIGHTING_WM2))
    parasitic_rng   = param_dict.get("PARASITIC_WM2_range", (DEFAULT_PARASITIC_WM2, DEFAULT_PARASITIC_WM2))
    tD_rng          = param_dict.get("tD_range", (DEFAULT_TD, DEFAULT_TD))
    tN_rng          = param_dict.get("tN_range", (DEFAULT_TN, DEFAULT_TN))
    lights_fraction_radiant_rng     = param_dict.get("lights_fraction_radiant_range", (DEFAULT_LIGHTS_FRACTION_RADIANT, DEFAULT_LIGHTS_FRACTION_RADIANT))
    lights_fraction_visible_rng     = param_dict.get("lights_fraction_visible_range", (DEFAULT_LIGHTS_FRACTION_VISIBLE, DEFAULT_LIGHTS_FRACTION_VISIBLE))
    lights_fraction_replace_rng     = param_dict.get("lights_fraction_replaceable_range", (DEFAULT_LIGHTS_FRACTION_REPLACEABLE, DEFAULT_LIGHTS_FRACTION_REPLACEABLE))
    equip_fraction_radiant_rng      = param_dict.get("equip_fraction_radiant_range", (DEFAULT_EQUIP_FRACTION_RADIANT, DEFAULT_EQUIP_FRACTION_RADIANT))
    equip_fraction_lost_rng         = param_dict.get("equip_fraction_lost_range", (DEFAULT_EQUIP_FRACTION_LOST, DEFAULT_EQUIP_FRACTION_LOST))

    print(f"[DEBUG assign_light_params] Initial ranges from param_dict/defaults (before overrides):")
    print(f"  LIGHTS_WM2_range: {lights_rng} {'(from param_dict)' if 'LIGHTS_WM2_range' in param_dict else '(default const)'}")
    print(f"  PARASITIC_WM2_range: {parasitic_rng} {'(from param_dict)' if 'PARASITIC_WM2_range' in param_dict else '(default const)'}")
    print(f"  tD_range: {tD_rng} {'(from param_dict)' if 'tD_range' in param_dict else '(default const)'}")
    print(f"  tN_range: {tN_rng} {'(from param_dict)' if 'tN_range' in param_dict else '(default const)'}")
    print(f"  lights_fraction_radiant_range: {lights_fraction_radiant_rng} {'(from param_dict)' if 'lights_fraction_radiant_range' in param_dict else '(default const)'}")
    print(f"  lights_fraction_visible_range: {lights_fraction_visible_rng} {'(from param_dict)' if 'lights_fraction_visible_range' in param_dict else '(default const)'}")
    print(f"  lights_fraction_replaceable_range: {lights_fraction_replace_rng} {'(from param_dict)' if 'lights_fraction_replaceable_range' in param_dict else '(default const)'}")
    print(f"  equip_fraction_radiant_range: {equip_fraction_radiant_rng} {'(from param_dict)' if 'equip_fraction_radiant_range' in param_dict else '(default const)'}")
    print(f"  equip_fraction_lost_range: {equip_fraction_lost_rng} {'(from param_dict)' if 'equip_fraction_lost_range' in param_dict else '(default const)'}")

    # (E) Find any user overrides that apply
    if user_config is not None:
        matches = find_applicable_overrides(building_id, sub_type, age_range, user_config)
    else:
        matches = []
    
    # This debug print is already in your code and is useful:
    print(f"[DEBUG lighting] bldg_id={building_id}, type='{sub_type}', matched overrides => {matches}") # Original debug line

    # (F) Override default ranges with user-config
    if matches:
        print(f"[DEBUG assign_light_params] Applying {len(matches)} overrides...")
    for row_idx, row in enumerate(matches):
        pname = row.get("param_name", "").strip().lower()
        fv = row.get("fixed_value", None) 
        mn = row.get("min_val", None)
        mx = row.get("max_val", None)
        
        current_rng = None
        if fv is not None: current_rng = (float(fv), float(fv))
        elif mn is not None and mx is not None: current_rng = (float(mn), float(mx))
        
        if current_rng:
            print(f"  [DEBUG assign_light_params] Override {row_idx+1}: param='{pname}', new_range={current_rng}")
            if pname == "lights_wm2": lights_rng = current_rng
            elif pname == "parasitic_wm2": parasitic_rng = current_rng
            elif pname == "td": tD_rng = current_rng
            elif pname == "tn": tN_rng = current_rng
            elif pname == "lights_fraction_radiant": lights_fraction_radiant_rng = current_rng
            elif pname == "lights_fraction_visible": lights_fraction_visible_rng = current_rng
            elif pname == "lights_fraction_replaceable": lights_fraction_replace_rng = current_rng
            elif pname == "equip_fraction_radiant": equip_fraction_radiant_rng = current_rng
            elif pname == "equip_fraction_lost": equip_fraction_lost_rng = current_rng
            else: print(f"    [DEBUG assign_light_params] Unrecognized param_name '{pname}' in override row.")
        else:
            print(f"  [DEBUG assign_light_params] Override {row_idx+1} for '{pname}' skipped (no fixed_value or min/max_val).")
    
    if matches: print(f"[DEBUG assign_light_params] Ranges after overrides: lights_rng={lights_rng}, parasitic_rng={parasitic_rng}, etc.")

    # (G) Pick final values
    def pick_val(param_name, r): # Added param_name for better logging
        val = None
        if strategy == "A": val = (r[0] + r[1]) / 2.0
        elif strategy == "B": val = random.uniform(r[0], r[1])
        else: val = r[0]
        print(f"  [DEBUG assign_light_params] pick_val for '{param_name}': range={r}, strategy='{strategy}', picked={val}")
        return val

    assigned_lights = pick_val("lights_wm2", lights_rng)
    assigned_paras  = pick_val("parasitic_wm2", parasitic_rng)
    assigned_tD     = pick_val("tD", tD_rng)
    assigned_tN     = pick_val("tN", tN_rng)
    assigned_lights_frac_rad = pick_val("lights_fraction_radiant", lights_fraction_radiant_rng)
    assigned_lights_frac_vis = pick_val("lights_fraction_visible", lights_fraction_visible_rng)
    assigned_lights_frac_rep = pick_val("lights_fraction_replaceable", lights_fraction_replace_rng)
    assigned_equip_frac_rad  = pick_val("equip_fraction_radiant", equip_fraction_radiant_rng)
    assigned_equip_frac_lost = pick_val("equip_fraction_lost", equip_fraction_lost_rng)
    
    # (H) Build final dict
    assigned = {
        "lights_wm2": {"assigned_value": assigned_lights, "min_val": lights_rng[0], "max_val": lights_rng[1], "object_name": "LIGHTS"},
        "parasitic_wm2": {"assigned_value": assigned_paras, "min_val": parasitic_rng[0], "max_val": parasitic_rng[1], "object_name": "ELECTRICEQUIPMENT"},
        "tD": {"assigned_value": assigned_tD, "min_val": tD_rng[0], "max_val": tD_rng[1], "object_name": "LIGHTS_SCHEDULE"},
        "tN": {"assigned_value": assigned_tN, "min_val": tN_rng[0], "max_val": tN_rng[1], "object_name": "LIGHTS_SCHEDULE"},
        "lights_fraction_radiant": {"assigned_value": assigned_lights_frac_rad, "min_val": lights_fraction_radiant_rng[0], "max_val": lights_fraction_radiant_rng[1], "object_name": "LIGHTS.Fraction_Radiant"},
        "lights_fraction_visible": {"assigned_value": assigned_lights_frac_vis, "min_val": lights_fraction_visible_rng[0], "max_val": lights_fraction_visible_rng[1], "object_name": "LIGHTS.Fraction_Visible"},
        "lights_fraction_replaceable": {"assigned_value": assigned_lights_frac_rep, "min_val": lights_fraction_replace_rng[0], "max_val": lights_fraction_replace_rng[1], "object_name": "LIGHTS.Fraction_Replaceable"},
        "equip_fraction_radiant": {"assigned_value": assigned_equip_frac_rad, "min_val": equip_fraction_radiant_rng[0], "max_val": equip_fraction_radiant_rng[1], "object_name": "ELECTRICEQUIPMENT.Fraction_Radiant"},
        "equip_fraction_lost": {"assigned_value": assigned_equip_frac_lost, "min_val": equip_fraction_lost_rng[0], "max_val": equip_fraction_lost_rng[1], "object_name": "ELECTRICEQUIPMENT.Fraction_Lost"}
    }
    print(f"[DEBUG assign_light_params] Final assigned dict structure: {assigned}")

    # (I) Optionally store in assigned_log
    if assigned_log is not None:
        assigned_log[building_id] = assigned
    
    print(f"--- [END DEBUG assign_lighting_parameters for bldg_id {building_id}] ---")
    return assigned