# Elec/overrides_helper.py

"""
Helper functions to filter user_config rows that match a given building's
characteristics (id, type, age_range, scenario, etc.).
"""

def find_applicable_overrides(building_id, building_type, age_range, user_config):
    """
    Given a building's unique ID, type, and age_range, plus a user_config list (or table)
    of override definitions, returns the subset of rows that apply to this building.

    Each row in user_config might look like:
      {
        "building_id": 4136730,
        "building_type": "Meeting Function",
        "age_range": "1992 - 2005",
        "param_name": "lights_wm2",
        "fixed_value": 12.0,
        "min_val": None,
        "max_val": None
      }

    or any variation. If a field is missing or doesn't match, we skip it.
    For example:
      - If row["building_id"] is present but doesn't match the building_id, skip.
      - If row["building_type"] is present but doesn't match the building_type, skip.
      - If row["age_range"] is present but doesn't match the building's age_range, skip.

    Returns a list of all rows that pass these checks.
    """

    if not user_config:
        return []

    matches = []
    for row in user_config:
        # building_id check (if specified in row)
        if "building_id" in row and row["building_id"] is not None:
            if row["building_id"] != building_id:
                continue  # skip if mismatch

        # building_type check (if specified in row)
        if "building_type" in row and row["building_type"]:
            if row["building_type"].lower() != building_type.lower():
                continue  # skip if mismatch

        # age_range check (if specified in row)
        if "age_range" in row and row["age_range"]:
            if age_range and row["age_range"] != age_range:
                continue  # skip if mismatch
            elif age_range is None and row["age_range"]:
                # If building has no age_range but row requires one, skip
                continue

        # scenario check, if you want to handle scenario-based overrides:
        # if "scenario" in row and row["scenario"]:
        #     # Suppose building has building_row["scenario"] => compare
        #     # Or if you pass scenario as a parameter to find_applicable_overrides
        #     # you can do a similar logic here.
        #     pass

        # If we got here, it means the row matches all relevant criteria
        matches.append(row)

    return matches
