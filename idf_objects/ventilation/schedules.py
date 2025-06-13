# ventilation/schedules.py

import random
import math # For isnan checks if needed
from typing import List, Tuple, Optional, Any, Dict

# Import IDF class for type hinting (assuming geomeppy is used)
try:
    from geomeppy import IDF
except ImportError:
    IDF = Any # Fallback if geomeppy not available

# Import the new schedule patterns lookup
try:
    from .schedule_lookup import SCHEDULE_LOOKUP
except ImportError:
    print("[ERROR] schedules.py: Could not import SCHEDULE_LOOKUP from .schedule_lookup. Ensure the file exists and is correct.")
    SCHEDULE_LOOKUP: Dict = {} # Provide an empty dict to avoid crashes, but functionality will be limited


# Type alias for chosen schedule patterns (with single values)
ChosenSchedulePattern = List[Tuple[int, int, float]]
# Type alias for ranged schedule patterns from the lookup
RangedSchedulePattern = List[Tuple[int, int, Tuple[float, float]]]


def ensure_schedule_type_limits(idf: IDF, limits_name: str, numeric_type: str = "Continuous", unit_type: Optional[str] = None) -> Optional[Any]:
    """
    Checks if ScheduleTypeLimits exists in the IDF, creates it if not.

    Args:
        idf: The geomeppy IDF object.
        limits_name: The name for the ScheduleTypeLimits object (e.g., "Fraction", "Temperature").
        numeric_type: The numeric type for the limits (e.g., "Continuous", "Discrete").
        unit_type: The unit type for the limits (e.g., "Dimensionless", "Temperature").

    Returns:
        The ScheduleTypeLimits object or None if creation fails.
    """
    if not idf.getobject("SCHEDULETYPELIMITS", limits_name.upper()):
        print(f"[INFO] schedules.py: Creating ScheduleTypeLimits: {limits_name}")
        try:
            lims = idf.newidfobject("SCHEDULETYPELIMITS", Name=limits_name)
            lims.Numeric_Type = numeric_type
            if unit_type:
                lims.Unit_Type = unit_type
            # EnergyPlus defaults for Lower/Upper Limit Value are often sufficient.
            # For "Fraction", common limits are 0.0 and 1.0.
            if limits_name.lower() == "fraction":
                 if not hasattr(lims, 'Lower_Limit_Value') or lims.Lower_Limit_Value == "":
                     lims.Lower_Limit_Value = 0.0
                 if not hasattr(lims, 'Upper_Limit_Value') or lims.Upper_Limit_Value == "":
                     lims.Upper_Limit_Value = 1.0
            return lims
        except Exception as e:
            print(f"[ERROR] schedules.py: Failed to create SCHEDULETYPELIMITS {limits_name}: {e}")
            return None
    return idf.getobject("SCHEDULETYPELIMITS", limits_name.upper())


def create_always_on_schedule(idf: IDF, sched_name: str = "AlwaysOnSched") -> Optional[Any]:
    """
    Creates or retrieves a SCHEDULE:CONSTANT representing a value of 1.0,
    typically used for "Fraction" type limits.

    Args:
        idf: The geomeppy IDF object.
        sched_name: The desired name for the schedule.

    Returns:
        The SCHEDULE:CONSTANT object or None if creation fails.
    """
    limits_obj = ensure_schedule_type_limits(idf, "Fraction", unit_type="Dimensionless")
    if not limits_obj:
        print(f"[ERROR] schedules.py: Could not ensure ScheduleTypeLimits 'Fraction' for {sched_name}.")
        return None

    existing = idf.getobject("SCHEDULE:CONSTANT", sched_name.upper())
    if existing:
        return existing

    try:
        schedule = idf.newidfobject("SCHEDULE:CONSTANT", Name=sched_name)
        schedule.Schedule_Type_Limits_Name = "Fraction"
        schedule.Hourly_Value = 1.0
        return schedule
    except Exception as e:
        print(f"[ERROR] schedules.py: Failed to create SCHEDULE:CONSTANT {sched_name}: {e}")
        return None


def _pick_value_from_range(value_range: Tuple[float, float], strategy: str) -> float:
    """
    Helper to pick a single value from a (min_val, max_val) range based on strategy.
    """
    min_v, max_v = value_range
    if not (isinstance(min_v, (int, float)) and isinstance(max_v, (int, float))):
        print(f"[WARNING] schedules.py: Invalid range encountered: ({min_v}, {max_v}). Defaulting to 0.0.")
        return 0.0
    if math.isnan(min_v) or math.isnan(max_v):
        print(f"[WARNING] schedules.py: NaN in range tuple ({min_v}, {max_v}). Defaulting to 0.0.")
        return 0.0
    if min_v > max_v:
        print(f"[WARNING] schedules.py: Min value > Max value in range ({min_v}, {max_v}). Using min value.")
        max_v = min_v

    if strategy == "B":  # Random
        return random.uniform(min_v, max_v)
    elif strategy == "C":  # Minimum
        return min_v
    # Default to "A" (Midpoint) or if strategy is unknown
    if strategy != "A":
        print(f"[WARNING] schedules.py: Unknown pick strategy '{strategy}'. Defaulting to Midpoint.")
    return (min_v + max_v) / 2.0


def get_or_create_archetype_schedule(
    idf: IDF,
    target_schedule_name: str,
    building_function: str,
    archetype_key: str,
    purpose: str,  # 'ventilation' or 'infiltration'
    strategy: str,
    schedule_type_limits_name: str = "Fraction"
) -> Tuple[Optional[Any], Optional[ChosenSchedulePattern], Optional[ChosenSchedulePattern]]:
    """
    Retrieves or creates an archetype-specific SCHEDULE:COMPACT object.

    This function looks up ranged patterns from SCHEDULE_LOOKUP, picks values
    based on the strategy, creates the schedule if it doesn't exist, and
    returns the schedule object along with the chosen patterns (for logging).

    Args:
        idf: The geomeppy IDF object.
        target_schedule_name: The desired unique name for the schedule.
        building_function: E.g., 'residential', 'non_residential'.
        archetype_key: E.g., 'Apartment', 'Office Function', or 'default'.
        purpose: E.g., 'ventilation', 'infiltration'.
        strategy: Value picking strategy ('A', 'B', 'C').
        schedule_type_limits_name: Name of the ScheduleTypeLimits object.

    Returns:
        A tuple: (schedule_object, chosen_weekday_pattern, chosen_weekend_pattern).
        Patterns are None if the schedule already existed or creation failed.
    """
    # FIX for VENT_003: Add debug logging for schedule creation
    print(f"[SCHEDULE DEBUG] Creating schedule '{target_schedule_name}' for {building_function}/{archetype_key}/{purpose} with strategy {strategy}")
    
    # Ensure the ScheduleTypeLimits object exists
    unit_type = "Dimensionless" if schedule_type_limits_name.lower() == "fraction" else None
    if schedule_type_limits_name.lower() == "temperature":
        unit_type = "Temperature"

    limits_obj = ensure_schedule_type_limits(idf, schedule_type_limits_name, unit_type=unit_type)
    if not limits_obj:
        print(f"[ERROR] schedules.py: Could not ensure ScheduleTypeLimits '{schedule_type_limits_name}' for {target_schedule_name}.")
        return None, None, None

    # Check if schedule already exists
    existing_sched = idf.getobject("SCHEDULE:COMPACT", target_schedule_name.upper()) or \
                     idf.getobject("SCHEDULE:CONSTANT", target_schedule_name.upper())
    if existing_sched:
        print(f"[INFO] schedules.py: Schedule '{target_schedule_name}' already exists. Using existing.")
        return existing_sched, None, None # Cannot return chosen patterns if it already existed

    # 1. Look up the ranged patterns from SCHEDULE_LOOKUP
    if not SCHEDULE_LOOKUP:
        print(f"[ERROR] schedules.py: SCHEDULE_LOOKUP is empty. Cannot create archetype schedule {target_schedule_name}.")
        return None, None, None

    func_patterns = SCHEDULE_LOOKUP.get(building_function, {})
    archetype_patterns = func_patterns.get(archetype_key, func_patterns.get("default", {}))
    purpose_patterns = archetype_patterns.get(purpose, {})

    if not purpose_patterns:
        # FIX for VENT_003: Log when no patterns found
        print(f"[WARNING] schedules.py: No specific pattern for '{building_function}/{archetype_key}/{purpose}'. "
              f"Creating AlwaysOn schedule named '{target_schedule_name}'.")
        sched = create_always_on_schedule(idf, target_schedule_name)
        # Return a representative "chosen" pattern for AlwaysOn
        always_on_pattern: ChosenSchedulePattern = [(0, 24, 1.0)]
        return sched, always_on_pattern, always_on_pattern

    ranged_weekday_pattern: Optional[RangedSchedulePattern] = purpose_patterns.get("weekday")
    ranged_weekend_pattern: Optional[RangedSchedulePattern] = purpose_patterns.get("weekend")
    ranged_allday_pattern: Optional[RangedSchedulePattern] = purpose_patterns.get("allday")

    if ranged_allday_pattern:
        ranged_weekday_pattern = ranged_allday_pattern
        ranged_weekend_pattern = ranged_allday_pattern
    
    if not ranged_weekday_pattern or not ranged_weekend_pattern:
        print(f"[ERROR] schedules.py: Incomplete ranged patterns for {target_schedule_name} "
              f"({building_function}/{archetype_key}/{purpose}). Weekday/Allday and Weekend/Allday must be defined.")
        # Fallback to AlwaysOn if patterns are malformed in lookup
        sched = create_always_on_schedule(idf, target_schedule_name)
        always_on_pattern = [(0, 24, 1.0)]
        return sched, always_on_pattern, always_on_pattern
    
    # FIX for VENT_003: Log found patterns
    print(f"[SCHEDULE DEBUG] Found patterns: weekday={bool(ranged_weekday_pattern)}, weekend={bool(ranged_weekend_pattern)}")

    # 2. Convert ranged patterns to chosen patterns using strategy
    chosen_weekday_pattern: ChosenSchedulePattern = []
    for start_hr, end_hr, value_range in ranged_weekday_pattern:
        chosen_value = _pick_value_from_range(value_range, strategy)
        chosen_weekday_pattern.append((start_hr, end_hr, chosen_value))

    chosen_weekend_pattern: ChosenSchedulePattern = []
    for start_hr, end_hr, value_range in ranged_weekend_pattern:
        chosen_value = _pick_value_from_range(value_range, strategy)
        chosen_weekend_pattern.append((start_hr, end_hr, chosen_value))

    # 3. Create the SCHEDULE:COMPACT object
    try:
        sched_obj = idf.newidfobject("SCHEDULE:COMPACT", Name=target_schedule_name)
        sched_obj.Schedule_Type_Limits_Name = schedule_type_limits_name
        
        field_idx = 1
        sched_obj[f"Field_{field_idx}"] = "Through: 12/31"
        field_idx += 1

        # --- Weekday Rules ---
        sched_obj[f"Field_{field_idx}"] = "For: Weekdays SummerDesignDay WinterDesignDay" # Apply to design days as well
        field_idx += 1
        # Sort by end_hour for correct SCHEDULE:COMPACT format
        sorted_chosen_weekday = sorted(chosen_weekday_pattern, key=lambda x: x[1])
        last_wd_end_hour = 0
        for _, end_hr, val in sorted_chosen_weekday:
            if end_hr <= last_wd_end_hour: continue # Skip redundant/overlapping segments
            sched_obj[f"Field_{field_idx}"] = f"Until: {end_hr:02d}:00,{val:.4f}"
            field_idx += 1
            last_wd_end_hour = end_hr
        if last_wd_end_hour < 24 and sorted_chosen_weekday: # Ensure it covers 24h if pattern exists
            # Fill the gap with the last value if not explicitly 24:00
             sched_obj[f"Field_{field_idx}"] = f"Until: 24:00,{sorted_chosen_weekday[-1][2]:.4f}"
             field_idx += 1


        # --- Weekend/Holiday Rules ---
        sched_obj[f"Field_{field_idx}"] = "For: Saturday Sunday Holiday AllOtherDays"
        field_idx += 1
        sorted_chosen_weekend = sorted(chosen_weekend_pattern, key=lambda x: x[1])
        last_we_end_hour = 0
        for _, end_hr, val in sorted_chosen_weekend:
            if end_hr <= last_we_end_hour: continue # Skip redundant/overlapping segments
            sched_obj[f"Field_{field_idx}"] = f"Until: {end_hr:02d}:00,{val:.4f}"
            field_idx += 1
            last_we_end_hour = end_hr
        if last_we_end_hour < 24 and sorted_chosen_weekend: # Ensure it covers 24h if pattern exists
             sched_obj[f"Field_{field_idx}"] = f"Until: 24:00,{sorted_chosen_weekend[-1][2]:.4f}"
             field_idx += 1
        
        print(f"[INFO] schedules.py: Created archetype schedule '{target_schedule_name}'.")
        return sched_obj, chosen_weekday_pattern, chosen_weekend_pattern

    except Exception as e:
        print(f"[ERROR] schedules.py: Failed to create SCHEDULE:COMPACT {target_schedule_name} from archetype patterns: {e}")
        # Attempt to create a fallback AlwaysOn schedule to prevent downstream errors
        fallback_sched = create_always_on_schedule(idf, target_schedule_name + "_fallback_AlwaysOn")
        if fallback_sched:
            print(f"[WARNING] schedules.py: Created fallback AlwaysOn schedule: {fallback_sched.Name}")
            always_on_pattern = [(0, 24, 1.0)]
            return fallback_sched, always_on_pattern, always_on_pattern
        return None, None, None

# Note: create_day_night_schedule and create_workhours_schedule can be kept for legacy use
# or if a user explicitly wants these very generic schedules via overrides.
# They are not part of the primary archetype-based schedule creation flow anymore.