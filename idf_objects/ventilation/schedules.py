# ventilation/schedules.py

from geomeppy import IDF

def create_always_on_schedule(idf, sched_name="AlwaysOnSched"):
    """
    Creates a SCHEDULE:CONSTANT with a Fraction = 1.0
    for infiltration or ventilation that runs 24/7.
    """
    # Check if already exists
    existing = idf.getobject("SCHEDULE:CONSTANT", sched_name.upper())
    if existing:
        return existing  # No need to recreate

    schedule = idf.newidfobject("SCHEDULE:CONSTANT")
    schedule.Name = sched_name
    schedule.Schedule_Type_Limits_Name = "Fraction"
    schedule.Hourly_Value = 1.0
    return schedule


def create_day_night_schedule(idf, sched_name="VentSched_DayNight"):
    """
    Day/Night schedule that is 0.5 at night, 1.0 during day.
    Example: 06:00-22:00 => 1.0, else => 0.5
    """
    # Check if already exists
    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    schedule = idf.newidfobject("SCHEDULE:COMPACT")
    schedule.Name = sched_name
    schedule.Schedule_Type_Limits_Name = "Fraction"

    schedule.Field_1 = "Through: 12/31"
    schedule.Field_2 = "For: AllDays"
    schedule.Field_3 = "Until: 06:00,0.5"
    schedule.Field_4 = "Until: 22:00,1.0"
    schedule.Field_5 = "Until: 24:00,0.5"
    return schedule


def create_workhours_schedule(idf, sched_name="WorkHoursSched"):
    """
    Workhours schedule: 
      - 0.2 fraction from midnight to 09:00,
      - 1.0 from 09:00 to 17:00,
      - 0.2 from 17:00 to midnight,
      - weekends/holidays => 0.2 all day
    """
    # Check if already exists
    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    schedule = idf.newidfobject("SCHEDULE:COMPACT")
    schedule.Name = sched_name
    schedule.Schedule_Type_Limits_Name = "Fraction"

    schedule.Field_1 = "Through: 12/31"
    schedule.Field_2 = "For: Weekdays"
    schedule.Field_3 = "Until: 09:00,0.2"
    schedule.Field_4 = "Until: 17:00,1.0"
    schedule.Field_5 = "Until: 24:00,0.2"
    schedule.Field_6 = "For: Saturday Sunday Holiday"
    schedule.Field_7 = "Until: 24:00,0.2"
    return schedule


# ------------------------------------------------------------------------
# NEW HELPER FUNCTIONS FOR DYNAMIC SCHEDULES
# ------------------------------------------------------------------------

def create_schedule_from_pattern(idf, sched_name, pattern, schedule_type_limits="Fraction"):
    """
    Creates a SCHEDULE:COMPACT in the IDF from a single pattern of
    (start_hour, end_hour, fraction_value) tuples for ALL days.

    :param idf: geomeppy IDF instance
    :param sched_name: name of the schedule in E+
    :param pattern: list of (start_hour, end_hour, value), e.g. [(0,6,0.5), (6,22,1.0), (22,24,0.5)]
    :param schedule_type_limits: e.g. "Fraction" or "OnOff"
    :returns: the new or existing SCHEDULE:COMPACT object
    """
    # Check if schedule already exists
    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    sched_obj = idf.newidfobject("SCHEDULE:COMPACT")
    sched_obj.Name = sched_name
    sched_obj.Schedule_Type_Limits_Name = schedule_type_limits

    # We'll define just one set of rules "Through: 12/31", "For: AllDays"
    # If you want to differentiate weekdays vs. weekends in the same schedule,
    # see create_schedule_from_weekday_weekend_pattern() below.
    field_idx = 1
    sched_obj[f"Field_{field_idx}"] = "Through: 12/31"
    field_idx += 1

    sched_obj[f"Field_{field_idx}"] = "For: AllDays"
    field_idx += 1

    # Now loop over the pattern, building lines like "Until: HH:MM, fraction"
    for (start_hr, end_hr, val) in pattern:
        # E+ SCHEDULE:COMPACT lines are sequential. We just say "Until: end_hr"
        # The fraction applies from previous end_hr to new end_hr.
        # For the first chunk, it starts at midnight implicitly.
        # e.g. "Until: 06:00,0.5"
        line_str = f"Until: {end_hr:02d}:00,{val}"
        sched_obj[f"Field_{field_idx}"] = line_str
        field_idx += 1

    return sched_obj


def create_schedule_from_weekday_weekend_pattern(idf, sched_name, weekday_pattern, weekend_pattern, 
                                                 schedule_type_limits="Fraction"):
    """
    Creates a SCHEDULE:COMPACT with two sets of rules:
    - One for Weekdays
    - One for Saturday Sunday Holiday

    :param idf: geomeppy IDF instance
    :param sched_name: name of the schedule in E+
    :param weekday_pattern: list of (start_hr, end_hr, fraction) for M-F
    :param weekend_pattern: list of (start_hr, end_hr, fraction) for Sat/Sun/Holiday
    :param schedule_type_limits: e.g. "Fraction"
    :returns: new or existing SCHEDULE:COMPACT
    """
    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    sched_obj = idf.newidfobject("SCHEDULE:COMPACT")
    sched_obj.Name = sched_name
    sched_obj.Schedule_Type_Limits_Name = schedule_type_limits

    # First chunk: Through: 12/31, For: Weekdays
    field_idx = 1
    sched_obj[f"Field_{field_idx}"] = "Through: 12/31"
    field_idx += 1

    sched_obj[f"Field_{field_idx}"] = "For: Weekdays"
    field_idx += 1

    for (start_hr, end_hr, val) in weekday_pattern:
        line_str = f"Until: {end_hr:02d}:00,{val}"
        sched_obj[f"Field_{field_idx}"] = line_str
        field_idx += 1

    # Next chunk: For Saturday Sunday Holiday
    sched_obj[f"Field_{field_idx}"] = "For: Saturday Sunday Holiday"
    field_idx += 1

    for (start_hr, end_hr, val) in weekend_pattern:
        line_str = f"Until: {end_hr:02d}:00,{val}"
        sched_obj[f"Field_{field_idx}"] = line_str
        field_idx += 1

    return sched_obj


def ensure_dynamic_schedule(idf, sched_name, weekday_pattern=None, weekend_pattern=None):
    """
    A convenience function that:
     - if only weekday_pattern is provided, creates schedule from that pattern for all days;
     - if both weekday & weekend patterns provided, creates a weekday/weekend schedule.

    :param idf: geomeppy IDF
    :param sched_name: string
    :param weekday_pattern: list of (start_hr, end_hr, fraction)
    :param weekend_pattern: list of (start_hr, end_hr, fraction)
    :return: the schedule object
    """
    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    if weekday_pattern and not weekend_pattern:
        # same pattern for all days
        return create_schedule_from_pattern(idf, sched_name, weekday_pattern)

    elif weekday_pattern and weekend_pattern:
        return create_schedule_from_weekday_weekend_pattern(idf, sched_name, weekday_pattern, weekend_pattern)

    else:
        # fallback => always on
        return create_always_on_schedule(idf, sched_name)
