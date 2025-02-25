# ventilation/assign_ventilation_values.py

import random
from .ventilation_lookup import ventilation_lookup

def find_vent_overrides(
    building_id,
    building_function,
    age_range,
    scenario,
    calibration_stage,
    user_config
):
    """
    Return a list of user_config rows that match all provided criteria:
      - building_id
      - building_function
      - age_range
      - scenario
      - calibration_stage
    """
    matches = []
    if user_config:
        for row in user_config:
            # building_id match if present
            if "building_id" in row and row["building_id"] != building_id:
                continue
            # building_function match if present
            if "building_function" in row and row["building_function"] != building_function:
                continue
            # age_range match if present
            if "age_range" in row and row["age_range"] != age_range:
                continue
            # scenario match if present
            if "scenario" in row and row["scenario"] != scenario:
                continue
            # calibration_stage match if present
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
    rng_tuple = (min_val, max_val) or None.
    strategy  = "A"=>midpoint, "B"=>random, "C"=>pick min, etc.
    log_dict  => optional dictionary for storing final picks.
    param_name=> e.g. "infiltration_base", "fan_pressure", etc.

    Returns the chosen numeric value.
    Also logs (param_name + param_name_range) if log_dict is provided.
    """
    if rng_tuple is None:
        return 0.0  # fallback => 0

    min_v, max_v = rng_tuple

    # pick final
    if strategy == "A":
        chosen = (min_v + max_v) / 2.0
    elif strategy == "B":
        chosen = random.uniform(min_v, max_v)
    elif strategy == "C":
        chosen = min_v  # pick min
    else:
        chosen = min_v  # default => pick min

    if log_dict is not None and param_name:
        # store the numeric range
        log_dict[f"{param_name}_range"] = (min_v, max_v)
        # store the final
        log_dict[param_name] = chosen

    return chosen


def assign_ventilation_params_with_overrides(
    building_id=None,
    building_function="residential",
    age_range="2015 and later",
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",         # "A" => midpoint, "B" => random, "C" => min, etc.
    random_seed=None,
    user_config_vent=None,     # possibly a list of override rows
    assigned_vent_log=None,    # dictionary to store final picks if desired
    infiltration_key=None,     # e.g. "Corner House" or "Office Function"
    year_key=None,             # e.g. "1975 - 1991"
    is_residential=True,
    default_flow_exponent=0.67
):
    """
    Returns a dict containing:
        {
          "infiltration_base": float,
          "infiltration_base_range": (min, max),
          "year_factor": float,
          "year_factor_range": (min, max),
          "system_type": str,
          "fan_pressure": float,
          "fan_pressure_range": (min, max),
          "f_ctrl": float,
          "f_ctrl_range": (min, max),
          "hrv_eff": float,
          "hrv_eff_range": (min, max),
          "infiltration_schedule_name": str,
          "ventilation_schedule_name": str,
          "flow_exponent": default_flow_exponent
        }

    Steps:
      1) Look up default ranges from ventilation_lookup (scenario, calibration_stage).
      2) Merge user overrides => modifies these ranges or sets fixed values.
      3) Use 'strategy' to pick final numeric values from each range.
      4) Return the final assigned dictionary, which includes both final picks & range info.
      5) Optionally log them to assigned_vent_log if provided.

    The infiltration_key for a residential building might be "Corner House", etc.
    For non-residential, infiltration_key might be "Office Function", etc.
    """
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Ensure scenario & calibration_stage exist in ventilation_lookup
    if scenario not in ventilation_lookup:
        scenario = "scenario1"
    if calibration_stage not in ventilation_lookup[scenario]:
        calibration_stage = "pre_calibration"

    stage_dict = ventilation_lookup[scenario][calibration_stage]

    # Prepare a local dictionary for logging (if assigned_vent_log is used).
    log_dict = None
    if assigned_vent_log is not None:
        if building_id not in assigned_vent_log:
            assigned_vent_log[building_id] = {}
        log_dict = assigned_vent_log[building_id]

    # 2) Default infiltration_base range from infiltration_key
    if is_residential:
        res_infil = stage_dict["residential_infiltration_range"]
        infiltration_base_rng = res_infil.get(infiltration_key, (1.0, 1.0))  # fallback
        sys_ctrl_ranges = stage_dict["system_control_range_res"]
    else:
        nonres_infil = stage_dict["non_res_infiltration_range"]
        infiltration_base_rng = nonres_infil.get(infiltration_key, (0.5, 0.5))  # fallback
        sys_ctrl_ranges = stage_dict["system_control_range_nonres"]

    # 3) year_factor range
    year_factor_rng = stage_dict["year_factor_range"].get(year_key, (1.0, 1.0))

    # 4) Determine system_type from the system_type_map if available
    #    Otherwise fallback to "A" for residential, "D" for non-res.
    default_system_type = "A" if is_residential else "D"
    system_type_final = default_system_type

    if "system_type_map" in stage_dict:
        stm = stage_dict["system_type_map"]
        func_key = "residential" if is_residential else "non_residential"
        if func_key in stm:
            func_map = stm[func_key]
            if year_key in func_map:
                subtype_map = func_map[year_key]
                # pick system if infiltration_key is in subtype_map
                if infiltration_key in subtype_map:
                    system_type_final = subtype_map[infiltration_key]

    # 5) fan_pressure => we might pull from stage_dict["fan_pressure_range"] if needed
    #    but typically that is a single dictionary with subkeys like "res_mech", "nonres_intake", etc.
    #    We'll set a default (0.0,0.0) and let user overrides do the rest if needed.
    fan_pressure_rng = (0.0, 0.0)
    if "fan_pressure_range" in stage_dict:
        # For example, we might choose "res_mech" for residential, "nonres_intake"/"nonres_exhaust" for non-res.
        # But you can do more advanced logic if desired. We'll keep it 0 unless user overrides it.
        pass

    # 6) f_ctrl => pick from system_control_range (depending on system_type_final)
    if system_type_final in sys_ctrl_ranges:
        f_ctrl_rng = sys_ctrl_ranges[system_type_final].get("f_ctrl_range", (1.0, 1.0))
    else:
        f_ctrl_rng = (1.0, 1.0)

    # 7) HRV => only relevant if system_type=="D"
    hrv_eff_rng = (0.0, 0.0)
    if "hrv_sensible_eff_range" in stage_dict:
        hrv_eff_rng = stage_dict["hrv_sensible_eff_range"]

    # 8) apply user overrides
    matches = find_vent_overrides(
        building_id or 0,
        building_function or "residential",
        age_range or "2015 and later",
        scenario or "scenario1",
        calibration_stage,
        user_config_vent
    )

    def override_range(current_range, row):
        """
        If row has 'fixed_value', convert it to (val, val).
        If row has 'min_val' and 'max_val', return that tuple.
        Otherwise return current_range.
        """
        if "fixed_value" in row:
            val = row["fixed_value"]
            try:
                f = float(val)
                return (f, f)
            except (ValueError, TypeError):
                return current_range
        elif "min_val" in row and "max_val" in row:
            return (row["min_val"], row["max_val"])
        return current_range

    infiltration_sched_name = "AlwaysOnSched"
    ventilation_sched_name = "VentSched_DayNight"

    for row in matches:
        pname = row.get("param_name", "")
        if pname == "infiltration_base":
            infiltration_base_rng = override_range(infiltration_base_rng, row)

        elif pname == "year_factor":
            year_factor_rng = override_range(year_factor_rng, row)

        elif pname == "system_type":
            # If user sets a fixed_value => override system_type_final
            if "fixed_value" in row:
                system_type_final = row["fixed_value"]

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

    # 9) pick final infiltration_base, year_factor, fan_pressure, f_ctrl, hrv_eff
    local_log = {}
    infiltration_base_val = pick_val_with_range(infiltration_base_rng, strategy, local_log, "infiltration_base")
    year_factor_val       = pick_val_with_range(year_factor_rng,       strategy, local_log, "year_factor")
    fan_pressure_val      = pick_val_with_range(fan_pressure_rng,      strategy, local_log, "fan_pressure")
    f_ctrl_val            = pick_val_with_range(f_ctrl_rng,            strategy, local_log, "f_ctrl")

    hrv_eff_val = 0.0
    if system_type_final == "D":
        hrv_eff_val = pick_val_with_range(hrv_eff_rng, strategy, local_log, "hrv_eff")
    else:
        local_log["hrv_eff_range"] = (0.0, 0.0)
        local_log["hrv_eff"] = 0.0

    # 10) infiltration/vent schedules => infiltration_sched_name, ventilation_sched_name
    local_log["infiltration_schedule_name"] = infiltration_sched_name
    local_log["ventilation_schedule_name"]  = ventilation_sched_name
    local_log["system_type"] = system_type_final

    # 11) Build final assigned dict
    assigned = {
        # infiltration_base
        "infiltration_base": local_log["infiltration_base"],
        "infiltration_base_range": local_log["infiltration_base_range"],

        # year_factor
        "year_factor": local_log["year_factor"],
        "year_factor_range": local_log["year_factor_range"],

        # fan_pressure
        "fan_pressure": local_log["fan_pressure"],
        "fan_pressure_range": local_log["fan_pressure_range"],

        # f_ctrl
        "f_ctrl": local_log["f_ctrl"],
        "f_ctrl_range": local_log["f_ctrl_range"],

        # hrv_eff
        "hrv_eff": local_log["hrv_eff"],
        "hrv_eff_range": local_log["hrv_eff_range"],

        # Schedules
        "infiltration_schedule_name": local_log["infiltration_schedule_name"],
        "ventilation_schedule_name": local_log["ventilation_schedule_name"],

        # System type
        "system_type": local_log["system_type"],

        # Flow exponent
        "flow_exponent": default_flow_exponent
    }

    # 12) If logging externally => store
    if log_dict is not None:
        log_dict["ventilation_params"] = assigned

    return assigned




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
      - plus override fields for infiltration_base, year_factor, system_type, fan_pressure, f_ctrl, hrv_eff, etc.

    If any of those fields are present in the row and do not match the
    current building, that row is skipped. Otherwise, the row is considered
    a match and is returned in the list.
    """

    """
    Return a dict with infiltration_base, year_factor, system_type, f_ctrl, fan_pressure,
    hrv_eff, infiltration_schedule_name, ventilation_schedule_name, etc.

    This function uses:
      1) The scenario & calibration_stage to locate a sub-dict in 'ventilation_lookup'
      2) The infiltration_key/year_key to get infiltration & year_factor ranges
      3) user_config_vent overrides to optionally override any of the above
      4) A picking strategy (A=midpoint, B=uniform random, C=lower bound) for final selection
      5) The building_function & usage_key to also fetch schedule_info from 'ventilation_lookup'
         => infiltration_schedule_name & ventilation_schedule_name

    Then logs final picks into assigned_vent_log if provided (dict-based log).
    """

