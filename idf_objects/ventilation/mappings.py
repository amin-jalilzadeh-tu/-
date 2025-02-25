# ventilation/mappings.py

def safe_lower(val):
    """Helper to safely lowercase a string."""
    if isinstance(val, str):
        return val.lower()
    return ""

def map_age_range_to_year_key(age_range_str):
    """
    Converts a building_row's age_range into one of the 7 keys used in 
    ventilation_lookup (e.g. "< 1945", "1945 - 1964", etc.).

    If the input doesn't match exactly, we fallback to "2015 and later".
    """
    valid_keys = {
        "< 1945": "< 1945",
        "1945 - 1964": "1945 - 1964",
        "1965 - 1974": "1965 - 1974",
        "1975 - 1991": "1975 - 1991",
        "1992 - 2005": "1992 - 2005",
        "2006 - 2014": "2006 - 2014",
        "2015 and later": "2015 and later"
    }
    return valid_keys.get(age_range_str, "2015 and later")

def map_infiltration_key(building_row):
    """
    Returns a string key that matches the infiltration range in your
    ventilation_lookup. We no longer rely on any perimeter logic.

    - If building_function == "residential", we use the "residential_type" field
      (e.g. "Corner House", "Apartment", etc.). If not found, fallback "other_res".

    - If building_function == "non_residential", we use the "non_residential_type"
      (e.g. "Office Function", "Meeting Function", etc.). If not found, fallback "other_nonres".
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func == "residential":
        # Exact sub-type, e.g. "Corner House"
        res_type = building_row.get("residential_type", "other_res")
        # Match exactly what's in the lookup keys:
        valid_res_types = {
            "Corner House", 
            "Apartment", 
            "Terrace or Semi-detached House", 
            "Detached House", 
            "Two-and-a-half-story House"
        }
        if res_type not in valid_res_types:
            return "other_res"
        return res_type
    else:
        # Non-res
        nonres_type = building_row.get("non_residential_type", "other_nonres")
        valid_nonres_types = {
            "Meeting Function",
            "Healthcare Function",
            "Sport Function",
            "Cell Function",
            "Retail Function",
            "Industrial Function",
            "Accommodation Function",
            "Office Function",
            "Education Function",
            "Other Use Function"
        }
        if nonres_type not in valid_nonres_types:
            return "other_nonres"
        return nonres_type

def map_usage_key(building_row):
    """
    For calculating required ventilation flows in non-res buildings.
    If the building is residential => return None.
    Otherwise, return a usage_key that is recognized by calc_required_ventilation_flow.

    Here, you can customize how each non_residential_type maps to a usage flow.
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func == "residential":
        return None
    else:
        # Example usage mapping:
        usage_map = {
            "Meeting Function": "office_area_based",
            "Healthcare Function": "office_area_based",
            "Sport Function": "office_area_based",
            "Cell Function": "office_area_based",
            "Retail Function": "retail",
            "Industrial Function": "retail",
            "Accommodation Function": "office_area_based",
            "Office Function": "office_area_based",
            "Education Function": "office_area_based",
            "Other Use Function": "retail"
        }
        nonres_type = building_row.get("non_residential_type", "Other Use Function")
        return usage_map.get(nonres_type, "retail")

# We no longer need a 'map_ventilation_system' function, because system A/B/C/D
# is now determined by the system_type_map in ventilation_lookup. 
# That logic is handled in assign_ventilation_params_with_overrides (or a helper).
