# elec_functions.py

"""
This module provides functions for applying lighting + parasitic equipment
parameters to an EnergyPlus IDF, similar to how 'hvac_functions.py' and
'vent_functions.py' work.

Typically, you'll do something like:
  - build a param_dict from your assigned_lighting.csv
  - call apply_building_level_elec(idf, param_dict)
OR
  - if you want each row to define a specific object name / param, 
    call apply_object_level_elec(idf, df_lighting)

You can adapt these approaches to your exact CSV structure and naming.
"""

import math

##############################################################################
# 1) APPLY BUILDING-LEVEL ELECTRICAL PARAMETERS
##############################################################################

def apply_building_level_elec(idf, param_dict, zonelist_name="ALL_ZONES"):
    """
    Interprets a dictionary of lighting/electrical parameters, for example:

      param_dict = {
        "lights_wm2": 10.0,
        "parasitic_wm2": 0.285,
        "tD": 2000,
        "tN": 300,
        "lights_fraction_radiant": 0.7,
        "lights_fraction_visible": 0.2,
        "lights_fraction_replaceable": 1.0,
        "equip_fraction_radiant": 0.0,
        "equip_fraction_lost": 1.0,
        # possibly "object_name" or "schedule_name" if needed
      }

    Then we create or update:
      - A single 'LIGHTS' object for the zone list
      - A single 'ELECTRICEQUIPMENT' object for the zone list
      - Possibly schedules for lighting or equipment usage

    This is analogous to how 'apply_building_level_hvac' works, but for lighting/equipment.
    """

    # 1) Extract the relevant numeric picks
    lights_wm2 = param_dict.get("lights_wm2", 10.0)
    parasitic_wm2 = param_dict.get("parasitic_wm2", 0.285)

    # Fractions for LIGHTS
    lights_frac_radiant = param_dict.get("lights_fraction_radiant", 0.7)
    lights_frac_visible = param_dict.get("lights_fraction_visible", 0.2)
    lights_frac_replace = param_dict.get("lights_fraction_replaceable", 1.0)

    # Fractions for ELECTRICEQUIPMENT
    equip_frac_radiant = param_dict.get("equip_fraction_radiant", 0.0)
    equip_frac_lost = param_dict.get("equip_fraction_lost", 1.0)

    # Optional usage times if you want them for schedules
    tD = param_dict.get("tD", 2000)  # e.g. day burning hours
    tN = param_dict.get("tN", 300)   # e.g. night burning hours
    # If you want to create advanced schedules from tD/tN, you can. Or skip.

    print("[ELEC] Creating building-level lighting & equipment objects with:")
    print(f"  lights_wm2={lights_wm2}, parasitic_wm2={parasitic_wm2},")
    print(f"  lights_fraction_radiant={lights_frac_radiant}, visible={lights_frac_visible}, replaceable={lights_frac_replace}")
    print(f"  equip_fraction_radiant={equip_frac_radiant}, equip_fraction_lost={equip_frac_lost}")

    # 2) Create or update a LIGHTS object for the entire building (via a ZoneList)
    lights_obj_name = f"Lights_{zonelist_name}"
    lights_obj = _create_or_update_lights_object(
        idf,
        obj_name=lights_obj_name,
        zone_or_zonelist=zonelist_name,
        lights_wm2=lights_wm2,
        frac_radiant=lights_frac_radiant,
        frac_visible=lights_frac_visible,
        frac_replace=lights_frac_replace
    )

    # 3) Create or update an ELECTRICEQUIPMENT object for parasitic loads
    equip_obj_name = f"Parasitic_{zonelist_name}"
    equip_obj = _create_or_update_equip_object(
        idf,
        obj_name=equip_obj_name,
        zone_or_zonelist=zonelist_name,
        equip_wm2=parasitic_wm2,
        frac_radiant=equip_frac_radiant,
        frac_lost=equip_frac_lost
    )

    # 4) If you want to build schedules from tD/tN or param_dict, you can create them here
    #    or call your existing schedule creation code from lighting.py (like create_lighting_schedule).
    #    Then you can assign those schedules to the lights_obj.Schedule_Name, equip_obj.Schedule_Name, etc.

    # Example:
    # lights_sched_name = create_lighting_schedule(idf, "Non-Residential", "Office Function", "LightsSchedule")
    # lights_obj.Schedule_Name = lights_sched_name

    return lights_obj, equip_obj


def _create_or_update_lights_object(
    idf,
    obj_name,
    zone_or_zonelist="ALL_ZONES",
    lights_wm2=10.0,
    frac_radiant=0.7,
    frac_visible=0.2,
    frac_replace=1.0
):
    """
    Creates or updates a LIGHTS object with 'Watts/Area' method,
    applying the fractions given.
    """
    existing = [
        lt for lt in idf.idfobjects["LIGHTS"]
        if lt.Name.upper() == obj_name.upper()
    ]
    if existing:
        lights_obj = existing[0]
    else:
        lights_obj = idf.newidfobject("LIGHTS", Name=obj_name)

    # zone or zone list
    if hasattr(lights_obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        lights_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_or_zonelist
    else:
        lights_obj.Zone_or_ZoneList_Name = zone_or_zonelist

    # design method
    lights_obj.Design_Level_Calculation_Method = "Watts/Area"
    lights_obj.Watts_per_Zone_Floor_Area = lights_wm2

    # fractions
    lights_obj.Fraction_Radiant = frac_radiant
    lights_obj.Fraction_Visible = frac_visible

    # if older IDD doesn't have Fraction_Replaceable, skip
    if hasattr(lights_obj, "Fraction_Replaceable"):
        lights_obj.Fraction_Replaceable = frac_replace

    return lights_obj


def _create_or_update_equip_object(
    idf,
    obj_name,
    zone_or_zonelist="ALL_ZONES",
    equip_wm2=0.285,
    frac_radiant=0.0,
    frac_lost=1.0
):
    """
    Creates or updates an ELECTRICEQUIPMENT object with 'Watts/Area' method,
    applying fraction fields as well.
    """
    existing = [
        eq for eq in idf.idfobjects["ELECTRICEQUIPMENT"]
        if eq.Name.upper() == obj_name.upper()
    ]
    if existing:
        equip_obj = existing[0]
    else:
        equip_obj = idf.newidfobject("ELECTRICEQUIPMENT", Name=obj_name)

    if hasattr(equip_obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        equip_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_or_zonelist
    else:
        equip_obj.Zone_or_ZoneList_Name = zone_or_zonelist

    equip_obj.Design_Level_Calculation_Method = "Watts/Area"
    equip_obj.Watts_per_Zone_Floor_Area = equip_wm2

    if hasattr(equip_obj, "Fraction_Radiant"):
        equip_obj.Fraction_Radiant = frac_radiant
    if hasattr(equip_obj, "Fraction_Lost"):
        equip_obj.Fraction_Lost = frac_lost
    # if older IDD uses e.g. Fraction_Visible for equip, you can set it here as well

    return equip_obj


##############################################################################
# 2) APPLY OBJECT-LEVEL ELECTRIC PARAMETERS (Optional)
##############################################################################

def apply_object_level_elec(idf, df_lighting):
    """
    This approach reads from a DataFrame like `assigned_lighting.csv` row by row,
    where each row has:
       ogc_fid, object_name, param_name, assigned_value, min_val, max_val
    For instance:
       4136730, LIGHTS, lights_wm2, 10, 10, 10
       4136730, ELECTRICEQUIPMENT, parasitic_wm2, 0.285, 0.285, 0.285
       4136730, LIGHTS_SCHEDULE, tD, 2000, 2000, 2000
       ...
       4136730, LIGHTS.Fraction_Radiant, lights_fraction_radiant, 0.7, 0.7, 0.7
       ...

    We interpret object_name (e.g. "LIGHTS") as the type of object,
    param_name (e.g. "lights_wm2") as which field to set,
    assigned_value as the final numeric or string value.

    Then we create/update that object in the IDF. 
    This is a more direct "object-based" approach, 
    rather than a single building-level dictionary.

    Steps:
      1) group df_lighting by object_name
      2) for each object_name, parse the rows to see which param_name => assigned_value
      3) create or update IDF object with those fields
    """
    object_groups = df_lighting.groupby("object_name")

    for obj_name, group_df in object_groups:
        print(f"[ELEC] Handling object_name='{obj_name}' with {len(group_df)} rows.")
        # We'll accumulate a local dictionary of {param_name => assigned_value}
        local_params = {}
        for row in group_df.itertuples():
            p_name = row.param_name
            val    = row.assigned_value
            # Attempt float cast if numeric
            try:
                val_float = float(val)
                local_params[p_name] = val_float
            except:
                # might be a string
                local_params[p_name] = val

        # Decide how to create or update the IDF object
        if obj_name.upper() == "LIGHTS":
            # Typically a single object? 
            # Maybe we create or update an object named "LIGHTS"
            # This is somewhat unorthodox because usually you name objects more specifically.
            _update_generic_lights_obj(idf, obj_name="LIGHTS", param_dict=local_params)

        elif obj_name.upper() == "ELECTRICEQUIPMENT":
            _update_generic_equip_obj(idf, obj_name="ELECTRICEQUIPMENT", param_dict=local_params)

        elif "SCHEDULE" in obj_name.upper():
            # e.g. "LIGHTS_SCHEDULE"
            # parse param_name => "tD", "tN" => do something for schedule
            # or skip if not needed
            pass

        elif obj_name.upper().startswith("LIGHTS.FRACTION_"):
            # This might indicate you're referencing fraction fields on the LIGHTS object
            # If so, handle it in your logic or combined approach. 
            # The CSV approach suggests you're storing "lights_fraction_radiant" in param_name,
            # assigned_value=0.7. 
            pass

        else:
            print(f"[ELEC WARNING] Unknown object_name='{obj_name}', skipping.")


def _update_generic_lights_obj(idf, obj_name, param_dict):
    """
    Example of updating a single 'LIGHTS' object named `obj_name` in the IDF,
    using the fields in `param_dict` (e.g. "lights_wm2", "lights_fraction_radiant", etc.).
    """
    # Find or create the LIGHTS object
    existing = [
        lt for lt in idf.idfobjects["LIGHTS"]
        if lt.Name.upper() == obj_name.upper()
    ]
    if existing:
        lights_obj = existing[0]
    else:
        lights_obj = idf.newidfobject("LIGHTS", Name=obj_name)

    # param_dict might contain keys like "lights_wm2", "lights_fraction_radiant"...
    if "lights_wm2" in param_dict:
        val = float(param_dict["lights_wm2"])
        lights_obj.Design_Level_Calculation_Method = "Watts/Area"
        lights_obj.Watts_per_Zone_Floor_Area = val

    if "lights_fraction_radiant" in param_dict:
        lights_obj.Fraction_Radiant = float(param_dict["lights_fraction_radiant"])

    if "lights_fraction_visible" in param_dict:
        lights_obj.Fraction_Visible = float(param_dict["lights_fraction_visible"])

    if "lights_fraction_replaceable" in param_dict and hasattr(lights_obj, "Fraction_Replaceable"):
        lights_obj.Fraction_Replaceable = float(param_dict["lights_fraction_replaceable"])

    # If there's a schedule param, e.g. "schedule_name" or "lights_sched"
    # you can parse it similarly
    # For example:
    # if "lights_schedule_name" in param_dict:
    #     lights_obj.Schedule_Name = param_dict["lights_schedule_name"]


def _update_generic_equip_obj(idf, obj_name, param_dict):
    """
    Example of updating a single 'ELECTRICEQUIPMENT' object.
    param_dict might have "parasitic_wm2", "equip_fraction_radiant", etc.
    """
    existing = [
        eq for eq in idf.idfobjects["ELECTRICEQUIPMENT"]
        if eq.Name.upper() == obj_name.upper()
    ]
    if existing:
        equip_obj = existing[0]
    else:
        equip_obj = idf.newidfobject("ELECTRICEQUIPMENT", Name=obj_name)

    if "parasitic_wm2" in param_dict:
        val = float(param_dict["parasitic_wm2"])
        equip_obj.Design_Level_Calculation_Method = "Watts/Area"
        equip_obj.Watts_per_Zone_Floor_Area = val

    if "equip_fraction_radiant" in param_dict and hasattr(equip_obj, "Fraction_Radiant"):
        equip_obj.Fraction_Radiant = float(param_dict["equip_fraction_radiant"])

    if "equip_fraction_lost" in param_dict and hasattr(equip_obj, "Fraction_Lost"):
        equip_obj.Fraction_Lost = float(param_dict["equip_fraction_lost"])
