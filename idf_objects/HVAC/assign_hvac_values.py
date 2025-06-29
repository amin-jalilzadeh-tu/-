# File: HVAC/assign_hvac_values.py

import random
from .hvac_lookup import hvac_lookup

def find_hvac_overrides(
    building_id,
    building_function,
    residential_type,
    non_residential_type,
    age_range,
    scenario,
    calibration_stage,
    user_config
):
    """
    Returns a list of user_config rows that match the specified building criteria.
    Each row might contain override data for setpoints or even schedule definitions.
    For example, a row might say:
      {
        "building_id": 123,
        "param_name": "heating_day_setpoint",
        "fixed_value": 20.5
      }
    or:
      {
        "building_id": 123,
        "param_name": "hvac_availability_weekday",
        "override_blocks": [
          ("06:00",1.0),
          ("22:00",0.3),
          ("24:00",0.0)
        ]
      }
    """
    matches = []
    for row in user_config or []:
        if "building_id" in row and row["building_id"] != building_id:
            continue
        if "building_function" in row and row["building_function"] != building_function:
            continue

        if "residential_type" in row and row["residential_type"] != residential_type:
            continue
        if "non_residential_type" in row and row["non_residential_type"] != non_residential_type:
            continue

        if "age_range" in row and row["age_range"] != age_range:
            continue
        if "scenario" in row and row["scenario"] != scenario:
            continue
        if "calibration_stage" in row and row["calibration_stage"] != calibration_stage:
            continue

        matches.append(row)
    return matches


def pick_val_with_range(rng_tuple, strategy="A", log_dict=None, param_name=None):
    """
    rng_tuple = (min_val, max_val).
    strategy  = "A" => midpoint, 
                "B" => random uniform in [min,max],
                else => pick min_val.

    If log_dict and param_name are given, store both the chosen value and the
    (min_val, max_val) range in log_dict for reference.
    """
    min_v, max_v = rng_tuple

    if strategy == "A":  # midpoint
        chosen = (min_v + max_v) / 2.0
    elif strategy == "B":
        chosen = random.uniform(min_v, max_v)
    else:
        chosen = min_v  # default => pick min

    if log_dict is not None and param_name is not None:
        log_dict[f"{param_name}_range"] = (min_v, max_v)
        log_dict[param_name] = chosen

    return chosen


def override_numeric_range(current_range, row):
    """
    If row has a 'fixed_value' => returns (v, v).
    If row has 'min_val' and 'max_val' => returns (min_val, max_val).
    Otherwise returns current_range unchanged.
    """
    if "fixed_value" in row and row["fixed_value"] is not None:
        v = row["fixed_value"]
        return (v, v)
    if "min_val" in row and "max_val" in row and row["min_val"] is not None and row["max_val"] is not None:
        return (row["min_val"], row["max_val"])
    return current_range


def override_schedule_details(schedule_details, row):
    """
    If row has param_name like "hvac_availability_weekday" or "occupancy_weekend", etc.,
    and 'override_blocks' = a list of (time, value),
    we replace the default schedule details with user-provided blocks.

    For example:
      row = {
        "param_name": "hvac_availability_weekday",
        "override_blocks": [
           ("06:00",1.0), ("22:00",0.2), ("24:00",0.0)
        ]
      }
    We'll do:
      schedule_details["hvac_availability"]["weekday"] = that new list
    """

    pname = row.get("param_name", "").lower()
    override_blocks = row.get("override_blocks")
    if not override_blocks:
        return  # nothing to do

    # Example approach:
    if pname == "hvac_availability_weekday" and "hvac_availability" in schedule_details:
        schedule_details["hvac_availability"]["weekday"] = override_blocks
    elif pname == "hvac_availability_weekend" and "hvac_availability" in schedule_details:
        schedule_details["hvac_availability"]["weekend"] = override_blocks

    elif pname == "occupancy_weekday" and "occupancy" in schedule_details:
        schedule_details["occupancy"]["weekday"] = override_blocks
    elif pname == "occupancy_weekend" and "occupancy" in schedule_details:
        schedule_details["occupancy"]["weekend"] = override_blocks

    elif pname == "setpoints_weekday" and "setpoints" in schedule_details:
        schedule_details["setpoints"]["weekday"] = override_blocks
    elif pname == "setpoints_weekend" and "setpoints" in schedule_details:
        schedule_details["setpoints"]["weekend"] = override_blocks

    # etc. Expand for infiltration, ventilation, or other schedule types
    # if row["param_name"] = "infiltration_weekday" => ...
    return


def assign_hvac_ideal_parameters(
    building_id=None,
    building_function=None,
    residential_type=None,
    non_residential_type=None,
    age_range=None,
    scenario=None,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_hvac=None,
    assigned_hvac_log=None
):
    """
    1) Look up default parameter ranges + schedule_details from hvac_lookup
       using (calibration_stage, scenario, building_function, subtype, age_range).
    2) Find user_config rows that override numeric setpoints or schedule blocks.
    3) Apply those overrides.
    4) Pick final numeric setpoints with pick_val_with_range(...).
    5) Build a dictionary "final_hvac_params" including:
       - heating_day_setpoint, cooling_day_setpoint, etc.
       - schedule_details (with possibly overridden time blocks).
    6) Optionally store it in assigned_hvac_log[bldg_id]["hvac_params"].
    7) Return final_hvac_params.
    """

    # For reproducibility if desired
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Lookup the base data in hvac_lookup
    if calibration_stage not in hvac_lookup:
        calibration_stage = "pre_calibration"
    stage_block = hvac_lookup[calibration_stage]

    if scenario not in stage_block:
        scenario = next(iter(stage_block.keys()))
    scenario_block = stage_block[scenario]

    if building_function not in scenario_block:
        building_function = next(iter(scenario_block.keys()))
    bf_block = scenario_block[building_function]

    # Decide subtype based on function
    if building_function.lower() == "residential":
        subtype = residential_type or next(iter(bf_block.keys()))
    else:
        subtype = non_residential_type or next(iter(bf_block.keys()))

    if subtype not in bf_block:
        subtype = next(iter(bf_block.keys()))
    sub_block = bf_block[subtype]

    if age_range not in sub_block:
        age_range = next(iter(sub_block.keys()))
    final_block = sub_block[age_range]

    # Extract base setpoint ranges
    heat_day_rng     = final_block.get("heating_day_setpoint_range", (20.0, 20.0))
    heat_night_rng   = final_block.get("heating_night_setpoint_range", (16.0, 16.0))
    cool_day_rng     = final_block.get("cooling_day_setpoint_range", (25.0, 25.0))
    cool_night_rng   = final_block.get("cooling_night_setpoint_range", (27.0, 27.0))
    max_heat_air_rng = final_block.get("max_heating_supply_air_temp_range", (50.0, 50.0))
    min_cool_air_rng = final_block.get("min_cooling_supply_air_temp_range", (13.0, 13.0))

    # Extract default schedule_details (which might contain multi-block definitions)
    schedule_details = final_block.get("schedule_details", {})

    # 2) Gather user_config overrides
    matches = find_hvac_overrides(
        building_id or 0,
        building_function or "",
        residential_type or "",
        non_residential_type or "",
        age_range or "",
        scenario or "",
        calibration_stage,
        user_config_hvac
    )

    # We'll store intermediate picks in local_log
    local_log = {}

    # 3) Apply overrides
    for row in matches:
        pname = row.get("param_name", "")

        # (A) Numeric setpoint overrides
        if pname == "heating_day_setpoint":
            heat_day_rng = override_numeric_range(heat_day_rng, row)
        elif pname == "heating_night_setpoint":
            heat_night_rng = override_numeric_range(heat_night_rng, row)
        elif pname == "cooling_day_setpoint":
            cool_day_rng = override_numeric_range(cool_day_rng, row)
        elif pname == "cooling_night_setpoint":
            cool_night_rng = override_numeric_range(cool_night_rng, row)
        elif pname == "max_heating_supply_air_temp":
            max_heat_air_rng = override_numeric_range(max_heat_air_rng, row)
        elif pname == "min_cooling_supply_air_temp":
            min_cool_air_rng = override_numeric_range(min_cool_air_rng, row)

        # (B) Schedule block overrides
        elif "override_blocks" in row:
            # This means we might override hvac_availability "weekday" or "weekend" blocks, etc.
            override_schedule_details(schedule_details, row)

        # else: skip if we don't recognize param_name

    # 4) Pick final numeric setpoints
    heating_day_setpoint = pick_val_with_range(
        heat_day_rng, strategy, local_log, param_name="heating_day_setpoint"
    )
    heating_night_setpoint = pick_val_with_range(
        heat_night_rng, strategy, local_log, param_name="heating_night_setpoint"
    )
    cooling_day_setpoint = pick_val_with_range(
        cool_day_rng, strategy, local_log, param_name="cooling_day_setpoint"
    )
    cooling_night_setpoint = pick_val_with_range(
        cool_night_rng, strategy, local_log, param_name="cooling_night_setpoint"
    )
    max_heating_supply_air_temp = pick_val_with_range(
        max_heat_air_rng, strategy, local_log, param_name="max_heating_supply_air_temp"
    )
    min_cooling_supply_air_temp = pick_val_with_range(
        min_cool_air_rng, strategy, local_log, param_name="min_cooling_supply_air_temp"
    )

    # 5) Build final dictionary
    final_hvac_params = {
        "heating_day_setpoint": heating_day_setpoint,
        "heating_day_setpoint_range": local_log["heating_day_setpoint_range"],

        "heating_night_setpoint": heating_night_setpoint,
        "heating_night_setpoint_range": local_log["heating_night_setpoint_range"],

        "cooling_day_setpoint": cooling_day_setpoint,
        "cooling_day_setpoint_range": local_log["cooling_day_setpoint_range"],

        "cooling_night_setpoint": cooling_night_setpoint,
        "cooling_night_setpoint_range": local_log["cooling_night_setpoint_range"],

        "max_heating_supply_air_temp": max_heating_supply_air_temp,
        "max_heating_supply_air_temp_range": local_log["max_heating_supply_air_temp_range"],

        "min_cooling_supply_air_temp": min_cooling_supply_air_temp,
        "min_cooling_supply_air_temp_range": local_log["min_cooling_supply_air_temp_range"],

        "schedule_details": schedule_details
    }

    # 6) Optionally store in assigned_hvac_log
    if assigned_hvac_log is not None and building_id is not None:
        if building_id not in assigned_hvac_log:
            assigned_hvac_log[building_id] = {}
        assigned_hvac_log[building_id]["hvac_params"] = final_hvac_params

    # 7) Return
    return final_hvac_params
