# DHW/building_type_map.py

def map_building_function_to_dhw_key(building_row):
    """
    Decide which DHW key from dhw_lookup to use, based on:

      - building_function: 'Residential' or 'Non-Residential'
      - For Residential, we use 'area' to assign one of:
          "Corner House"
          "Terrace or Semi-detached House"
          "Detached House"
          "Two-and-a-half-story House"
          "Apartment"
        (Feel free to adjust thresholds or logic as needed.)
      
      - For Non-Residential, we read the non_residential_type and map directly to:
          "Meeting Function"
          "Healthcare Function"
          "Sport Function"
          "Cell Function"
          "Retail Function"
          "Industrial Function"
          "Accommodation Function"
          "Office Function"
          "Education Function"
          "Other Use Function" (fallback)

    Returns the exact string that corresponds to the keys in your dhw_lookup.
    """

    bldg_func = (building_row.get("building_function") or "Residential").lower()
    bldg_area = building_row.get("area", 80)  # fallback if area not provided
    
    # ---------------------
    # RESIDENTIAL LOGIC
    # ---------------------
    if bldg_func == "residential":
        # Example area-based classification
        if bldg_area < 60:
            return "Corner House"
        elif bldg_area < 100:
            return "Terrace or Semi-detached House"
        elif bldg_area < 150:
            return "Detached House"
        elif bldg_area < 250:
            return "Two-and-a-half-story House"
        else:
            return "Apartment"

    # ---------------------
    # NON-RESIDENTIAL LOGIC
    # ---------------------
    else:
        nrtype = building_row.get("non_residential_type", "")
        # Map directly, or fallback to "Other Use Function"
        valid_nonres = {
            "Meeting Function":       "Meeting Function",
            "Healthcare Function":    "Healthcare Function",
            "Sport Function":         "Sport Function",
            "Cell Function":          "Cell Function",
            "Retail Function":        "Retail Function",
            "Industrial Function":    "Industrial Function",
            "Accommodation Function": "Accommodation Function",
            "Office Function":        "Office Function",
            "Education Function":     "Education Function",
            "Other Use Function":     "Other Use Function"
        }
        return valid_nonres.get(nrtype, "Other Use Function")
