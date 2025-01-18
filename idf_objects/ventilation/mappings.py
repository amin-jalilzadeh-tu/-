# ventilation/mappings.py

def safe_lower(val):
    """Helper to safely lowercase a string."""
    if isinstance(val, str):
        return val.lower()
    return ""

def map_age_range_to_year_key(age_range_str):
    """
    Convert your main DataFrame's age_range
    into the short keys used in your infiltration/vent lookup or NTA data.

    Now expanded to include:
      - "1900-2000" => "1900-2000"
      - "2000-2024" => "2000-2024"
      - plus older ones like "<1970", "1970-1992", etc.
    """
    # You can expand as needed.
    mapping = {
        "pre-1970": "<1970",
        "1970 - 1992": "1970-1992",
        "1992 - 2005": "1992-2005",
        "2005 - 2015": "2005-2015",
        "2015 and later": ">2015",
        "1900-2000": "1900-2000",
        "2000-2024": "2000-2024"
    }
    return mapping.get(age_range_str, ">2015")  # fallback => >2015

def map_infiltration_key(building_row):
    """
    Decide infiltration key from building function + sub-type fields.
    Updated to handle e.g. 'two_and_a_half_story_house' for certain residential types,
    or 'meeting_function' for certain non-res types, etc.

    If not recognized, fall back to a perimeter-based logic or default.
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func == "residential":
        # 1) check if we have a recognized 'residential_type'
        res_type = safe_lower(building_row.get("residential_type", ""))
        if "two-and-a-half-story" in res_type:
            return "two_and_a_half_story_house"
        # Could add more if/elif logic for other residential_type strings:
        # elif "row house" in res_type:
        #     return "row_house"
        #
        # else fallback to perimeter-based approach as in original
        perimeter = building_row.get("perimeter", 40)
        if perimeter > 60:
            return "A_detached"
        else:
            return "A_corner"

    else:
        # Non-res => check 'non_residential_type'
        nonres_type = safe_lower(building_row.get("non_residential_type", ""))
        if "meeting function" in nonres_type:
            return "meeting_function"
        # else fallback
        return "office_multi_top"

def map_usage_key(building_row):
    """
    For non-res ventilation usage flow reference. 
    If building is residential => usage_key => None.
    If it's e.g. 'meeting function' => 'office_area_based' (example).
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func == "residential":
        return None
    else:
        nonres_type = safe_lower(building_row.get("non_residential_type", ""))
        if "meeting function" in nonres_type:
            return "office_area_based"
        else:
            return "retail"

def map_ventilation_system(building_row):
    """
    Decide system type (A, B, C, or D) from building row.
    As an example: default 'C' for residential, 'D' for non-res.
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func == "residential":
        return "C"  # default mechanical exhaust for res
    else:
        return "D"  # default balanced w/ HRV for non-res
