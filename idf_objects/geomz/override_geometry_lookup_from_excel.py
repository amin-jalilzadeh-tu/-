# geomz/override_geometry_lookup_from_excel.py
#####################

def override_geometry_lookup_from_excel(geometry_lookup, excel_rules):
    """
    Read each row in excel_rules (list of dicts) and update geometry_lookup in-place.

    For example, if excel_rules has keys like:
      {
        "building_function": "residential",
        "building_type": "Two-and-a-half-story House",
        "calibration_stage": "pre_calibration",  # optional
        "perimeter_depth_min": 2.0,
        "perimeter_depth_max": 3.0,
        "has_core_value": True/False/None
        ...
      }
    we insert or update geometry_lookup[function][type][stage] accordingly.
    """

    for rule in excel_rules:
        bldg_func = rule["building_function"]  # "residential" or "non_residential"
        bldg_type = rule["building_type"]
        # if "calibration_stage" doesn't exist, assume "pre_calibration" or something
        cal_stage = rule.get("calibration_stage", "pre_calibration")

        # Ensure the keys exist
        if bldg_func not in geometry_lookup:
            geometry_lookup[bldg_func] = {}
        if bldg_type not in geometry_lookup[bldg_func]:
            geometry_lookup[bldg_func][bldg_type] = {}
        if cal_stage not in geometry_lookup[bldg_func][bldg_type]:
            # Initialize empty dictionary for that stage
            geometry_lookup[bldg_func][bldg_type][cal_stage] = {}

        # Update perimeter_depth_range
        pmin = rule["perimeter_depth_min"]
        pmax = rule["perimeter_depth_max"]
        geometry_lookup[bldg_func][bldg_type][cal_stage]["perimeter_depth_range"] = (pmin, pmax)

        # If has_core_value is not None, override 'has_core'
        if rule.get("has_core_value") is not None:
            geometry_lookup[bldg_func][bldg_type][cal_stage]["has_core"] = rule["has_core_value"]

    # No return, because we modify geometry_lookup in-place
