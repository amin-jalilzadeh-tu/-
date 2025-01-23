"""
user_config_overrides.py

Handles partial overrides from user-provided configurations (e.g. JSON).
If the user sets infiltration=0.4–0.6 or occupant_density=0.08, we apply
those in memory, without permanently changing the default dictionaries.

We demonstrate separate functions for geometry, fenestration, DHW, HVAC,
lighting, ventilation, epw, etc. Each function merges user config fields
into the base dictionary.
"""
import os
import json

###############################################################################
# A) LOADING JSON FILES
###############################################################################
def load_json_file(json_path):
    """
    Safely load a single JSON file. 
    Returns a Python dictionary or None if file not found or invalid.
    """
    if not os.path.isfile(json_path):
        return None
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[WARN] Could not parse {json_path}: {e}")
        return None


def load_all_user_configs(user_configs_folder):
    """
    Loads multiple JSON files from the user_configs folder:
      - main_config.json (if present)
      - geometry.json
      - fenestration.json
      - dhw.json
      - hvac.json
      - lighting.json
      - vent.json
      - epw.json
      - shading.json

    Consolidates them into a single dictionary. 
    1) If main_config.json is found, we take that as the base user_config.
    2) Then we merge geometry.json => user_config["user_overrides"]["geometry"] = [...]
       fenestration.json => user_config["user_overrides"]["fenestration"] = [...]
       etc.
    3) If a top-level key conflicts, we allow the main_config.json to remain 
       but add the new data under user_config["user_overrides"].

    Returns the final merged dictionary.
    """
    user_config = {}

    # 1) Load main_config.json if present
    main_config_path = os.path.join(user_configs_folder, "main_config.json")
    main_data = load_json_file(main_config_path)
    if main_data:
        user_config = main_data
    else:
        # If no main_config, we create empty placeholders 
        # so we have a structure to hold overrides
        user_config = {
            "paths": {},
            "excel_overrides": {},
            "default_dicts": {},
            "user_overrides": {},
            "idf_creation": {},
            "modification": {},
            "validation": {},
            "sensitivity": {},
            "surrogate": {},
            "calibration": {}
        }

    # Make sure we have a "user_overrides" key to store partial overrides
    if "user_overrides" not in user_config:
        user_config["user_overrides"] = {}

    # 2) Define the typical override files
    override_files = [
        "geometry.json",
        "fenestration.json",
        "dhw.json",
        "hvac.json",
        "lighting.json",
        "vent.json",
        "epw.json",
        "shading.json"
    ]

    for fname in override_files:
        fpath = os.path.join(user_configs_folder, fname)
        data = load_json_file(fpath)
        if not data:
            continue  # skip if file missing or invalid

        # Each typically has a top-level key matching the file name 
        # (e.g. "fenestration": [ ... ]) or something similar.
        for top_key, val in data.items():
            if top_key not in user_config["user_overrides"]:
                user_config["user_overrides"][top_key] = val
            else:
                # If we already have something, merge or append.
                if isinstance(user_config["user_overrides"][top_key], list) and isinstance(val, list):
                    user_config["user_overrides"][top_key].extend(val)
                elif isinstance(user_config["user_overrides"][top_key], dict) and isinstance(val, dict):
                    user_config["user_overrides"][top_key].update(val)
                else:
                    user_config["user_overrides"][top_key] = val

    return user_config


###############################################################################
# B) APPLYING PARTIAL OVERRIDES
###############################################################################
def apply_geometry_user_config(geometry_dict, user_config_geom):
    """
    user_config_geom: list of override rules:
      [
        { "building_id":4136730, "param_name":"perimeter_depth", "fixed_value":3.5 },
        { "building_type":"Meeting Function", "param_name":"has_core", "fixed_value":True }
      ]
    We'll parse these rules & override geometry_dict accordingly.
    """
    if not user_config_geom:
        return geometry_dict

    for rule in user_config_geom:
        param_name = rule.get("param_name")
        fixed_val  = rule.get("fixed_value")
        if param_name and fixed_val is not None:
            geometry_dict[param_name] = fixed_val

        # If min_val/max_val exist, you might store or do random picking, etc.
        # For simplicity, we do only fixed_value demonstration here.

    return geometry_dict



def apply_fenestration_user_config(fenez_dict, user_config_fenez):
    """
    user_config_fenez can be:
      1) A list of rule dicts from fenestration.json, e.g.
         [
           {
             "building_id":4136730,
             "building_function":"residential",
             "age_range":"1992 - 2005",
             "scenario":"scenario1",
             "param_name":"wwr",
             "min_val":0.25,
             "max_val":0.30
           },
           ...
         ]
      2) A dictionary of top-level keys like { "wwr":0.32, "elements":{...} } if loaded inline.

    We'll handle both cases. For the list:
      - We interpret param_name, fixed_value, min_val, max_val, etc. 
      - Possibly do random picks or store them.

    For the dict:
      - We just assign the keys directly to fenez_dict.
    """

    if not user_config_fenez:
        return fenez_dict

    # CASE A: If user_config_fenez is a list => treat it as a list of rules
    if isinstance(user_config_fenez, list):
        for rule in user_config_fenez:
            p_name     = rule.get("param_name")
            fixed_val  = rule.get("fixed_value")
            min_val    = rule.get("min_val")
            max_val    = rule.get("max_val")

            # If there's a building_id or building_function or scenario, we could check them
            # but for a simple override, let's just store param_name => fixed_val
            # or param_name => random pick in [min_val, max_val] if that's your logic.

            if p_name and fixed_val is not None:
                # e.g. fenez_dict["wwr"] = 0.27
                fenez_dict[p_name] = fixed_val
            elif p_name and (min_val is not None) and (max_val is not None):
                # e.g. do random pick or just store the range
                # For demonstration, store the mid-point:
                chosen_val = (min_val + max_val) / 2.0
                fenez_dict[p_name] = chosen_val

        return fenez_dict

    # CASE B: If user_config_fenez is a dict => direct assignment
    elif isinstance(user_config_fenez, dict):
        for key, val in user_config_fenez.items():
            if key == "elements" and isinstance(val, dict):
                # handle sub-elements
                # e.g. if fenez_dict.get("elements") is a dict, update it
                # or if you prefer direct assignment
                pass
            else:
                fenez_dict[key] = val

        return fenez_dict

    else:
        print("[WARN] Unknown fenestration config format or mismatch. No changes applied.")
        return fenez_dict









def apply_dhw_user_config(dhw_lookup, user_config_dhw):
    """
    If user_config_dhw is a list of rules, e.g. from dhw.json:
      [
         {
             "building_id":4136730,
             "param_name":"occupant_density_m2_per_person",
             "fixed_value":null
         },
         {
             "dhw_key":"Office",
             "param_name":"setpoint_c",
             "min_val":58.0,
             "max_val":60.0
         }
      ]
    We'll interpret them and partially override dhw_lookup in memory.
    """
    if not user_config_dhw:
        return dhw_lookup

    for rule in user_config_dhw:
        dhw_key     = rule.get("dhw_key")
        param_name  = rule.get("param_name")
        fixed_value = rule.get("fixed_value")
        min_val     = rule.get("min_val")
        max_val     = rule.get("max_val")

        if dhw_key and dhw_key in dhw_lookup:
            # e.g. override
            if fixed_value is not None:
                dhw_lookup[dhw_key][param_name] = fixed_value
            else:
                # If min_val/max_val exist => pick or store
                pass
        else:
            # Possibly building_id-based overrides might be done differently
            pass

    return dhw_lookup


def apply_lighting_user_config(lighting_lookup, user_config_lighting):
    """
    user_config_lighting could be a list of rules from lighting.json:
      [
        { "building_id":4136730, "param_name":"lights_wm2","min_val":8.0,"max_val":10.0 },
        ...
      ]
    We'll parse them. For a real logic, you'd store or pick a random in [min_val,max_val].
    """
    if not user_config_lighting:
        return lighting_lookup

    for rule in user_config_lighting:
        p_name     = rule.get("param_name")
        fixed_val  = rule.get("fixed_value")
        min_val    = rule.get("min_val")
        max_val    = rule.get("max_val")

        if p_name and fixed_val is not None:
            lighting_lookup[p_name] = fixed_val
        # If min_val/max_val => do random picking or storing logic

    return lighting_lookup


def apply_hvac_user_config(hvac_lookup, user_config_hvac):
    """
    user_config_hvac can be a list of rules from hvac.json:
      [
        {
          "building_id":4136730,
          "param_name":"heating_day_setpoint",
          "min_val":20.0,
          "max_val":21.0
        },
        ...
      ]
    or a direct dict approach. We handle the list-of-rules approach here.
    """
    if not user_config_hvac:
        return hvac_lookup

    if isinstance(user_config_hvac, list):
        for rule in user_config_hvac:
            p_name     = rule.get("param_name")
            fixed_val  = rule.get("fixed_value")
            min_val    = rule.get("min_val")
            max_val    = rule.get("max_val")

            if p_name and fixed_val is not None:
                hvac_lookup[p_name] = fixed_val
            # If min_val/max_val => store or pick random
    elif isinstance(user_config_hvac, dict):
        for k, v in user_config_hvac.items():
            hvac_lookup[k] = v

    return hvac_lookup


def apply_ventilation_user_config(vent_lookup, user_config_vent):
    """
    user_config_vent can be a list from vent.json:
      [
         {"building_id":4136730, "param_name":"infiltration_base","min_val":1.3,"max_val":1.4},
         ...
      ]
    We'll parse similarly.
    """
    if not user_config_vent:
        return vent_lookup

    for rule in user_config_vent:
        p_name    = rule.get("param_name")
        fixed_val = rule.get("fixed_value")
        min_val   = rule.get("min_val")
        max_val   = rule.get("max_val")

        if p_name and fixed_val is not None:
            vent_lookup[p_name] = fixed_val
        # If min_val/max_val => do random picking or store

    return vent_lookup


def apply_epw_user_config(epw_lookup, user_config_epw):
    """
    user_config_epw might be a list from epw.json:
      [
        {
            "building_id":4136730,
            "fixed_epw_path":"C:/MyCustom.epw"
        },
        {
            "desired_year":2050,
            "override_year_to":2018
        }
      ]
    You might store these in epw_lookup or handle them in another step 
    (like picking the correct weather file).
    """
    if not user_config_epw:
        return epw_lookup

    for rule in user_config_epw:
        if "fixed_epw_path" in rule:
            # e.g. set epw_lookup for that building
            pass
        if "desired_year" in rule and "override_year_to" in rule:
            pass

    return epw_lookup


def apply_shading_user_config(shading_dict, user_config_shading):
    """
    If you have shading.json with a list of rules:
      [
        {
           "building_id":4136730,
           "param_name":"top_n_buildings",
           "fixed_value":5
        },
        {
           "building_function":"residential",
           "param_name":"summer_value",
           "min_val":0.4,"max_val":0.6
        }
      ]
    We store them in shading_dict or do some logic.
    """
    if not user_config_shading:
        return shading_dict

    for rule in user_config_shading:
        p_name     = rule.get("param_name")
        fixed_val  = rule.get("fixed_value")
        min_val    = rule.get("min_val")
        max_val    = rule.get("max_val")

        if p_name and fixed_val is not None:
            shading_dict[p_name] = fixed_val
        # If min_val/max_val => pick random or store

    return shading_dict
