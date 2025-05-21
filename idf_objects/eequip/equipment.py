"""equipment.py

Adds ELECTRICEQUIPMENT objects to an IDF using default lookup tables
and optional user overrides.
"""

from idf_objects.Elec.lighting import get_building_category_and_subtype
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

    building_category, sub_type = get_building_category_and_subtype(building_row)
    bldg_id = int(building_row.get("ogc_fid", 0))

    picks = assign_equipment_parameters(
        building_id=bldg_id,
        building_category=building_category,
        sub_type=sub_type,
        age_range=None,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config,
        assigned_log=assigned_values_log,
    )

    equip_wm2 = picks["equip_wm2"]

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

    return eq_obj
