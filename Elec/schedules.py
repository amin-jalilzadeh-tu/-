# Elec/schedules.py

from .schedule_def import SCHEDULE_DEFINITIONS

"""
This module creates detailed lighting schedules for weekdays and weekends,
differentiating by building_category (Residential/Non-Residential)
and by sub_type (Apartment, Office Function, etc.).

We have two main functions:
1) create_lighting_schedule(idf, building_category, sub_type, schedule_name)
   - Creates a SCHEDULE:COMPACT with different time blocks for 'WeekDays',
     'Saturday', and 'Sunday' (or 'AllDays' if you prefer).
2) create_parasitic_schedule(idf, sched_name)
   - Creates an always-on (1.0) schedule, typically for parasitic loads.

Important:
- This code assumes you already loaded or potentially overrode
  SCHEDULE_DEFINITIONS in schedule_def.py (for instance, by calling
  `read_schedule_overrides_from_excel()` + `apply_schedule_overrides_to_schedules()`).
- If you want more advanced day-splitting, feel free to expand the logic below.
"""


def create_lighting_schedule(idf, building_category, sub_type, schedule_name="LightsSchedule"):
    """
    Create a SCHEDULE:COMPACT in the IDF using SCHEDULE_DEFINITIONS[building_category][sub_type].
    We define separate blocks for:
      - For: WeekDays
      - For: Saturday
      - For: Sunday

    If the sub_type is missing in SCHEDULE_DEFINITIONS, we fallback to a simple always-0.5 pattern.

    The final IDF object name is `schedule_name`. We return that string for convenience.
    """

    # Attempt to get sub-type dictionary from SCHEDULE_DEFINITIONS
    try:
        sub_dict = SCHEDULE_DEFINITIONS[building_category][sub_type]
    except KeyError:
        # Fallback: If not found, create a simple always-0.5 schedule
        sub_dict = {
            "weekday": [(0, 24, 0.5)],
            "weekend": [(0, 24, 0.5)],
        }

    # Some sub-types might not have a separate weekend pattern. 
    # So ensure we have 'weekday' and 'weekend' keys:
    if "weekday" not in sub_dict:
        sub_dict["weekday"] = [(0, 24, 0.5)]
    if "weekend" not in sub_dict:
        sub_dict["weekend"] = [(0, 24, 0.5)]

    # Create the schedule object
    schedule = idf.newidfobject("SCHEDULE:COMPACT")
    schedule.Name = schedule_name
    schedule.Schedule_Type_Limits_Name = "Fraction"

    # We'll define the entire year with "Through: 12/31" and break it down by day types
    # The pattern is:
    #   Field_1:  "Through: 12/31"
    #   Field_2:  "For: WeekDays"
    #   Field_3+: "Until: HH:MM,<fraction>"
    #
    # Then for Saturday, Sunday, etc.

    field_idx = 1
    setattr(schedule, f"Field_{field_idx}", "Through: 12/31")
    field_idx += 1

    # 1) WeekDays
    setattr(schedule, f"Field_{field_idx}", "For: WeekDays")
    field_idx += 1
    for (start_hour, end_hour, frac) in sub_dict["weekday"]:
        # e.g. "Until: 06:00,0.05"
        setattr(schedule, f"Field_{field_idx}",
                f"Until: {int(end_hour):02d}:00,{frac:.2f}")
        field_idx += 1

    # 2) Saturday
    setattr(schedule, f"Field_{field_idx}", "For: Saturday")
    field_idx += 1
    for (start_hour, end_hour, frac) in sub_dict["weekend"]:
        setattr(schedule, f"Field_{field_idx}",
                f"Until: {int(end_hour):02d}:00,{frac:.2f}")
        field_idx += 1

    # 3) Sunday
    setattr(schedule, f"Field_{field_idx}", "For: Sunday")
    field_idx += 1
    for (start_hour, end_hour, frac) in sub_dict["weekend"]:
        setattr(schedule, f"Field_{field_idx}",
                f"Until: {int(end_hour):02d}:00,{frac:.2f}")
        field_idx += 1

    return schedule.Name


def create_parasitic_schedule(idf, sched_name="ParasiticSchedule"):
    """
    Creates an always-on schedule (1.0) for parasitic loads (24/7).
    """
    schedule = idf.newidfobject("SCHEDULE:COMPACT")
    schedule.Name = sched_name
    schedule.Schedule_Type_Limits_Name = "Fraction"

    # Single block covering all days, 24 hours
    schedule.Field_1 = "Through: 12/31"
    schedule.Field_2 = "For: AllDays"
    schedule.Field_3 = "Until: 24:00,1.0"

    return schedule.Name
