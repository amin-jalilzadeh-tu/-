# Elec/lighting.py

from .assign_lighting_values import assign_lighting_parameters
from .schedules import create_lighting_schedule, create_parasitic_schedule

def get_building_category_and_subtype(building_row):
    """
    Returns (building_category, sub_type) strings based on building_row.
    Adjust the logic as needed, depending on how your CSV or DB fields
    are structured.

    If building_row["building_function"] is something like "Residential"
    or "Meeting Function", use that as your sub_type.
    If building_row["building_function"] says "Residential", set building_category="Residential".
    Otherwise, assume building_category="Non-Residential".

    Update as necessary for your own classification logic.
    """
    bldg_func = building_row.get("building_function", "").strip()
    if not bldg_func:
        # fallback
        return ("Non-Residential", "Other Use Function")

    # Example simple logic:
    if "resid" in bldg_func.lower():
        building_category = "Residential"
        sub_type = bldg_func  # e.g. "Residential" or "Corner House"
    else:
        building_category = "Non-Residential"
        sub_type = bldg_func  # e.g. "Office Function", "Meeting Function"

    return (building_category, sub_type)


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

    assigned_dict = assign_lighting_parameters(
        building_id=bldg_id,
        building_type=sub_type,
        # Optional:
        # age_range=building_row.get("age_range", None),
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config,
        assigned_log=assigned_values_log  # logs the final sub-dict structure
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

    # Optionally, you can also set eq_obj.Fraction_Visible if needed,
    # but typically for "Parasitic" loads we do not.

    return lights_obj, eq_obj
