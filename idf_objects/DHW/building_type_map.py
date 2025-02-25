# DHW/building_type_map.py

def map_building_function_to_dhw_key(building_row):
    """
    Decide which DHW key from dhw_lookup to use, based on:
      - building_function: 'Residential' or 'Non-Residential'
      - For Residential, read the 'residential_type' field
        directly. Return one of:
          "Corner House"
          "Apartment"
          "Terrace or Semi-detached House"
          "Detached House"
          "Two-and-a-half-story House"
        If it doesn't match exactly, fallback to e.g. "Apartment".
      
      - For Non-Residential, read the 'non_residential_type'
        field and map directly to:
          "Meeting Function", "Healthcare Function", ...
          "Other Use Function" (fallback)
    """

    bldg_func = (building_row.get("building_function") or "").strip().lower()

    # ---------------------
    # RESIDENTIAL
    # ---------------------
    if bldg_func == "residential":
        # Grab the explicit "residential_type" from the data
        res_type = (building_row.get("residential_type") or "").strip()

        # Our known valid residential types:
        valid_res_types = {
            "Corner House",
            "Apartment",
            "Terrace or Semi-detached House",
            "Detached House",
            "Two-and-a-half-story House"
        }

        # If the row's residential_type is valid, use it;
        # otherwise fallback to "Apartment" (or your choice).
        if res_type in valid_res_types:
            return res_type
        else:
            return "Apartment"

    # ---------------------
    # NON-RESIDENTIAL
    # ---------------------
    else:
        nrtype = (building_row.get("non_residential_type") or "").strip()
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
