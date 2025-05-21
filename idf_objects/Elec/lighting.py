# File: D:\Documents\E_Plus_2030_py\idf_objects\Elec\lighting.py

from .assign_lighting_values import assign_lighting_parameters
from .schedules import create_lighting_schedule, create_parasitic_schedule

def get_building_category_and_subtype(building_row):
    """
    Return (building_category, sub_type) based on ``building_row``.
    It now correctly uses 'residential_type' or 'non_residential_type'
    based on the value of 'building_function'.
    """
    
    # Get values from the building_row, defaulting to empty strings if keys are missing
    building_function_val = building_row.get("building_function", "").strip().lower() # Normalize to lowercase for easier comparison
    residential_type_val = building_row.get("residential_type", "").strip()
    non_residential_type_val = building_row.get("non_residential_type", "").strip()

    print(f"\n--- [DEBUG get_category_subtype] ---")
    print(f"[DEBUG get_category_subtype] Input building_row.get('building_function'): '{building_row.get('building_function')}' -> processed as '{building_function_val}'")
    print(f"[DEBUG get_category_subtype] Input building_row.get('residential_type'): '{residential_type_val}'")
    print(f"[DEBUG get_category_subtype] Input building_row.get('non_residential_type'): '{non_residential_type_val}'")

    building_category = None
    sub_type_for_lookup = None

    if building_function_val == "residential":
        if residential_type_val: # Check if there is a specific residential type
            building_category = "Residential"
            sub_type_for_lookup = residential_type_val
            print(f"[DEBUG get_category_subtype] 'building_function' is 'residential'. Using 'residential_type': '{sub_type_for_lookup}' as sub_type.")
        else:
            # building_function is "residential" but residential_type is empty. This is an issue.
            print(f"[DEBUG get_category_subtype] WARNING: 'building_function' is 'residential' but 'residential_type' is empty.")
            building_category = "Residential" # Still assume residential
            sub_type_for_lookup = "Apartment"   # Fallback to a default specific residential type or "Other Use Function" if more appropriate
            print(f"[DEBUG get_category_subtype] Defaulting to category='{building_category}', sub_type='{sub_type_for_lookup}' due to empty residential_type.")
            
    elif building_function_val == "non_residential":
        if non_residential_type_val: # Check if there is a specific non-residential type
            building_category = "Non-Residential"
            sub_type_for_lookup = non_residential_type_val
            print(f"[DEBUG get_category_subtype] 'building_function' is 'non_residential'. Using 'non_residential_type': '{sub_type_for_lookup}' as sub_type.")
        else:
            # building_function is "non_residential" but non_residential_type is empty.
            print(f"[DEBUG get_category_subtype] WARNING: 'building_function' is 'non_residential' but 'non_residential_type' is empty.")
            building_category = "Non-Residential" # Still assume non-residential
            sub_type_for_lookup = "Other Use Function" # Fallback to a default specific non-residential type
            print(f"[DEBUG get_category_subtype] Defaulting to category='{building_category}', sub_type='{sub_type_for_lookup}' due to empty non_residential_type.")
            
    else: # building_function is not "residential" or "non_residential", or it's empty.
          # This case handles if building_function itself contains the specific sub-type.
        direct_bldg_func_val = building_row.get("building_function", "").strip() # Use original casing if not "residential"/"non_residential"
        print(f"[DEBUG get_category_subtype] 'building_function' ('{direct_bldg_func_val}') is not 'residential' or 'non_residential'. Attempting direct categorization of this value.")
        
        if not direct_bldg_func_val: # If building_function was empty to begin with
            print(f"[DEBUG get_category_subtype] 'building_function' is empty. Defaulting to Non-Residential, Other Use Function.")
            building_category = "Non-Residential"
            sub_type_for_lookup = "Other Use Function"
        else:
            sub_type_for_lookup = direct_bldg_func_val # The value from building_function IS the specific sub-type
            # Define known types here for this fallback path
            known_residential_sub_types = {
                "Apartment", "Corner House", "Detached House",
                "Terrace or Semi-detached House", "Two-and-a-half-story House",
            }
            known_non_residential_sub_types = {
                "Accommodation Function", "Cell Function", "Education Function",
                "Healthcare Function", "Industrial Function", "Meeting Function",
                "Office Function", "Other Use Function", "Retail Function", "Sport Function",
            }

            if sub_type_for_lookup in known_residential_sub_types:
                building_category = "Residential"
                print(f"[DEBUG get_category_subtype] Matched direct building_function '{sub_type_for_lookup}' to known_residential_sub_types.")
            elif sub_type_for_lookup in known_non_residential_sub_types:
                building_category = "Non-Residential"
                print(f"[DEBUG get_category_subtype] Matched direct building_function '{sub_type_for_lookup}' to known_non_residential_sub_types.")
            else:
                print(f"[DEBUG get_category_subtype] WARNING: Unknown direct building_function '{sub_type_for_lookup}'. Defaulting category to Non-Residential.")
                building_category = "Non-Residential" # Default for truly unknown specific types

    # Final safety net if logic above somehow fails to set category or sub_type
    if not building_category or not sub_type_for_lookup:
        print(f"[DEBUG get_category_subtype] CRITICAL FALLBACK: Could not determine valid category or sub_type from inputs. Defaulting to Non-Residential, Other Use Function.")
        building_category = "Non-Residential"
        sub_type_for_lookup = "Other Use Function"

    print(f"[DEBUG get_category_subtype] Final Determined: building_category='{building_category}', sub_type_for_lookup='{sub_type_for_lookup}'")
    print(f"--- [END DEBUG get_category_subtype] ---")
    return (building_category, sub_type_for_lookup)


def add_lights_and_parasitics(
    idf,
    building_row,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config=None,
    assigned_values_log=None,
    zonelist_name="ALL_ZONES"
):
    """
    1) Determine building_category (Residential/Non-Residential) and sub_type.
    2) Retrieve assigned lighting parameters (including fraction fields).
    3) Create schedules in IDF:
       - A lighting schedule for the LIGHTS object
       - An always-on parasitic schedule for ELECTRICEQUIPMENT
    4) Add LIGHTS and ELECTRICEQUIPMENT objects referencing a ZoneList in the IDF.

    The assigned parameters and final picks are stored in assigned_values_log[ogc_fid]
    if assigned_values_log is provided.
    """

    # 1) Get building_category / sub_type
    building_category, sub_type = get_building_category_and_subtype(building_row) 
    
    # 2) Retrieve lighting parameters
    bldg_id = int(building_row.get("ogc_fid", 0)) # Ensure bldg_id is fetched
    print(f"\n--- [DEBUG add_lights_and_parasitics for bldg_id {bldg_id}] ---") # Moved print to after bldg_id is known
    print(f"[DEBUG add_lights_and_parasitics] From get_building_category_and_subtype: category='{building_category}', sub_type='{sub_type}'")


    assigned_dict = assign_lighting_parameters( 
        building_id=bldg_id,
        building_category=building_category,
        sub_type=sub_type,
        age_range=building_row.get("age_range", None), # Pass age_range if available and used by overrides
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config,
        assigned_log=assigned_values_log 
    )

    # Extract main power densities
    lights_wm2 = assigned_dict["lights_wm2"]["assigned_value"]
    parasitic_wm2 = assigned_dict["parasitic_wm2"]["assigned_value"]

    # Extract fraction parameters for LIGHTS
    lights_frac_radiant = assigned_dict["lights_fraction_radiant"]["assigned_value"]
    lights_frac_visible = assigned_dict["lights_fraction_visible"]["assigned_value"]
    lights_frac_replace = assigned_dict["lights_fraction_replaceable"]["assigned_value"]

    # Extract fraction parameters for EQUIPMENT
    equip_frac_radiant = assigned_dict["equip_fraction_radiant"]["assigned_value"]
    equip_frac_lost = assigned_dict["equip_fraction_lost"]["assigned_value"]

    # 3) Create schedules
    lights_sched_name = create_lighting_schedule(
        idf,
        building_category=building_category,
        sub_type=sub_type,
        schedule_name="LightsSchedule"
    )
    paras_sched_name = create_parasitic_schedule(idf, sched_name="ParasiticSchedule")

    # 4) Add a single LIGHTS object for the entire ZoneList
    lights_obj = idf.newidfobject("LIGHTS")
    lights_obj.Name = f"Lights_{zonelist_name}"
    lights_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zonelist_name
    lights_obj.Schedule_Name = lights_sched_name
    lights_obj.Design_Level_Calculation_Method = "Watts/Area"
    lights_obj.Watts_per_Zone_Floor_Area = lights_wm2

    # Apply fraction fields
    lights_obj.Fraction_Radiant = lights_frac_radiant
    lights_obj.Fraction_Visible = lights_frac_visible
    lights_obj.Fraction_Replaceable = lights_frac_replace

    # Add ELECTRICEQUIPMENT object for parasitic loads
    eq_obj = idf.newidfobject("ELECTRICEQUIPMENT")
    eq_obj.Name = f"Parasitic_{zonelist_name}"
    eq_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zonelist_name
    eq_obj.Schedule_Name = paras_sched_name
    eq_obj.Design_Level_Calculation_Method = "Watts/Area"
    eq_obj.Watts_per_Zone_Floor_Area = parasitic_wm2

    # Apply fraction fields
    eq_obj.Fraction_Radiant = equip_frac_radiant
    eq_obj.Fraction_Lost = equip_frac_lost
    
    print(f"[DEBUG add_lights_and_parasitics] Successfully created LIGHTS and ELECTRICEQUIPMENT objects for bldg_id {bldg_id}.")
    print(f"--- [END DEBUG add_lights_and_parasitics for bldg_id {bldg_id}] ---")
    return lights_obj, eq_obj