# File: idf_objects/HVAC/schedule_creation.py
# Last Updated: 2025-05-01 (Based on discussions to handle lookup table format)

from typing import List, Tuple, Dict, Optional, Any
import traceback # For more detailed error logging

# Helper function to ensure time blocks are valid and formatted for IDF (WITHOUT trailing punctuation)
def _validate_and_format_until_blocks(
    blocks: Optional[List[Tuple[str, Any]]],
    default_value: float = 0.0
) -> List[str]:
    """
    Validates a list of (time, value) blocks, ensures it covers up to 24:00,
    and formats them into IDF 'Until: HH:MM,Value' strings (no trailing comma/semicolon).

    Args:
        blocks: List of (time_string, value) tuples, e.g., [("07:00", 20.0), ("22:00", 16.0)].
                Times should be sorted, ending <= 24:00. Can be None or empty.
        default_value: Value to use if blocks is None or empty.

    Returns:
        List of formatted strings like ["Until: 07:00,20.0", "Until: 22:00,16.0", "Until: 24:00,16.0"].
        Returns [f"Until: 24:00,{default_value_str}"] if input is empty or None.
    """
    # Format default value consistently
    try:
        # Format as float with reasonable precision, remove trailing zeros/decimal if integer
        default_value_str = f"{float(default_value):.3f}".rstrip('0').rstrip('.')
        if default_value_str == "-0": default_value_str = "0" # Handle negative zero
    except (ValueError, TypeError):
         default_value_str = str(default_value) # Keep as string if not convertible

    if not blocks:
        # If no blocks provided, assume default value applies all day
        return [f"Until: 24:00,{default_value_str}"]

    formatted_lines = []
    last_value = default_value # Initialize with default

    # Sort by time to ensure correct order (HH:MM format sorts correctly)
    try:
        # Filter out any potential None entries before sorting if they occur
        valid_blocks = [b for b in blocks if b is not None and isinstance(b, (list, tuple)) and len(b) == 2]
        if len(valid_blocks) != len(blocks):
             print(f"Warning: Invalid entries found in schedule blocks: {blocks}. Attempting to process valid entries.")
        if not valid_blocks: # If filtering removed everything
             return [f"Until: 24:00,{default_value_str}"]
        sorted_blocks = sorted(valid_blocks, key=lambda x: x[0])
    except (TypeError, IndexError) as e:
        print(f"Warning: Could not sort schedule blocks due to invalid data ({e}), proceeding anyway: {blocks}")
        sorted_blocks = valid_blocks # Proceed with original order if sorting fails

    last_time = "00:00"
    for i, block_item in enumerate(sorted_blocks):
        try:
            time_str, value = block_item
            if not isinstance(time_str, str) or ':' not in time_str or len(time_str) != 5:
                print(f"Warning: Invalid time format '{time_str}' in schedule block {block_item}. Skipping.")
                continue
            # Basic check for time order, more robust validation might be needed elsewhere
            if time_str <= last_time and last_time != "00:00":
                 print(f"Warning: Schedule block time '{time_str}' is not after previous '{last_time}'. Check schedule logic.")

            # Format value appropriately
            try:
                # Format as float with up to 3 decimal places, remove trailing stuff
                value_str = f"{float(value):.3f}".rstrip('0').rstrip('.')
                if value_str == "-0": value_str = "0"
            except (ValueError, TypeError):
                 value_str = str(value) # Keep non-numeric values as string

            # *** Store WITHOUT trailing comma/semicolon ***
            formatted_lines.append(f"Until: {time_str},{value_str}")
            last_value = value # Keep track of the last valid value
            last_time = time_str
        except (ValueError, TypeError, IndexError) as e:
             print(f"Warning: Skipping malformed schedule block {block_item} due to error: {e}")
             continue


    # Ensure the schedule goes until 24:00 if blocks were processed
    if formatted_lines and last_time < "24:00":
        # Use the value from the last specified block to extend to 24:00
        try:
            value_str = f"{float(last_value):.3f}".rstrip('0').rstrip('.')
            if value_str == "-0": value_str = "0"
        except (ValueError, TypeError):
             value_str = str(last_value)
        formatted_lines.append(f"Until: 24:00,{value_str}") # No trailing punctuation
    elif last_time > "24:00":
        print(f"Warning: Schedule block time '{last_time}' exceeds 24:00. IDF may error.")
    elif not formatted_lines: # Handle case where input 'blocks' was not empty but contained no valid entries
         return [f"Until: 24:00,{default_value_str}"]

    return formatted_lines


def create_or_update_time_block_schedule(
    idf,
    sched_name: str,
    schedule_type_limits: str,
    # --- Provide data for the day types you need ---
    weekday_blocks: Optional[List[Tuple[str, Any]]] = None,
    saturday_blocks: Optional[List[Tuple[str, Any]]] = None,
    sunday_blocks: Optional[List[Tuple[str, Any]]] = None,
    holiday_blocks: Optional[List[Tuple[str, Any]]] = None,
    summer_designday_blocks: Optional[List[Tuple[str, Any]]] = None,
    winter_designday_blocks: Optional[List[Tuple[str, Any]]] = None,
    # --- Alternatively, use weekend_blocks or allotherday_blocks ---
    weekend_blocks: Optional[List[Tuple[str, Any]]] = None, # If provided, typically overrides saturday/sunday
    allotherday_blocks: Optional[List[Tuple[str, Any]]] = None, # Catch-all for unspecified days
    # --- Control parameters ---
    default_value: float = 0.0, # Default value if a specific block list is empty/None
    bldg_id: Optional[int] = None,
    log_dict: Optional[Dict] = None,
    schedule_category: str = "General"
):
    """
    Creates or updates a SCHEDULE:COMPACT object in the IDF using provided time-value blocks
    for various day types. Relies on the IDF library (eppy) to add commas
    and only explicitly adds the final semicolon.

    Args:
       (Args remain the same as previous version)
    """
    # Retrieve or create the schedule object
    sched_obj = idf.getobject("SCHEDULE:COMPACT", sched_name.upper())
    if not sched_obj:
        sched_obj = idf.newidfobject("SCHEDULE:COMPACT")
        sched_obj.Name = sched_name
        print(f"[Schedule Creation] Created new SCHEDULE:COMPACT: {sched_name}")
    else:
        print(f"[Schedule Creation] Found existing SCHEDULE:COMPACT: {sched_name}, updating fields.")
        # Clear existing fields beyond Name and TypeLimits to avoid leftover data
        max_field_num = 0
        for i in range(1, 200): # Check a reasonable number of fields
             field_attr = f"Field_{i}"
             if hasattr(sched_obj, field_attr) and getattr(sched_obj, field_attr, None):
                 max_field_num = i
             elif not hasattr(sched_obj, field_attr): # Stop if attribute doesn't exist
                 break
        # Clear potentially unused fields by setting them to empty string
        for i in range(1, max_field_num + 1):
             field_attr = f"Field_{i}"
             try:
                 if hasattr(sched_obj, field_attr):
                     setattr(sched_obj, field_attr, '')
             except AttributeError:
                 pass

    sched_obj.Schedule_Type_Limits_Name = schedule_type_limits

    # --- Build the list of CORE IDF fields (without any trailing punctuation) ---
    core_idf_fields = []
    # Field_1: Through
    core_idf_fields.append("Through: 12/31")

    # Define the order and mapping from input blocks to IDF 'For:' specifiers
    day_block_map = [
        ("For: WeekDays", weekday_blocks),
        ("For: Saturday", saturday_blocks if not weekend_blocks else None),
        ("For: Sunday", sunday_blocks if not weekend_blocks else None),
        ("For: Saturday Sunday", weekend_blocks),
        ("For: Holiday", holiday_blocks),
        ("For: SummerDesignDay", summer_designday_blocks),
        ("For: WinterDesignDay", winter_designday_blocks),
        ("For: AllOtherDays", allotherday_blocks),
    ]

    processed_any_block = False
    active_day_types = []
    for for_specifier, block_list in day_block_map:
        if block_list is not None:
            # Special handling for weekend override
            if for_specifier == "For: Saturday Sunday" and weekend_blocks is None: continue
            if for_specifier == "For: Saturday" and weekend_blocks is not None: continue
            if for_specifier == "For: Sunday" and weekend_blocks is not None: continue

            # Check if list is empty after potential filtering/validation
            validated_formatted_untils = _validate_and_format_until_blocks(block_list, default_value)
            if not validated_formatted_untils:
                 print(f"[Schedule Creation Warning] No valid blocks generated for '{for_specifier}' in schedule '{sched_name}'. Skipping this day type.")
                 continue # Skip if validation resulted in nothing

            if not block_list: # Log if the input was empty but resulted in default
                 print(f"[Schedule Creation Debug] Empty block list provided for '{for_specifier}' in schedule '{sched_name}'. Applying default value '{default_value}'.")

            core_idf_fields.append(for_specifier) # Add the 'For:' line
            core_idf_fields.extend(validated_formatted_untils)
            processed_any_block = True
            active_day_types.append(for_specifier)

    if not processed_any_block:
        print(f"[Schedule Creation Warning] No valid schedule blocks provided or generated for '{sched_name}'. Applying default value '{default_value}' for AllDays.")
        core_idf_fields.append("For: AllDays")
        core_idf_fields.extend(_validate_and_format_until_blocks(None, default_value))
        active_day_types.append("For: AllDays")

    # --- Assign fields to the IDF object, adding final semicolon ONLY ---
    if not core_idf_fields:
         print(f"[Schedule Creation Error] No fields generated for schedule '{sched_name}'. Cannot set IDF object.")
         return

    num_fields = len(core_idf_fields)
    # print(f"[Schedule Creation Debug] Assigning {num_fields} core fields for {sched_name}") # Less verbose

    for i, field_value in enumerate(core_idf_fields):
        field_attr = f"Field_{i+1}"
        final_value = field_value

        if i == num_fields - 1:
            final_value += ";" # Add semicolon ONLY to the last field value

        try:
            if hasattr(sched_obj, field_attr):
                setattr(sched_obj, field_attr, final_value)
            else:
                print(f"[Schedule Creation Warning] Schedule object '{sched_name}' does not have attribute '{field_attr}'. Field not set.")
        except Exception as e:
            print(f"[Schedule Creation Error] Failed to set {field_attr} for schedule {sched_name} with value '{final_value}': {e}\n{traceback.format_exc()}")


    # --- Optional Logging ---
    if log_dict is not None and bldg_id is not None:
        if bldg_id not in log_dict: log_dict[bldg_id] = {}
        if "schedules" not in log_dict[bldg_id]: log_dict[bldg_id]["schedules"] = {}
        log_entry = {
            "category": schedule_category, "schedule_type_limits": schedule_type_limits,
            "idf_fields_generated": num_fields, "active_day_types": active_day_types
        }
        block_inputs = {
            "Weekday": weekday_blocks, "Saturday": saturday_blocks, "Sunday": sunday_blocks,
            "Holiday": holiday_blocks, "SummerDesignDay": summer_designday_blocks,
            "WinterDesignDay": winter_designday_blocks, "Weekend": weekend_blocks,
            "AllOtherDay": allotherday_blocks
        }
        for key, blocks in block_inputs.items():
             if blocks is not None: log_entry[f"{key}_blocks_input"] = blocks
        log_dict[bldg_id]["schedules"][sched_name] = log_entry


def convert_setpoint_mode_to_values(
    mode_blocks: Optional[List[Tuple[str, str]]], # Allow None input
    day_value: float = 20.0,
    night_value: float = 16.0,
) -> List[Tuple[str, float]]:
    """
    Takes a list like [("07:00","night"), ("19:00","day"), ("24:00","night")]
    and replaces "night"/"day" with numeric setpoint values.

    Returns default night value all day if input is None or empty or invalid.
    """
    output = []
    # Default blocks if input is invalid or empty
    default_output = [("24:00", night_value)]

    if not mode_blocks:
        # print("[Setpoint Conversion Debug] Received empty or None mode_blocks. Defaulting.")
        return default_output

    for block_item in mode_blocks:
        try:
            tm, mode = block_item
            # Basic validation
            if not isinstance(tm, str) or ':' not in tm or len(tm) != 5:
                 print(f"Warning: Skipping invalid time '{tm}' in mode block {block_item}")
                 continue

            mode_lower = mode.lower() if isinstance(mode, str) else ''
            if mode_lower == "day":
                val = day_value
            elif mode_lower == "night":
                val = night_value
            else:
                print(f"Warning: Unrecognized setpoint mode '{mode}' at time {tm}. Using night value '{night_value}'.")
                val = night_value
            output.append( (tm, val) )
        except (ValueError, TypeError, IndexError) as e:
             print(f"Warning: Skipping malformed mode block {block_item} due to error: {e}")
             continue

    if not output:
         print("[Setpoint Conversion Warning] No valid mode blocks found after processing. Defaulting.")
         return default_output

    return output

# --- Helper to generate standard mode blocks ---
def _generate_standard_mode_blocks(day_start: str, day_end: str) -> Optional[List[Tuple[str, str]]]:
    """Generates [(start, 'night'), (end, 'day'), ('24:00', 'night')] mode blocks."""
    try:
        # Basic validation
        if not (isinstance(day_start, str) and ':' in day_start and len(day_start) == 5 and
                isinstance(day_end, str) and ':' in day_end and len(day_end) == 5):
            raise ValueError("Invalid time format for day_start or day_end")

        if day_start == "00:00": # Avoid issues if day starts exactly at midnight
            if day_end == "24:00":
                 return [("24:00", "day")] # Day all day
            elif day_end == "00:00":
                 return [("24:00", "night")] # Night all day
            else:
                 # Start is 00:00, Day until day_end, then Night
                 return [(day_end, "day"), ("24:00", "night")]
        elif day_end == "24:00": # Day ends exactly at midnight
            # Night until day_start, then Day
            return [(day_start, "night"), ("24:00", "day")]
        elif day_start >= day_end: # Handles same time or overnight 'day' period incorrectly - simple approach: night all day
            print(f"Warning: day_start '{day_start}' >= day_end '{day_end}'. Assuming 'night' setpoint applies all day.")
            return [("24:00", "night")]
        else:
            # Standard pattern: Night until start, Day until end, Night after end
            return [(day_start, "night"), (day_end, "day"), ("24:00", "night")]
    except Exception as e:
        print(f"Error generating standard mode blocks for start='{day_start}', end='{day_end}': {e}")
        return None # Indicate failure


# --- Main function to create schedules ---
def create_schedules_for_building(
    idf,
    schedule_details: Dict[str, Any],
    building_id: Optional[int] = None,
    assigned_hvac_log: Optional[Dict] = None
):
    """
    Given 'schedule_details' (potentially from hvac_lookup and overrides),
    creates or updates SCHEDULE:COMPACT objects in the IDF.
    **Adapts to lookup format:** generates setpoint schedules from day_start/day_end,
    skips occupancy schedule creation if names are provided instead of blocks.

    Args:
       (Args remain the same)
    """
    if not schedule_details:
        print("[Schedule Creation Warning] create_schedules_for_building called with empty schedule_details.")
        return

    # --- Retrieve assigned numeric setpoints ---
    h_day, h_night, c_day, c_night = (20.0, 16.0, 25.0, 28.0) # Defaults
    if assigned_hvac_log and building_id in assigned_hvac_log:
        hvac_params = assigned_hvac_log[building_id].get("hvac_params", {})
        if hvac_params and isinstance(hvac_params, dict): # Check if params exist and is a dict
            h_day = hvac_params.get("heating_day_setpoint", h_day)
            h_night = hvac_params.get("heating_night_setpoint", h_night)
            c_day = hvac_params.get("cooling_day_setpoint", c_day)
            c_night = hvac_params.get("cooling_night_setpoint", c_night)

    # --- Define Default Design Day Blocks (using actual numbers) ---
    default_designday_on = [("24:00", 1.0)]
    default_designday_off = [("24:00", 0.0)]
    # Use generated setpoints for design day defaults
    default_designday_heat_setpoint = [("24:00", h_day)]
    default_designday_cool_setpoint = [("24:00", c_day)]
    # Default design day mode block assumes 'day' setpoint applies all day
    default_designday_mode_block = [("24:00", "day")]

    print(f"[Schedule Creation Info] Using Setpoints: H_day={h_day}, H_night={h_night}, C_day={c_day}, C_night={c_night}")

    # --- 1) HVAC Availability Schedule ---
    hvac_avail_info = schedule_details.get("hvac_availability")
    if hvac_avail_info and isinstance(hvac_avail_info, dict):
        # Determine Holiday Blocks: Use specific if provided, else default to weekend blocks
        default_holiday_hvac = hvac_avail_info.get("weekend") if isinstance(hvac_avail_info.get("weekend"), list) else None
        holiday_blocks_hvac = hvac_avail_info.get("holiday", default_holiday_hvac)

        create_or_update_time_block_schedule(
            idf,
            sched_name=hvac_avail_info.get("schedule_name", "HVAC_Avail_Sched"),
            schedule_type_limits="Fraction",
            weekday_blocks=hvac_avail_info.get("weekday"),
            saturday_blocks=hvac_avail_info.get("saturday"),
            sunday_blocks=hvac_avail_info.get("sunday"),
            holiday_blocks=holiday_blocks_hvac, # Pass determined holiday blocks
            summer_designday_blocks=hvac_avail_info.get("summer_designday", default_designday_on),
            winter_designday_blocks=hvac_avail_info.get("winter_designday", default_designday_on),
            weekend_blocks=hvac_avail_info.get("weekend"),
            allotherday_blocks=hvac_avail_info.get("allotherday"),
            default_value=0.0,
            bldg_id=building_id, log_dict=assigned_hvac_log, schedule_category="HVAC Availability"
        )
    else:
        print("[Schedule Creation Warning] 'hvac_availability' details missing or invalid. Skipping HVAC Availability schedule.")


    # --- 2) Setpoint Schedules (Heating / Cooling) ---
    # *** MODIFIED SECTION ***
    setpoints_info = schedule_details.get("setpoints")
    if setpoints_info and isinstance(setpoints_info, dict):
        heat_sched_name = setpoints_info.get("schedule_name_heat", "ZONE_HEATING_SETPOINTS")
        cool_sched_name = setpoints_info.get("schedule_name_cool", "ZONE_COOLING_SETPOINTS")

        # Get day_start and day_end times from lookup data
        day_start = setpoints_info.get("day_start")
        day_end = setpoints_info.get("day_end")

        if day_start and day_end:
            print(f"[Schedule Creation Info] Generating setpoint schedules '{heat_sched_name}', '{cool_sched_name}' using DayStart={day_start}, DayEnd={day_end}")
            # Generate the standard mode blocks based on start/end times
            standard_mode_blocks = _generate_standard_mode_blocks(day_start, day_end)

            if standard_mode_blocks:
                # Assume standard blocks apply to Weekday, Saturday, Sunday, Holiday unless overridden
                # (Lookup doesn't provide overrides, so we use the standard blocks for these)
                weekday_mode_blocks = standard_mode_blocks
                saturday_mode_blocks = standard_mode_blocks
                sunday_mode_blocks = standard_mode_blocks
                holiday_mode_blocks = standard_mode_blocks
                # Use default 'day' mode for design days
                summer_designday_mode_blocks = default_designday_mode_block
                winter_designday_mode_blocks = default_designday_mode_block

                # Convert generated mode blocks to numeric value blocks
                weekday_shape_heat = convert_setpoint_mode_to_values(weekday_mode_blocks, h_day, h_night)
                saturday_shape_heat = convert_setpoint_mode_to_values(saturday_mode_blocks, h_day, h_night)
                sunday_shape_heat = convert_setpoint_mode_to_values(sunday_mode_blocks, h_day, h_night)
                holiday_shape_heat = convert_setpoint_mode_to_values(holiday_mode_blocks, h_day, h_night)
                summer_designday_heat = convert_setpoint_mode_to_values(summer_designday_mode_blocks, h_day, h_night)
                winter_designday_heat = convert_setpoint_mode_to_values(winter_designday_mode_blocks, h_day, h_night)

                weekday_shape_cool = convert_setpoint_mode_to_values(weekday_mode_blocks, c_day, c_night)
                saturday_shape_cool = convert_setpoint_mode_to_values(saturday_mode_blocks, c_day, c_night)
                sunday_shape_cool = convert_setpoint_mode_to_values(sunday_mode_blocks, c_day, c_night)
                holiday_shape_cool = convert_setpoint_mode_to_values(holiday_mode_blocks, c_day, c_night)
                summer_designday_cool = convert_setpoint_mode_to_values(summer_designday_mode_blocks, c_day, c_night)
                winter_designday_cool = convert_setpoint_mode_to_values(winter_designday_mode_blocks, c_day, c_night)

                # Create Heating Setpoint Schedule using GENERATED value blocks
                create_or_update_time_block_schedule(
                    idf, sched_name=heat_sched_name, schedule_type_limits="Temperature",
                    weekday_blocks=weekday_shape_heat,
                    saturday_blocks=saturday_shape_heat,
                    sunday_blocks=sunday_shape_heat,
                    holiday_blocks=holiday_shape_heat,
                    summer_designday_blocks=summer_designday_heat,
                    winter_designday_blocks=winter_designday_heat,
                    # No weekend_blocks override needed as Sat/Sun are explicitly generated
                    # No allotherday_blocks generated by default from start/end times
                    default_value=h_night, # Fallback default value
                    bldg_id=building_id, log_dict=assigned_hvac_log, schedule_category="Heating Setpoints"
                )

                # Create Cooling Setpoint Schedule using GENERATED value blocks
                create_or_update_time_block_schedule(
                    idf, sched_name=cool_sched_name, schedule_type_limits="Temperature",
                    weekday_blocks=weekday_shape_cool,
                    saturday_blocks=saturday_shape_cool,
                    sunday_blocks=sunday_shape_cool,
                    holiday_blocks=holiday_shape_cool,
                    summer_designday_blocks=summer_designday_cool,
                    winter_designday_blocks=winter_designday_cool,
                    default_value=c_night,
                    bldg_id=building_id, log_dict=assigned_hvac_log, schedule_category="Cooling Setpoints"
                )
            else:
                 print(f"[Schedule Creation Error] Could not generate valid mode blocks for setpoints using start='{day_start}', end='{day_end}'. Skipping setpoint schedule creation.")
        else:
            print(f"[Schedule Creation Warning] 'day_start' or 'day_end' missing in setpoints_info for schedules '{heat_sched_name}', '{cool_sched_name}'. Skipping setpoint schedule creation.")
    else:
        print("[Schedule Creation Warning] 'setpoints' details missing or invalid. Skipping setpoint schedule creation.")


    # --- 3) Occupancy Schedule ---
    # *** MODIFIED SECTION ***
    occupancy_info = schedule_details.get("occupancy")
    if occupancy_info and isinstance(occupancy_info, dict):
        weekday_occ_data = occupancy_info.get("weekday")
        weekend_occ_data = occupancy_info.get("weekend") # Lookup uses 'weekend' key

        # Check if the data looks like schedule names (strings) rather than blocks (lists)
        if isinstance(weekday_occ_data, str) and isinstance(weekend_occ_data, str):
            print(f"[Schedule Creation Info] Occupancy details refer to existing schedules: Weekday='{weekday_occ_data}', Weekend='{weekend_occ_data}'.")
            print("  Skipping creation of a new 'Occupancy_Sched'. Ensure these named schedules exist in the IDF.")
            # *** DO NOTHING - Do not create the schedule ***
            # Log this information if needed
            if log_dict is not None and bldg_id is not None:
                 if bldg_id not in log_dict: log_dict[bldg_id] = {}
                 if "schedules" not in log_dict[bldg_id]: log_dict[bldg_id]["schedules"] = {}
                 log_dict[bldg_id]["schedules"]["Occupancy_Sched_INFO"] = { # Use different key to avoid conflict
                     "status": "Skipped Creation - Referred to existing schedules",
                     "weekday_schedule_name": weekday_occ_data,
                     "weekend_schedule_name": weekend_occ_data,
                 }

        elif isinstance(weekday_occ_data, list) and isinstance(weekend_occ_data, list):
            # If data is unexpectedly provided as blocks, try to process it
            print("[Schedule Creation Warning] Occupancy details unexpectedly contain block data instead of names. Attempting to create 'Occupancy_Sched'.")
            # Determine Holiday Blocks: Default to weekend if specific not given
            default_holiday_occ = occupancy_info.get("weekend") if isinstance(occupancy_info.get("weekend"), list) else None
            holiday_blocks_occ = occupancy_info.get("holiday", default_holiday_occ)

            create_or_update_time_block_schedule(
                idf, sched_name=occupancy_info.get("schedule_name", "Occupancy_Sched"), schedule_type_limits="Fraction",
                weekday_blocks=weekday_occ_data, # Use the provided block data
                saturday_blocks=occupancy_info.get("saturday"), # Might be None
                sunday_blocks=occupancy_info.get("sunday"), # Might be None
                holiday_blocks=holiday_blocks_occ,
                summer_designday_blocks=occupancy_info.get("summer_designday", default_designday_off),
                winter_designday_blocks=occupancy_info.get("winter_designday", default_designday_off),
                weekend_blocks=weekend_occ_data, # Use the provided block data
                allotherday_blocks=occupancy_info.get("allotherday"),
                default_value=0.0,
                bldg_id=building_id, log_dict=assigned_hvac_log, schedule_category="Occupancy"
            )
        else:
            # Handle mixed types or other invalid formats
            print(f"[Schedule Creation Warning] Occupancy details format is unrecognized (weekday='{type(weekday_occ_data)}', weekend='{type(weekend_occ_data)}'). Skipping Occupancy schedule processing.")

    else:
        print("[Schedule Creation Warning] 'occupancy' details missing or invalid. Skipping Occupancy schedule processing.")


    # --- 4) Add other schedules (e.g., Ventilation, Infiltration) as needed ---
    # Follow the same pattern: get info, check format, define defaults, call create_or_update_time_block_schedule

    print(f"[Schedule Creation] Finished schedule creation/update for building {building_id or 'N/A'}.")