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
    """
    matches = []
    if not user_config: # Handle empty or None user_config
        return matches

    for row in user_config:
        if not isinstance(row, dict):
            continue

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
    """
    chosen = 0.0
    min_v, max_v = 0.0, 0.0

    if rng_tuple is not None and len(rng_tuple) == 2:
        try:
            min_v_in, max_v_in = rng_tuple
            min_v = float(min_v_in)
            max_v = float(max_v_in)
            if math.isnan(min_v) or math.isnan(max_v):
                raise ValueError("NaN in range tuple")
        except (ValueError, TypeError, IndexError):
            print(f"[WARNING] assign_ventilation_values.py: Invalid range values in tuple {rng_tuple} for {param_name}. Defaulting to (0.0, 0.0).")
            min_v, max_v = 0.0, 0.0
    elif rng_tuple is not None:
        print(f"[WARNING] assign_ventilation_values.py: Invalid range tuple format: {rng_tuple} for {param_name}. Defaulting to (0.0, 0.0).")

    if min_v > max_v:
        print(f"[WARNING] assign_ventilation_values.py: Min value > Max value in range ({min_v}, {max_v}) for {param_name}. Using min value for both.")
        max_v = min_v

    if strategy == "A":
        chosen = (min_v + max_v) / 2.0
    elif strategy == "B":
        chosen = random.uniform(min_v, max_v)
    elif strategy == "C":
        chosen = min_v
    else:
        print(f"[WARNING] assign_ventilation_values.py: Unknown pick strategy '{strategy}' for {param_name}. Defaulting to Minimum.")
        chosen = min_v

    if log_dict is not None and param_name:
        log_dict[f"{param_name}_range"] = (min_v, max_v)
        log_dict[param_name] = chosen
    return chosen


def override_range(current_range, row_override_spec, param_name_for_warning="parameter"):
    """
    Applies overrides from a user config row to a parameter's (min, max) range.
    """
    if "fixed_value" in row_override_spec:
        val = row_override_spec["fixed_value"]
        try:
            f_val = float(val)
            if math.isnan(f_val):
                print(f"[WARNING] assign_ventilation_values.py: Override 'fixed_value' {val} is NaN for {param_name_for_warning}. Using current range {current_range}.")
                return current_range
            return (f_val, f_val)
        except (ValueError, TypeError): # If it's not a number, it's likely a string (e.g. schedule name)
            # For non-numeric fixed_value (like schedule names), this function isn't the right place.
            # That override is handled directly in the main assign_ventilation_params_with_overrides.
            # This function is for numeric ranges. So, if fixed_value is non-numeric, we don't change the range here.
            # Let the main logic handle string fixed_values.
            if not isinstance(val, (int,float)): # if it's truly a string override for a range param, that's an error
                 print(f"[ERROR] assign_ventilation_values.py: 'fixed_value' {val} for numeric range parameter {param_name_for_warning} is not a number. Using current range {current_range}.")
            return current_range

    elif "min_val" in row_override_spec and "max_val" in row_override_spec:
        try:
            min_ovr = float(row_override_spec["min_val"])
            max_ovr = float(row_override_spec["max_val"])
            if math.isnan(min_ovr) or math.isnan(max_ovr):
                raise ValueError("Override range contains NaN")
            if min_ovr > max_ovr:
                print(f"[WARNING] assign_ventilation_values.py: Override min_val > max_val for {param_name_for_warning}. Using min_val for both.")
                return (min_ovr, min_ovr)
            return (min_ovr, max_ovr)
        except (ValueError, TypeError):
            print(f"[WARNING] assign_ventilation_values.py: Could not convert override range ({row_override_spec.get('min_val')}, {row_override_spec.get('max_val')}) to floats for {param_name_for_warning}. Using current range {current_range}.")
            return current_range
    return current_range


def assign_ventilation_params_with_overrides(
    building_id=None,
    building_function="residential",
    age_range="2015 and later",
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_vent=None,
    assigned_vent_log=None, # This argument is passed but not used within this function for logging. Logging happens in add_ventilation.py
    infiltration_key=None,  # This is the archetype_key
    year_key=None,
    is_residential=True,
    default_flow_exponent=0.67
):
    """
    Determines ventilation parameters, including archetype-specific schedule names,
    based on lookups and user overrides.
    """
    if random_seed is not None:
        random.seed(random_seed)

    # --- 1) Get Base Parameter Ranges from ventilation_lookup ---
    try:
        scenario_data = ventilation_lookup.get(scenario)
        if not scenario_data:
            print(f"[WARNING] assign_ventilation_values.py: Scenario '{scenario}' not found in ventilation_lookup. Defaulting to first available or 'scenario1'.")
            scenario = next(iter(ventilation_lookup)) if ventilation_lookup else "scenario1"
            scenario_data = ventilation_lookup.get(scenario, {})
        
        stage_dict = scenario_data.get(calibration_stage)
        if not stage_dict:
            print(f"[WARNING] assign_ventilation_values.py: Calibration stage '{calibration_stage}' not found for scenario '{scenario}'. Defaulting to first available or 'pre_calibration'.")
            calibration_stage = next(iter(scenario_data)) if scenario_data else "pre_calibration"
            stage_dict = scenario_data.get(calibration_stage, {})
    except Exception as e:
         raise ValueError(f"Error accessing ventilation_lookup for scenario='{scenario}', stage='{calibration_stage}'. Problem: {e}. Ensure lookup structure is correct.")

    # Initialize parameter ranges
    infiltration_base_rng = (0.0, 0.0)
    year_factor_rng = (1.0, 1.0)
    fan_pressure_rng = (0.0, 0.0)
    fan_total_efficiency_rng = (0.5, 0.7)
    f_ctrl_rng = (1.0, 1.0)
    hrv_sens_eff_rng = (0.0, 0.0)
    hrv_latent_eff_rng = (0.0, 0.0)

    # Determine system type (A/B/C/D) from ventilation_lookup
    system_type_final = "A" if is_residential else "D" # Default
    try:
        system_type_map_lookup = stage_dict.get("system_type_map", {})
        func_key_for_map = "residential" if is_residential else "non_residential"
        year_map = system_type_map_lookup.get(func_key_for_map, {}).get(year_key, {})
        system_type_final = year_map.get(infiltration_key, system_type_final) # infiltration_key is archetype
    except Exception as e:
         print(f"[WARNING] assign_ventilation_values.py: Error looking up system_type from map: {e}. Using default '{system_type_final}'.")

    # ---- NEW: Define Archetype-Specific Schedule Names ----
    # infiltration_key serves as the archetype identifier.
    # Clean the key for use in a schedule name.
    clean_archetype_key = infiltration_key.replace(" ", "_").replace("-", "") if infiltration_key else "default"
    
    # Default names, these will be used by add_ventilation.py to call schedule creation
    ventilation_sched_name = f"VentSched_{clean_archetype_key}"
    infiltration_sched_name = f"InfilSched_{clean_archetype_key}"
    # Fallback for infiltration often is AlwaysOn, but we make it archetype-specific by default.
    # User can override to "AlwaysOnSched" via user_config_vent if needed.
    # ---- END NEW Schedule Name Definition ----

    # Lookup other parameter ranges
    try:
        if is_residential:
            res_infil_lookup = stage_dict.get("residential_infiltration_range", {})
            infiltration_base_rng = res_infil_lookup.get(infiltration_key, (0.8, 1.2))
            sys_ctrl_ranges_lookup = stage_dict.get("system_control_range_res", {})
        else:
            nonres_infil_lookup = stage_dict.get("non_res_infiltration_range", {})
            infiltration_base_rng = nonres_infil_lookup.get(infiltration_key, (0.4, 0.6))
            sys_ctrl_ranges_lookup = stage_dict.get("system_control_range_nonres", {})
    except Exception as e:
         print(f"[WARNING] assign_ventilation_values.py: Error getting infiltration/control ranges from lookup: {e}. Using defaults.")
         sys_ctrl_ranges_lookup = {}

    year_factor_lookup = stage_dict.get("year_factor_range", {})
    year_factor_rng = year_factor_lookup.get(year_key, (1.0, 1.0))

    hrv_sens_eff_rng = stage_dict.get("hrv_sensible_eff_range", hrv_sens_eff_rng)
    hrv_latent_eff_rng = stage_dict.get("hrv_latent_eff_range", hrv_latent_eff_rng)
    fan_total_efficiency_rng = stage_dict.get("fan_total_efficiency_range", fan_total_efficiency_rng)
    # Example for fan_pressure_range if it were structured like others:
    # fan_pressure_data = stage_dict.get("fan_pressure_range", {})
    # fan_pressure_rng = fan_pressure_data.get("res_mech" if is_residential else "nonres_intake", fan_pressure_rng)


    if isinstance(sys_ctrl_ranges_lookup, dict):
        system_specific_ctrl_entry = sys_ctrl_ranges_lookup.get(system_type_final, {})
        if isinstance(system_specific_ctrl_entry, dict):
            f_ctrl_rng = system_specific_ctrl_entry.get("f_ctrl_range", f_ctrl_rng)
        else:
            print(f"[WARNING] assign_ventilation_values.py: Expected dict for sys_ctrl_ranges['{system_type_final}'], got {type(system_specific_ctrl_entry)}. Using default f_ctrl_range {f_ctrl_rng}.")
    else:
        print(f"[WARNING] assign_ventilation_values.py: System control ranges not found or invalid. Using default f_ctrl_range {f_ctrl_rng}.")

    # --- 2) Apply User Overrides from user_config_vent ---
    matches = find_vent_overrides(
        building_id or 0, building_function, age_range,
        scenario, calibration_stage, user_config_vent
    )

    for row in matches:
        pname = row.get("param_name", "")
        if pname == "infiltration_base":
            infiltration_base_rng = override_range(infiltration_base_rng, row, "infiltration_base")
        elif pname == "year_factor":
            year_factor_rng = override_range(year_factor_rng, row, "year_factor")
        elif pname == "system_type": # Overriding system_type
            if "fixed_value" in row:
                system_type_final = str(row["fixed_value"])
                # Re-lookup f_ctrl range based on potentially overridden system_type
                if isinstance(sys_ctrl_ranges_lookup, dict):
                    system_entry = sys_ctrl_ranges_lookup.get(system_type_final, {})
                    if isinstance(system_entry, dict):
                        f_ctrl_rng = system_entry.get("f_ctrl_range", (1.0, 1.0))
                    else: f_ctrl_rng = (1.0, 1.0)
                else: f_ctrl_rng = (1.0, 1.0)
        elif pname == "fan_pressure":
            fan_pressure_rng = override_range(fan_pressure_rng, row, "fan_pressure")
        elif pname == "fan_total_efficiency":
            fan_total_efficiency_rng = override_range(fan_total_efficiency_rng, row, "fan_total_efficiency")
        elif pname == "f_ctrl":
            f_ctrl_rng = override_range(f_ctrl_rng, row, "f_ctrl")
        elif pname == "hrv_eff":
            hrv_sens_eff_rng = override_range(hrv_sens_eff_rng, row, "hrv_eff")
        elif pname == "hrv_latent_eff":
            hrv_latent_eff_rng = override_range(hrv_latent_eff_rng, row, "hrv_latent_eff")
        # ---- Schedule Name Overrides ----
        elif pname == "infiltration_schedule_name":
            if "fixed_value" in row:
                infiltration_sched_name = str(row["fixed_value"]) # Direct string override
        elif pname == "ventilation_schedule_name":
            if "fixed_value" in row:
                ventilation_sched_name = str(row["fixed_value"]) # Direct string override

    # --- 3) Pick Final Values from Ranges ---
    local_log_for_params = {} # For storing picked values and their source ranges for parameters

    infiltration_base_val = pick_val_with_range(infiltration_base_rng, strategy, local_log_for_params, "infiltration_base_L_s_m2_10Pa")
    year_factor_val       = pick_val_with_range(year_factor_rng, strategy, local_log_for_params, "year_factor")
    fan_pressure_val      = pick_val_with_range(fan_pressure_rng, strategy, local_log_for_params, "fan_pressure")
    fan_total_efficiency_val = pick_val_with_range(fan_total_efficiency_rng, strategy, local_log_for_params, "fan_total_efficiency")
    f_ctrl_val            = pick_val_with_range(f_ctrl_rng, strategy, local_log_for_params, "f_ctrl")

    if system_type_final == "D":
        hrv_sens_eff_val = pick_val_with_range(hrv_sens_eff_rng, strategy, local_log_for_params, "hrv_eff")
        hrv_latent_eff_val = pick_val_with_range(hrv_latent_eff_rng, strategy, local_log_for_params, "hrv_lat_eff")
    else:
        hrv_sens_eff_val = 0.0
        hrv_latent_eff_val = 0.0
        local_log_for_params["hrv_eff_range"] = (0.0, 0.0)
        local_log_for_params["hrv_eff"] = 0.0
        local_log_for_params["hrv_lat_eff_range"] = (0.0, 0.0)
        local_log_for_params["hrv_lat_eff"] = 0.0

    # --- 4) Assemble Final Dictionary to be Returned ---
    # This dictionary includes the picked parameters and the determined schedule names.
    # The actual schedule objects are created later in add_ventilation.py.
    assigned_params = {
        "infiltration_base_L_s_m2_10Pa": local_log_for_params["infiltration_base_L_s_m2_10Pa"],
        "infiltration_base_L_s_m2_10Pa_range": local_log_for_params["infiltration_base_L_s_m2_10Pa_range"],
        "year_factor": local_log_for_params["year_factor"],
        "year_factor_range": local_log_for_params["year_factor_range"],
        "fan_pressure": local_log_for_params["fan_pressure"],
        "fan_pressure_range": local_log_for_params["fan_pressure_range"],
        "fan_total_efficiency": local_log_for_params["fan_total_efficiency"],
        "fan_total_efficiency_range": local_log_for_params["fan_total_efficiency_range"],
        "f_ctrl": local_log_for_params["f_ctrl"],
        "f_ctrl_range": local_log_for_params["f_ctrl_range"],
        "hrv_eff": local_log_for_params["hrv_eff"],
        "hrv_eff_range": local_log_for_params["hrv_eff_range"],
        "hrv_lat_eff": local_log_for_params["hrv_lat_eff"],
        "hrv_lat_eff_range": local_log_for_params["hrv_lat_eff_range"],
        "infiltration_schedule_name": infiltration_sched_name, # Final determined name
        "ventilation_schedule_name": ventilation_sched_name,   # Final determined name
        "system_type": system_type_final,
        "flow_exponent": default_flow_exponent,
        "strategy_letter": strategy # Pass the strategy letter for consistency if needed by other functions
    }
    
    # Logging of these 'assigned_params' happens in add_ventilation.py's 'assigned_vent_log'

    return assigned_params