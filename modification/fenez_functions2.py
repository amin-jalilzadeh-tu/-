# fenez_functions.py

"""
This module provides functions for applying fenestration & envelope parameters 
to an EnergyPlus IDF, analogous to HVAC or Vent modules.

It offers:
  1) apply_building_level_fenez(...) => calls update_construction_materials, 
     assign_constructions_to_surfaces, add_fenestration, etc.
  2) apply_object_level_fenez(...)  => advanced approach that processes 
     'structured_fenez_params.csv' row by row, updating IDF objects directly.
"""

import pandas as pd
from fenez.materials import (
    update_construction_materials,
    assign_constructions_to_surfaces
)
from fenez.fenestration import add_fenestration

##############################################################################
# 1) BUILDING-LEVEL FENESTRATION
##############################################################################

def apply_building_level_fenez(
    idf,
    building_row,
    param_dict=None,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_fenez=None,
    assigned_fenez_log=None,
    # controlling whether we create windows from WWR, etc.
    add_windows=True,
    use_computed_wwr=False,
    include_doors_in_wwr=False
):
    """
    A high-level function to:
      1) Generate new Materials & Constructions from fenestration data 
         (using update_construction_materials).
      2) Assign those Constructions to surfaces (assign_constructions_to_surfaces).
      3) Optionally call add_fenestration(...) to set WWR or create new windows.

    param_dict: 
      - If you already have a dictionary of final picks for R-values, U-values, 
        wwr, or material lookups, you can pass it via user_config_fenez. 
        (We typically do so, or rely on the building_row’s default data 
         plus any scenario-based logic.)

    building_row:
      - A dictionary with fields like "ogc_fid", "building_function", etc. 
      - This is used by `update_construction_materials` to find age_range, etc.

    assigned_fenez_log:
      - If provided, the final picks (R-values, thickness, conduction, WWR, etc.) 
        are logged under assigned_fenez_log[building_id].

    add_windows:
      - If True, we call add_fenestration(...) to create new FENESTRATIONSURFACE:DETAILED 
        in the IDF (using `geomeppy.IDF.set_wwr`).
      - If False, we skip that part.

    use_computed_wwr, include_doors_in_wwr:
      - Passed to add_fenestration(...) for computing WWR from sub-element areas 
        or including door area in the fenestration ratio.

    Returns:
      construction_map: dict mapping sub-element name => construction name 
                       (for reference if needed).
    """

    # 1) Update constructions & materials
    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=None,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez,  # param_dict could be merged here
        assigned_fenez_log=assigned_fenez_log
    )

    # 2) Assign them to surfaces
    assign_constructions_to_surfaces(idf, construction_map)

    # 3) Optionally add fenestration (WWR)
    if add_windows:
        add_fenestration(
            idf=idf,
            building_row=building_row,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=random_seed,
            user_config_fenez=user_config_fenez,
            assigned_fenez_log=assigned_fenez_log,
            use_computed_wwr=use_computed_wwr,
            include_doors_in_wwr=include_doors_in_wwr
        )

    return construction_map


##############################################################################
# 2) OBJECT-LEVEL FENESTRATION (Optional)
##############################################################################

def apply_object_level_fenez(idf, df_fenez):
    """
    Reads 'structured_fenez_params.csv' row by row (like 
    apply_zone_level_vent or apply_object_level_elec). Each row might specify:

      - ogc_fid
      - sub_key (like "top_opq", "exterior_wall_opq", "exterior_wall_win", etc.)
      - eplus_object_type (MATERIAL, MATERIAL:NOMASS, WINDOWMATERIAL:GLAZING, CONSTRUCTION, ...)
      - eplus_object_name  (the intended name to create or update)
      - param_name         (Thickness, Conductivity, R_value, U_value, roughness, etc.)
      - param_value
      - param_min, param_max

    Then we can do a grouping approach:
      1) group by (eplus_object_type, eplus_object_name)
      2) create or update that object in the IDF
      3) set param_name => param_value accordingly

    This is a more direct “row-based” approach. 
    *Use with caution*, as some fields like "R_value" are computed 
    rather than direct IDF fields. But you can adapt the logic 
    to recalc thickness or conductivity as needed.

    Steps:
      - group df_fenez by eplus_object_type + eplus_object_name
      - for each group, create or find the object in IDF
      - for each param_name => param_value, set the corresponding field 
        (or do a special logic if it’s “R_value” => recalc conductivity)
    """

    group_cols = ["eplus_object_type", "eplus_object_name"]
    grouped = df_fenez.groupby(group_cols)

    for (obj_type, obj_name), group_df in grouped:
        print(f"[FENEZ] Handling {obj_type} => '{obj_name}' with {len(group_df)} rows.")

        # 1) Attempt to find or create the object in IDF
        obj_type_upper = obj_type.upper()
        if obj_type_upper not in idf.idfobjects:
            # If your IDF doesn't have that object type, skip or handle
            print(f"[FENEZ WARNING] IDF has no object type '{obj_type_upper}', skipping.")
            continue

        # search by Name
        existing_obj = [
            o for o in idf.idfobjects[obj_type_upper]
            if hasattr(o, "Name") and o.Name.upper() == obj_name.upper()
        ]
        if existing_obj:
            eplus_obj = existing_obj[0]
        else:
            # create new
            eplus_obj = idf.newidfobject(obj_type_upper)
            if hasattr(eplus_obj, "Name"):
                eplus_obj.Name = obj_name
            else:
                print(f"[FENEZ WARNING] {obj_type_upper} has no 'Name' field? object creation is partial.")
                # continue or skip

        # 2) row by row => param_name => param_value
        for row in group_df.itertuples():
            p_name = row.param_name
            val    = row.param_value

            # example: if param_name == "Thickness", we set eplus_obj.Thickness = val
            # But if param_name is "R_value", we might recalc conductivity or Thermal_Resistance
            try:
                val_float = float(val)
            except (ValueError, TypeError):
                val_float = None  # might be a string

            # A simple approach:
            if p_name.lower() in ["roughness", "optical_data_type", "solar_diffusing"]:
                # likely a string
                if hasattr(eplus_obj, p_name):
                    setattr(eplus_obj, p_name, str(val))
            elif p_name.lower() in ["thickness", "conductivity", "density", "specific_heat",
                                    "thermal_resistance", "solar_transmittance", 
                                    "front_solar_reflectance", "back_solar_reflectance",
                                    "visible_transmittance", "front_visible_reflectance",
                                    "back_visible_reflectance", "front_ir_emissivity",
                                    "back_ir_emissivity", "dirt_correction_factor"]:
                # numeric
                field_name = _match_field_name(eplus_obj, p_name)  # optional helper
                if field_name:
                    setattr(eplus_obj, field_name, val_float)
            elif p_name.lower() in ["r_value", "u_value"]:
                # these are computed fields, not direct. 
                # you'd need to recalc thickness or conduction. 
                # For brevity, we skip or do partial logic:
                pass
            else:
                # fallback
                field_name = _match_field_name(eplus_obj, p_name)
                if field_name:
                    # try float or string
                    setattr(eplus_obj, field_name, val_float if val_float is not None else val)
                else:
                    print(f"[FENEZ WARNING] No direct field match for param_name='{p_name}'. Skipping.")

        print(f"[FENEZ] Updated {obj_type}=>'{obj_name}' with new fields.")


def _match_field_name(eplus_obj, param_name):
    """
    A small helper to guess the correct IDF field name from param_name 
    if there's a mismatch. If your param_name exactly matches the IDF field, 
    you can skip this step. If you want more advanced mappings 
    (like 'Front_Solar_Reflectance' => 'Front_Side_Solar_Reflectance_at_Normal_Incidence'), 
    code it here.
    """

    # e.g. if param_name=='Front_Solar_Reflectance', we match it to 
    # "Front_Side_Solar_Reflectance_at_Normal_Incidence"
    # This can be a dictionary approach:
    map_dict = {
        "front_solar_reflectance": "Front_Side_Solar_Reflectance_at_Normal_Incidence",
        "back_solar_reflectance":  "Back_Side_Solar_Reflectance_at_Normal_Incidence",
        "front_visible_reflectance": "Front_Side_Visible_Reflectance_at_Normal_Incidence",
        "back_visible_reflectance":  "Back_Side_Visible_Reflectance_at_Normal_Incidence",
        "front_ir_emissivity": "Front_Side_Infrared_Hemispherical_Emissivity",
        "back_ir_emissivity":  "Back_Side_Infrared_Hemispherical_Emissivity",
        "solar_transmittance": "Solar_Transmittance_at_Normal_Incidence",
        "visible_transmittance": "Visible_Transmittance_at_Normal_Incidence",
        "dirt_correction_factor": "Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance"
        # etc.
    }

    p_lower = param_name.lower()
    if p_lower in map_dict:
        candidate_field = map_dict[p_lower]
        if hasattr(eplus_obj, candidate_field):
            return candidate_field
        else:
            return None

    # If param_name matches a direct field:
    if hasattr(eplus_obj, param_name):
        return param_name

    # fallback => None
    return None
