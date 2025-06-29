# epw/assign_epw_file.py

import math
from .epw_lookup import epw_lookup

def find_epw_overrides(building_id, desired_year, user_config_epw):
    matches = []
    for row in user_config_epw:
        if "building_id" in row:
            if row["building_id"] != building_id:
                continue
        if "desired_year" in row:
            if row["desired_year"] != desired_year:
                continue
        matches.append(row)
    return matches

def assign_epw_for_building_with_overrides(building_row, user_config_epw=None, assigned_epw_log=None):
    """
    Attempt to pick an EPW by:
      1) checking user_config_epw for a forced or override logic
      2) else calling the original logic from assign_epw_for_building
    """

    building_id = building_row.get("ogc_fid", 0)
    bldg_lat = building_row.get("lat", 0.0)
    bldg_lon = building_row.get("lon", 0.0)
    desired_year = building_row.get("desired_climate_year", 2020)

    # 1) if user config => find matches
    if user_config_epw:
        matches = find_epw_overrides(building_id, desired_year, user_config_epw)
    else:
        matches = []

    # possibly define local overrides
    forced_epw = None
    override_year = None
    override_lat = bldg_lat
    override_lon = bldg_lon

    for row in matches:
        # if row has "fixed_epw_path"
        if "fixed_epw_path" in row:
            forced_epw = row["fixed_epw_path"]
        # if row wants to override year
        if "override_year_to" in row:
            override_year = row["override_year_to"]
        # if row has lat_lon_override
        if "epw_lat" in row and "epw_lon" in row:
            override_lat = row["epw_lat"]
            override_lon = row["epw_lon"]

    # if we have override_year => use that instead of desired_year
    if override_year is not None:
        desired_year = override_year

    # If forced_epw => we skip the normal logic
    chosen_epw = None
    if forced_epw:
        chosen_epw = forced_epw
    else:
        # else call your original logic with (override_lat, override_lon, desired_year)
        chosen_epw = pick_epw_from_lookup(
            lat=override_lat,
            lon=override_lon,
            desired_year=desired_year
        )

    # log if needed
    if assigned_epw_log is not None:
        assigned_epw_log[building_id] = chosen_epw

    return chosen_epw

def pick_epw_from_lookup(lat, lon, desired_year):
    """
    The original logic from assign_epw_for_building
    that picks among epw_lookup. Returns file_path or None.
    """
    # 1) minimal absolute year difference
    diff_years = [abs(e["year"] - desired_year) for e in epw_lookup]
    if not diff_years:
        return None
    min_diff = min(diff_years)

    possible_epws = [e for e in epw_lookup if abs(e["year"] - desired_year) == min_diff]
    best_epw = None
    best_dist = float("inf")
    for e in possible_epws:
        dlat = e["lat"] - lat
        dlon = e["lon"] - lon
        dist_km = math.sqrt(dlat**2 + dlon**2) * 111
        if dist_km < best_dist:
            best_epw = e
            best_dist = dist_km

    return best_epw["file_path"] if best_epw else None
