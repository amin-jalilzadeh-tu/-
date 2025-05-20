# D:\Documents\E_Plus_2030_py\geomz\zoning.py
# --------------------------------------------------------------------------
# This module handles the creation of zones (perimeter + core or single)
# for each floor in a building, plus optional interzone linking. 
# --------------------------------------------------------------------------

from .geometry import polygon_area, inward_offset_polygon

def link_surfaces(surface_a, surface_b):
    """
    Cross-link two surfaces as interzone partitions:
      1) Both Outside_Boundary_Condition = "Surface"
      2) Each references the other's name

    This is used for:
      - Perimeter zone to core zone partitions
      - Floor-to-ceiling linking between stories (in building.py)
    """
    surface_a.Outside_Boundary_Condition = "Surface"
    surface_b.Outside_Boundary_Condition = "Surface"
    surface_a.Outside_Boundary_Condition_Object = surface_b.Name
    surface_b.Outside_Boundary_Condition_Object = surface_a.Name


def create_zone_surfaces(
    idf,
    zone_name,
    base_poly,
    wall_height,
    floor_bc,
    wall_bcs,
    is_top_floor
):
    """
    Create a rectangular zone (Floor, 4 Walls, and a Roof or Ceiling).

    Parameters
    ----------
    idf : geomeppy.IDF
        The IDF to which we add surfaces.
    zone_name : str
        Name of the new Zone object (e.g. "Zone1", "Zone2_Core", etc.).
    base_poly : list of (x,y,z)
        4 corner points (in order) for the zone’s base polygon.
    wall_height : float
        Height of the walls for this floor (e.g. 2.5 m).
    floor_bc : str
        Boundary Condition for the floor (e.g. "Ground", "Adiabatic", "Outdoors").
    wall_bcs : list of str or dict
        4 items for the wall boundary conditions (one per edge).
        If a dict, e.g. {"bc": "Surface", "adj_surf_name": "..."},
        we can store info for cross-linking. If just a string, e.g. "Outdoors" or "Adiabatic".
    is_top_floor : bool
        If True => create a roof with Outdoors, else => a ceiling with "Adiabatic" (or a placeholder
        that can later be changed to "Surface" if linking to the floor above).

    Returns
    -------
    (zone_name, base_poly, top_poly, created_surfaces)
      zone_name        : str
      base_poly        : list of points (x,y,z) for the floor polygon
      top_poly         : list of points (x,y,z) for the upper polygon (floor + wall_height)
      created_surfaces : list of BUILDINGSURFACE:DETAILED objects created
    """
    zone = idf.newidfobject("ZONE")
    zone.Name = zone_name

    created_surfaces = []

    # ===== Floor =====
    floor_surf = idf.newidfobject("BUILDINGSURFACE:DETAILED")
    floor_surf.Name = f"{zone_name}_Floor"
    floor_surf.Surface_Type = "Floor"
    floor_surf.Zone_Name = zone_name
    floor_surf.Outside_Boundary_Condition = floor_bc

    # If we have "Outdoors", we set SunExposed, WindExposed; else NoSun/NoWind
    if floor_bc.lower() == "outdoors":
        floor_surf.Sun_Exposure = "SunExposed"
        floor_surf.Wind_Exposure = "WindExposed"
    else:
        floor_surf.Sun_Exposure = "NoSun"
        floor_surf.Wind_Exposure = "NoWind"

    # Reverse coords so the floor normal faces downward
    floor_surf.setcoords(base_poly[::-1])
    created_surfaces.append(floor_surf)

    # ===== Walls =====
    # The top polygon is base_poly + wall_height in Z
    top_poly = [(p[0], p[1], p[2] + wall_height) for p in base_poly]
    for i in range(4):
        p1 = base_poly[i]
        p2 = base_poly[(i + 1) % 4]
        p1t = top_poly[i]
        p2t = top_poly[(i + 1) % 4]

        wall_coords = [p1, p2, p2t, p1t]
        wall_obj = idf.newidfobject("BUILDINGSURFACE:DETAILED")
        wall_obj.Name = f"{zone_name}_Wall_{i}"
        wall_obj.Surface_Type = "Wall"
        wall_obj.Zone_Name = zone_name

        bc_info = wall_bcs[i]
        if isinstance(bc_info, dict):
            # If bc_info is a dict => can specify 'bc' and optionally 'adj_surf_name'
            bc_str = bc_info.get("bc", "Adiabatic")
            wall_obj.Outside_Boundary_Condition = bc_str
            if bc_str.lower() == "outdoors":
                wall_obj.Sun_Exposure = "SunExposed"
                wall_obj.Wind_Exposure = "WindExposed"
            else:
                wall_obj.Sun_Exposure = "NoSun"
                wall_obj.Wind_Exposure = "NoWind"

            # If "Surface", optionally set the adjacent surface name
            if bc_str.lower() == "surface":
                adj_name = bc_info.get("adj_surf_name", "")
                wall_obj.Outside_Boundary_Condition_Object = adj_name
        else:
            # bc_info is just a string
            wall_obj.Outside_Boundary_Condition = bc_info
            if bc_info.lower() == "outdoors":
                wall_obj.Sun_Exposure = "SunExposed"
                wall_obj.Wind_Exposure = "WindExposed"
            else:
                wall_obj.Sun_Exposure = "NoSun"
                wall_obj.Wind_Exposure = "NoWind"

        wall_obj.setcoords(wall_coords)
        created_surfaces.append(wall_obj)

    # ===== Ceiling or Roof =====
    if is_top_floor:
        # For top floors, we create a roof surface with "Outdoors"
        top_surf = idf.newidfobject("BUILDINGSURFACE:DETAILED")
        top_surf.Name = f"{zone_name}_Roof"
        top_surf.Surface_Type = "Roof"
        top_surf.Zone_Name = zone_name
        top_surf.Outside_Boundary_Condition = "Outdoors"
        top_surf.Sun_Exposure = "SunExposed"
        top_surf.Wind_Exposure = "WindExposed"
        top_surf.setcoords(top_poly)
        created_surfaces.append(top_surf)
    else:
        # For intermediate floors, we typically do "Ceiling" with "Adiabatic"
        # so it can be changed to "Surface" if we link it to the floor above.
        top_surf = idf.newidfobject("BUILDINGSURFACE:DETAILED")
        top_surf.Name = f"{zone_name}_Ceiling"
        top_surf.Surface_Type = "Ceiling"
        top_surf.Zone_Name = zone_name
        top_surf.Outside_Boundary_Condition = "Adiabatic"
        top_surf.Sun_Exposure = "NoSun"
        top_surf.Wind_Exposure = "NoWind"
        top_surf.setcoords(top_poly)
        created_surfaces.append(top_surf)

    # Return a 4-tuple: (zone_name, base_poly, top_poly, created_surfaces)
    return (zone_name, base_poly, top_poly, created_surfaces)


def create_zones_with_perimeter_depth(
    idf,
    floor_i,
    base_poly,
    wall_height,
    edge_types,
    perimeter_depth,
    floor_type,
    has_core,
    is_top_floor
):
    """
    Create multiple zones (4 perimeter + 1 core) or a single zone if no core.
    Then explicitly cross-link perimeter-to-core surfaces.

    Returns
    -------
    dict : { zone_name => (zname, bpoly, tpoly, list_of_surfaces) }

    Explanation:
      - "floor_type" can be "Ground" for the 1st floor (so floor BC="Ground"), or "Internal" for higher floors (so floor BC="Adiabatic" initially).
      - "edge_types" might be ["facade", "shared", ...], each mapping to "Outdoors" or "Adiabatic".
      - "has_core" => if True, we do perimeter+core. Otherwise, a single zone.

    The final dict has keys = zone_name ("Zone1", "Zone1_Core", etc.),
    each mapping to a tuple of 4 items: (zname, base_poly, top_poly, surfs_list).
    That means index [3] is the list of surfaces, so we can do zone_data[zname][3]
    in building.py.
    """
    def edge_to_bc(e):
        """
        Convert textual edge label to an EnergyPlus BC string:
          - "facade" => "Outdoors"
          - "shared" => "Adiabatic"
          - anything else => "Outdoors"
        """
        e_lower = e.lower().strip()
        if e_lower == "facade":
            return "Outdoors"
        elif e_lower == "shared":
            return "Adiabatic"
        else:
            return "Outdoors"

    zone_data = {}

    # Decide the floor boundary condition
    if floor_type.lower() == "ground":
        floor_bc = "Ground"
    else:
        # For intermediate floors, we temporarily set "Adiabatic"
        # The code in building.py can link surfaces for multi-story conduction.
        floor_bc = "Adiabatic"

    # Try to offset the polygon inward for a core
    A, B, C, D = base_poly
    inner_poly = None
    if has_core:
        inner_poly = inward_offset_polygon(A, B, C, D, perimeter_depth)
        if inner_poly:
            A2, B2, C2, D2 = inner_poly
            # Check if that offset polygon is large enough
            if polygon_area([A2, B2, C2, D2]) < 1e-3:
                inner_poly = None  # not valid => discard

    # ================= Single-Zone Case =================
    if not inner_poly:
        # Means no valid core => only one zone
        wall_bcs = [edge_to_bc(e) for e in edge_types]
        zname, bpoly, tpoly, surfs = create_zone_surfaces(
            idf,
            f"Zone{floor_i}",
            base_poly,
            wall_height,
            floor_bc,
            wall_bcs,
            is_top_floor
        )
        # Store 4 items => so we can do zone_data[zname][3] = surfaces later
        zone_data[zname] = (zname, bpoly, tpoly, surfs)
        return zone_data

    # ================= Perimeter + Core Case =================
    A2, B2, C2, D2 = inner_poly

    # We'll create 4 perimeter zones + 1 core zone

    # 1) Front perimeter
    front_bc = edge_to_bc(edge_types[0])
    front_base = [A, B, B2, A2]
    # We define the perimeter->core edge as the 3rd wall => "Surface"
    front_walls = [front_bc, "Adiabatic", "Surface", "Adiabatic"]
    zf, fbpoly, ftpoly, fsurfs = create_zone_surfaces(
        idf,
        f"Zone{floor_i}_FrontPerimeter",
        front_base,
        wall_height,
        floor_bc,
        front_walls,
        is_top_floor
    )
    zone_data[zf] = (zf, fbpoly, ftpoly, fsurfs)

    # 2) Right perimeter
    right_bc = edge_to_bc(edge_types[1])
    right_base = [B, C, C2, B2]
    right_walls = [right_bc, "Adiabatic", "Surface", "Adiabatic"]
    zr, rbpoly, rtpoly, rsurfs = create_zone_surfaces(
        idf,
        f"Zone{floor_i}_RightPerimeter",
        right_base,
        wall_height,
        floor_bc,
        right_walls,
        is_top_floor
    )
    zone_data[zr] = (zr, rbpoly, rtpoly, rsurfs)

    # 3) Rear perimeter
    rear_bc = edge_to_bc(edge_types[2])
    rear_base = [C, D, D2, C2]
    rear_walls = [rear_bc, "Adiabatic", "Surface", "Adiabatic"]
    zre, rebpoly, retpoly, resurfs = create_zone_surfaces(
        idf,
        f"Zone{floor_i}_RearPerimeter",
        rear_base,
        wall_height,
        floor_bc,
        rear_walls,
        is_top_floor
    )
    zone_data[zre] = (zre, rebpoly, retpoly, resurfs)

    # 4) Left perimeter
    left_bc = edge_to_bc(edge_types[3])
    left_base = [D, A, A2, D2]
    left_walls = [left_bc, "Adiabatic", "Surface", "Adiabatic"]
    zl, lbpoly, ltpoly, lsurfs = create_zone_surfaces(
        idf,
        f"Zone{floor_i}_LeftPerimeter",
        left_base,
        wall_height,
        floor_bc,
        left_walls,
        is_top_floor
    )
    zone_data[zl] = (zl, lbpoly, ltpoly, lsurfs)

    # 5) Core
    #
    # We pass a reversed polygon so each shared edge is reversed wrt the perimeter side:
    core_poly_reversed = [A2, D2, C2, B2]
    # All edges => "Surface" bc
    core_bc = ["Surface", "Surface", "Surface", "Surface"]
    zc, cbpoly, ctpoly, csurfs = create_zone_surfaces(
        idf,
        f"Zone{floor_i}_Core",
        core_poly_reversed,
        wall_height,
        floor_bc,
        core_bc,
        is_top_floor
    )
    zone_data[zc] = (zc, cbpoly, ctpoly, csurfs)

    # ===================== Cross-Linking Perimeter->Core =====================
    #
    # We assume:
    #  - The perimeter zone "Wall_2" (index=2 => array position=3 in the surfaces array) 
    #    is the interior partition to the core.
    #  - The matching core zone side is "Wall_x", using reversed polygon indexing logic.
    #
    # Because we reversed the core polygon, each perimeter edge B2->A2 lines up with A2->B2
    # in the core. We just have to ensure we pick the correct wall indexes.

    def get_wall(surfs, wall_idx):
        """
        For surfs array: 
          index 0 => Floor, 
          index 1..4 => Walls, 
          index 5 => Ceiling/Roof
        So the perimeter interior wall (index=2) => surfs[1+2] => surfs[3].
        """
        return surfs[1 + wall_idx]

    # front perimeter interior => index=2 => surfs[3]
    front_interior = get_wall(fsurfs, 2)
    right_interior = get_wall(rsurfs, 2)
    rear_interior  = get_wall(resurfs, 2)
    left_interior  = get_wall(lsurfs, 2)

    # In the core zone, we have reversed the polygon. We'll map:
    #   - front perimeter => core wall_3
    #   - right perimeter => core wall_2
    #   - rear perimeter  => core wall_1
    #   - left perimeter  => core wall_0
    core_wall_front = get_wall(csurfs, 3)
    core_wall_right = get_wall(csurfs, 2)
    core_wall_rear  = get_wall(csurfs, 1)
    core_wall_left  = get_wall(csurfs, 0)

    link_surfaces(front_interior, core_wall_front)
    link_surfaces(right_interior, core_wall_right)
    link_surfaces(rear_interior, core_wall_rear)
    link_surfaces(left_interior, core_wall_left)

    return zone_data
