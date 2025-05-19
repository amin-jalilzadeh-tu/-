# ventilation/assign_ventilation_values.py

import random
import math # Import math for isnan check
from .ventilation_lookup import ventilation_lookup # Assuming ventilation_lookup is in the same directory

def find_vent_overrides(
    building_id,
    building_function,
    age_range,
    scenario,
    calibration_stage,
    user_config
):
    """
    Searches a user_config list/dict for any override entries matching the
    building_id, building_function, age_range, scenario, and calibration_stage.
    Returns a list of matching dict rows.

    Each 'row' in user_config can specify:
      - "building_id"
      - "building_function"
      - "age_range"
      - "scenario"
      - "calibration_stage"
      - plus override fields for infiltration_base, year_factor, system_type,
        fan_pressure, f_ctrl, hrv_eff, schedule names, etc. using either
        "fixed_value" or ("min_val", "max_val").

    If any of the filtering fields (building_id, function, age, scenario, stage)
    are present in the row and do not match the current building, that row is skipped.
    Otherwise, the row is considered a match and is returned in the list.
    """
    matches = []
    if not user_config: # Handle empty or None user_config
        return matches

    for row in user_config:
        # Ensure row is a dictionary
        if not isinstance(row, dict):
            continue

        # Check filters - skip if a filter exists and doesn't match
        if "building_id" in row and row["building_id"] != building_id:
            continue
        if "building_function" in row and row["building_function"] != building_function:
            continue
        if "age_range" in row and row["age_range"] != age_range:
            continue
        if "scenario" in row and row["scenario"] != scenario:
            continue
        if "calibration_stage" in row and row["calibration_stage"] != calibration_stage:
            continue

        # If all present filters match, add the row
        matches.append(row)

    return matches


def pick_val_with_range(
    rng_tuple,
    strategy="A",
    log_dict=None,
    param_name=None
):
    """
    Selects a value from a (min_val, max_val) range based on the strategy.

    Args:
        rng_tuple (tuple or None): (min_val, max_val) or None.
        strategy (str): "A"=>midpoint, "B"=>random uniform, "C"=>min.
        log_dict (dict, optional): Dictionary to store final picks if provided.
        param_name (str, optional): Name of the parameter (e.g., "infiltration_base") for logging.

    Returns:
        float: The chosen numeric value. Logs range and pick if log_dict provided.
    """
    if rng_tuple is None or len(rng_tuple) != 2:
        chosen = 0.0 # Default fallback
        min_v, max_v = 0.0, 0.0
    else:
        min_v, max_v = rng_tuple
        # Ensure numeric types
        try:
            min_v = float(min_v)
            max_v = float(max_v)
        except (ValueError, TypeError):
             print(f"[WARNING] Invalid range values in tuple {rng_tuple} for {param_name}. Defaulting to 0.")
             min_v, max_v = 0.0, 0.0

        # Ensure min <= max
        if min_v > max_v:
             print(f"[WARNING] Min value > Max value in range {rng_tuple} for {param_name}. Using min value.")
             max_v = min_v # Or swap them: min_v, max_v = max_v, min_v

        # Pick final value based on strategy
        if strategy == "A": # Midpoint
            chosen = (min_v + max_v) / 2.0
        elif strategy == "B": # Random
            chosen = random.uniform(min_v, max_v)
        elif strategy == "C": # Minimum
            chosen = min_v
        else: # Default fallback to Minimum
            chosen = min_v

    # Log if requested
    if log_dict is not None and param_name:
        log_dict[f"{param_name}_range"] = (min_v, max_v)
        log_dict[param_name] = chosen

    return chosen


def override_range(current_range, row):
    """
    Applies overrides from a user config row to a parameter's (min, max) range.

    If row has 'fixed_value', convert it to (val, val).
    If row has 'min_val' and 'max_val', return that tuple.
    Otherwise return current_range.
    """
    if "fixed_value" in row:
        val = row["fixed_value"]
        try:
            # Attempt to convert to float, handle potential errors
            f = float(val)
            if math.isnan(f): # Check for NaN explicitly
                 print(f"[WARNING] Override 'fixed_value' {val} is NaN for {row.get('param_name')}. Using current range {current_range}.")
                 return current_range
            return (f, f)
        except (ValueError, TypeError):
            # If conversion fails (e.g., non-numeric string), keep original range
             print(f"[WARNING] Could not convert override 'fixed_value' {val} to float for {row.get('param_name')}. Using current range {current_range}.")
             return current_range
    elif "min_val" in row and "max_val" in row:
         try:
             min_ovr = float(row["min_val"])
             max_ovr = float(row["max_val"])
             if math.isnan(min_ovr) or math.isnan(max_ovr):
                  raise ValueError("Override range contains NaN")
             # Basic validation: min <= max
             if min_ovr > max_ovr:
                  print(f"[WARNING] Override min_val > max_val for {row.get('param_name')}. Using min_val for both.")
                  return (min_ovr, min_ovr)
             return (min_ovr, max_ovr)
         except (ValueError, TypeError):
             print(f"[WARNING] Could not convert override range ({row['min_val']}, {row['max_val']}) to floats for {row.get('param_name')}. Using current range {current_range}.")
             return current_range
    # If no valid override found in the row, return the original range
    return current_range


def assign_ventilation_params_with_overrides(
    building_id=None,
    building_function="residential",
    age_range="2015 and later",
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",           # "A" => midpoint, "B" => random, "C" => min, etc.
    random_seed=None,
    user_config_vent=None,      # List of user override dicts
    assigned_vent_log=None,     # Optional dict to store final building-level picks
    infiltration_key=None,      # e.g. "Corner House" or "Office Function"
    year_key=None,              # e.g. "1975 - 1991"
    is_residential=True,
    default_flow_exponent=0.67
):
    """
    Determines ventilation parameters based on lookups and user overrides.

    Returns a dictionary containing the final selected parameter values and their source ranges.

    Steps:
      1) Look up default ranges from ventilation_lookup based on scenario and stage.
      2) Apply user overrides found via find_vent_overrides.
      3) Use 'strategy' (via pick_val_with_range) to select final numeric values.
      4) Determine final system type and schedule names.
      5) Assemble and return the final dictionary of assigned parameters.
      6) Optionally log the assigned parameters to assigned_vent_log.
    """
    if random_seed is not None:
        random.seed(random_seed)

    # --- 1) Get Base Parameter Ranges from Lookup ---
    try:
        if scenario not in ventilation_lookup:
            print(f"[WARNING] Scenario '{scenario}' not found in ventilation_lookup. Defaulting to 'scenario1'.")
            scenario = "scenario1"
        if calibration_stage not in ventilation_lookup[scenario]:
            print(f"[WARNING] Calibration stage '{calibration_stage}' not found for scenario '{scenario}'. Defaulting to 'pre_calibration'.")
            calibration_stage = "pre_calibration"
        stage_dict = ventilation_lookup[scenario][calibration_stage]
    except KeyError as e:
        raise ValueError(f"Error accessing ventilation_lookup for scenario='{scenario}', stage='{calibration_stage}'. Missing key: {e}")
    except TypeError:
         raise ValueError(f"Error accessing ventilation_lookup. Ensure it's a correctly structured dictionary.")


    # Initialize parameters with defaults or lookups
    infiltration_base_rng = (0.0, 0.0) # Default empty range
    year_factor_rng = (1.0, 1.0)      # Default no factor
    fan_pressure_rng = (0.0, 0.0)     # Default no pressure
    f_ctrl_rng = (1.0, 1.0)           # Default no control factor
    hrv_eff_rng = (0.0, 0.0)          # Default no HRV
    system_type_final = "A" if is_residential else "D" # Default system types
    infiltration_sched_name = "AlwaysOnSched" # Default schedule
    ventilation_sched_name = "VentSched_DayNight" if is_residential else "WorkHoursSched" # Default schedules

    # Lookup infiltration range based on function and key
    try:
        if is_residential:
            res_infil = stage_dict.get("residential_infiltration_range", {})
            infiltration_base_rng = res_infil.get(infiltration_key, (1.0, 1.0)) # Use a default range if key not found
            sys_ctrl_ranges = stage_dict.get("system_control_range_res", {})
        else:
            nonres_infil = stage_dict.get("non_res_infiltration_range", {})
            infiltration_base_rng = nonres_infil.get(infiltration_key, (0.5, 0.5)) # Use a default range
            sys_ctrl_ranges = stage_dict.get("system_control_range_nonres", {})
    except Exception as e:
         print(f"[WARNING] Error getting infiltration/control ranges from lookup: {e}. Using defaults.")
         sys_ctrl_ranges = {} # Ensure it's a dict

    # Lookup year factor range
    year_factor_lookup = stage_dict.get("year_factor_range", {})
    year_factor_rng = year_factor_lookup.get(year_key, (1.0, 1.0)) # Default if age range key not found

    # Lookup HRV efficiency range
    hrv_eff_rng = stage_dict.get("hrv_sensible_eff_range", (0.0, 0.0))

    # Determine system type based on lookup map
    try:
        if "system_type_map" in stage_dict:
            stm = stage_dict["system_type_map"]
            func_key = "residential" if is_residential else "non_residential"
            if func_key in stm:
                func_map = stm[func_key]
                if year_key in func_map:
                    subtype_map = func_map[year_key]
                    if infiltration_key in subtype_map:
                        system_type_final = subtype_map[infiltration_key]
                    # else: Use default system type if infiltration_key not in subtype_map
                # else: Use default system type if year_key not in func_map
            # else: Use default system type if func_key not in stm
    except Exception as e:
         print(f"[WARNING] Error looking up system_type: {e}. Using default '{system_type_final}'.")

    # Lookup f_ctrl range based on the determined system type
    if isinstance(sys_ctrl_ranges, dict) and system_type_final in sys_ctrl_ranges:
         # Ensure the entry for the system type is also a dict
         system_entry = sys_ctrl_ranges[system_type_final]
         if isinstance(system_entry, dict):
              f_ctrl_rng = system_entry.get("f_ctrl_range", (1.0, 1.0)) # Default if key missing
         else:
              print(f"[WARNING] Expected dict for sys_ctrl_ranges['{system_type_final}'], got {type(system_entry)}. Using default f_ctrl_range.")
              f_ctrl_rng = (1.0, 1.0)
    else:
         # Handle cases where system_type_final might not be in sys_ctrl_ranges
         print(f"[WARNING] System type '{system_type_final}' not found in system_control_ranges. Using default f_ctrl_range.")
         f_ctrl_rng = (1.0, 1.0)


    # --- 2) Apply User Overrides ---
    matches = find_vent_overrides(
        building_id or 0,
        building_function or "residential",
        age_range or "2015 and later",
        scenario or "scenario1",
        calibration_stage,
        user_config_vent
    )

    # Apply overrides to ranges and fixed values
    for row in matches:
        pname = row.get("param_name", "")
        if pname == "infiltration_base":
            infiltration_base_rng = override_range(infiltration_base_rng, row)
        elif pname == "year_factor":
            year_factor_rng = override_range(year_factor_rng, row)
        elif pname == "system_type":
            if "fixed_value" in row:
                system_type_final = row["fixed_value"] # Directly override system type
                 # Re-lookup f_ctrl range based on potentially overridden system_type
                if isinstance(sys_ctrl_ranges, dict) and system_type_final in sys_ctrl_ranges:
                     system_entry = sys_ctrl_ranges[system_type_final]
                     if isinstance(system_entry, dict):
                         f_ctrl_rng = system_entry.get("f_ctrl_range", (1.0, 1.0))
                     else: f_ctrl_rng = (1.0, 1.0)
                else: f_ctrl_rng = (1.0, 1.0)
        elif pname == "fan_pressure":
            fan_pressure_rng = override_range(fan_pressure_rng, row)
        elif pname == "f_ctrl":
            f_ctrl_rng = override_range(f_ctrl_rng, row)
        elif pname == "hrv_eff":
            hrv_eff_rng = override_range(hrv_eff_rng, row)
        elif pname == "infiltration_schedule_name":
            if "fixed_value" in row:
                infiltration_sched_name = row["fixed_value"]
        elif pname == "ventilation_schedule_name":
            if "fixed_value" in row:
                ventilation_sched_name = row["fixed_value"]
        # Add elif for other parameters like flow_exponent if needed

    # --- 3) Pick Final Values from Ranges ---
    local_log = {} # Dictionary to hold final picks and ranges for assembly
    infiltration_base_val = pick_val_with_range(infiltration_base_rng, strategy, local_log, "infiltration_base")
    year_factor_val       = pick_val_with_range(year_factor_rng,       strategy, local_log, "year_factor")
    fan_pressure_val      = pick_val_with_range(fan_pressure_rng,      strategy, local_log, "fan_pressure")
    f_ctrl_val            = pick_val_with_range(f_ctrl_rng,            strategy, local_log, "f_ctrl")

    # Only pick HRV efficiency if system is D (balanced mechanical)
    if system_type_final == "D":
        hrv_eff_val = pick_val_with_range(hrv_eff_rng, strategy, local_log, "hrv_eff")
    else:
        hrv_eff_val = 0.0 # Ensure it's zero for non-D systems
        local_log["hrv_eff_range"] = (0.0, 0.0)
        local_log["hrv_eff"] = 0.0

    # Store final schedule names and system type
    local_log["infiltration_schedule_name"] = infiltration_sched_name
    local_log["ventilation_schedule_name"]  = ventilation_sched_name
    local_log["system_type"] = system_type_final
    # Store flow exponent (currently default, but could be overridden)
    local_log["flow_exponent"] = default_flow_exponent

    # --- 4) Assemble Final Dictionary ---
    assigned = {
        "infiltration_base": local_log["infiltration_base"],
        "infiltration_base_range": local_log["infiltration_base_range"],
        "year_factor": local_log["year_factor"],
        "year_factor_range": local_log["year_factor_range"],
        "fan_pressure": local_log["fan_pressure"],
        "fan_pressure_range": local_log["fan_pressure_range"],
        "f_ctrl": local_log["f_ctrl"],
        "f_ctrl_range": local_log["f_ctrl_range"],
        "hrv_eff": local_log["hrv_eff"],
        "hrv_eff_range": local_log["hrv_eff_range"],
        "infiltration_schedule_name": local_log["infiltration_schedule_name"],
        "ventilation_schedule_name": local_log["ventilation_schedule_name"],
        "system_type": local_log["system_type"],
        "flow_exponent": local_log["flow_exponent"]
    }

    # --- 5) Optionally Log Externally ---
    if assigned_vent_log is not None:
        # Ensure the building entry exists
        if building_id not in assigned_vent_log:
            assigned_vent_log[building_id] = {}
        # Store the entire assigned dictionary
        assigned_vent_log[building_id]["building_params"] = assigned # Changed key to match add_ventilation.py

    return assigned