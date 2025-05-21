# File: D:\Documents\E_Plus_2030_py\idf_objects\Elec\lighting.py

from .assign_lighting_values import assign_lighting_parameters
from .schedules import create_lighting_schedule, create_parasitic_schedule

def get_building_category_and_subtype(building_row):
    """
    Return (building_category, sub_type) based on ``building_row``.
    It now correctly uses 'residential_type' or 'non_residential_type'
    based on the value of 'building_function', and handles potential float inputs.
    """
    
    print(f"\n--- [DEBUG get_category_subtype] ---")
    
    # Get raw values first for logging their original types
    raw_building_function = building_row.get("building_function")
    raw_residential_type = building_row.get("residential_type")
    raw_non_residential_type = building_row.get("non_residential_type")

    print(f"[DEBUG get_category_subtype] Raw building_row.get('building_function'): '{raw_building_function}' (type: {type(raw_building_function)})")
    print(f"[DEBUG get_category_subtype] Raw building_row.get('residential_type'): '{raw_residential_type}' (type: {type(raw_residential_type)})")
    print(f"[DEBUG get_category_subtype] Raw building_row.get('non_residential_type'): '{raw_non_residential_type}' (type: {type(raw_non_residential_type)})")

    # Convert to string, then strip/lower. Default to "" if key is missing before str().
    building_function_str = str(building_row.get("building_function", ""))
    residential_type_str = str(building_row.get("residential_type", ""))
    non_residential_type_str = str(building_row.get("non_residential_type", ""))

    # Debug after string conversion
    print(f"[DEBUG get_category_subtype] Stringified building_function: '{building_function_str}'")
    print(f"[DEBUG get_category_subtype] Stringified residential_type: '{residential_type_str}'")
    print(f"[DEBUG get_category_subtype] Stringified non_residential_type: '{non_residential_type_str}'")

    building_function_val = building_function_str.strip().lower()
    residential_type_val = residential_type_str.strip() # Specific types should retain their case for lookup
    non_residential_type_val = non_residential_type_str.strip() # Specific types should retain their case
    
    print(f"[DEBUG get_category_subtype] Processed building_function_val (lowercase, stripped): '{building_function_val}'")
    print(f"[DEBUG get_category_subtype] Processed residential_type_val (stripped): '{residential_type_val}'")
    print(f"[DEBUG get_category_subtype] Processed non_residential_type_val (stripped): '{non_residential_type_val}'")

    building_category = None
    sub_type_for_lookup = None
    
    # Check for "empty" or non-informative strings like "nan" or "none" after stripping
    def is_valid_type_string(s):
        if not s: return False
        s_lower = s.lower()
        return s_lower != 'nan' and s_lower != 'none' and s_lower != '<na>' # Common pandas NA string representation

    if building_function_val == "residential":
        if is_valid_type_string(residential_type_val):
            building_category = "Residential"
            sub_type_for_lookup = residential_type_val # Use the value with original casing
            print(f"[DEBUG get_category_subtype] 'building_function' is 'residential'. Using 'residential_type': '{sub_type_for_lookup}' as sub_type.")
        else:
            print(f"[DEBUG get_category_subtype] WARNING: 'building_function' is 'residential' but 'residential_type' ('{residential_type_val}') is empty or non-informative.")
            building_category = "Residential"
            sub_type_for_lookup = "Apartment" # Fallback to a default specific residential type
            print(f"[DEBUG get_category_subtype] Defaulting to category='{building_category}', sub_type='{sub_type_for_lookup}' due to problematic residential_type.")
            
    elif building_function_val == "non_residential":
        if is_valid_type_string(non_residential_type_val):
            building_category = "Non-Residential"
            sub_type_for_lookup = non_residential_type_val # Use the value with original casing
            print(f"[DEBUG get_category_subtype] 'building_function' is 'non_residential'. Using 'non_residential_type': '{sub_type_for_lookup}' as sub_type.")
        else:
            print(f"[DEBUG get_category_subtype] WARNING: 'building_function' is 'non_residential' but 'non_residential_type' ('{non_residential_type_val}') is empty or non-informative.")
            building_category = "Non-Residential"
            sub_type_for_lookup = "Other Use Function" # Fallback to a default specific non-residential type
            print(f"[DEBUG get_category_subtype] Defaulting to category='{building_category}', sub_type='{sub_type_for_lookup}' due to problematic non_residential_type.")
            
    else: 
        # building_function itself might be the specific sub-type, or it's empty/invalid.
        # Use original casing for direct_bldg_func_val before stripping.
        direct_bldg_func_val_str = str(building_row.get("building_function", ""))
        direct_bldg_func_val_stripped = direct_bldg_func_val_str.strip()
        
        print(f"[DEBUG get_category_subtype] 'building_function' ('{direct_bldg_func_val_stripped}') is not 'residential' or 'non_residential'. Attempting direct categorization of this value.")
        
        if not is_valid_type_string(direct_bldg_func_val_stripped):
            print(f"[DEBUG get_category_subtype] Direct 'building_function' ('{direct_bldg_func_val_stripped}') is empty or non-informative. Defaulting to Non-Residential, Other Use Function.")
            building_category = "Non-Residential"
            sub_type_for_lookup = "Other Use Function"
        else:
            sub_type_for_lookup = direct_bldg_func_val_stripped # This is the specific sub-type
            # Define known types here for this fallback path
            known_residential_sub_types = {
                "Apartment", "Corner House", "Detached House",
                "Terrace or Semi-detached House", "Two-and-a-half-story House",
            } # Ensure these match your lookup keys' casing
            known_non_residential_sub_types = {
                "Accommodation Function", "Cell Function", "Education Function",
                "Healthcare Function", "Industrial Function", "Meeting Function",
                "Office Function", "Other Use Function", "Retail Function", "Sport Function",
            } # Ensure these match your lookup keys' casing

            if sub_type_for_lookup in known_residential_sub_types:
                building_category = "Residential"
                print(f"[DEBUG get_category_subtype] Matched direct building_function '{sub_type_for_lookup}' to known_residential_sub_types.")
            elif sub_type_for_lookup in known_non_residential_sub_types:
                building_category = "Non-Residential"
                print(f"[DEBUG get_category_subtype] Matched direct building_function '{sub_type_for_lookup}' to known_non_residential_sub_types.")
            else:
                print(f"[DEBUG get_category_subtype] WARNING: Unknown direct building_function '{sub_type_for_lookup}'. Defaulting category to Non-Residential.")
                building_category = "Non-Residential" # Default for truly unknown specific types

    # Final safety net if logic above somehow fails to set category or sub_type adequately
    if not building_category or not is_valid_type_string(sub_type_for_lookup):
        print(f"[DEBUG get_category_subtype] CRITICAL FALLBACK: Could not determine valid category or sub_type (current sub_type: '{sub_type_for_lookup}'). Defaulting to Non-Residential, Other Use Function.")
        building_category = "Non-Residential"
        sub_type_for_lookup = "Other Use Function"

    print(f"[DEBUG get_category_subtype] Final Determined: building_category='{building_category}', sub_type_for_lookup='{sub_type_for_lookup}'")
    print(f"--- [END DEBUG get_category_subtype] ---")
    return (building_category, sub_type_for_lookup)


# The rest of your Elec/lighting.py file (add_lights_and_parasitics function) remains the same
# as the version I provided in the previous message with its own debug prints.
# Ensure it uses this updated get_building_category_and_subtype function.

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
    bldg_id = int(building_row.get("ogc_fid", 0)) 
    print(f"\n--- [DEBUG add_lights_and_parasitics for bldg_id {bldg_id}] ---") 
    print(f"[DEBUG add_lights_and_parasitics] From get_building_category_and_subtype: category='{building_category}', sub_type='{sub_type}'")


    assigned_dict = assign_lighting_parameters( 
        building_id=bldg_id,
        building_category=building_category,
        sub_type=sub_type,
        age_range=building_row.get("age_range", None), 
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config,
        assigned_log=assigned_values_log 
    )

    lights_wm2 = assigned_dict["lights_wm2"]["assigned_value"]
    parasitic_wm2 = assigned_dict["parasitic_wm2"]["assigned_value"]
    lights_frac_radiant = assigned_dict["lights_fraction_radiant"]["assigned_value"]
    lights_frac_visible = assigned_dict["lights_fraction_visible"]["assigned_value"]
    lights_frac_replace = assigned_dict["lights_fraction_replaceable"]["assigned_value"]
    equip_frac_radiant = assigned_dict["equip_fraction_radiant"]["assigned_value"]
    equip_frac_lost = assigned_dict["equip_fraction_lost"]["assigned_value"]

    lights_sched_name = create_lighting_schedule(
        idf, building_category=building_category, sub_type=sub_type, schedule_name="LightsSchedule"
    )
    paras_sched_name = create_parasitic_schedule(idf, sched_name="ParasiticSchedule")

    lights_obj = idf.newidfobject("LIGHTS")
    lights_obj.Name = f"Lights_{zonelist_name}"
    lights_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zonelist_name
    lights_obj.Schedule_Name = lights_sched_name
    lights_obj.Design_Level_Calculation_Method = "Watts/Area"
    lights_obj.Watts_per_Zone_Floor_Area = lights_wm2
    lights_obj.Fraction_Radiant = lights_frac_radiant
    lights_obj.Fraction_Visible = lights_frac_visible
    lights_obj.Fraction_Replaceable = lights_frac_replace

    eq_obj = idf.newidfobject("ELECTRICEQUIPMENT")
    eq_obj.Name = f"Parasitic_{zonelist_name}"
    eq_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zonelist_name
    eq_obj.Schedule_Name = paras_sched_name
    eq_obj.Design_Level_Calculation_Method = "Watts/Area"
    eq_obj.Watts_per_Zone_Floor_Area = parasitic_wm2
    eq_obj.Fraction_Radiant = equip_frac_radiant
    eq_obj.Fraction_Lost = equip_frac_lost
    
    print(f"[DEBUG add_lights_and_parasitics] Successfully created LIGHTS and ELECTRICEQUIPMENT objects for bldg_id {bldg_id}.")
    print(f"--- [END DEBUG add_lights_and_parasitics for bldg_id {bldg_id}] ---")
    return lights_obj, eq_obj