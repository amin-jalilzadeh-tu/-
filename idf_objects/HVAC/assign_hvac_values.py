# HVAC/assign_hvac_values.py

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
    Returns a list of user_config rows that match the specified building_id, 
    building_function, etc.
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
    strategy  = "A" => midpoint, "B" => random, else => pick min_val.
    log_dict  => optional dict to store param_name_range + param_name => chosen_value
    param_name=> e.g. "heating_day_setpoint".

    Returns the chosen numeric value.
    Also logs (param_name + param_name_range) if log_dict is provided.
    """
    min_v, max_v = rng_tuple

    # Pick the final numeric value
    if strategy == "A":  # midpoint
        chosen = (min_v + max_v) / 2.0
    elif strategy == "B":
        chosen = random.uniform(min_v, max_v)
    else:
        chosen = min_v  # default => pick min

    # Store in the local log if provided
    if log_dict is not None and param_name is not None:
        log_dict[f"{param_name}_range"] = (min_v, max_v)
        log_dict[param_name] = chosen

    return chosen


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
    1) Looks up default parameter ranges from hvac_lookup using 
       (calibration_stage, scenario, building_function, subtype, age_range).
    2) Applies user_config overrides to update those ranges or fix values.
    3) Picks final values using pick_val_with_range(...).
    4) Builds a single dictionary 'final_hvac_params' that includes both the 
       final numeric picks and their ranges (e.g. "heating_day_setpoint_range").
    5) Optionally stores final_hvac_params in assigned_hvac_log[bldg_id]["hvac_params"].
    6) Returns final_hvac_params.

    The returned dict might look like:
    {
        "heating_day_setpoint": 20.2788,
        "heating_day_setpoint_range": (19.0, 21.0),
        "heating_night_setpoint": 15.0250,
        "heating_night_setpoint_range": (15.0, 16.0),
        ...
        "schedule_details": {
            "day_start": "07:00",
            "day_end": "23:00",
            "occupancy_schedule": {
                "weekday": "FullOccupancy",
                "weekend": "FullOccupancy"
            }
        }
    }
    """

    # For reproducibility if desired
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Fallback if stage not in hvac_lookup
    if calibration_stage not in hvac_lookup:
        calibration_stage = "pre_calibration"
    stage_block = hvac_lookup[calibration_stage]

    # scenario fallback
    if scenario not in stage_block:
        scenario = next(iter(stage_block.keys()))
    scenario_block = stage_block[scenario]

    # building_function fallback
    if building_function not in scenario_block:
        building_function = next(iter(scenario_block.keys()))
    bf_block = scenario_block[building_function]

    # Determine subtype
    # If building_function=="residential", use 'residential_type'
    # else use 'non_residential_type'
    if building_function and building_function.lower() == "residential":
        subtype = residential_type or next(iter(bf_block.keys()))
    else:
        subtype = non_residential_type or next(iter(bf_block.keys()))

    if subtype not in bf_block:
        subtype = next(iter(bf_block.keys()))
    sub_block = bf_block[subtype]

    # age_range fallback
    if age_range not in sub_block:
        age_range = next(iter(sub_block.keys()))
    final_block = sub_block[age_range]

    # final_block might have:
    # {
    #   "heating_day_setpoint_range": (19,21),
    #   ...
    #   "schedule_details": {...}
    # }

    # 2) Extract the base ranges
    heat_day_rng     = final_block.get("heating_day_setpoint_range", (20.0, 20.0))
    heat_night_rng   = final_block.get("heating_night_setpoint_range", (16.0, 16.0))
    cool_day_rng     = final_block.get("cooling_day_setpoint_range", (25.0, 25.0))
    cool_night_rng   = final_block.get("cooling_night_setpoint_range", (27.0, 27.0))
    max_heat_air_rng = final_block.get("max_heating_supply_air_temp_range", (50.0, 50.0))
    min_cool_air_rng = final_block.get("min_cooling_supply_air_temp_range", (13.0, 13.0))

    # schedule_details => might contain day/night times, occupancy, etc.
    schedule_details = final_block.get("schedule_details", {})

    # 3) Apply user_config overrides
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

    def override_range(current_range, row):
        """
        If row has fixed_value => (val,val),
        else if row has min_val & max_val => (min_val,max_val),
        else keep current_range.
        """
        if "fixed_value" in row and row["fixed_value"] is not None:
            v = row["fixed_value"]
            return (v, v)
        if "min_val" in row and "max_val" in row and row["min_val"] is not None and row["max_val"] is not None:
            return (row["min_val"], row["max_val"])
        return current_range

    # If we want to store picks in a local dictionary
    # (similar approach as with ventilation).
    local_log = {}

    for row in matches:
        pname = row.get("param_name", "")
        # Override numeric ranges
        if pname == "heating_day_setpoint":
            heat_day_rng = override_range(heat_day_rng, row)
        elif pname == "heating_night_setpoint":
            heat_night_rng = override_range(heat_night_rng, row)
        elif pname == "cooling_day_setpoint":
            cool_day_rng = override_range(cool_day_rng, row)
        elif pname == "cooling_night_setpoint":
            cool_night_rng = override_range(cool_night_rng, row)
        elif pname == "max_heating_supply_air_temp":
            max_heat_air_rng = override_range(max_heat_air_rng, row)
        elif pname == "min_cooling_supply_air_temp":
            min_cool_air_rng = override_range(min_cool_air_rng, row)

        # If schedule overrides exist, you might parse them similarly
        # e.g., if row["schedule_day_start"] => override schedule_details["day_start"]
        # etc. This depends on how you structure your user config.

    # 4) Pick final numeric values using pick_val_with_range
    heating_day_setpoint      = pick_val_with_range(heat_day_rng,     strategy, local_log, "heating_day_setpoint")
    heating_night_setpoint    = pick_val_with_range(heat_night_rng,   strategy, local_log, "heating_night_setpoint")
    cooling_day_setpoint      = pick_val_with_range(cool_day_rng,     strategy, local_log, "cooling_day_setpoint")
    cooling_night_setpoint    = pick_val_with_range(cool_night_rng,   strategy, local_log, "cooling_night_setpoint")
    max_heating_supply_air_temp=pick_val_with_range(max_heat_air_rng, strategy, local_log, "max_heating_supply_air_temp")
    min_cooling_supply_air_temp=pick_val_with_range(min_cool_air_rng, strategy, local_log, "min_cooling_supply_air_temp")

    # 5) Build a single dictionary with final picks + ranges + schedule_details
    final_hvac_params = {
        "heating_day_setpoint": local_log["heating_day_setpoint"],
        "heating_day_setpoint_range": local_log["heating_day_setpoint_range"],

        "heating_night_setpoint": local_log["heating_night_setpoint"],
        "heating_night_setpoint_range": local_log["heating_night_setpoint_range"],

        "cooling_day_setpoint": local_log["cooling_day_setpoint"],
        "cooling_day_setpoint_range": local_log["cooling_day_setpoint_range"],

        "cooling_night_setpoint": local_log["cooling_night_setpoint"],
        "cooling_night_setpoint_range": local_log["cooling_night_setpoint_range"],

        "max_heating_supply_air_temp": local_log["max_heating_supply_air_temp"],
        "max_heating_supply_air_temp_range": local_log["max_heating_supply_air_temp_range"],

        "min_cooling_supply_air_temp": local_log["min_cooling_supply_air_temp"],
        "min_cooling_supply_air_temp_range": local_log["min_cooling_supply_air_temp_range"],

        # Insert schedule details as-is
        "schedule_details": schedule_details
    }

    # 6) Store in assigned_hvac_log if desired
    if assigned_hvac_log is not None and building_id is not None:
        if building_id not in assigned_hvac_log:
            assigned_hvac_log[building_id] = {}
        # We store it like "hvac_params" for building-level picks
        assigned_hvac_log[building_id]["hvac_params"] = final_hvac_params

    # 7) Return the consolidated dictionary
    return final_hvac_params
