# eequip/overrides_helper.py

def find_applicable_overrides(building_id, building_type, age_range, user_config):
    """
    This function filters the user_config (list of override rows)
    to find all rows that match the specified building_id, building_type, 
    and age_range (if provided).

    Each 'row' in user_config is expected to be a dict with fields like:
      {
         "building_id": <int or None>,
         "building_type": <str or None>,
         "age_range": <str or None>,
         "param_name": "equip_wm2",
         "min_val": 8.0,
         "max_val": 12.0
      }

    Returns a list of matching rows.
    """

    matches = []
    for row in user_config:
        # building_id check: only if row has building_id
        if "building_id" in row and row["building_id"] is not None:
            if row["building_id"] != building_id:
                continue

        # building_type check
        if "building_type" in row and row["building_type"] is not None:
            if row["building_type"] != building_type:
                continue

        # age_range check
        if "age_range" in row and row["age_range"] is not None:
            if row["age_range"] != age_range:
                continue

        matches.append(row)

    return matches
