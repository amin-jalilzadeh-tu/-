# ventilation/schedules.py

from typing import List, Tuple, Optional, Any # Keep Any for type hints

# Import IDF class for type hinting (assuming geomeppy is used)
try:
    from geomeppy import IDF
    # We cannot reliably get the IDFObject type at module level without an instance.
    # Use Any or a more generic type hint for IDF objects within function signatures if needed.
except ImportError:
    IDF = Any # Fallback if geomeppy not available

# Helper function to ensure ScheduleTypeLimits exist
def ensure_schedule_type_limits(idf: IDF, limits_name: str, numeric_type: str = "Continuous", unit_type: Optional[str] = None):
    """Checks if ScheduleTypeLimits exists, creates it if not."""
    # Use uppercase for case-insensitive check with getobject
    if not idf.getobject("SCHEDULETYPELIMITS", limits_name.upper()):
        print(f"[INFO] Creating ScheduleTypeLimits: {limits_name}")
        try:
            lims = idf.newidfobject("SCHEDULETYPELIMITS")
            lims.Name = limits_name
            lims.Numeric_Type = numeric_type
            if unit_type:
                lims.Unit_Type = unit_type
            # Set default lower/upper limits (often left blank in E+ for defaults)
            # Example: lims.Lower_Limit_Value = 0.0
            # Example: lims.Upper_Limit_Value = 1.0 # For Fraction type
            return lims
        except Exception as e:
            print(f"[ERROR] Failed to create SCHEDULETYPELIMITS {limits_name}: {e}")
            return None # Return None if creation failed
    return idf.getobject("SCHEDULETYPELIMITS", limits_name.upper())


def create_always_on_schedule(idf: IDF, sched_name: str = "AlwaysOnSched") -> Optional[Any]: # Return type hint Any or specific eppy/geomeppy type if known
    """
    Creates or retrieves a SCHEDULE:CONSTANT representing a value of 1.0 (Fraction).

    Args:
        idf: The geomeppy IDF object.
        sched_name: The desired name for the schedule.

    Returns:
        The schedule object or None if creation fails.
    """
    # Ensure the required ScheduleTypeLimits exists
    limits_obj = ensure_schedule_type_limits(idf, "Fraction", numeric_type="Continuous", unit_type="Dimensionless")
    if not limits_obj:
        print(f"[ERROR] Could not ensure ScheduleTypeLimits 'Fraction' for {sched_name}.")
        return None # Cannot create schedule without limits

    # Check if schedule already exists (case-insensitive check)
    existing = idf.getobject("SCHEDULE:CONSTANT", sched_name.upper())
    if existing:
        return existing

    try:
        schedule = idf.newidfobject("SCHEDULE:CONSTANT")
        schedule.Name = sched_name
        schedule.Schedule_Type_Limits_Name = "Fraction" # Reference the limits object
        schedule.Hourly_Value = 1.0
        return schedule
    except Exception as e:
        print(f"[ERROR] Failed to create SCHEDULE:CONSTANT {sched_name}: {e}")
        return None


def create_day_night_schedule(idf: IDF, sched_name: str = "VentSched_DayNight") -> Optional[Any]:
    """
    Creates or retrieves a SCHEDULE:COMPACT for Day/Night operation.
    Example: 0.5 fraction at night (22:00-06:00), 1.0 during the day (06:00-22:00).

    Args:
        idf: The geomeppy IDF object.
        sched_name: The desired name for the schedule.

    Returns:
        The schedule object or None if creation fails.
    """
    limits_obj = ensure_schedule_type_limits(idf, "Fraction", numeric_type="Continuous", unit_type="Dimensionless")
    if not limits_obj:
        print(f"[ERROR] Could not ensure ScheduleTypeLimits 'Fraction' for {sched_name}.")
        return None

    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    try:
        schedule = idf.newidfobject("SCHEDULE:COMPACT")
        schedule.Name = sched_name
        schedule.Schedule_Type_Limits_Name = "Fraction"

        # Define the schedule profile
        schedule.Field_1 = "Through: 12/31"     # Apply for the whole year
        schedule.Field_2 = "For: AllDays"        # Apply to all days
        schedule.Field_3 = "Until: 06:00,0.5"    # Value from midnight until 6:00 is 0.5
        schedule.Field_4 = "Until: 22:00,1.0"    # Value from 6:00 until 22:00 is 1.0
        schedule.Field_5 = "Until: 24:00,0.5"    # Value from 22:00 until midnight is 0.5
        return schedule
    except Exception as e:
        print(f"[ERROR] Failed to create SCHEDULE:COMPACT {sched_name}: {e}")
        return None


def create_workhours_schedule(idf: IDF, sched_name: str = "WorkHoursSched") -> Optional[Any]:
    """
    Creates or retrieves a SCHEDULE:COMPACT for typical Work Hours.
      - Weekdays: 0.2 (unoccupied), 1.0 (09:00-17:00), 0.2 (unoccupied)
      - Weekends/Holidays: 0.2 all day

    Args:
        idf: The geomeppy IDF object.
        sched_name: The desired name for the schedule.

    Returns:
        The schedule object or None if creation fails.
    """
    limits_obj = ensure_schedule_type_limits(idf, "Fraction", numeric_type="Continuous", unit_type="Dimensionless")
    if not limits_obj:
        print(f"[ERROR] Could not ensure ScheduleTypeLimits 'Fraction' for {sched_name}.")
        return None

    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    try:
        schedule = idf.newidfobject("SCHEDULE:COMPACT")
        schedule.Name = sched_name
        schedule.Schedule_Type_Limits_Name = "Fraction"

        # Define the schedule profile
        schedule.Field_1 = "Through: 12/31"                 # Apply for the whole year
        schedule.Field_2 = "For: Weekdays"                   # Rules for weekdays
        schedule.Field_3 = "Until: 09:00,0.2"                # Value until 9:00 is 0.2
        schedule.Field_4 = "Until: 17:00,1.0"                # Value until 17:00 is 1.0
        schedule.Field_5 = "Until: 24:00,0.2"                # Value until midnight is 0.2
        schedule.Field_6 = "For: Saturday Sunday Holiday"  # Rules for weekends/holidays
        schedule.Field_7 = "Until: 24:00,0.2"                # Value all day is 0.2
        return schedule
    except Exception as e:
        print(f"[ERROR] Failed to create SCHEDULE:COMPACT {sched_name}: {e}")
        return None


# Define type hint for the pattern tuples
SchedulePattern = List[Tuple[int, int, float]]

def create_schedule_from_pattern(
    idf: IDF,
    sched_name: str,
    pattern: SchedulePattern,
    schedule_type_limits: str = "Fraction"
) -> Optional[Any]:
    """
    Creates or retrieves a SCHEDULE:COMPACT from a single pattern applied to AllDays.

    Args:
        idf: geomeppy IDF instance.
        sched_name: Name for the schedule in EnergyPlus.
        pattern: List of (start_hour, end_hour, value) tuples defining the daily profile.
                 Hours are 0-24. The pattern should cover the full 24 hours.
                 Example: [(0, 6, 0.5), (6, 22, 1.0), (22, 24, 0.5)]
                 Note: start_hour is inclusive, end_hour is exclusive in pattern logic,
                       but for "Until: HH:MM,Value", HH:MM is the end time of the period.
        schedule_type_limits: Name of the ScheduleTypeLimits object (e.g., "Fraction").

    Returns:
        The schedule object or None if creation fails.
    """
    # Ensure the ScheduleTypeLimits object exists (e.g., "Fraction", "Temperature")
    # Determine unit_type for ensure_schedule_type_limits based on common schedule_type_limits names
    limit_unit_type = "Dimensionless" # Default for Fraction
    if schedule_type_limits.lower() == "temperature":
        limit_unit_type = "Temperature"
    elif schedule_type_limits.lower() == "on/off": # Or "Control Type"
        limit_unit_type = "Dimensionless" # Or a specific control type unit if defined
    # Add other common types as needed

    limits_obj = ensure_schedule_type_limits(idf, schedule_type_limits, unit_type=limit_unit_type) # Ensure limits exist
    if not limits_obj:
        print(f"[ERROR] Could not ensure ScheduleTypeLimits '{schedule_type_limits}' for {sched_name}.")
        return None

    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    if not pattern:
        print(f"[ERROR] Empty pattern provided for schedule {sched_name}. Cannot create.")
        return None

    try:
        sched_obj = idf.newidfobject("SCHEDULE:COMPACT")
        sched_obj.Name = sched_name
        sched_obj.Schedule_Type_Limits_Name = schedule_type_limits

        field_idx = 1
        sched_obj[f"Field_{field_idx}"] = "Through: 12/31"
        field_idx += 1
        sched_obj[f"Field_{field_idx}"] = "For: AllDays"
        field_idx += 1

        # Sort pattern by end_hour just in case, though E+ compact schedule fields are sequential.
        # The pattern [(0,6,0.5), (6,22,1.0), (22,24,0.5)] means:
        # Until 06:00, value is 0.5 (covers 00:00 to 06:00)
        # Until 22:00, value is 1.0 (covers 06:00 to 22:00)
        # Until 24:00, value is 0.5 (covers 22:00 to 24:00)
        sorted_pattern = sorted(pattern, key=lambda x: x[1]) # x[1] is end_hr

        last_pattern_end_hour = 0
        for (start_hr, end_hr, val) in sorted_pattern:
            # Basic validation for pattern elements
            if not (isinstance(start_hr, int) and isinstance(end_hr, int) and isinstance(val, (int, float))):
                print(f"[WARNING] Invalid data types in pattern segment ({start_hr}, {end_hr}, {val}) for {sched_name}. Skipping.")
                continue
            # Ensure chronological order and valid hour ranges (0-24 for end_hr)
            if end_hr <= last_pattern_end_hour or end_hr > 24 or start_hr < 0 or start_hr >= end_hr:
                print(f"[WARNING] Invalid time segment ({start_hr}-{end_hr}) in pattern for {sched_name}. Last end hour was {last_pattern_end_hour}. Skipping segment.")
                continue

            # Format "Until: HH:MM,Value"
            # Ensure HH is zero-padded if less than 10.
            line_str = f"Until: {end_hr:02d}:00,{val:.4f}" # Format value for consistency (e.g., 4 decimal places)
            
            # Dynamically assign fields; geomeppy/eppy usually handle field count limits.
            sched_obj[f"Field_{field_idx}"] = line_str
            field_idx += 1
            last_pattern_end_hour = end_hr

        # Check if the pattern covers the full 24 hours based on the last segment's end_hr.
        if last_pattern_end_hour < 24:
            print(f"[WARNING] Pattern for schedule {sched_name} does not cover until 24:00. Last segment ended at {last_pattern_end_hour}:00. EnergyPlus might fill with the last value or error.")

        return sched_obj
    except Exception as e:
        print(f"[ERROR] Failed to create SCHEDULE:COMPACT {sched_name} from pattern: {e}")
        return None

def create_schedule_from_weekday_weekend_pattern(
    idf: IDF,
    sched_name: str,
    weekday_pattern: SchedulePattern,
    weekend_pattern: SchedulePattern, # Can be the same as weekday_pattern if only one profile needed for all days
    schedule_type_limits="Fraction"
) -> Optional[Any]:
    """
    Creates or retrieves a SCHEDULE:COMPACT with different profiles for
    Weekdays and Weekends/Holidays.

    Args:
        idf: geomeppy IDF instance.
        sched_name: Name for the schedule in EnergyPlus.
        weekday_pattern: List of (start_hr, end_hr, value) for Weekdays.
        weekend_pattern: List of (start_hr, end_hr, value) for Sat/Sun/Holiday.
        schedule_type_limits: Name of the ScheduleTypeLimits object.

    Returns:
        The schedule object or None if creation fails.
    """
    limit_unit_type = "Dimensionless"
    if schedule_type_limits.lower() == "temperature": limit_unit_type = "Temperature"
    # Add more type mappings as needed

    limits_obj = ensure_schedule_type_limits(idf, schedule_type_limits, unit_type=limit_unit_type)
    if not limits_obj:
        print(f"[ERROR] Could not ensure ScheduleTypeLimits '{schedule_type_limits}' for {sched_name}.")
        return None

    existing = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing:
        return existing

    if not weekday_pattern or not weekend_pattern: # Both patterns must be provided
        print(f"[ERROR] Weekday or weekend pattern missing for schedule {sched_name}. Cannot create.")
        return None

    try:
        sched_obj = idf.newidfobject("SCHEDULE:COMPACT")
        sched_obj.Name = sched_name
        sched_obj.Schedule_Type_Limits_Name = schedule_type_limits

        field_idx = 1
        sched_obj[f"Field_{field_idx}"] = "Through: 12/31"
        field_idx += 1

        # --- Weekday Rules ---
        sched_obj[f"Field_{field_idx}"] = "For: Weekdays"
        field_idx += 1
        sorted_weekday = sorted(weekday_pattern, key=lambda x: x[1])
        last_end_hour_wd = 0
        for (start_hr, end_hr, val) in sorted_weekday:
            if not (isinstance(start_hr, int) and isinstance(end_hr, int) and isinstance(val, (int, float))): continue # Skip malformed
            if end_hr <= last_end_hour_wd or end_hr > 24 or start_hr < 0 or start_hr >= end_hr: continue # Basic validation
            sched_obj[f"Field_{field_idx}"] = f"Until: {end_hr:02d}:00,{val:.4f}"
            field_idx += 1
            last_end_hour_wd = end_hr
        if last_end_hour_wd < 24: print(f"[WARNING] Weekday pattern for {sched_name} doesn't cover 24h. Last segment ended at {last_end_hour_wd}:00.")

        # --- Weekend/Holiday Rules ---
        # Note: EnergyPlus allows "For: Weekends", "For: Holidays", "For: AllOtherDays" etc.
        # "Saturday Sunday Holiday" is a common combination.
        sched_obj[f"Field_{field_idx}"] = "For: Saturday Sunday Holiday"
        field_idx += 1
        sorted_weekend = sorted(weekend_pattern, key=lambda x: x[1])
        last_end_hour_we = 0
        for (start_hr, end_hr, val) in sorted_weekend:
            if not (isinstance(start_hr, int) and isinstance(end_hr, int) and isinstance(val, (int, float))): continue
            if end_hr <= last_end_hour_we or end_hr > 24 or start_hr < 0 or start_hr >= end_hr: continue # Basic validation
            sched_obj[f"Field_{field_idx}"] = f"Until: {end_hr:02d}:00,{val:.4f}"
            field_idx += 1
            last_end_hour_we = end_hr
        if last_end_hour_we < 24: print(f"[WARNING] Weekend pattern for {sched_name} doesn't cover 24h. Last segment ended at {last_end_hour_we}:00.")

        return sched_obj
    except Exception as e:
        print(f"[ERROR] Failed to create SCHEDULE:COMPACT {sched_name} from weekday/weekend patterns: {e}")
        return None


def ensure_dynamic_schedule(
    idf: IDF,
    sched_name: str,
    weekday_pattern: Optional[SchedulePattern] = None,
    weekend_pattern: Optional[SchedulePattern] = None, # If None, and weekday_pattern is given, could apply weekday to AllDays
    schedule_type_limits="Fraction"
) -> Optional[Any]:
    """
    Convenience function to create/retrieve a schedule:
      - If only weekday_pattern is provided (and weekend_pattern is None), applies it to AllDays.
      - If both weekday_pattern and weekend_pattern are provided, creates a Weekday/Weekend schedule.
      - If neither pattern is provided, falls back to creating an AlwaysOn schedule with the given sched_name.

    Args:
        idf: geomeppy IDF instance.
        sched_name: Desired name for the schedule.
        weekday_pattern: Optional pattern for weekdays.
        weekend_pattern: Optional pattern for weekends. If None, weekday_pattern is used for AllDays.
        schedule_type_limits: Name of the limits object.

    Returns:
        The created or retrieved schedule object, or None on failure.
    """
    # Check if schedule already exists (case-insensitive for both Compact and Constant)
    existing_compact = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if existing_compact:
        return existing_compact
    existing_constant = idf.getobject("SCHEDULE:CONSTANT", sched_name.upper())
    if existing_constant:
        # If a Constant schedule exists with this name:
        # - If no patterns were provided, this is the intended AlwaysOn, so return it.
        # - If patterns *were* provided, it's a conflict. Warn and return the Constant.
        if not weekday_pattern and not weekend_pattern: # No new pattern, existing constant is fine
            return existing_constant
        else: # New patterns provided, but a constant with same name exists.
            print(f"[WARNING] Dynamic patterns provided for '{sched_name}', but a SCHEDULE:CONSTANT with this name already exists. Returning the existing Constant schedule. Consider using a different name for the dynamic schedule.")
            return existing_constant

    # Create new schedule based on provided patterns
    if weekday_pattern and weekend_pattern:
        # Both weekday and weekend patterns are distinct
        return create_schedule_from_weekday_weekend_pattern(
            idf, sched_name, weekday_pattern, weekend_pattern, schedule_type_limits
        )
    elif weekday_pattern: # Only weekday pattern provided (weekend_pattern is None or implicitly same)
        # Apply weekday_pattern to AllDays
        return create_schedule_from_pattern(
            idf, sched_name, weekday_pattern, schedule_type_limits
        )
    else: # No patterns provided, fallback to AlwaysOn (or Always Off if value is 0)
        # This implies an "always 1.0" schedule if type limits are Fraction.
        # If a different constant value is needed, this function would need modification or
        # create_always_on_schedule would need a value parameter.
        print(f"[INFO] No patterns provided for '{sched_name}'. Falling back to creating/retrieving an AlwaysOn (value 1.0) schedule.")
        return create_always_on_schedule(idf, sched_name) # Assumes "Fraction" and value 1.0