# eequip/schedules.py

from .schedule_def import EQUIP_SCHEDULE_DEFINITIONS

"""
This module creates detailed schedules for electric equipment usage
(weekday vs. weekend), differentiating by building category (Residential vs. Non-Residential)
and sub-type (e.g. Corner House, Office, Retail, etc.).

We provide two main functions:

1) create_equipment_schedule(idf, building_category, sub_type, schedule_name)
   - Creates a multi-day schedule with 'WeekDays', 'Saturday', 'Sunday'.

2) create_equipment_parasitic_schedule(idf, sched_name)
   - Creates a schedule that is always ON (1.0).
"""


def create_equipment_schedule(idf, building_category, sub_type, schedule_name="EquipSchedule"):
    """
    Creates a SCHEDULE:COMPACT object in the IDF representing a typical 
    equipment usage pattern for weekdays vs. weekends, based on 
    EQUIP_SCHEDULE_DEFINITIONS.

    Parameters:
        - idf: Eppy IDF object (or a similar interface)
        - building_category: e.g. "Residential" or "Non-Residential"
        - sub_type: e.g. "Corner House", "Office Function"
        - schedule_name: name of the schedule in IDF

    Returns:
        - The name of the new schedule object (same as schedule_name).
    """

    # Attempt to retrieve a sub-type dict. If not found, fallback to a simple 0.5 fraction all day.
    try:
        sub_dict = EQUIP_SCHEDULE_DEFINITIONS[building_category][sub_type]
    except KeyError:
        sub_dict = {
            "weekday": [(0, 24, 0.5)],
            "weekend": [(0, 24, 0.5)],
        }

    # Create a new schedule object in the IDF
    schedule = idf.newidfobject("SCHEDULE:COMPACT")
    schedule.Name = schedule_name
    schedule.Schedule_Type_Limits_Name = "Fraction"

    # We'll define a pattern that covers the full year:
    field_idx = 1

    # First line: "Through: 12/31"
    setattr(schedule, f"Field_{field_idx}", "Through: 12/31")
    field_idx += 1

    # 1) WeekDays
    setattr(schedule, f"Field_{field_idx}", "For: WeekDays")
    field_idx += 1
    for (start_hour, end_hour, fraction) in sub_dict["weekday"]:
        setattr(
            schedule,
            f"Field_{field_idx}",
            f"Until: {end_hour:02d}:00,{fraction:.2f}"
        )
        field_idx += 1

    # 2) Saturday
    setattr(schedule, f"Field_{field_idx}", "For: Saturday")
    field_idx += 1
    for (start_hour, end_hour, fraction) in sub_dict["weekend"]:
        setattr(
            schedule,
            f"Field_{field_idx}",
            f"Until: {end_hour:02d}:00,{fraction:.2f}"
        )
        field_idx += 1

    # 3) Sunday
    setattr(schedule, f"Field_{field_idx}", "For: Sunday")
    field_idx += 1
    for (start_hour, end_hour, fraction) in sub_dict["weekend"]:
        setattr(
            schedule,
            f"Field_{field_idx}",
            f"Until: {end_hour:02d}:00,{fraction:.2f}"
        )
        field_idx += 1

    return schedule.Name


def create_equipment_parasitic_schedule(idf, sched_name="EquipParasiticSchedule"):
    """
    Creates a schedule that is always ON at 1.0 for parasitic equipment loads.
    You can also rename it or adjust if you want partial load or special schedules.

    Parameters:
        - idf: Eppy IDF object
        - sched_name: the schedule name in the IDF

    Returns:
        - The name of the new schedule object
    """

    schedule = idf.newidfobject("SCHEDULE:COMPACT")
    schedule.Name = sched_name
    schedule.Schedule_Type_Limits_Name = "Fraction"

    # A simple all-day, all-year schedule at 1.0
    schedule.Field_1 = "Through: 12/31"
    schedule.Field_2 = "For: AllDays"
    schedule.Field_3 = "Until: 24:00,1.0"

    return schedule.Name
