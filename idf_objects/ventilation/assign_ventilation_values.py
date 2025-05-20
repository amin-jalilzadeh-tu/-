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
    chosen = 0.0 # Default fallback
    min_v, max_v = 0.0, 0.0 # Default range values

    if rng_tuple is not None and len(rng_tuple) == 2:
        try:
            min_v_in, max_v_in = rng_tuple
            min_v = float(min_v_in)
            max_v = float(max_v_in)
            if math.isnan(min_v) or math.isnan(max_v):
                raise ValueError("NaN in range tuple")
        except (ValueError, TypeError, IndexError): # More specific exception handling
            print(f"[WARNING] Invalid range values in tuple {rng_tuple} for {param_name}. Defaulting to (0.0, 0.0).")
            min_v, max_v = 0.0, 0.0 # Reset to default on error
    else:
        if rng_tuple is not None: # Log if rng_tuple was provided but invalid (e.g. not None, but not a 2-tuple)
             print(f"[WARNING] Invalid range tuple format: {rng_tuple} for {param_name}. Defaulting to (0.0, 0.0).")
        # Otherwise, if rng_tuple is None, min_v and max_v remain 0.0

    # Ensure min <= max
    if min_v > max_v:
        print(f"[WARNING] Min value > Max value in range ({min_v}, {max_v}) for {param_name}. Using min value for both.")
        max_v = min_v

    # Pick final value based on strategy
    if strategy == "A": # Midpoint
        chosen = (min_v + max_v) / 2.0
    elif strategy == "B": # Random
        chosen = random.uniform(min_v, max_v)
    elif strategy == "C": # Minimum
        chosen = min_v
    else: # Default fallback to Minimum if strategy is unknown
        print(f"[WARNING] Unknown pick strategy '{strategy}' for {param_name}. Defaulting to Minimum.")
        chosen = min_v

    # Log if requested
    if log_dict is not None and param_name:
        log_dict[f"{param_name}_range"] = (min_v, max_v) # Log the processed (and potentially corrected) range
        log_dict[param_name] = chosen

    return chosen


def override_range(current_range, row_override_spec, param_name_for_warning="parameter"):
    """
    Applies overrides from a user config row_override_spec to a parameter's (min, max) range.

    If row_override_spec has 'fixed_value', convert it to (val, val).
    If row_override_spec has 'min_val' and 'max_val', return that tuple.
    Otherwise return current_range.
    """
    if "fixed_value" in row_override_spec:
        val = row_override_spec["fixed_value"]
        try:
            # Attempt to convert to float, handle potential errors
            f = float(val)
            if math.isnan(f): # Check for NaN explicitly
                 print(f"[WARNING] Override 'fixed_value' {val} is NaN for {param_name_for_warning}. Using current range {current_range}.")
                 return current_range
            return (f, f)
        except (ValueError, TypeError):
            # If conversion fails (e.g., non-numeric string), keep original range
             print(f"[WARNING] Could not convert override 'fixed_value' {val} to float for {param_name_for_warning}. Using current range {current_range}.")
             return current_range
    elif "min_val" in row_override_spec and "max_val" in row_override_spec:
         try:
             min_ovr = float(row_override_spec["min_val"])
             max_ovr = float(row_override_spec["max_val"])
             if math.isnan(min_ovr) or math.isnan(max_ovr):
                  raise ValueError("Override range contains NaN")
             # Basic validation: min <= max
             if min_ovr > max_ovr:
                  print(f"[WARNING] Override min_val > max_val for {param_name_for_warning}. Using min_val for both.")
                  return (min_ovr, min_ovr)
             return (min_ovr, max_ovr)
         except (ValueError, TypeError):
             print(f"[WARNING] Could not convert override range ({row_override_spec['min_val']}, {row_override_spec['max_val']}) to floats for {param_name_for_warning}. Using current range {current_range}.")
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
        # Ensure scenario and calibration_stage exist, with fallbacks
        scenario_data = ventilation_lookup.get(scenario)
        if not scenario_data:
            print(f"[WARNING] Scenario '{scenario}' not found in ventilation_lookup. Defaulting to first available or 'scenario1'.")
            scenario = next(iter(ventilation_lookup)) if ventilation_lookup else "scenario1" # Fallback to first key or hardcoded
            scenario_data = ventilation_lookup.get(scenario, {}) # Get data for the (potentially fallback) scenario
        
        stage_dict = scenario_data.get(calibration_stage)
        if not stage_dict:
            print(f"[WARNING] Calibration stage '{calibration_stage}' not found for scenario '{scenario}'. Defaulting to first available or 'pre_calibration'.")
            calibration_stage = next(iter(scenario_data)) if scenario_data else "pre_calibration" # Fallback
            stage_dict = scenario_data.get(calibration_stage, {}) # Get data for the (potentially fallback) stage

    except Exception as e: # Broad exception for unforeseen issues with lookup structure
         raise ValueError(f"Error accessing ventilation_lookup for scenario='{scenario}', stage='{calibration_stage}'. Problem: {e}. Ensure lookup structure is correct.")

    # Initialize parameters with defaults or lookups
    # Unit assumption for infiltration_base: L/s/m2 @ 10Pa from ventilation_lookup.py
    infiltration_base_rng = (0.0, 0.0)  # (min_L/s/m2@10Pa, max_L/s/m2@10Pa)
    year_factor_rng = (1.0, 1.0)      # Default no factor
    fan_pressure_rng = (0.0, 0.0)     # Default no pressure (Pa)
    fan_total_efficiency_rng = (0.5, 0.7) # Default typical fan efficiency range
    f_ctrl_rng = (1.0, 1.0)           # Default no control factor adjustment
    hrv_sens_eff_rng = (0.0, 0.0)     # Default no sensible HRV
    hrv_latent_eff_rng = (0.0, 0.0)   # Default no latent HRV

    # Default system types and schedules (can be overridden by lookups or user_config)
    system_type_final = "A" if is_residential else "D" # Default system types
    infiltration_sched_name = "AlwaysOnSched" # Default schedule for infiltration
    ventilation_sched_name = "VentSched_DayNight" if is_residential else "WorkHoursSched" # Default schedules for mech vent

    # Lookup infiltration range based on function and specific building type (infiltration_key)
    try:
        if is_residential:
            res_infil_lookup = stage_dict.get("residential_infiltration_range", {})
            # Provide a more generic default if infiltration_key is not found in the specific lookup
            infiltration_base_rng = res_infil_lookup.get(infiltration_key, (0.8, 1.2)) # Example default residential range
            sys_ctrl_ranges_lookup = stage_dict.get("system_control_range_res", {})
        else: # Non-residential
            nonres_infil_lookup = stage_dict.get("non_res_infiltration_range", {})
            infiltration_base_rng = nonres_infil_lookup.get(infiltration_key, (0.4, 0.6)) # Example default non-res range
            sys_ctrl_ranges_lookup = stage_dict.get("system_control_range_nonres", {})
    except Exception as e: # Catch potential errors during lookup
         print(f"[WARNING] Error getting infiltration/control ranges from lookup: {e}. Using defaults.")
         sys_ctrl_ranges_lookup = {} # Ensure it's a dict to prevent further errors if lookup fails

    # Lookup year factor range based on construction period (year_key)
    year_factor_lookup = stage_dict.get("year_factor_range", {})
    year_factor_rng = year_factor_lookup.get(year_key, (1.0, 1.0)) # Default if year_key not in lookup

    # Lookup HRV effectiveness ranges and fan efficiency range from the stage_dict
    # These keys should exist in ventilation_lookup.py at the calibration_stage level
    hrv_sens_eff_rng = stage_dict.get("hrv_sensible_eff_range", hrv_sens_eff_rng) # Use initialized default if key missing
    hrv_latent_eff_rng = stage_dict.get("hrv_latent_eff_range", hrv_latent_eff_rng) # NEW
    # Fan pressure might be more nuanced (e.g., per system type in SYSTEMS_CONFIG, not a single range here)
    # For now, let's assume a general lookup if available, or it's primarily driven by SYSTEMS_CONFIG
    # and overrides are for specific cases.
    # fan_pressure_rng = stage_dict.get("fan_pressure_range", fan_pressure_rng)
    # A more plausible scenario for this file is to allow override of a fan_pressure_range
    # that might be sourced from a general section of ventilation_lookup OR be used to override
    # values that would otherwise come from SYSTEMS_CONFIG.
    # For simplicity, we'll allow "fan_pressure_range" to be specified in ventilation_lookup stage_dict.
    # If not found, the initialized default (0.0, 0.0) is used, implying it's set elsewhere or not applicable.
    # Example: if ventilation_lookup had a generic fan pressure range:
    # fan_pressure_rng = stage_dict.get("generic_fan_pressure_Pa_range", fan_pressure_rng)

    fan_total_efficiency_rng = stage_dict.get("fan_total_efficiency_range", fan_total_efficiency_rng) # NEW

    # Determine system type (A/B/C/D) based on the detailed lookup map
    try:
        system_type_map_lookup = stage_dict.get("system_type_map", {})
        func_key_for_map = "residential" if is_residential else "non_residential"
        # Graceful fallback: if keys are missing, system_type_final retains its default value
        year_map = system_type_map_lookup.get(func_key_for_map, {}).get(year_key, {})
        system_type_final = year_map.get(infiltration_key, system_type_final)
    except Exception as e:
         print(f"[WARNING] Error looking up system_type from map: {e}. Using default '{system_type_final}'.")

    # Lookup f_ctrl range based on the now-determined system_type_final
    if isinstance(sys_ctrl_ranges_lookup, dict):
        system_specific_ctrl_entry = sys_ctrl_ranges_lookup.get(system_type_final, {}) # Get specific entry for system type
        if isinstance(system_specific_ctrl_entry, dict): # Expecting a dict like {"f_ctrl_range": (min, max)}
            f_ctrl_rng = system_specific_ctrl_entry.get("f_ctrl_range", f_ctrl_rng) # Use initialized default if key missing
        else:
            # This handles cases where system_type_final might not have a sub-dict for f_ctrl_range
            print(f"[WARNING] Expected dict for sys_ctrl_ranges['{system_type_final}'], got {type(system_specific_ctrl_entry)}. Using default f_ctrl_range {f_ctrl_rng}.")
            # f_ctrl_rng remains its initialized default
    else:
        # This handles cases where sys_ctrl_ranges_lookup itself is not a dict (e.g., if initial lookup failed)
        print(f"[WARNING] System control ranges ('system_control_range_res' or '_nonres') not found or invalid type. Using default f_ctrl_range {f_ctrl_rng}.")
        # f_ctrl_rng remains its initialized default


    # --- 2) Apply User Overrides ---
    # `matches` will be a list of override rows applicable to this building/scenario/stage
    matches = find_vent_overrides(
        building_id or 0, # Use 0 if building_id is None, for matching rows that don't specify ID
        building_function, # Already defaulted if None
        age_range,         # Already defaulted if None
        scenario,          # Already defaulted
        calibration_stage, # Already defaulted
        user_config_vent
    )

    # Apply overrides to ranges and fixed values by iterating through matched rows
    for row in matches: # override_row
        pname = row.get("param_name", "") # param_name_in_override
        # Pass param_name to override_range for better warning messages
        if pname == "infiltration_base": # Assumed L/s/m2@10Pa
            infiltration_base_rng = override_range(infiltration_base_rng, row, "infiltration_base")
        elif pname == "year_factor":
            year_factor_rng = override_range(year_factor_rng, row, "year_factor")
        elif pname == "system_type":
            if "fixed_value" in row:
                system_type_final = str(row["fixed_value"]) # Directly override system type
                 # Re-lookup f_ctrl range based on potentially overridden system_type
                if isinstance(sys_ctrl_ranges_lookup, dict): # sys_ctrl_ranges
                     system_entry = sys_ctrl_ranges_lookup.get(system_type_final, {}) # system_specific_ctrl_entry
                     if isinstance(system_entry, dict): # Check if the entry itself is a dict
                         f_ctrl_rng = system_entry.get("f_ctrl_range", (1.0, 1.0)) # Default if "f_ctrl_range" not in sub-dict
                     else: f_ctrl_rng = (1.0, 1.0) # Default if system_entry is not a dict
                else: f_ctrl_rng = (1.0, 1.0) # Default if sys_ctrl_ranges_lookup is not a dict
        elif pname == "fan_pressure": # Pa
            fan_pressure_rng = override_range(fan_pressure_rng, row, "fan_pressure")
        elif pname == "fan_total_efficiency": # NEW
            fan_total_efficiency_rng = override_range(fan_total_efficiency_rng, row, "fan_total_efficiency")
        elif pname == "f_ctrl":
            f_ctrl_rng = override_range(f_ctrl_rng, row, "f_ctrl")
        elif pname == "hrv_eff": # Sensible HRV effectiveness
            hrv_sens_eff_rng = override_range(hrv_sens_eff_rng, row, "hrv_eff")
        elif pname == "hrv_latent_eff": # NEW - Latent HRV effectiveness
            hrv_latent_eff_rng = override_range(hrv_latent_eff_rng, row, "hrv_latent_eff")
        elif pname == "infiltration_schedule_name":
            if "fixed_value" in row:
                infiltration_sched_name = str(row["fixed_value"])
        elif pname == "ventilation_schedule_name":
            if "fixed_value" in row:
                ventilation_sched_name = str(row["fixed_value"])
        # Add elif for other parameters like "flow_exponent" if it needs to be configurable via overrides

    # --- 3) Pick Final Values from Ranges ---
    # This local_log will be used to build the `assigned` dictionary returned by the function.
    local_log = {} # Dictionary to hold final picks and ranges for assembly

    # Renaming for clarity on assumed units from lookup/override step for infiltration_base
    # The param_name here will be the key in the output dictionary
    infiltration_base_val = pick_val_with_range(infiltration_base_rng, strategy, local_log, "infiltration_base_L_s_m2_10Pa")
    year_factor_val       = pick_val_with_range(year_factor_rng,       strategy, local_log, "year_factor")
    fan_pressure_val      = pick_val_with_range(fan_pressure_rng,      strategy, local_log, "fan_pressure")
    fan_total_efficiency_val = pick_val_with_range(fan_total_efficiency_rng, strategy, local_log, "fan_total_efficiency") # NEW
    f_ctrl_val            = pick_val_with_range(f_ctrl_rng,            strategy, local_log, "f_ctrl")

    # Only pick HRV efficiency if system is D (balanced mechanical)
    if system_type_final == "D":
        hrv_sens_eff_val = pick_val_with_range(hrv_sens_eff_rng, strategy, local_log, "hrv_eff") # Sensible
        hrv_latent_eff_val = pick_val_with_range(hrv_latent_eff_rng, strategy, local_log, "hrv_lat_eff") # Latent - NEW
    else: # For non-D systems, HRV effectiveness is zero.
        hrv_sens_eff_val = 0.0
        hrv_latent_eff_val = 0.0 # NEW
        local_log["hrv_eff_range"] = (0.0, 0.0) # Log zero range for sensible
        local_log["hrv_eff"] = 0.0
        local_log["hrv_lat_eff_range"] = (0.0, 0.0) # Log zero range for latent - NEW
        local_log["hrv_lat_eff"] = 0.0

    # Store final schedule names and system type
    local_log["infiltration_schedule_name"] = infiltration_sched_name
    local_log["ventilation_schedule_name"]  = ventilation_sched_name
    local_log["system_type"] = system_type_final
    # Store flow exponent (currently default, but could be made configurable/overridable)
    local_log["flow_exponent"] = default_flow_exponent

    # --- 4) Assemble Final Dictionary ---
    # This is the dictionary that will be returned.
    assigned = {
        # Using keys from local_log directly to ensure consistency
        "infiltration_base_L_s_m2_10Pa": local_log["infiltration_base_L_s_m2_10Pa"],
        "infiltration_base_L_s_m2_10Pa_range": local_log["infiltration_base_L_s_m2_10Pa_range"],
        "year_factor": local_log["year_factor"],
        "year_factor_range": local_log["year_factor_range"],
        "fan_pressure": local_log["fan_pressure"], # Pa
        "fan_pressure_range": local_log["fan_pressure_range"],
        "fan_total_efficiency": local_log["fan_total_efficiency"], # NEW (fraction)
        "fan_total_efficiency_range": local_log["fan_total_efficiency_range"], # NEW
        "f_ctrl": local_log["f_ctrl"],
        "f_ctrl_range": local_log["f_ctrl_range"],
        "hrv_eff": local_log["hrv_eff"], # Sensible HRV effectiveness (fraction)
        "hrv_eff_range": local_log["hrv_eff_range"],
        "hrv_lat_eff": local_log["hrv_lat_eff"], # Latent HRV effectiveness (fraction) - NEW
        "hrv_lat_eff_range": local_log["hrv_lat_eff_range"], # NEW
        "infiltration_schedule_name": local_log["infiltration_schedule_name"],
        "ventilation_schedule_name": local_log["ventilation_schedule_name"],
        "system_type": local_log["system_type"],
        "flow_exponent": local_log["flow_exponent"]
    }

    # --- 5) Optionally Log Externally ---
    if assigned_vent_log is not None and isinstance(assigned_vent_log, dict): # Check type of log object
        # Ensure the building entry exists using a sensible key
        building_key_for_log = building_id if building_id is not None else "unknown_building"
        if building_key_for_log not in assigned_vent_log:
            assigned_vent_log[building_key_for_log] = {}
        # Store the entire assigned dictionary, using a copy to avoid modification issues
        assigned_vent_log[building_key_for_log]["building_params"] = assigned.copy() # Changed key to match add_ventilation.py

    return assigned