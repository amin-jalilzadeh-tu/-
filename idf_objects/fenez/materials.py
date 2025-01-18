# fenez/materials.py

from geomeppy import IDF
from .materials_config import get_extended_materials_data

def _store_material_picks(assigned_fenez_log, building_id, label, mat_data):
    """
    A helper to store final material picks (and any range fields) in assigned_fenez_log[building_id].
    `label` might be "top_opq", "top_win", or "exterior_wall_opq", etc.

    We'll flatten the dict so that each key becomes:
      "fenez_{label}.{key}" => value

    Example:
      if label == "top_opq" and mat_data == {
         "obj_type": "MATERIAL",
         "Thickness": 0.2,
         "Thickness_range": (0.15, 0.25),
         ...
      }
      we'll store assigned_fenez_log[building_id]["fenez_top_opq.obj_type"] = "MATERIAL"
      assigned_fenez_log[building_id]["fenez_top_opq.Thickness_range"] = (0.15, 0.25), etc.
    """
    if not mat_data:
        return

    if building_id not in assigned_fenez_log:
        assigned_fenez_log[building_id] = {}

    for k, v in mat_data.items():
        # Flatten as "fenez_{label}.{key}"
        assigned_fenez_log[building_id][f"fenez_{label}.{k}"] = v


def update_construction_materials(
    idf,
    building_row,
    building_index=None,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_fenez=None,
    assigned_fenez_log=None
):
    """
    1) Calls get_extended_materials_data(...) => returns a dict with final picks
       (including sub-element R/U and range fields).
    2) Removes all existing Materials & Constructions from the IDF (clean slate).
    3) Creates new Opaque & Window materials => including top-level fallback
       so geometry references remain valid.
    4) Creates distinct sub-element-based materials & constructions (e.g. "exterior_wall_Construction").
    5) Logs assigned final picks (and ranges) into assigned_fenez_log if provided.

    Returns
    -------
    construction_map : dict
        Maps sub-element name => construction name
        (e.g. {"exterior_wall": "exterior_wall_Construction", ...}).
    """
    # 1) Figure out building_id for logging
    building_id = building_row.get("ogc_fid", None)
    if building_id is None:
        building_id = building_index

    # 2) Retrieve extended materials data (with overrides)
    data = get_extended_materials_data(
        building_function=building_row.get("building_function", "residential"),
        building_type=(building_row.get("residential_type", "")
                       if building_row.get("building_function","").lower() == "residential"
                       else building_row.get("non_residential_type","")),
        age_range=building_row.get("age_range", "2015 and later"),
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez
    )

    mat_opq = data.get("material_opaque", None)
    mat_win = data.get("material_window", None)
    elements_data = data.get("elements", {})

    # 2b) If logging final picks + ranges, store them now
    if assigned_fenez_log is not None and building_id is not None:
        # <-- NEW: ensure we have a sub-dict
        if building_id not in assigned_fenez_log:
            assigned_fenez_log[building_id] = {}
            
        # Log top-level data: "roughness", "wwr_range_used", "wwr", etc.
        for top_key in ["roughness", "wwr_range_used", "wwr"]:
            if top_key in data:
                assigned_fenez_log[building_id][f"fenez_{top_key}"] = data[top_key]

        # Also store the top-level opaque and window material details
        _store_material_picks(assigned_fenez_log, building_id, "top_opq", mat_opq)
        _store_material_picks(assigned_fenez_log, building_id, "top_win", mat_win)

        # For each sub-element, store final picks + ranges
        for elem_name, elem_data in elements_data.items():
            # e.g. store "exterior_wall_R_value", "exterior_wall_R_value_range_used"
            if "R_value" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_R_value"] = elem_data["R_value"]
            if "R_value_range_used" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_R_value_range_used"] = elem_data["R_value_range_used"]

            if "U_value" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_U_value"] = elem_data["U_value"]
            if "U_value_range_used" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_U_value_range_used"] = elem_data["U_value_range_used"]

            if "area_m2" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_area_m2"] = elem_data["area_m2"]

            # Now store the sub-element's opaque & window material dict
            opq_sub = elem_data.get("material_opaque", None)
            win_sub = elem_data.get("material_window", None)
            _store_material_picks(assigned_fenez_log, building_id, f"{elem_name}_opq", opq_sub)
            _store_material_picks(assigned_fenez_log, building_id, f"{elem_name}_win", win_sub)

    # 3) Remove existing Materials & Constructions from the IDF
    for obj_type in [
        "MATERIAL",
        "MATERIAL:NOMASS",
        "WINDOWMATERIAL:GLAZING",
        "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
        "CONSTRUCTION"
    ]:
        for obj in idf.idfobjects[obj_type][:]:
            idf.removeidfobject(obj)

    def create_opaque_material(idf, mat_data, mat_name):
        if mat_data["obj_type"].upper() == "MATERIAL":
            mat_obj = idf.newidfobject("MATERIAL")
            mat_obj.Name = mat_name
            mat_obj.Roughness = mat_data.get("Roughness", "MediumRough")
            mat_obj.Thickness = mat_data["Thickness"]
            mat_obj.Conductivity = mat_data["Conductivity"]
            mat_obj.Density = mat_data["Density"]
            mat_obj.Specific_Heat = mat_data["Specific_Heat"]
            mat_obj.Thermal_Absorptance = mat_data["Thermal_Absorptance"]
            mat_obj.Solar_Absorptance   = mat_data["Solar_Absorptance"]
            mat_obj.Visible_Absorptance = mat_data["Visible_Absorptance"]
            return mat_obj.Name

        elif mat_data["obj_type"].upper() == "MATERIAL:NOMASS":
            mat_obj = idf.newidfobject("MATERIAL:NOMASS")
            mat_obj.Name = mat_name
            mat_obj.Roughness = mat_data.get("Roughness", "MediumRough")
            mat_obj.Thermal_Resistance = mat_data["Thermal_Resistance"]
            mat_obj.Thermal_Absorptance = mat_data["Thermal_Absorptance"]
            mat_obj.Solar_Absorptance   = mat_data["Solar_Absorptance"]
            mat_obj.Visible_Absorptance = mat_data["Visible_Absorptance"]
            return mat_obj.Name

        return None

    def create_window_material(idf, mat_data, mat_name):
        wtype = mat_data["obj_type"].upper()
        if wtype == "WINDOWMATERIAL:GLAZING":
            wmat = idf.newidfobject("WINDOWMATERIAL:GLAZING")
            wmat.Name = mat_name
            wmat.Optical_Data_Type = mat_data.get("Optical_Data_Type", "SpectralAverage")
            wmat.Thickness = mat_data["Thickness"]
            wmat.Solar_Transmittance_at_Normal_Incidence = mat_data["Solar_Transmittance"]
            wmat.Front_Side_Solar_Reflectance_at_Normal_Incidence = mat_data["Front_Solar_Reflectance"]
            wmat.Back_Side_Solar_Reflectance_at_Normal_Incidence  = mat_data["Back_Solar_Reflectance"]
            wmat.Visible_Transmittance_at_Normal_Incidence        = mat_data["Visible_Transmittance"]
            wmat.Front_Side_Visible_Reflectance_at_Normal_Incidence = mat_data["Front_Visible_Reflectance"]
            wmat.Back_Side_Visible_Reflectance_at_Normal_Incidence  = mat_data["Back_Visible_Reflectance"]
            wmat.Infrared_Transmittance_at_Normal_Incidence         = mat_data["IR_Transmittance"]
            wmat.Front_Side_Infrared_Hemispherical_Emissivity       = mat_data["Front_IR_Emissivity"]
            wmat.Back_Side_Infrared_Hemispherical_Emissivity        = mat_data["Back_IR_Emissivity"]
            wmat.Conductivity = mat_data["Conductivity"]
            wmat.Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance = mat_data["Dirt_Correction_Factor"]
            wmat.Solar_Diffusing = mat_data["Solar_Diffusing"]
            return wmat.Name

        elif wtype == "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM":
            wmat = idf.newidfobject("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM")
            wmat.Name = mat_name
            # If you want to set UFactor, SHGC, etc., do it here
            return wmat.Name

        return None

    # 4) Create top-level fallback Materials & Constructions
    opq_name = None
    if mat_opq:
        opq_name = create_opaque_material(idf, mat_opq, mat_opq["Name"])
        # Log the top-level opaque material name
        if assigned_fenez_log and building_id is not None and opq_name:
            assigned_fenez_log[building_id]["fenez_top_opaque_material_name"] = opq_name

    win_name = None
    if mat_win:
        win_name = create_window_material(idf, mat_win, mat_win["Name"])
        # Log the top-level window material name
        if assigned_fenez_log and building_id is not None and win_name:
            assigned_fenez_log[building_id]["fenez_top_window_material_name"] = win_name

    # Create fallback Constructions (CEILING1C, Window1C, etc.)
    if opq_name:
        c_ceil = idf.newidfobject("CONSTRUCTION")
        c_ceil.Name = "CEILING1C"
        c_ceil.Outside_Layer = opq_name

        c_ext = idf.newidfobject("CONSTRUCTION")
        c_ext.Name = "Ext_Walls1C"
        c_ext.Outside_Layer = opq_name

        c_intw = idf.newidfobject("CONSTRUCTION")
        c_intw.Name = "Int_Walls1C"
        c_intw.Outside_Layer = opq_name

        c_roof = idf.newidfobject("CONSTRUCTION")
        c_roof.Name = "Roof1C"
        c_roof.Outside_Layer = opq_name

        c_grnd = idf.newidfobject("CONSTRUCTION")
        c_grnd.Name = "GroundFloor1C"
        c_grnd.Outside_Layer = opq_name

        c_ifloor = idf.newidfobject("CONSTRUCTION")
        c_ifloor.Name = "IntFloor1C"
        c_ifloor.Outside_Layer = opq_name

        # If needed, log each fallback construction name

    if win_name:
        c_win = idf.newidfobject("CONSTRUCTION")
        c_win.Name = "WINDOW1C"
        c_win.Outside_Layer = win_name

        if assigned_fenez_log and building_id is not None:
            assigned_fenez_log[building_id]["fenez_window1C_construction"] = c_win.Name

    # 5) Create sub-element-based Materials & Constructions
    construction_map = {}
    for elem_name, elem_data in elements_data.items():
        mat_opq_sub = elem_data.get("material_opaque", None)
        mat_win_sub = elem_data.get("material_window", None)

        opq_sub_name = None
        win_sub_name = None

        # create opaque
        if mat_opq_sub:
            sub_opq_name = f"{elem_name}_OpaqueMat"
            opq_sub_name = create_opaque_material(idf, mat_opq_sub, sub_opq_name)
            # Log the actual E+ material name
            if assigned_fenez_log and building_id is not None and opq_sub_name:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_opq_material_name"] = opq_sub_name

        # create window
        if mat_win_sub:
            sub_win_name = f"{elem_name}_WindowMat"
            win_sub_name = create_window_material(idf, mat_win_sub, sub_win_name)
            # Log the actual E+ material name
            if assigned_fenez_log and building_id is not None and win_sub_name:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_win_material_name"] = win_sub_name

        # create new Opaque Construction
        if opq_sub_name:
            c_sub = idf.newidfobject("CONSTRUCTION")
            c_sub.Name = f"{elem_name}_Construction"
            c_sub.Outside_Layer = opq_sub_name
            construction_map[elem_name] = c_sub.Name

            if assigned_fenez_log and building_id is not None:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_construction_name"] = c_sub.Name

        # Optional: create a separate window construction
        if win_sub_name:
            c_sub_win = idf.newidfobject("CONSTRUCTION")
            c_sub_win.Name = f"{elem_name}_WindowConst"
            c_sub_win.Outside_Layer = win_sub_name
            construction_map[f"{elem_name}_window"] = c_sub_win.Name

            if assigned_fenez_log and building_id is not None:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_window_construction_name"] = c_sub_win.Name

    print("[update_construction_materials] => Created fallback top-level constructions (CEILING1C, etc.).")
    print("[update_construction_materials] => Created sub-element-based constructions:")
    for k, v in construction_map.items():
        print(f"   {k} => {v}")

    return construction_map


def assign_constructions_to_surfaces(idf, construction_map):
    """
    Assign each BUILDINGSURFACE:DETAILED to a suitable construction name
    based on sub-element keys and boundary conditions.

    construction_map: e.g.
      {
        "exterior_wall": "exterior_wall_Construction",
        "exterior_wall_window": "exterior_wall_WindowConst",
        "ground_floor": "ground_floor_Construction",
        ...
      }
    """
    for surface in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        s_type = surface.Surface_Type.upper()
        bc = surface.Outside_Boundary_Condition.upper()

        if s_type == "WALL":
            if bc == "OUTDOORS":
                if "exterior_wall" in construction_map:
                    surface.Construction_Name = construction_map["exterior_wall"]
                else:
                    surface.Construction_Name = "Ext_Walls1C"
            elif bc in ["SURFACE", "ADIABATIC"]:
                if "interior_wall" in construction_map:
                    surface.Construction_Name = construction_map["interior_wall"]
                else:
                    surface.Construction_Name = "Int_Walls1C"
            else:
                surface.Construction_Name = "Ext_Walls1C"

        elif s_type == "ROOF":
            if bc == "OUTDOORS":
                if "flat_roof" in construction_map:
                    surface.Construction_Name = construction_map["flat_roof"]
                else:
                    surface.Construction_Name = "Roof1C"
            else:
                surface.Construction_Name = "Int_Walls1C"

        elif s_type == "CEILING":
            if bc in ["SURFACE", "ADIABATIC"]:
                if "inter_floor" in construction_map:
                    surface.Construction_Name = construction_map["inter_floor"]
                else:
                    surface.Construction_Name = "IntFloor1C"
            else:
                surface.Construction_Name = "CEILING1C"

        elif s_type == "FLOOR":
            if bc == "GROUND":
                if "ground_floor" in construction_map:
                    surface.Construction_Name = construction_map["ground_floor"]
                else:
                    surface.Construction_Name = "GroundFloor1C"
            elif bc in ["SURFACE", "ADIABATIC"]:
                if "inter_floor" in construction_map:
                    surface.Construction_Name = construction_map["inter_floor"]
                else:
                    surface.Construction_Name = "IntFloor1C"
            else:
                surface.Construction_Name = "GroundFloor1C"
        else:
            # fallback
            surface.Construction_Name = "Ext_Walls1C"

    # Fenestrations
    for fen in idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]:
        # If there's a sub-element key "windows" in the construction_map
        if "windows" in construction_map:
            fen.Construction_Name = construction_map["windows"]
        else:
            fen.Construction_Name = "Window1C"

    print("[assign_constructions_to_surfaces] => Surfaces assigned via sub-element logic.")
