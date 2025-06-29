# ventilation/mappings.py
from typing import Optional, Dict, Any, Set

# Define type alias for building_row for clarity
BuildingRow = Dict[str, Any]

def safe_lower(val: Optional[Any]) -> str:
    """Helper to safely lowercase a string, returning empty string for non-strings."""
    if isinstance(val, str):
        return val.lower()
    return ""

def map_age_range_to_year_key(age_range_str: Optional[str]) -> str:
    """
    Converts a building_row's age_range string into one of the 7 standard keys
    used in ventilation_lookup (e.g., "< 1945", "1945 - 1964", etc.).

    Args:
        age_range_str: The age range string from the building data.

    Returns:
        The corresponding standard key, or "2015 and later" as a fallback.
    """
    # Explicitly define the valid keys expected by the lookup table
    valid_keys: Dict[str, str] = {
        "< 1945": "< 1945",
        "1945 - 1964": "1945 - 1964",
        "1965 - 1974": "1965 - 1974",
        "1975 - 1991": "1975 - 1991",
        "1992 - 2005": "1992 - 2005",
        "2006 - 2014": "2006 - 2014",
        "2015 and later": "2015 and later"
    }
    # Use .get() for safe lookup with a default fallback
    return valid_keys.get(str(age_range_str), "2015 and later")

def map_infiltration_key(building_row: BuildingRow) -> str:
    """
    Determines the appropriate key for looking up infiltration ranges based on
    the building's function and specific type.

    - Residential buildings use their 'residential_type' field.
    - Non-residential buildings use their 'non_residential_type' field.
    - Fallbacks ('other_res', 'other_nonres') are used if the specific type
      is not recognized or missing.

    Args:
        building_row: The dictionary containing building data.

    Returns:
        A string key matching those used in the ventilation_lookup dictionary's
        infiltration range sections.
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))

    if bldg_func == "residential":
        res_type = building_row.get("residential_type")
        # Explicit set of known residential type keys used in the lookup
        valid_res_types: Set[str] = {
            "Corner House",
            "Apartment",
            "Terrace or Semi-detached House",
            "Detached House",
            "Two-and-a-half-story House"
            # Add any other specific keys expected in ventilation_lookup here
        }
        if res_type in valid_res_types:
            return res_type
        else:
            # print(f"[DEBUG] Unknown residential_type '{res_type}', using fallback 'other_res'.")
            return "other_res" # Fallback key
    else: # Non-residential
        nonres_type = building_row.get("non_residential_type")
        # Explicit set of known non-residential type keys used in the lookup
        valid_nonres_types: Set[str] = {
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
             # Add any other specific keys expected in ventilation_lookup here
        }
        if nonres_type in valid_nonres_types:
            return nonres_type
        else:
            # print(f"[DEBUG] Unknown non_residential_type '{nonres_type}', using fallback 'other_nonres'.")
            return "other_nonres" # Fallback key

def map_usage_key(building_row: BuildingRow) -> Optional[str]:
    """
    Determines the appropriate key for looking up non-residential ventilation flow rates.

    Returns None for residential buildings.
    For non-residential, maps the 'non_residential_type' to a simplified usage key
    recognized by `calc_required_ventilation_flow`.

    Args:
        building_row: The dictionary containing building data.

    Returns:
        A string usage key (e.g., "office_area_based", "retail") for non-residential,
        or None for residential.
    """
    bldg_func = safe_lower(building_row.get("building_function", "residential"))

    if bldg_func == "residential":
        return None
    else:
        nonres_type = building_row.get("non_residential_type", "Other Use Function")
        # Define the mapping from detailed non-res types to the simplified keys
        # used in calc_required_ventilation_flow's 'usage_flow_map'.
        # This mapping should be consistent with the keys in that function.
        usage_map: Dict[str, str] = {
            "Meeting Function": "office_area_based",
            "Healthcare Function": "healthcare_function", # Example: Add if specific rate exists
            "Sport Function": "sport_function",         # Example: Add if specific rate exists
            "Cell Function": "office_area_based",       # Example mapping
            "Retail Function": "retail",
            "Industrial Function": "industrial_function", # Example: Add if specific rate exists
            "Accommodation Function": "accommodation_function", # Example: Add if specific rate exists
            "Office Function": "office_area_based",
            "Education Function": "education_function",     # Example: Add if specific rate exists
            "Other Use Function": "retail"                # Fallback usage type
        }
        # Use .get() for safe lookup with a default fallback usage type
        fallback_usage = "retail" # Or "office_area_based" might be safer default
        return usage_map.get(nonres_type, fallback_usage)