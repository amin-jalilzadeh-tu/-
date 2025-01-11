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
    """
    final_mat = dict(mat_def)  # shallow copy to preserve original
    obj_type = final_mat["obj_type"].upper()

    if obj_type == "MATERIAL":
        # mass-based
        thick = pick_val(final_mat.get("Thickness_range", (0.2, 0.2)), strategy)
        cond  = pick_val(final_mat.get("Conductivity_range", (1.4, 1.4)), strategy)
        dens  = pick_val(final_mat.get("Density_range", (2300, 2300)), strategy)
        sh    = pick_val(final_mat.get("Specific_Heat_range", (900, 900)), strategy)
        thabs = pick_val(final_mat.get("Thermal_Absorptance_range", (0.9, 0.9)), strategy)
        soabs = pick_val(final_mat.get("Solar_Absorptance_range", (0.7, 0.7)), strategy)
        viabs = pick_val(final_mat.get("Visible_Absorptance_range", (0.7, 0.7)), strategy)

        final_mat["Thickness"]           = thick
        final_mat["Conductivity"]        = cond
        final_mat["Density"]             = dens
        final_mat["Specific_Heat"]       = sh
        final_mat["Thermal_Absorptance"] = thabs
        final_mat["Solar_Absorptance"]   = soabs
        final_mat["Visible_Absorptance"] = viabs

    elif obj_type == "MATERIAL:NOMASS":
        # no-mass => thermal_resistance
        r_val  = pick_val(final_mat.get("Thermal_Resistance_range", (0.35, 0.35)), strategy)
        thabs = pick_val(final_mat.get("Thermal_Absorptance_range", (0.9, 0.9)), strategy)
        soabs = pick_val(final_mat.get("Solar_Absorptance_range", (0.7, 0.7)), strategy)
        viabs = pick_val(final_mat.get("Visible_Absorptance_range", (0.7, 0.7)), strategy)

        final_mat["Thermal_Resistance"]  = r_val
        final_mat["Thermal_Absorptance"] = thabs
        final_mat["Solar_Absorptance"]   = soabs
        final_mat["Visible_Absorptance"] = viabs

    elif obj_type == "WINDOWMATERIAL:GLAZING":
        # single-pane or multi-pane glass
        thick = pick_val(final_mat.get("Thickness_range", (0.003, 0.003)), strategy)
        s_trans = pick_val(final_mat.get("Solar_Transmittance_range", (0.76, 0.76)), strategy)
        fsr = pick_val(final_mat.get("Front_Solar_Reflectance_range", (0.07, 0.07)), strategy)
        bsr = pick_val(final_mat.get("Back_Solar_Reflectance_range", (0.07, 0.07)), strategy)
        v_trans = pick_val(final_mat.get("Visible_Transmittance_range", (0.86, 0.86)), strategy)
        fvr = pick_val(final_mat.get("Front_Visible_Reflectance_range", (0.06, 0.06)), strategy)
        bvr = pick_val(final_mat.get("Back_Visible_Reflectance_range", (0.06, 0.06)), strategy)
        fir = pick_val(final_mat.get("Front_IR_Emissivity_range", (0.84, 0.84)), strategy)
        bir = pick_val(final_mat.get("Back_IR_Emissivity_range", (0.84, 0.84)), strategy)
        cond = pick_val(final_mat.get("Conductivity_range", (1.0, 1.0)), strategy)
        dcf  = pick_val(final_mat.get("Dirt_Correction_Factor_range", (1.0, 1.0)), strategy)

        final_mat["Thickness"]                          = thick
        final_mat["Solar_Transmittance"]                = s_trans
        final_mat["Front_Solar_Reflectance"]            = fsr
        final_mat["Back_Solar_Reflectance"]             = bsr
        final_mat["Visible_Transmittance"]              = v_trans
        final_mat["Front_Visible_Reflectance"]          = fvr
        final_mat["Back_Visible_Reflectance"]           = bvr
        final_mat["Front_IR_Emissivity"]                = fir
        final_mat["Back_IR_Emissivity"]                 = bir
        final_mat["Conductivity"]                       = cond
        final_mat["Dirt_Correction_Factor"]             = dcf

    else:
        # fallback - do nothing special
        pass

    return final_mat

###############################################################################
#   The main function to retrieve data and combine user overrides
###############################################################################

def compute_wwr(elements_dict, include_doors=False):
    """
    Compute WWR => (window area) / (external wall area).
    If include_doors=True, add door area to the 'window portion'.
    """
    external_wall_area = 0.0
    # summation of known exterior wall keys
    if "exterior_wall" in elements_dict:
        external_wall_area += elements_dict["exterior_wall"].get("area_m2", 0.0)
    # If your data uses e.g. "solid_wall", "facade_wall", etc., accumulate them similarly.

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
    4) Then for sub-elements => e.g. ground_floor, windows, doors => picks R_value, U_value, area, etc.
       plus references to 'material_opaque_lookup' or 'material_window_lookup' if present.
    5) If user_config_fenez is provided, it can override some picks at the end.
    6) We recompute conductivity or thermal_resistance so the final R or U from data dictionary is used.
    7) Returns a dictionary => {
         "roughness": ...,
         "wwr": ...,
         "material_opaque": ...,
         "material_window": ...,
         "elements": {...}
       }
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
            "material_opaque": None,
            "material_window": None,
            "elements": {}
        }
        # Possibly let user_config_fenez override WWR
        if user_config_fenez and "wwr" in user_config_fenez:
            output_fallback["wwr"] = user_config_fenez["wwr"]
        return output_fallback

    data_entry = ds[dict_key]

    # pick wwr
    wwr_val = pick_val(data_entry.get("wwr_range", (0.3, 0.3)), strategy)
    # roughness
    rough_str = data_entry.get("roughness", "MediumRough")

    # top-level opaque & window
    mat_opq_key = data_entry.get("material_opaque_lookup", None)
    final_opq = None
    if mat_opq_key and mat_opq_key in material_lookup:
        final_opq = assign_material_from_lookup(material_lookup[mat_opq_key], strategy)

    mat_win_key = data_entry.get("material_window_lookup", None)
    final_win = None
    if mat_win_key and mat_win_key in material_lookup:
        final_win = assign_material_from_lookup(material_lookup[mat_win_key], strategy)

    # sub-elements
    elements = {}
    possible_elems = [
        "ground_floor", "exterior_wall", "flat_roof", "sloping_flat_roof", 
        "inter_floor", "interior_wall", "windows", "doors"
    ]
    for elem_name in possible_elems:
        if elem_name in data_entry:
            subd = data_entry[elem_name]
            out_sub = dict(subd)  # shallow copy

            # pick R_value
            if "R_value_range" in subd:
                out_sub["R_value"] = pick_val(subd["R_value_range"], strategy)
            # pick U_value
            if "U_value_range" in subd:
                out_sub["U_value"] = pick_val(subd["U_value_range"], strategy)

            # material_opaque
            if "material_opaque_lookup" in subd:
                mokey = subd["material_opaque_lookup"]
                if mokey in material_lookup:
                    out_sub["material_opaque"] = assign_material_from_lookup(
                        material_lookup[mokey],
                        strategy
                    )

            # material_window
            if "material_window_lookup" in subd:
                mwkey = subd["material_window_lookup"]
                if mwkey in material_lookup:
                    out_sub["material_window"] = assign_material_from_lookup(
                        material_lookup[mwkey],
                        strategy
                    )
            elements[elem_name] = out_sub

    result = {
        "roughness": rough_str,
        "wwr": wwr_val,
        "material_opaque": final_opq,
        "material_window": final_win,
        "elements": elements
    }

    # user_config_fenez override
    if user_config_fenez is not None:
        # override top-level WWR
        if "wwr" in user_config_fenez:
            result["wwr"] = user_config_fenez["wwr"]
        # override top-level mat lookups
        if "material_opaque_lookup" in user_config_fenez:
            new_opq_key = user_config_fenez["material_opaque_lookup"]
            if new_opq_key in material_lookup:
                result["material_opaque"] = assign_material_from_lookup(material_lookup[new_opq_key], strategy)
        if "material_window_lookup" in user_config_fenez:
            new_win_key = user_config_fenez["material_window_lookup"]
            if new_win_key in material_lookup:
                result["material_window"] = assign_material_from_lookup(material_lookup[new_win_key], strategy)
        # override sub-elements
        if "elements" in user_config_fenez:
            for elem_key, elem_val in user_config_fenez["elements"].items():
                if elem_key not in result["elements"]:
                    result["elements"][elem_key] = {}
                if "R_value" in elem_val:
                    result["elements"][elem_key]["R_value"] = elem_val["R_value"]
                if "U_value" in elem_val:
                    result["elements"][elem_key]["U_value"] = elem_val["U_value"]
                if "area_m2" in elem_val:
                    result["elements"][elem_key]["area_m2"] = elem_val["area_m2"]
                if "material_opaque_lookup" in elem_val:
                    mk = elem_val["material_opaque_lookup"]
                    if mk in material_lookup:
                        result["elements"][elem_key]["material_opaque"] = assign_material_from_lookup(
                            material_lookup[mk], strategy
                        )
                if "material_window_lookup" in elem_val:
                    mwk = elem_val["material_window_lookup"]
                    if mwk in material_lookup:
                        result["elements"][elem_key]["material_window"] = assign_material_from_lookup(
                            material_lookup[mwk], strategy
                        )

    # final step => enforce the R_value or U_value in the sub-element materials
    for elem_name, elem_data in result["elements"].items():
        r_val = elem_data.get("R_value", None)
        u_val = elem_data.get("U_value", None)
        if r_val is None and u_val is not None and u_val != 0:
            r_val = 1.0 / u_val

        # override opaque
        mat_opq = elem_data.get("material_opaque", None)
        if mat_opq and r_val is not None:
            if mat_opq["obj_type"].upper() == "MATERIAL":
                # conduction = thickness / R
                thick = mat_opq["Thickness"]
                if r_val != 0:
                    mat_opq["Conductivity"] = thick / r_val
            elif mat_opq["obj_type"].upper() == "MATERIAL:NOMASS":
                # set Thermal_Resistance
                mat_opq["Thermal_Resistance"] = r_val

        # override window
        mat_win = elem_data.get("material_window", None)
        if mat_win and u_val is not None and u_val != 0:
            if mat_win["obj_type"].upper() == "WINDOWMATERIAL:GLAZING":
                thick = mat_win["Thickness"]
                # approximate => conduction = U * thickness
                mat_win["Conductivity"] = u_val * thick

    return result
