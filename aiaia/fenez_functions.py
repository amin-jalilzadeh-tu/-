# fenez_functions.py

import pandas as pd
import math
import random

def apply_object_level_fenez(idf, csv_path):
    """
    Reads 'structured_fenez_params.csv' from csv_path, which has columns:
       - ogc_fid
       - sub_key
       - eplus_object_type
       - eplus_object_name
       - param_name
       - param_value
       - param_min
       - param_max
    Groups the data by (eplus_object_type, eplus_object_name) and updates or creates
    the corresponding IDF objects. Then sets param_name => param_value.

    Special logic:
      - If param_name is 'R_value' or 'U_value', we recalc thickness/conductivity
        or thermal_resistance for (MATERIAL or MATERIAL:NOMASS).
      - For window material fields (WINDOWMATERIAL:GLAZING, etc.), we map short
        param_name => the actual IDF field.

    Usage example:
      apply_object_level_fenez(my_idf, "output/assigned/structured_fenez_params.csv")
    """
    df = pd.read_csv(csv_path)

    # 1) Group by object type & name
    group_cols = ["eplus_object_type", "eplus_object_name"]
    grouped = df.groupby(group_cols, dropna=False)

    for (obj_type, obj_name), group_df in grouped:
        if not isinstance(obj_type, str) or not isinstance(obj_name, str):
            # If either is blank or NaN, skip
            continue

        obj_type_upper = obj_type.upper().strip()
        obj_name_str   = obj_name.strip()

        if not obj_type_upper or not obj_name_str:
            continue

        # 2) Attempt to find or create the IDF object
        if obj_type_upper not in idf.idfobjects:
            # Possibly handle unknown IDF object types here
            print(f"[FENEZ WARNING] IDF does not have object type='{obj_type_upper}'. Skipping...")
            continue

        target_obj = _get_or_create_idf_object(idf, obj_type_upper, obj_name_str)
        # We'll track data needed for R_value or U_value recalculation
        mat_meta = {
            "obj_type": obj_type_upper,
            "thickness": None,
            "conductivity": None,
            "thermal_resistance": None
        }
        pending_rvalue = None
        pending_uvalue = None

        # 3) Iterate through each param row in the group
        for row in group_df.itertuples():
            p_name = str(row.param_name).strip()
            p_val  = row.param_value

            # Attempt numeric
            try:
                val_num = float(p_val)
                is_number = True
            except (ValueError, TypeError):
                val_num = p_val
                is_number = False

            # If p_name is "R_value" or "U_value", store temporarily
            if p_name.lower() == "r_value":
                pending_rvalue = val_num
                continue
            elif p_name.lower() == "u_value":
                pending_uvalue = val_num
                continue

            # If p_name is "Thickness", "Conductivity", or "Thermal_Resistance",
            # store in mat_meta so we can use it after we see an R_value or U_value
            if p_name.lower() in ["thickness", "conductivity", "thermal_resistance"]:
                if p_name.lower() == "thickness":
                    mat_meta["thickness"] = val_num
                elif p_name.lower() == "conductivity":
                    mat_meta["conductivity"] = val_num
                elif p_name.lower() == "thermal_resistance":
                    mat_meta["thermal_resistance"] = val_num

            # 4) Match the CSV param_name to the actual IDF field
            field_name = _map_param_to_idf_field(target_obj, p_name)
            if not field_name:
                # If no direct field, skip or warn
                print(f"[FENEZ WARNING] No matched field for '{p_name}' in {obj_type_upper} '{obj_name_str}'")
                continue

            # 5) Set the field
            setattr(target_obj, field_name, val_num)

        # 6) Handle R_value / U_value if present
        if (pending_rvalue is not None) or (pending_uvalue is not None):
            _handle_rvalue_or_uvalue(target_obj, mat_meta, pending_rvalue, pending_uvalue)

        print(f"[FENEZ] Updated {obj_type_upper} => '{obj_name_str}' with {len(group_df)} param rows.")


def _get_or_create_idf_object(idf, obj_type, name_str):
    """
    Finds or creates a new object in 'idf' of type obj_type
    (e.g. "MATERIAL", "WINDOWMATERIAL:GLAZING"), with Name == name_str.
    """
    existing_objs = [
        o for o in idf.idfobjects[obj_type]
        if hasattr(o, "Name") and str(o.Name).lower() == name_str.lower()
    ]
    if existing_objs:
        return existing_objs[0]
    else:
        new_obj = idf.newidfobject(obj_type)
        if hasattr(new_obj, "Name"):
            new_obj.Name = name_str
        return new_obj


def _map_param_to_idf_field(eplus_obj, param_name):
    """
    Maps CSV param_name => actual IDF field name on eplus_obj.
    If param_name is recognized from a known dictionary, return that mapped name.
    If param_name matches an attribute exactly, return that.
    Otherwise None.
    """
    # Example mapping dictionary for window fields:
    field_map = {
        "solar_transmittance": "Solar_Transmittance_at_Normal_Incidence",
        "front_solar_reflectance": "Front_Side_Solar_Reflectance_at_Normal_Incidence",
        "back_solar_reflectance":  "Back_Side_Solar_Reflectance_at_Normal_Incidence",
        "visible_transmittance":   "Visible_Transmittance_at_Normal_Incidence",
        "front_visible_reflectance": "Front_Side_Visible_Reflectance_at_Normal_Incidence",
        "back_visible_reflectance":  "Back_Side_Visible_Reflectance_at_Normal_Incidence",
        "ir_transmittance": "Infrared_Transmittance_at_Normal_Incidence",
        "front_ir_emissivity": "Front_Side_Infrared_Hemispherical_Emissivity",
        "back_ir_emissivity":  "Back_Side_Infrared_Hemispherical_Emissivity",
        "conductivity": "Conductivity",  # example
        "dirt_correction_factor": "Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance",
    }

    pn_lower = param_name.lower()

    if pn_lower in field_map:
        # If the mapped field is actually present on eplus_obj, use it
        mapped = field_map[pn_lower]
        if hasattr(eplus_obj, mapped):
            return mapped
        else:
            return None

    # If param_name matches an IDF field exactly (case-sensitive)
    if hasattr(eplus_obj, param_name):
        return param_name

    # If param_name differs by case:
    #   We can loop eplus_obj.fieldnames or eplus_obj.fieldkeys
    #   But let's keep it simple for this example
    # e.g. if param_name="Roughness" but the IDF object has "Roughness" => we can do direct match
    #   or if param_name="roughness" we might do an upper-lower approach.
    # In a real scenario, you'd do something like:
    # field_candidates = [f for f in eplus_obj.fieldnames if f.lower()==param_name.lower()]
    # if field_candidates:
    #     return field_candidates[0]
    # else:
    #     return None

    # We'll attempt a naive approach for this example:
    # check each field in eplus_obj.fieldnames ignoring case
    if hasattr(eplus_obj, "fieldnames"):
        for fn in eplus_obj.fieldnames:
            if fn.lower() == pn_lower:
                return fn

    return None


def _handle_rvalue_or_uvalue(eplus_obj, mat_meta, r_val, u_val):
    """
    If we have an R_value or U_value for a MATERIAL or MATERIAL:NOMASS,
    recalc the conductivity or Thermal_Resistance in eplus_obj accordingly.

    mat_meta = {
        "obj_type": "MATERIAL" or "MATERIAL:NOMASS",
        "thickness": float or None,
        "conductivity": float or None,
        "thermal_resistance": float or None
    }
    """
    if mat_meta["obj_type"].upper() in ["MATERIAL", "MATERIAL:NOMASS"]:
        # for MATERIAL => conduction = thickness / R_value or thickness * U_value
        if mat_meta["obj_type"].upper() == "MATERIAL":
            thick = mat_meta["thickness"]
            # if R_value is provided
            if r_val is not None and r_val != 0 and thick is not None:
                new_cond = float(thick) / float(r_val)
                if hasattr(eplus_obj, "Conductivity"):
                    eplus_obj.Conductivity = new_cond
                    print(f"    -> Recalc Conductivity from R_value={r_val}, thickness={thick:.4f} => {new_cond:.4f}")
            # if U_value is provided
            elif u_val is not None and u_val != 0 and thick is not None:
                new_cond = float(thick) * float(u_val)
                if hasattr(eplus_obj, "Conductivity"):
                    eplus_obj.Conductivity = new_cond
                    print(f"    -> Recalc Conductivity from U_value={u_val}, thickness={thick:.4f} => {new_cond:.4f}")

        # for MATERIAL:NOMASS => Thermal_Resistance = R_value or 1 / U_value
        elif mat_meta["obj_type"].upper() == "MATERIAL:NOMASS":
            if r_val is not None and r_val != 0:
                if hasattr(eplus_obj, "Thermal_Resistance"):
                    eplus_obj.Thermal_Resistance = float(r_val)
                    print(f"    -> Set Thermal_Resistance={r_val} (from R_value)")
            elif u_val is not None and u_val != 0:
                if hasattr(eplus_obj, "Thermal_Resistance"):
                    new_r = 1.0 / float(u_val)
                    eplus_obj.Thermal_Resistance = new_r
                    print(f"    -> Set Thermal_Resistance={new_r:.4f} (from U_value={u_val})")
    else:
        # for window materials or other object types => skip
        pass

