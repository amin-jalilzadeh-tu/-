# fenez/materials_config.py

import random
from .data_materials_residential import residential_materials_data
from .data_materials_non_residential import non_residential_materials_data
from .materials_lookup import material_lookup

###############################################################################
#   pick_val(...) & assign_material_from_lookup(...) helper functions
###############################################################################

def pick_val(rng, strategy="A"):
    """
    Helper to pick a single float from (min_val, max_val).
    If rng=(x,x), return x.
    If strategy="A", pick the midpoint. If "B", pick random uniform in the range.
    Otherwise, fallback to rng[0].
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
    # If one side is None, you could handle that or just return min
    return min_val if min_val is not None else max_val


def assign_material_from_lookup(mat_def: dict, strategy="A"):
    """
    Takes a dict from material_lookup, which has fields like "Thickness_range",
    "Conductivity_range", etc. Returns a *copy* with final numeric picks assigned.

    # NEW OR CHANGED:
    # This function remains mostly the same, but you can store the picked range
    # in the returned dict if you want. For instance, final_mat["Thickness_range_used"] = ...
    """
    final_mat = dict(mat_def)  # shallow copy to preserve original
    obj_type = final_mat["obj_type"].upper()

    # Extract the relevant ranges for convenience
    thick_rng = final_mat.get("Thickness_range", None)
    cond_rng  = final_mat.get("Conductivity_range", None)

    if obj_type == "MATERIAL":
        # mass-based
        final_mat["Thickness"] = pick_val(thick_rng, strategy)
        final_mat["Conductivity"] = pick_val(cond_rng, strategy)
        final_mat["Density"] = pick_val(final_mat.get("Density_range", (2300, 2300)), strategy)
        final_mat["Specific_Heat"] = pick_val(final_mat.get("Specific_Heat_range", (900, 900)), strategy)
        final_mat["Thermal_Absorptance"] = pick_val(final_mat.get("Thermal_Absorptance_range", (0.9, 0.9)), strategy)
        final_mat["Solar_Absorptance"]   = pick_val(final_mat.get("Solar_Absorptance_range", (0.7, 0.7)), strategy)
        final_mat["Visible_Absorptance"] = pick_val(final_mat.get("Visible_Absorptance_range", (0.7, 0.7)), strategy)

    elif obj_type == "MATERIAL:NOMASS":
        # no-mass => thermal_resistance
        r_rng = final_mat.get("Thermal_Resistance_range", None)
        final_mat["Thermal_Resistance"] = pick_val(r_rng, strategy)
        final_mat["Thermal_Absorptance"] = pick_val(final_mat.get("Thermal_Absorptance_range", (0.9, 0.9)), strategy)
        final_mat["Solar_Absorptance"]   = pick_val(final_mat.get("Solar_Absorptance_range", (0.7, 0.7)), strategy)
        final_mat["Visible_Absorptance"] = pick_val(final_mat.get("Visible_Absorptance_range", (0.7, 0.7)), strategy)

    elif obj_type == "WINDOWMATERIAL:GLAZING":
        # single-pane or multi-pane glass
        final_mat["Thickness"] = pick_val(thick_rng, strategy)
        final_mat["Solar_Transmittance"] = pick_val(final_mat.get("Solar_Transmittance_range", (0.76, 0.76)), strategy)
        final_mat["Front_Solar_Reflectance"] = pick_val(final_mat.get("Front_Solar_Reflectance_range", (0.07, 0.07)), strategy)
        final_mat["Back_Solar_Reflectance"]  = pick_val(final_mat.get("Back_Solar_Reflectance_range", (0.07, 0.07)), strategy)
        final_mat["Visible_Transmittance"]   = pick_val(final_mat.get("Visible_Transmittance_range", (0.86, 0.86)), strategy)
        final_mat["Front_Visible_Reflectance"] = pick_val(final_mat.get("Front_Visible_Reflectance_range", (0.06, 0.06)), strategy)
        final_mat["Back_Visible_Reflectance"]  = pick_val(final_mat.get("Back_Visible_Reflectance_range", (0.06, 0.06)), strategy)
        final_mat["Front_IR_Emissivity"]       = pick_val(final_mat.get("Front_IR_Emissivity_range", (0.84, 0.84)), strategy)
        final_mat["Back_IR_Emissivity"]        = pick_val(final_mat.get("Back_IR_Emissivity_range", (0.84, 0.84)), strategy)
        final_mat["Conductivity"]              = pick_val(cond_rng, strategy)
        final_mat["Dirt_Correction_Factor"]    = pick_val(final_mat.get("Dirt_Correction_Factor_range", (1.0, 1.0)), strategy)
        # IR_Transmittance is usually zero, so we keep as is

    else:
        # fallback - do nothing special
        pass

    return final_mat


###############################################################################
#   The main function to retrieve data and combine user overrides (ranges + final)
###############################################################################

def compute_wwr(elements_dict, include_doors=False):
    """
    Compute WWR => (window area) / (external wall area).
    If include_doors=True, add door area as part of fenestration.
    """
    external_wall_area = 0.0
    if "exterior_wall" in elements_dict:
        external_wall_area += elements_dict["exterior_wall"].get("area_m2", 0.0)
    # If your data uses e.g. "solid_wall", etc., you can accumulate similarly.

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
    2) Picks from wwr_range => final wwr.
    3) Also grabs top-level 'material_opaque_lookup', 'material_window_lookup' if any.
    4) Then for sub-elements => e.g. ground_floor, windows, doors => picks R_value, U_value,
       area, etc., plus references to 'material_opaque_lookup' or 'material_window_lookup' if present.
    5) user_config_fenez can override the final picks, the range picks, or both.
    6) We recompute 'Conductivity' or 'Thermal_Resistance' so the final R or U from data dictionary is used.
    7) Returns a dictionary with all final picks (and new "xxx_range_used" fields).

    # NEW OR CHANGED:
    # - We'll also store "xxx_range_used" so that you can record what range was used
    #   before picking the final value. Then in materials.py, you can log it in assigned_fenez_log.
    # - We handle user_config_fenez that might override "R_value_range", "U_value_range", etc.
    """

    if random_seed is not None:
        random.seed(random_seed)

    # decide data source
    if building_function.lower() == "residential":
        ds = residential_materials_data
    else:
        ds = non_residential_materials_data

    dict_key = (building_type, age_range, scenario, calibration_stage)
    if dict_key not in ds:
        # fallback
        output_fallback = {
            "roughness": "MediumRough",
            "wwr": 0.3,
            "wwr_range_used": (0.3, 0.3),  # logging the fallback range
            "material_opaque": None,
            "material_window": None,
            "elements": {}
        }

        # Possibly let user_config_fenez override top-level WWR or WWR range
        if user_config_fenez:
            # override wwr range if present
            if "wwr_range" in user_config_fenez:
                output_fallback["wwr_range_used"] = user_config_fenez["wwr_range"]
            # final wwr
            if "wwr" in user_config_fenez:
                output_fallback["wwr"] = user_config_fenez["wwr"]

        return output_fallback

    data_entry = ds[dict_key]

    # Pick or override wwr range
    default_wwr_range = data_entry.get("wwr_range", (0.3, 0.3))
    if user_config_fenez and "wwr_range" in user_config_fenez:
        default_wwr_range = user_config_fenez["wwr_range"]  # override the range

    # Now pick final wwr from that range
    wwr_val = pick_val(default_wwr_range, strategy)

    # Possibly override the final wwr if user_config_fenez["wwr"] is present
    if user_config_fenez and "wwr" in user_config_fenez:
        wwr_val = user_config_fenez["wwr"]

    # top-level roughness
    rough_str = data_entry.get("roughness", "MediumRough")

    # top-level opaque & window (before user overrides)
    mat_opq_key = data_entry.get("material_opaque_lookup", None)
    mat_win_key = data_entry.get("material_window_lookup", None)

    # If user_config_fenez overrides these lookups
    if user_config_fenez:
        if "material_opaque_lookup" in user_config_fenez:
            mat_opq_key = user_config_fenez["material_opaque_lookup"]
        if "material_window_lookup" in user_config_fenez:
            mat_win_key = user_config_fenez["material_window_lookup"]

    # create final picks for top-level materials
    final_opq = None
    if mat_opq_key and mat_opq_key in material_lookup:
        final_opq = assign_material_from_lookup(material_lookup[mat_opq_key], strategy)
    final_win = None
    if mat_win_key and mat_win_key in material_lookup:
        final_win = assign_material_from_lookup(material_lookup[mat_win_key], strategy)

    # sub-elements
    possible_elems = [
        "ground_floor", "exterior_wall", "flat_roof", "sloping_flat_roof",
        "inter_floor", "interior_wall", "windows", "doors"
    ]
    elements = {}
    for elem_name in possible_elems:
        if elem_name in data_entry:
            subd = dict(data_entry[elem_name])  # shallow copy
            # (A) possibly override sub-element's R_value_range, U_value_range, area_m2, etc.
            if user_config_fenez and "elements" in user_config_fenez:
                user_elem_config = user_config_fenez["elements"].get(elem_name, {})
                # override sub-element range if found
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

            out_sub = dict(subd)  # Keep a copy that we will finalize

            # (B) pick R_value from its range
            r_val_rng = subd.get("R_value_range", None)
            r_val = pick_val(r_val_rng, strategy) if r_val_rng else None
            # (C) pick U_value from its range
            u_val_rng = subd.get("U_value_range", None)
            u_val = pick_val(u_val_rng, strategy) if u_val_rng else None

            # If user_config_fenez sets a fixed R_value or U_value, override
            if user_config_fenez and "elements" in user_config_fenez:
                user_elem_vals = user_config_fenez["elements"].get(elem_name, {})
                if "R_value" in user_elem_vals and user_elem_vals["R_value"] is not None:
                    r_val = user_elem_vals["R_value"]
                if "U_value" in user_elem_vals and user_elem_vals["U_value"] is not None:
                    u_val = user_elem_vals["U_value"]

            out_sub["R_value"] = r_val
            out_sub["U_value"] = u_val
            # also store "range_used" for clarity
            if r_val_rng:
                out_sub["R_value_range_used"] = r_val_rng
            if u_val_rng:
                out_sub["U_value_range_used"] = u_val_rng

            # (D) create sub-element material_opaque
            mat_opq_sub_key = subd.get("material_opaque_lookup", None)
            if mat_opq_sub_key and mat_opq_sub_key in material_lookup:
                out_sub["material_opaque"] = assign_material_from_lookup(
                    material_lookup[mat_opq_sub_key], strategy
                )
            else:
                out_sub["material_opaque"] = None

            # (E) create sub-element material_window
            mat_win_sub_key = subd.get("material_window_lookup", None)
            if mat_win_sub_key and mat_win_sub_key in material_lookup:
                out_sub["material_window"] = assign_material_from_lookup(
                    material_lookup[mat_win_sub_key], strategy
                )
            else:
                out_sub["material_window"] = None

            elements[elem_name] = out_sub

    # Build the result
    result = {
        "roughness": rough_str,
        "wwr_range_used": default_wwr_range,  # store the used range
        "wwr": wwr_val,
        "material_opaque": final_opq,
        "material_window": final_win,
        "elements": elements
    }

    # final step => enforce the R_value or U_value in the sub-element materials
    # i.e., if sub-element has R=2.5, we recalc thickness or conductivity for the opaque material
    for elem_name, elem_data in result["elements"].items():
        r_val = elem_data.get("R_value", None)
        u_val = elem_data.get("U_value", None)
        if r_val is None and u_val is not None and u_val != 0:
            r_val = 1.0 / u_val

        # override opaque
        mat_opq = elem_data.get("material_opaque", None)
        if mat_opq and r_val is not None:
            if mat_opq["obj_type"].upper() == "MATERIAL":
                thick = mat_opq["Thickness"]
                if r_val != 0:
                    mat_opq["Conductivity"] = thick / r_val
            elif mat_opq["obj_type"].upper() == "MATERIAL:NOMASS":
                mat_opq["Thermal_Resistance"] = r_val

        # override window
        mat_win = elem_data.get("material_window", None)
        if mat_win and u_val is not None and u_val != 0:
            if mat_win["obj_type"].upper() == "WINDOWMATERIAL:GLAZING":
                thick = mat_win["Thickness"]
                # approximate => conduction = U * thickness
                mat_win["Conductivity"] = u_val * thick

    return result
