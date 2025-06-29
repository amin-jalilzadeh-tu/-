"""
fenez/materials_config.py

Contains logic for picking final material properties from ranges,
including references to material_lookup for different obj_types (MATERIAL,
MATERIAL:NOMASS, WINDOWMATERIAL:GLAZING, WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM, etc.).

Key functions:
    - pick_val(...)
    - assign_material_from_lookup(...)
    - get_extended_materials_data(...)
    - compute_wwr(...)
"""

import random

# Update these imports to match your actual file locations:
from Lookups.data_materials_residential import residential_materials_data
from Lookups.data_materials_non_residential import non_residential_materials_data
from .materials_lookup import material_lookup


###############################################################################
#    pick_val(...) & assign_material_from_lookup(...) helper functions
###############################################################################

def pick_val(rng, strategy="A"):
    """
    Helper to pick a single float from a numeric range (min_val, max_val).
    If rng=(x,x), returns x.
    If strategy="A", picks the midpoint. If "B", picks random uniform.
    Otherwise, fallback to min_val.

    Parameters
    ----------
    rng : tuple of (float, float)
        (min_val, max_val).
    strategy : str
        "A" => midpoint, "B" => random uniform, etc.

    Returns
    -------
    A float in [min_val, max_val], or None if invalid.
    """
    if not rng or len(rng) < 2:
        return None
    min_val, max_val = rng
    if min_val is None and max_val is None:
        return None
    if min_val is not None and max_val is not None:
        if min_val == max_val:
            return min_val
        if strategy == "A":
            return (min_val + max_val) / 2.0
        elif strategy == "B":
            return random.uniform(min_val, max_val)
        else:
            # fallback => pick min
            return min_val
    # If one side is None, fallback to the other
    return min_val if min_val is not None else max_val


def assign_material_from_lookup(mat_def: dict, strategy="A"):
    """
    Takes a dict from material_lookup (which has fields like "Thickness_range",
    "Conductivity_range", etc.) and returns a *copy* with final numeric picks assigned.

    The function modifies keys like "Thickness", "Conductivity", "Thermal_Resistance",
    etc., based on the strategy for picking from each _range.

    Returns the updated dict.
    """
    final_mat = dict(mat_def)  # shallow copy to preserve original
    obj_type = final_mat["obj_type"].upper()

    # Some materials have thickness & conductivity ranges
    thick_rng = final_mat.get("Thickness_range", None)
    cond_rng  = final_mat.get("Conductivity_range", None)

    if obj_type == "MATERIAL":
        # Mass-based opaque
        final_mat["Thickness"] = pick_val(thick_rng, strategy)
        final_mat["Conductivity"] = pick_val(cond_rng, strategy)
        final_mat["Density"] = pick_val(final_mat.get("Density_range", (2300, 2300)), strategy)
        final_mat["Specific_Heat"] = pick_val(final_mat.get("Specific_Heat_range", (900, 900)), strategy)
        final_mat["Thermal_Absorptance"] = pick_val(final_mat.get("Thermal_Absorptance_range", (0.9, 0.9)), strategy)
        final_mat["Solar_Absorptance"]   = pick_val(final_mat.get("Solar_Absorptance_range", (0.7, 0.7)), strategy)
        final_mat["Visible_Absorptance"] = pick_val(final_mat.get("Visible_Absorptance_range", (0.7, 0.7)), strategy)

    elif obj_type == "MATERIAL:NOMASS":
        # No-mass => thermal_resistance
        r_rng = final_mat.get("Thermal_Resistance_range", None)
        final_mat["Thermal_Resistance"] = pick_val(r_rng, strategy)
        final_mat["Thermal_Absorptance"] = pick_val(final_mat.get("Thermal_Absorptance_range", (0.9, 0.9)), strategy)
        final_mat["Solar_Absorptance"]   = pick_val(final_mat.get("Solar_Absorptance_range", (0.7, 0.7)), strategy)
        final_mat["Visible_Absorptance"] = pick_val(final_mat.get("Visible_Absorptance_range", (0.7, 0.7)), strategy)

    elif obj_type == "WINDOWMATERIAL:GLAZING":
        # Typical single/multi-pane window material
        final_mat["Thickness"] = pick_val(thick_rng, strategy)
        final_mat["Solar_Transmittance"] = pick_val(
            final_mat.get("Solar_Transmittance_range", (0.76, 0.76)),
            strategy
        )
        final_mat["Front_Solar_Reflectance"] = pick_val(
            final_mat.get("Front_Solar_Reflectance_range", (0.07, 0.07)),
            strategy
        )
        final_mat["Back_Solar_Reflectance"]  = pick_val(
            final_mat.get("Back_Solar_Reflectance_range", (0.07, 0.07)),
            strategy
        )
        final_mat["Visible_Transmittance"]   = pick_val(
            final_mat.get("Visible_Transmittance_range", (0.86, 0.86)),
            strategy
        )
        final_mat["Front_Visible_Reflectance"] = pick_val(
            final_mat.get("Front_Visible_Reflectance_range", (0.06, 0.06)),
            strategy
        )
        final_mat["Back_Visible_Reflectance"]  = pick_val(
            final_mat.get("Back_Visible_Reflectance_range", (0.06, 0.06)),
            strategy
        )
        final_mat["Front_IR_Emissivity"]       = pick_val(
            final_mat.get("Front_IR_Emissivity_range", (0.84, 0.84)),
            strategy
        )
        final_mat["Back_IR_Emissivity"]        = pick_val(
            final_mat.get("Back_IR_Emissivity_range", (0.84, 0.84)),
            strategy
        )
        final_mat["Conductivity"]              = pick_val(cond_rng, strategy)
        final_mat["Dirt_Correction_Factor"]    = pick_val(
            final_mat.get("Dirt_Correction_Factor_range", (1.0, 1.0)),
            strategy
        )
        # IR_Transmittance often 0 => if stored, keep as is

    elif obj_type == "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM":
        # For simple glazing, you typically just set U-factor, SHGC, Visible Transmittance in E+.
        # We'll just pick from the provided ranges if present:
        final_mat["SHGC"] = pick_val(final_mat.get("SHGC_range", (0.40, 0.40)), strategy)
        # If "Optical_Data_Type" is stored as a numeric range for some reason, pick it:
        opt_dat = final_mat.get("Optical_Data_Type", None)
        # This might be a numeric or fixed string; handle gracefully:
        if isinstance(opt_dat, tuple) and len(opt_dat) == 2:
            final_mat["Optical_Data_Type"] = pick_val(opt_dat, strategy)
        else:
            # If it's a single string or float, just keep as is
            pass

        # You may also store a default U_value here if you keep a "U_value_range" in the dict

    else:
        # fallback - do nothing special
        pass

    return final_mat


###############################################################################
#    The main function to retrieve data & combine user overrides
###############################################################################

def compute_wwr(elements_dict, include_doors=False):
    """
    Compute WWR => (window area) / (exterior wall area).
    If include_doors=True, add door area to the fenestration area.
    """
    external_wall_area = 0.0
    if "exterior_wall" in elements_dict:
        external_wall_area += elements_dict["exterior_wall"].get("area_m2", 0.0)

    window_area = elements_dict.get("windows", {}).get("area_m2", 0.0)
    if include_doors and "doors" in elements_dict:
        window_area += elements_dict["doors"].get("area_m2", 0.0)

    if external_wall_area > 0:
        return window_area / external_wall_area
    else:
        return 0.0


def get_extended_materials_data(
    building_function: str,
    building_type: str,
    age_range: str,
    scenario: str,
    calibration_stage: str,
    strategy: str = "A",
    random_seed=None,
    user_config_fenez=None
):
    """
    1) Looks up either residential_materials_data or non_residential_materials_data
       by (building_type, age_range, scenario, calibration_stage).
    2) Retrieves "wwr_range" and picks a final 'wwr' if relevant.
    3) Grabs top-level 'material_opaque_lookup', 'material_window_lookup' if present.
    4) For each sub-element (e.g., ground_floor, windows, doors),
       picks R_value, U_value from (R_value_range, U_value_range).
    5) If user_config_fenez is provided, we override some fields (range or fixed).
    6) Return a dictionary with "wwr", "material_opaque", "material_window",
       plus "elements" sub-dicts for each sub-element with final picks.

    The final dict can then be used in materials.py to actually create IDF Materials/Constructions.
    """
    if random_seed is not None:
        random.seed(random_seed)

    # Pick which dataset to use
    if building_function.lower() == "residential":
        ds = residential_materials_data
    else:
        ds = non_residential_materials_data

    dict_key = (building_type, age_range, scenario, calibration_stage)
    if dict_key not in ds:
        # fallback if no data
        output_fallback = {
            "roughness": "MediumRough",
            "wwr": 0.3,
            "wwr_range_used": (0.3, 0.3),
            "material_opaque": None,
            "material_window": None,
            "elements": {}
        }
        # Possibly let user_config_fenez override wwr or wwr_range
        if user_config_fenez:
            if "wwr_range" in user_config_fenez:
                output_fallback["wwr_range_used"] = user_config_fenez["wwr_range"]
            if "wwr" in user_config_fenez:
                output_fallback["wwr"] = user_config_fenez["wwr"]
        return output_fallback

    data_entry = ds[dict_key]

    # 1) pick or override wwr_range
    default_wwr_range = data_entry.get("wwr_range", (0.3, 0.3))
    if user_config_fenez and "wwr_range" in user_config_fenez:
        default_wwr_range = user_config_fenez["wwr_range"]
    wwr_val = pick_val(default_wwr_range, strategy)

    # If user overrides wwr directly, apply it
    if user_config_fenez and "wwr" in user_config_fenez:
        wwr_val = user_config_fenez["wwr"]

    # 2) top-level roughness
    rough_str = data_entry.get("roughness", "MediumRough")

    # top-level materials
    mat_opq_key = data_entry.get("material_opaque_lookup", None)
    mat_win_key = data_entry.get("material_window_lookup", None)

    if user_config_fenez:
        if "material_opaque_lookup" in user_config_fenez:
            mat_opq_key = user_config_fenez["material_opaque_lookup"]
        if "material_window_lookup" in user_config_fenez:
            mat_win_key = user_config_fenez["material_window_lookup"]

    final_opq = None
    if mat_opq_key and mat_opq_key in material_lookup:
        final_opq = assign_material_from_lookup(material_lookup[mat_opq_key], strategy)

    final_win = None
    if mat_win_key and mat_win_key in material_lookup:
        final_win = assign_material_from_lookup(material_lookup[mat_win_key], strategy)

    # 3) sub-elements
    possible_elems = [
        "ground_floor", "exterior_wall", "flat_roof", "sloping_flat_roof",
        "inter_floor", "interior_wall", "windows", "doors"
    ]
    elements = {}
    for elem_name in possible_elems:
        if elem_name in data_entry:
            subd = dict(data_entry[elem_name])  # shallow copy

            # apply user overrides for sub-element if present
            if user_config_fenez and "elements" in user_config_fenez:
                user_elem_config = user_config_fenez["elements"].get(elem_name, {})
                if "R_value_range" in user_elem_config:
                    subd["R_value_range"] = user_elem_config["R_value_range"]
                if "U_value_range" in user_elem_config:
                    subd["U_value_range"] = user_elem_config["U_value_range"]
                if "area_m2" in user_elem_config:
                    subd["area_m2"] = user_elem_config["area_m2"]
                if "material_opaque_lookup" in user_elem_config:
                    subd["material_opaque_lookup"] = user_elem_config["material_opaque_lookup"]
                if "material_window_lookup" in user_elem_config:
                    subd["material_window_lookup"] = user_elem_config["material_window_lookup"]

            out_sub = dict(subd)

            # pick R_value / U_value
            r_val_rng = subd.get("R_value_range", None)
            u_val_rng = subd.get("U_value_range", None)
            r_val = pick_val(r_val_rng, strategy) if r_val_rng else None
            u_val = pick_val(u_val_rng, strategy) if u_val_rng else None

            # if user has a forced R_value / U_value
            if user_config_fenez and "elements" in user_config_fenez:
                user_elem_vals = user_config_fenez["elements"].get(elem_name, {})
                if "R_value" in user_elem_vals and user_elem_vals["R_value"] is not None:
                    r_val = user_elem_vals["R_value"]
                if "U_value" in user_elem_vals and user_elem_vals["U_value"] is not None:
                    u_val = user_elem_vals["U_value"]

            out_sub["R_value"] = r_val
            out_sub["U_value"] = u_val
            if r_val_rng:
                out_sub["R_value_range_used"] = r_val_rng
            if u_val_rng:
                out_sub["U_value_range_used"] = u_val_rng

            # sub-element material picks
            mat_opq_sub_key = subd.get("material_opaque_lookup", None)
            mat_win_sub_key = subd.get("material_window_lookup", None)

            if mat_opq_sub_key and mat_opq_sub_key in material_lookup:
                out_sub["material_opaque"] = assign_material_from_lookup(
                    material_lookup[mat_opq_sub_key],
                    strategy
                )
            else:
                out_sub["material_opaque"] = None

            if mat_win_sub_key and mat_win_sub_key in material_lookup:
                out_sub["material_window"] = assign_material_from_lookup(
                    material_lookup[mat_win_sub_key],
                    strategy
                )
            else:
                out_sub["material_window"] = None

            elements[elem_name] = out_sub

    # build final result
    result = {
        "roughness": rough_str,
        "wwr_range_used": default_wwr_range,
        "wwr": wwr_val,
        "material_opaque": final_opq,
        "material_window": final_win,
        "elements": elements
    }

    # 4) final step => if R_value or U_value is set, override the derived thickness/conductivity
    for elem_name, elem_data in result["elements"].items():
        r_val = elem_data.get("R_value", None)
        u_val = elem_data.get("U_value", None)
        if r_val is None and u_val is not None and u_val != 0:
            r_val = 1.0 / u_val

        mat_opq = elem_data.get("material_opaque", None)
        if mat_opq and r_val is not None:
            # re-derive Conductivity or Thermal_Resistance
            if mat_opq["obj_type"].upper() == "MATERIAL":
                thick = mat_opq["Thickness"]
                if r_val != 0:
                    mat_opq["Conductivity"] = thick / r_val
            elif mat_opq["obj_type"].upper() == "MATERIAL:NOMASS":
                mat_opq["Thermal_Resistance"] = r_val

        mat_win = elem_data.get("material_window", None)
        if mat_win and u_val is not None and u_val != 0:
            # For WINDOWMATERIAL:GLAZING, approximate conduction => U_value * thickness
            # For WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM, you might set a 'U_value' field directly
            if mat_win["obj_type"].upper() == "WINDOWMATERIAL:GLAZING":
                thick = mat_win.get("Thickness", 0.003)
                mat_win["Conductivity"] = u_val * thick
            elif mat_win["obj_type"].upper() == "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM":
                # store a direct property
                mat_win["U_value"] = u_val

    return result
