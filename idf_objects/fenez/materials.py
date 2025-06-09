"""
materials.py

This module handles:
 1) Creating new MATERIAL & CONSTRUCTION objects in the IDF
    (including window materials).
 2) Storing logs of the final picks (and any range fields) in assigned_fenez_log
    for possible CSV or JSON output.
 3) Optionally reassigning surfaces to the newly created constructions.

Key functions:
  - update_construction_materials(...)
  - assign_constructions_to_surfaces(...)
"""

from geomeppy import IDF
from .materials_config import get_extended_materials_data

def _store_material_picks(assigned_fenez_log, building_id, label, mat_data):
    """
    A helper to store final material picks (and any range fields) in
    assigned_fenez_log[building_id].

    'label' might be "top_opq", "top_win", or "exterior_wall_opq", etc.

    We flatten the dict so each key becomes:
       f"fenez_{label}.{key}" => value

    Example:
      label == "top_opq"
      mat_data == {
         "obj_type": "MATERIAL",
         "Thickness": 0.2,
         "Thickness_range": (0.15, 0.25),
         ...
      }
      We store:
        assigned_fenez_log[building_id]["fenez_top_opq.obj_type"] = "MATERIAL"
        assigned_fenez_log[building_id]["fenez_top_opq.Thickness_range"] = (0.15, 0.25)
      etc.
    """
    if not mat_data or not assigned_fenez_log:
        return

    if building_id not in assigned_fenez_log:
        assigned_fenez_log[building_id] = {}

    for k, v in mat_data.items():
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
       (including sub-element R/U and range fields, plus top-level materials).
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

    Notes
    -----
    - The newly created Constructions (CEILING1C, Ext_Walls1C, Window1C, etc.)
      can be referenced when you set surfaces or WWR. These fallback
      constructions now first look for element-specific materials before
      defaulting to the top-level material.
    - If you have many building surfaces, you'll typically call
      'assign_constructions_to_surfaces(...)' afterwards to match them properly.
    """

    # 1) Determine building_id for logging
    building_id = building_row.get("ogc_fid", None)
    if building_id is None:
        building_id = building_index

    # 2) Retrieve extended materials data (with overrides)
    data = get_extended_materials_data(
        building_function=building_row.get("building_function", "residential"),
        building_type=(
            building_row.get("residential_type", "")
            if building_row.get("building_function", "").lower() == "residential"
            else building_row.get("non_residential_type", "")
        ),
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
        if building_id not in assigned_fenez_log:
            assigned_fenez_log[building_id] = {}
        # Log top-level data: "roughness", "wwr_range_used", "wwr", etc.
        for top_key in ["roughness", "wwr_range_used", "wwr"]:
            if top_key in data:
                assigned_fenez_log[building_id][f"fenez_{top_key}"] = data[top_key]

        # Also store the top-level opaque/window material details
        _store_material_picks(assigned_fenez_log, building_id, "top_opq", mat_opq)
        _store_material_picks(assigned_fenez_log, building_id, "top_win", mat_win)

        # For each sub-element, store final picks + ranges
        for elem_name, elem_data in elements_data.items():
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
        "CONSTRUCTION",
    ]:
        for obj in idf.idfobjects[obj_type][:]:
            try:
                idf.removeidfobject(obj)
            except ValueError:
                # Object might have been removed earlier; ignore
                pass

    def create_opaque_material(idf_obj, mat_data, mat_name):
        """
        Create or update a MATERIAL or MATERIAL:NOMASS in the IDF with the
        given name and properties from ``mat_data``.  Existing objects with the
        same name are removed first to avoid EnergyPlus duplicate name errors.

        Returns the new object's name or ``None``.
        """
        if not mat_data or "obj_type" not in mat_data:
            return None

        mat_type = mat_data["obj_type"].upper()

        # Remove any existing object with this name first
        if mat_type in ["MATERIAL", "MATERIAL:NOMASS"]:
            for obj in idf_obj.idfobjects[mat_type]:
                if obj.Name == mat_name:
                    try:
                        idf_obj.removeidfobject(obj)
                    except ValueError:
                        pass

        if mat_type == "MATERIAL":
            mat_obj = idf_obj.newidfobject("MATERIAL")
            mat_obj.Name = mat_name  # Use the exact name from the lookup/dict
            mat_obj.Roughness = mat_data.get("Roughness", "MediumRough")
            mat_obj.Thickness = mat_data.get("Thickness", 0.1)
            mat_obj.Conductivity = mat_data.get("Conductivity", 1.0)
            mat_obj.Density = mat_data.get("Density", 2000.0)
            mat_obj.Specific_Heat = mat_data.get("Specific_Heat", 900.0)
            mat_obj.Thermal_Absorptance = mat_data.get("Thermal_Absorptance", 0.9)
            mat_obj.Solar_Absorptance   = mat_data.get("Solar_Absorptance", 0.7)
            mat_obj.Visible_Absorptance = mat_data.get("Visible_Absorptance", 0.7)
            return mat_obj.Name

        elif mat_type == "MATERIAL:NOMASS":
            mat_obj = idf_obj.newidfobject("MATERIAL:NOMASS")
            mat_obj.Name = mat_name  # Use the exact name from the lookup/dict
            mat_obj.Roughness = mat_data.get("Roughness", "MediumRough")
            mat_obj.Thermal_Resistance = mat_data.get("Thermal_Resistance", 0.5)
            mat_obj.Thermal_Absorptance = mat_data.get("Thermal_Absorptance", 0.9)
            mat_obj.Solar_Absorptance   = mat_data.get("Solar_Absorptance", 0.7)
            mat_obj.Visible_Absorptance = mat_data.get("Visible_Absorptance", 0.7)
            return mat_obj.Name

        return None

    def create_window_material(idf_obj, mat_data, mat_name):
        """
        Create a window material (GLAZING or SIMPLEGLAZINGSYSTEM) with mat_data.
        Returns the new object's name or None.
        """
        if not mat_data or "obj_type" not in mat_data:
            return None

        wtype = mat_data["obj_type"].upper()

        # Remove existing object with this name first
        if wtype in ["WINDOWMATERIAL:GLAZING", "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM"]:
            for obj in idf_obj.idfobjects[wtype]:
                if obj.Name == mat_name:
                    try:
                        idf_obj.removeidfobject(obj)
                    except ValueError:
                        pass

        if wtype == "WINDOWMATERIAL:GLAZING":
            wmat = idf_obj.newidfobject("WINDOWMATERIAL:GLAZING")
            wmat.Name = mat_name
            wmat.Optical_Data_Type = mat_data.get("Optical_Data_Type", "SpectralAverage")
            wmat.Thickness = mat_data.get("Thickness", 0.003)
            wmat.Solar_Transmittance_at_Normal_Incidence = mat_data.get("Solar_Transmittance", 0.77)
            wmat.Front_Side_Solar_Reflectance_at_Normal_Incidence = mat_data.get("Front_Solar_Reflectance", 0.07)
            wmat.Back_Side_Solar_Reflectance_at_Normal_Incidence  = mat_data.get("Back_Solar_Reflectance", 0.07)
            wmat.Visible_Transmittance_at_Normal_Incidence        = mat_data.get("Visible_Transmittance", 0.86)
            wmat.Front_Side_Visible_Reflectance_at_Normal_Incidence = mat_data.get("Front_Visible_Reflectance", 0.07)
            wmat.Back_Side_Visible_Reflectance_at_Normal_Incidence  = mat_data.get("Back_Visible_Reflectance", 0.07)
            wmat.Infrared_Transmittance_at_Normal_Incidence         = mat_data.get("IR_Transmittance", 0.0)
            wmat.Front_Side_Infrared_Hemispherical_Emissivity       = mat_data.get("Front_IR_Emissivity", 0.84)
            wmat.Back_Side_Infrared_Hemispherical_Emissivity        = mat_data.get("Back_IR_Emissivity", 0.84)
            wmat.Conductivity = mat_data.get("Conductivity", 1.0)
            wmat.Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance = mat_data.get("Dirt_Correction_Factor", 1.0)
            wmat.Solar_Diffusing = mat_data.get("Solar_Diffusing", "No")
            return wmat.Name

        elif wtype == "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM":
            wmat = idf_obj.newidfobject("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM")
            wmat.Name = mat_name
            # If your code includes a derived U_value or SHGC, set them here:
            u_val  = mat_data.get("U_value", 2.9)
            shgc   = mat_data.get("SHGC", 0.6)
            vt     = mat_data.get("Visible_Transmittance", 0.7)  # if you store one
            wmat.UFactor = u_val
            wmat.Solar_Heat_Gain_Coefficient = shgc
            wmat.Visible_Transmittance = vt
            return wmat.Name

        return None

    # 4) Create top-level fallback Materials & Constructions
    opq_name = None
    if mat_opq:
        # Use the dictionary's own "Name" if present
        name_from_dict = mat_opq.get("Name", "TopOpaqueMaterialFallback")
        opq_name = create_opaque_material(idf, mat_opq, name_from_dict)
        if assigned_fenez_log and building_id is not None and opq_name:
            assigned_fenez_log[building_id]["fenez_top_opaque_material_name"] = opq_name

    win_name = None
    if mat_win:
        # Use the dictionary's own "Name" if present
        name_from_dict = mat_win.get("Name", "TopWindowMaterialFallback")
        win_name = create_window_material(idf, mat_win, name_from_dict)
        if assigned_fenez_log and building_id is not None and win_name:
            assigned_fenez_log[building_id]["fenez_top_window_material_name"] = win_name

    # Create fallback Constructions (CEILING1C, Ext_Walls1C, etc.).
    # Each construction uses the element-specific material when available,
    # otherwise it falls back to the top-level opaque material.
    # Avoid creating duplicate materials by caching.

    created_layers = {}
    if opq_name:
        created_layers[opq_name] = opq_name

    def _layer_for_fallback(elem_key):
        """
        If we have a sub-element material, use its lookup name.
        Otherwise fallback to the top-level opq_name.
        """
        mat = elements_data.get(elem_key, {}).get("material_opaque")
        if not mat:
            return opq_name  # fallback

        name = mat.get("Name", f"{elem_key}_Mat")
        if name not in created_layers:
            created_layers[name] = create_opaque_material(idf, mat, name)
        return created_layers[name]

    ceil_layer = _layer_for_fallback("flat_roof")
    ext_layer  = _layer_for_fallback("exterior_wall")
    intw_layer = _layer_for_fallback("interior_wall")
    roof_layer = _layer_for_fallback("flat_roof")   # same as ceil_layer in this example
    grnd_layer = _layer_for_fallback("ground_floor")
    ifloor_layer = _layer_for_fallback("inter_floor")

    # If any of these exist, create the fallback 1C constructions
    # (CEILING1C, Ext_Walls1C, Int_Walls1C, etc.)
    if any([ceil_layer, ext_layer, intw_layer, roof_layer, grnd_layer, ifloor_layer]):
        if ceil_layer:
            c_ceil = idf.newidfobject("CONSTRUCTION")
            c_ceil.Name = "CEILING1C"
            c_ceil.Outside_Layer = ceil_layer

        if ext_layer:
            c_ext = idf.newidfobject("CONSTRUCTION")
            c_ext.Name = "Ext_Walls1C"
            c_ext.Outside_Layer = ext_layer

        if intw_layer:
            c_intw = idf.newidfobject("CONSTRUCTION")
            c_intw.Name = "Int_Walls1C"
            c_intw.Outside_Layer = intw_layer

        if roof_layer:
            c_roof = idf.newidfobject("CONSTRUCTION")
            c_roof.Name = "Roof1C"
            c_roof.Outside_Layer = roof_layer

        if grnd_layer:
            c_grnd = idf.newidfobject("CONSTRUCTION")
            c_grnd.Name = "GroundFloor1C"
            c_grnd.Outside_Layer = grnd_layer

        if ifloor_layer:
            c_ifloor = idf.newidfobject("CONSTRUCTION")
            c_ifloor.Name = "IntFloor1C"
            c_ifloor.Outside_Layer = ifloor_layer

    # Create a fallback Window1C construction if top-level window name exists
    if win_name:
        c_win = idf.newidfobject("CONSTRUCTION")
        c_win.Name = "Window1C"
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

        # For the sub-element's opaque material, use its actual "Name" from the dictionary
        if mat_opq_sub:
            sub_opq_name = mat_opq_sub.get("Name", f"{elem_name}_OpaqueMat")
            opq_sub_name = create_opaque_material(idf, mat_opq_sub, sub_opq_name)
            if assigned_fenez_log and building_id is not None and opq_sub_name:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_opq_material_name"] = opq_sub_name

        # For the sub-element's window material
        if mat_win_sub:
            sub_win_name = mat_win_sub.get("Name", f"{elem_name}_WindowMat")
            win_sub_name = create_window_material(idf, mat_win_sub, sub_win_name)
            if assigned_fenez_log and building_id is not None and win_sub_name:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_win_material_name"] = win_sub_name

        # create new Opaque Construction for the sub-element
        if opq_sub_name:
            c_sub = idf.newidfobject("CONSTRUCTION")
            c_sub.Name = f"{elem_name}_Construction"
            c_sub.Outside_Layer = opq_sub_name
            construction_map[elem_name] = c_sub.Name

            if assigned_fenez_log and building_id is not None:
                assigned_fenez_log[building_id][f"fenez_{elem_name}_construction_name"] = c_sub.Name

        # create a separate window construction if we have a window material
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
    based on sub-element keys, surface type, boundary condition, etc.

    construction_map: e.g.
      {
        "exterior_wall": "exterior_wall_Construction",
        "exterior_wall_window": "exterior_wall_WindowConst",
        "ground_floor": "ground_floor_Construction",
        ...
      }

    Typically, you'll call this after update_construction_materials(...).

    Example usage:
        c_map = update_construction_materials(...)
        assign_constructions_to_surfaces(idf, c_map)
    """
    for surface in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        s_type = surface.Surface_Type.upper()
        bc = surface.Outside_Boundary_Condition.upper()

        if s_type == "WALL":
            if bc == "OUTDOORS":
                # If sub-element 'exterior_wall' is in the map, use it; otherwise fallback
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
                # fallback
                surface.Construction_Name = "Ext_Walls1C"

        elif s_type in ["ROOF", "CEILING"]:
            if bc == "OUTDOORS":
                if "flat_roof" in construction_map:
                    surface.Construction_Name = construction_map["flat_roof"]
                else:
                    surface.Construction_Name = "Roof1C"
            elif bc in ["ADIABATIC", "SURFACE"]:
                if "inter_floor" in construction_map:
                    surface.Construction_Name = construction_map["inter_floor"]
                else:
                    surface.Construction_Name = "IntFloor1C"
            else:
                surface.Construction_Name = "Roof1C"

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

    # Now fenestrations
    for fen in idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]:
        # If there's a sub-element key "windows" or "exterior_wall_window"
        # in the construction_map, assign it. Otherwise fallback to "Window1C".
        if "windows" in construction_map:
            fen.Construction_Name = construction_map["windows"]
        else:
            # If you have e.g. "exterior_wall_window" in the map, you can do:
            # if "exterior_wall_window" in construction_map:
            #     fen.Construction_Name = construction_map["exterior_wall_window"]
            # else: fallback
            fen.Construction_Name = "Window1C"

    print("[assign_constructions_to_surfaces] => Surfaces assigned via sub-element logic.")
