# geomz/building.py

from .assign_geometry_values import assign_geometry_values
from .geometry import compute_dimensions_from_area_perimeter, create_building_base_polygon
from .zoning import create_zones_with_perimeter_depth, link_surfaces
import math
import pandas as pd

def create_building_with_roof_type(
    idf,
    area,
    perimeter,
    orientation,
    building_row,
    edge_types,
    wall_height=None,
    roof_slope_axis='length',
    ridge_position=0.5,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config=None,
    assigned_geom_log=None,
    excel_rules=None
):
    """
    Create building geometry in the IDF, multi-floor, optionally perimeter+core.
    Now includes logic to link each new floor's Floor to the old floor's Ceiling.
    """

     # --------------------------------------------------------------------
    # 1) Safely read gem_hoogte (float) and num_floors (int), with defaults
    # --------------------------------------------------------------------
    raw_hoogte = building_row.get("gem_hoogte", 3)  # default 3
    if pd.isna(raw_hoogte) or raw_hoogte is None:
        gem_hoogte = 3.0
    else:
        try:
            gem_hoogte = float(raw_hoogte)
        except ValueError:
            # In case it's a weird string
            gem_hoogte = 3.0

    # Safely get num_floors as an int
    raw_floors = building_row.get("gem_bouwlagen", 1)  # default 1
    if pd.isna(raw_floors) or raw_floors is None:
        num_floors = 1
    else:
        try:
            # Round or floor/ceil as needed
            num_floors = int(round(float(raw_floors)))
        except ValueError:
            # In case it's a weird string
            num_floors = 1

    # Guard against zero or negative floors
    if num_floors < 1:
        num_floors = 1






    # ------------------------------------------------
    # Approach A: Reconcile total height & floors
    # ------------------------------------------------
    bldg_func = building_row.get("building_function", "").lower()

    # Decide typical min/max floor heights per function
    if "residential" in bldg_func:
        typical_floor_height_min = 2.5
        typical_floor_height_max = 4.0
    else:
        # e.g. non-res might allow taller floors
        typical_floor_height_min = 3.0
        typical_floor_height_max = 6.0

    # implied floor height
    implied_floor_height = gem_hoogte / num_floors

    # If each floor is taller than max => increase floors
    if implied_floor_height > typical_floor_height_max:
        new_floors = int(round(gem_hoogte / typical_floor_height_max))
        if new_floors < 1:
            new_floors = 1
        num_floors = new_floors

    # Recompute after possible update above
    implied_floor_height = gem_hoogte / num_floors

    # If each floor is shorter than min => reduce floors (only if floors>1)
    if implied_floor_height < typical_floor_height_min and num_floors > 1:
        new_floors = int(round(gem_hoogte / typical_floor_height_min))
        if new_floors < 1:
            new_floors = 1
        num_floors = new_floors
















    if wall_height is None:
        if gem_hoogte is not None:
            total_height = gem_hoogte
        else:
            total_height = 3.0 * num_floors
        wall_height = total_height / num_floors

    # 2) Determine geometry parameters (perimeter_depth, has_core) from dictionary + overrides
    geom_params = assign_geometry_values(
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config,
        assigned_geom_log=assigned_geom_log,
        excel_rules=excel_rules
    )
    perimeter_depth = geom_params["perimeter_depth"]
    has_core = geom_params["has_core"]

    # 3) Rectangle dimensions from area & perimeter
    width, length = compute_dimensions_from_area_perimeter(area, perimeter)

    # 4) Create base polygon for ground floor
    A0, B0, C0, D0 = create_building_base_polygon(width, length, orientation)
    base_poly_0 = [A0, B0, C0, D0]

    # 5) Create each floor in a loop
    floors_zones = {}
    current_base_poly = base_poly_0

    prev_floor_zones = None  # Will store the zone surfaces from the previous floor
    for floor_i in range(1, num_floors + 1):
        # "Ground" for 1st floor, else "Internal"
        floor_type = "Ground" if floor_i == 1 else "Internal"
        is_top_floor = (floor_i == num_floors)

        # Create zones for this floor (could be single or perimeter+core)
        zones_data = create_zones_with_perimeter_depth(
            idf=idf,
            floor_i=floor_i,
            base_poly=current_base_poly,
            wall_height=wall_height,
            edge_types=edge_types,
            perimeter_depth=perimeter_depth,
            floor_type=floor_type,
            has_core=has_core,
            is_top_floor=is_top_floor
        )
        floors_zones[floor_i] = zones_data

        # -------------------------------------------------------
        #  LINK THIS FLOOR’S "FLOOR" SURFACES TO PREV FLOOR’S "CEILING" SURFACES
        # -------------------------------------------------------
        if floor_i > 1 and prev_floor_zones:
            # We'll do a basic approach: match zone names in sorted order
            old_zone_names = sorted(prev_floor_zones.keys())
            new_zone_names = sorted(zones_data.keys())

            for oz, nz in zip(old_zone_names, new_zone_names):
                old_zone_surfs = prev_floor_zones[oz][3]  # (bpoly, tpoly, surf_list) => index 3
                new_zone_surfs = zones_data[nz][3]

                # find the "Ceiling" in old zone
                old_ceiling = None
                for srf in old_zone_surfs:
                    if srf.Name.endswith("_Ceiling") or srf.Name.endswith("_Roof"):
                        # If the old floor was not top floor, we expect a "Ceiling"
                        # If the old floor was top floor (?), it might be a "Roof" -- but typically that wouldn't stack
                        old_ceiling = srf
                        break

                # find the "Floor" in new zone
                new_floor = new_zone_surfs[0]  # typically index=0 is the Floor object from create_zone_surfaces

                # If found both, link them (interzone conduction)
                if old_ceiling and new_floor:
                    link_surfaces(new_floor, old_ceiling)

        prev_floor_zones = zones_data

        # shift the base polygon upward by wall_height for the next floor
        current_base_poly = [(p[0], p[1], p[2] + wall_height) for p in current_base_poly]

    # (Optional) if you want to add pitched roof logic, do it after the top floor is created
    return floors_zones
