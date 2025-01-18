# geomz/geometry_overrides_helper.py

def find_geom_overrides(building_id, building_type, user_config):
    """
    Returns a list of geometry override rows that match the given building_id and/or building_type.
    Each row can have:
      - building_id (exact match)
      - building_type (exact match)
      - param_name in ["perimeter_depth", "has_core"]
      - for numeric: (min_val, max_val)
      - for boolean: (fixed_value)
    """
    matches = []
    for row in user_config:
        if "building_id" in row:
            if row["building_id"] != building_id:
                continue
        if "building_type" in row:
            if row["building_type"] != building_type:
                continue
        matches.append(row)
    return matches
