# fenez/materials.py

from geomeppy import IDF
from .materials_config import get_extended_materials_data

def _store_material_picks(assigned_fenez_log, building_id, label, mat_data):
    """
    A helper to store final material picks in assigned_fenez_log[building_id][label].
    Skips any keys that end with '_range'.
    E.g. label might be 'top_opq' or 'top_win' or 'element_floor', etc.
    """
    if not mat_data:
        return

    # Only store final picks (no ranges)
    filtered = {}
    for k, v in mat_data.items():
        if k.endswith("_range"):
            continue
        filtered[k] = v

    if building_id not in assigned_fenez_log:
        assigned_fenez_log[building_id] = {}

    assigned_fenez_log[building_id][f"fenez_{label}"] = filtered


def update_construction_materials(
    idf,
    building_row,
    building_index=None,         # <--- add this
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_fenez=None,
    assigned_fenez_log=None
):
    """
    1) Calls get_extended_materials_data(...) => returns a dict with final picks
       (no longer just ranges).
    2) Removes all existing Materials & Constructions from the IDF (clean slate).
    3) Creates new Opaque & Window materials (if present) => including top-level fallback
       named e.g. "CEILING1C", "WINDOW1C", etc. so your geometry references remain valid.
    4) Creates distinct sub-element-based materials & constructions if you want to assign them
       separately (like "exterior_wall_Construction", "ground_floor_Construction", etc.).
    5) Logs assigned final picks (no range) into assigned_fenez_log if provided.

    Returns
    -------
    construction_map : dict
        A dictionary that maps sub-element name => construction name (e.g.
        "exterior_wall" => "exterior_wall_Construction"). You can use this to
        assign surfaces more precisely in your geometry code or assign_constructions_to_surfaces(...).
    """
    # 1) Get ID from building_row or fall back to building_index
    building_id = building_row.get("ogc_fid", None)
    if building_id is None:
        building_id = building_index

    # 1) Identify building function & type
    bldg_func = building_row.get("building_function", "residential")
    if bldg_func.lower() == "residential":
        bldg_type = building_row.get("residential_type", "")
    else:
        bldg_type = building_row.get("non_residential_type", "")

    age_range = building_row.get("age_range", "2015 and later")
    building_id = building_row.get("ogc_fid", None)  # or "pand_id"

    # 2) Retrieve extended materials data
    data = get_extended_materials_data(
        building_function=bldg_func,
        building_type=bldg_type,
        age_range=age_range,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez
    )

    mat_opq = data.get("material_opaque", None)
    mat_win = data.get("material_window", None)
    elements_data = data.get("elements", {})

    # 2b) If logging final picks, store them now
    if assigned_fenez_log is not None and building_id is not None:
        _store_material_picks(assigned_fenez_log, building_id, "top_opq", mat_opq)
        _store_material_picks(assigned_fenez_log, building_id, "top_win", mat_win)
        for elem_name, elem_data in elements_data.items():
            opq_sub = elem_data.get("material_opaque", None)
            win_sub = elem_data.get("material_window", None)
            _store_material_picks(assigned_fenez_log, building_id, f"{elem_name}_opq", opq_sub)
            _store_material_picks(assigned_fenez_log, building_id, f"{elem_name}_win", win_sub)

            # Also store final numeric R_value / U_value, area, etc.
            if "R_value" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_R_value"] = elem_data["R_value"]
            if "U_value" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_U_value"] = elem_data["U_value"]
            if "area_m2" in elem_data:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_area_m2"] = elem_data["area_m2"]

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

    # Helper to create an Opaque Material in E+
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

    # Helper to create a Window Material in E+
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

    # 4) Create top-level fallback Opaque & Window Materials
    opq_name = None
    if mat_opq:
        opq_name = create_opaque_material(idf, mat_opq, mat_opq["Name"])

    win_name = None
    if mat_win:
        win_name = create_window_material(idf, mat_win, mat_win["Name"])

    #
    # 4B) Create top-level *Constructions* using EXACT names that your geometry references
    # e.g. "CEILING1C" for ceilings, "WINDOW1C" for fenestrations, etc.
    #

    # If your geometry references "CEILING1C" for all ceilings, create that:
    if opq_name:
        c_ceil = idf.newidfobject("CONSTRUCTION")
        c_ceil.Name = "CEILING1C"        # EXACT match
        c_ceil.Outside_Layer = opq_name

    # Possibly also create "Ext_Walls1C", "Roof1C", "GroundFloor1C", etc.
    # so that no mismatch occurs for surfaces referencing them.
    if opq_name:
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

        # Key for interior floors (and ceilings) that are interzone:
        c_ifloor = idf.newidfobject("CONSTRUCTION")
        c_ifloor.Name = "IntFloor1C"
        c_ifloor.Outside_Layer = opq_name

    if win_name:
        c_win = idf.newidfobject("CONSTRUCTION")
        c_win.Name = "WINDOW1C"         # EXACT name used by your fenestration surfaces
        c_win.Outside_Layer = win_name

    #
    # 5) Create sub-element materials & constructions if you want to do more granular assignment
    #

    construction_map = {}  # { "exterior_wall": "exterior_wall_Construction", ...}

    for elem_name, elem_data in elements_data.items():
        mat_opq_sub = elem_data.get("material_opaque", None)
        mat_win_sub = elem_data.get("material_window", None)

        opq_sub_name = None
        win_sub_name = None

        # Create a new material for Opaque
        if mat_opq_sub:
            sub_opq_name = f"{elem_name}_OpaqueMat"
            opq_sub_name = create_opaque_material(idf, mat_opq_sub, sub_opq_name)

        # Create a new material for Window
        if mat_win_sub:
            sub_win_name = f"{elem_name}_WindowMat"
            win_sub_name = create_window_material(idf, mat_win_sub, sub_win_name)

        # Create a new Opaque Construction
        if opq_sub_name:
            c_sub = idf.newidfobject("CONSTRUCTION")
            c_sub.Name = f"{elem_name}_Construction"
            c_sub.Outside_Layer = opq_sub_name
            construction_map[elem_name] = c_sub.Name

        # (Optional) Create a separate Window Construction
        # if you want sub-element windows => e.g. "exterior_wall_window_Construction"
        if win_sub_name:
            c_sub_win = idf.newidfobject("CONSTRUCTION")
            c_sub_win.Name = f"{elem_name}_WindowConst"
            c_sub_win.Outside_Layer = win_sub_name
            construction_map[f"{elem_name}_window"] = c_sub_win.Name

    # Print them out
    print("[update_construction_materials] => Created fallback top-level constructions:")
    if opq_name:
        print("  -> CEILING1C, Ext_Walls1C, Int_Walls1C, Roof1C, GroundFloor1C, IntFloor1C")
    if win_name:
        print("  -> WINDOW1C")

    print("[update_construction_materials] => Created sub-element-based constructions:")
    for k, v in construction_map.items():
        print(f"  {k} => {v}")

    return construction_map


def assign_constructions_to_surfaces(idf, construction_map):
    """
    Assign each BUILDINGSURFACE:DETAILED to a suitable construction name
    based on sub-element keys and boundary conditions.

    We assume you have sub-element keys like:
      - "exterior_wall", "ground_floor", "flat_roof", "inter_floor", etc.
    and that your code in update_construction_materials(...) created
    'exterior_wall_Construction', 'ground_floor_Construction', etc.

    construction_map : dict
      e.g. {"exterior_wall": "exterior_wall_Construction",
            "ground_floor": "ground_floor_Construction",
            "windows": "windows_Construction" (maybe?),
            ...}

    NOTE: For interzone floors/ceilings, we use "IntFloor1C" so that both sides
    of the same partition share the same construction, avoiding E+ layer mismatch.
    """

    for surface in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        s_type = surface.Surface_Type.upper()  # "WALL", "ROOF", "CEILING", "FLOOR", etc.
        bc = surface.Outside_Boundary_Condition.upper()  # "OUTDOORS", "SURFACE", "GROUND", ...

        if s_type == "WALL":
            if bc == "OUTDOORS":
                # Use sub-element "exterior_wall" if exists
                if "exterior_wall" in construction_map:
                    surface.Construction_Name = construction_map["exterior_wall"]
                else:
                    surface.Construction_Name = "Ext_Walls1C"
            elif bc in ["SURFACE", "ADIABATIC"]:
                # Interior or adiabatic => maybe "interior_wall"
                if "interior_wall" in construction_map:
                    surface.Construction_Name = construction_map["interior_wall"]
                else:
                    surface.Construction_Name = "Int_Walls1C"
            else:
                surface.Construction_Name = "Ext_Walls1C"

        elif s_type == "ROOF":
            if bc == "OUTDOORS":
                # Possibly "flat_roof" or fallback
                if "flat_roof" in construction_map:
                    surface.Construction_Name = construction_map["flat_roof"]
                else:
                    surface.Construction_Name = "Roof1C"
            else:
                # If it's an interior roof for some reason
                surface.Construction_Name = "Int_Walls1C"

        elif s_type == "CEILING":
            # If it's an interzone (bc = SURFACE), use the same as IntFloor1C
            if bc in ["SURFACE", "ADIABATIC"]:
                if "inter_floor" in construction_map:
                    surface.Construction_Name = construction_map["inter_floor"]
                else:
                    surface.Construction_Name = "IntFloor1C"
            else:
                # e.g. an external or zone-ceiling to unconditioned attic
                surface.Construction_Name = "CEILING1C"

        elif s_type == "FLOOR":
            if bc == "GROUND":
                # sub-element "ground_floor"
                if "ground_floor" in construction_map:
                    surface.Construction_Name = construction_map["ground_floor"]
                else:
                    surface.Construction_Name = "GroundFloor1C"
            elif bc in ["SURFACE", "ADIABATIC"]:
                # inter_floor
                if "inter_floor" in construction_map:
                    surface.Construction_Name = construction_map["inter_floor"]
                else:
                    surface.Construction_Name = "IntFloor1C"
            else:
                surface.Construction_Name = "GroundFloor1C"

        else:
            # fallback if we see e.g. "OTHER"
            surface.Construction_Name = "Ext_Walls1C"

    # 2) Fenestrations
    for fen in idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]:
        # If you created "windows" sub-element => "windows_Construction"
        # or simply "Window1C" as fallback
        if "windows" in construction_map:
            fen.Construction_Name = construction_map["windows"]
        else:
            fen.Construction_Name = "Window1C"

    print("[assign_constructions_to_surfaces] => Surfaces assigned via sub-element logic.")
