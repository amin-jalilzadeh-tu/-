# File: D:\Documents\E_Plus_2030_py\idf_objects\eequip\equipment.py
"""equipment.py

Adds ELECTRICEQUIPMENT objects to an IDF using default lookup tables
and optional user overrides.
"""

from idf_objects.Elec.lighting import get_building_category_and_subtype # This will use the debugged version from Elec/lighting.py
from .assign_equip_values import assign_equipment_parameters
from .schedules import create_equipment_schedule


def add_electric_equipment(
    idf,
    building_row,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config=None,
    assigned_values_log=None,
    zonelist_name="ALL_ZONES",
):
    """Create an ELECTRICEQUIPMENT object for the entire building.

    Parameters
    ----------
    idf : Eppy IDF
        The IDF object to modify.
    building_row : pd.Series or dict
        Row with at least ``ogc_fid`` and ``building_function`` fields.
    calibration_stage : str, default "pre_calibration"
        Lookup key for ``equip_lookup``.
    strategy : str, default "A"
        Selection strategy for value picking.
    random_seed : int, optional
        Seed for the random generator if strategy uses randomness.
    user_config : list of dicts, optional
        Override rows for equipment parameters.
    assigned_values_log : dict, optional
        If provided, the picked parameters are stored under
        ``assigned_values_log[building_id]``.
    zonelist_name : str, default "ALL_ZONES"
        ZoneList name to reference in the created object.
    """

    # 1) Get building_category / sub_type
    building_category, sub_type = get_building_category_and_subtype(building_row) # Uses the debugged version
    
    bldg_id = int(building_row.get("ogc_fid", 0))
    print(f"\n--- [DEBUG add_electric_equipment for bldg_id {bldg_id}] ---")
    print(f"[DEBUG add_electric_equipment] Calling get_building_category_and_subtype, received: category='{building_category}', sub_type='{sub_type}'")

    picks = assign_equipment_parameters( # Call to assign_equipment_parameters
        building_id=bldg_id,
        building_category=building_category,
        sub_type=sub_type,
        age_range=None, # Assuming age_range is not the issue for now
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config,
        assigned_log=assigned_values_log,
    )

    equip_wm2 = picks["equip_wm2"]["assigned_value"]
    frac_latent = picks.get("equip_fraction_latent", {}).get("assigned_value")
    frac_radiant = picks.get("equip_fraction_radiant", {}).get("assigned_value")
    frac_lost = picks.get("equip_fraction_lost", {}).get("assigned_value")

    sched_name = create_equipment_schedule(
        idf,
        building_category=building_category,
        sub_type=sub_type,
        schedule_name="EquipSchedule",
    )

    eq_obj = idf.newidfobject("ELECTRICEQUIPMENT")
    eq_obj.Name = f"Equip_{zonelist_name}"
    eq_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zonelist_name
    eq_obj.Schedule_Name = sched_name
    eq_obj.Design_Level_Calculation_Method = "Watts/Area"
    eq_obj.Watts_per_Zone_Floor_Area = equip_wm2
    if frac_latent is not None and hasattr(eq_obj, "Fraction_Latent"):
        eq_obj.Fraction_Latent = frac_latent
    if frac_radiant is not None and hasattr(eq_obj, "Fraction_Radiant"):
        eq_obj.Fraction_Radiant = frac_radiant
    if frac_lost is not None and hasattr(eq_obj, "Fraction_Lost"):
        eq_obj.Fraction_Lost = frac_lost
    
    print(f"[DEBUG add_electric_equipment] Successfully created ELECTRICEQUIPMENT object for bldg_id {bldg_id} with equip_wm2 = {equip_wm2}.")
    print(f"--- [END DEBUG add_electric_equipment for bldg_id {bldg_id}] ---")
    return eq_obj