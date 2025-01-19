"""
user_config_overrides.py

Handles partial overrides from user-provided configurations (e.g. JSON).
If the user sets infiltration=0.4–0.6 or occupant_density=0.08, we apply
those in memory, without permanently changing the default dictionaries.

We demonstrate separate functions for geometry, fenestration, DHW, HVAC,
lighting, ventilation, epw, etc. Each function merges user config fields
into the base dictionary.
"""

def apply_geometry_user_config(geometry_dict, user_config_geom):
    """
    user_config_geom might be a list of override rules like:
      [
        { "building_id": 4136730, "param_name": "perimeter_depth", "fixed_value": 3.5 },
        { "building_type": "Meeting Function", "param_name": "has_core", "fixed_value": True }
      ]
    We'll parse these rules and override geometry_dict accordingly.
    """
    if not user_config_geom:
        return geometry_dict

    # Example approach:
    for rule in user_config_geom:
        # parse building_id, building_type, param_name, fixed_value / min_val / max_val
        param_name = rule.get("param_name")
        fixed_val = rule.get("fixed_value")
        if param_name and fixed_val is not None:
            geometry_dict[param_name] = fixed_val

    return geometry_dict


def apply_fenestration_user_config(fenez_dict, user_config_fenez):
    """
    If the user config has keys like "wwr", or "material_window_lookup",
    we override those in fenez_dict.
    """
    if not user_config_fenez:
        return fenez_dict

    # If the user config is a dictionary:
    # Example:
    # {
    #   "wwr": 0.32,
    #   "material_opaque_lookup": "Concrete_200mm",
    #   "elements": {
    #       "windows": { "U_value": 3.0, ... },
    #       "doors": { ... }
    #   }
    # }
    for key, val in user_config_fenez.items():
        if key == "elements":
            # handle sub-elements
            for elem_name, elem_dict in val.items():
                # e.g. fenez_dict["elements"][elem_name].update(elem_dict)
                pass
        else:
            # top-level override
            fenez_dict[key] = val

    return fenez_dict


def apply_dhw_user_config(dhw_lookup, user_config_dhw):
    """
    If user_config_dhw is a list of rules or a dict for partial override.
    """
    if not user_config_dhw:
        return dhw_lookup

    # Example if user_config_dhw is a list of override rules
    for rule in user_config_dhw:
        # { "dhw_key": "Office", "param_name": "setpoint_c", "min_val": 58.0, "max_val": 60.0 }
        dhw_key = rule.get("dhw_key")
        param_name = rule.get("param_name")
        fixed_value = rule.get("fixed_value")
        min_val = rule.get("min_val")
        max_val = rule.get("max_val")

        if dhw_key in dhw_lookup:
            # Suppose dhw_lookup[dhw_key] is a dict
            if fixed_value is not None:
                dhw_lookup[dhw_key][param_name] = fixed_value
            else:
                # If we do random pick from min_val/max_val
                # ...
                pass

    return dhw_lookup


def apply_lighting_user_config(lighting_lookup, user_config_lighting):
    """
    If user_config_lighting is a list or dict specifying new ranges/values for lighting.
    """
    if not user_config_lighting:
        return lighting_lookup

    # Example if it's a list of rules
    for rule in user_config_lighting:
        # { "building_id": 4136730, "param_name": "lights_wm2", "min_val":8.0, "max_val":10.0 }
        # Might do an in-memory override. Pseudocode below:
        pass

    return lighting_lookup


def apply_hvac_user_config(hvac_lookup, user_config_hvac):
    """
    Merge partial overrides like { "heating_day_setpoint": 21.0 } into hvac_lookup.
    """
    if not user_config_hvac:
        return hvac_lookup

    # Example if user_config_hvac is a list or a dict
    if isinstance(user_config_hvac, dict):
        # Merge dictionary
        for k, v in user_config_hvac.items():
            hvac_lookup[k] = v
    else:
        # or if it's a list of rules
        for rule in user_config_hvac:
            # ...
            pass

    return hvac_lookup


def apply_ventilation_user_config(vent_lookup, user_config_vent):
    """
    If user_config_vent is a list of infiltration or system param overrides
    for building_id or building_function.
    """
    if not user_config_vent:
        return vent_lookup

    # For each override rule, apply partial changes
    for rule in user_config_vent:
        # ...
        pass

    return vent_lookup


def apply_epw_user_config(epw_lookup, user_config_epw):
    """
    If the user wants to fix a certain EPW path for building_id X, or override a year.
    """
    if not user_config_epw:
        return epw_lookup

    # For example, user_config_epw = [
    #     {"building_id": 4136730, "fixed_epw_path": "C:/MyCustom.epw"}
    # ]
    for rule in user_config_epw:
        # ...
        pass

    return epw_lookup
