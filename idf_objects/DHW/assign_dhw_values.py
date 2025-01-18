# DHW/assign_dhw_values.py

import random
from .dhw_lookup import dhw_lookup

def find_dhw_overrides(building_id, dhw_key, user_config):
    """
    Helper function to search user_config_dhw for any overrides 
    specific to this building_id and dhw_key.
    Each row in user_config might look like:
      {
        "building_id": 4136730,
        "dhw_key": "Apartment",
        "param_name": "liters_per_person_per_day",
        "fixed_value": 52.0
      }
      or
      {
        "dhw_key": "Apartment",
        "param_name": "liters_per_person_per_day",
        "min_val": 50.0,
        "max_val": 55.0
      }
      etc.
    """
    matches = []
    for row in (user_config or []):
        # If building_id is specified and doesn't match => skip
        if "building_id" in row and row["building_id"] is not None:
            if row["building_id"] != building_id:
                continue
        # If dhw_key is specified and doesn't match => skip
        if "dhw_key" in row and row["dhw_key"] is not None:
            if row["dhw_key"] != dhw_key:
                continue
        matches.append(row)
    return matches

def pick_val_with_range(
    rng_tuple,
    strategy: str = "A",
    log_dict: dict = None,      # dictionary to store final value & range
    param_name: str = None      # e.g. "liters_per_person_per_day"
):
    """
    rng_tuple = (min_val, max_val)
    strategy  = "A" => pick midpoint
                "B" => random.uniform(min_val, max_val)
                else => pick min_val as fallback

    If log_dict is provided, store the final chosen value and (min_val, max_val)
    in e.g. log_dict[param_name] and log_dict[f"{param_name}_range"].

    If both min_val and max_val are None => final value is None (no range).
    """
    if rng_tuple is None or len(rng_tuple) < 2:
        # No valid range => just skip
        chosen = None
        if log_dict is not None and param_name:
            log_dict[f"{param_name}_range"] = (None, None)
            log_dict[param_name] = None
        return chosen

    min_val, max_val = rng_tuple

    # If both sides are None => no data
    if min_val is None and max_val is None:
        chosen = None
        if log_dict is not None and param_name:
            log_dict[f"{param_name}_range"] = (None, None)
            log_dict[param_name] = None
        return chosen

    # Otherwise, pick based on strategy
    if strategy == "A":  
        chosen = (min_val + max_val) / 2.0  # midpoint
    elif strategy == "B":  
        chosen = random.uniform(min_val, max_val)
    else:
        chosen = min_val  # fallback => pick lower bound

    # Store in the log if provided
    if log_dict is not None and param_name is not None:
        log_dict[f"{param_name}_range"] = (min_val, max_val)
        log_dict[param_name] = chosen

    return chosen

def assign_dhw_parameters(
    building_id: int,
    dhw_key: str,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: int = None,
    user_config_dhw: list = None,
    assigned_dhw_log: dict = None,
    building_row: dict = None,
    use_nta: bool = False
):
    """
    Returns a dict of selected DHW parameter values from dhw_lookup + user overrides:

      - occupant_density_m2_per_person
      - liters_per_person_per_day
      - default_tank_volume_liters
      - default_heater_capacity_w
      - setpoint_c
      - usage_split_factor
      - peak_hours
      - sched_morning
      - sched_peak
      - sched_afternoon
      - sched_evening

    Steps:
      1) Identify param ranges from dhw_lookup[calibration_stage][dhw_key], or fallback.
      2) Gather user_config overrides (if any) => override param ranges.
      3) Possibly compute occupant density from building_row if none is found.
      4) Use the chosen strategy ("A", "B", fallback) to pick final numeric values.
      5) If use_nta=True => do occupant-based usage override for residential.
      6) Return a dict with final picks. Also store them in assigned_dhw_log if provided.
    """

    # optional reproducibility
    if random_seed is not None:
        random.seed(random_seed)

    # Ensure assigned_dhw_log has a subdict for building_id
    if assigned_dhw_log is not None and building_id is not None:
        if building_id not in assigned_dhw_log:
            assigned_dhw_log[building_id] = {}

    # 1) Determine calibration stage => fallback to "pre_calibration"
    if calibration_stage not in dhw_lookup:
        calibration_stage = "pre_calibration"
    stage_dict = dhw_lookup[calibration_stage]

    # If dhw_key not found => fallback with typical values
    if dhw_key not in stage_dict:
        fallback = {
            "occupant_density_m2_per_person": None,
            "liters_per_person_per_day": 50.0,
            "default_tank_volume_liters": 200.0,
            "default_heater_capacity_w": 4000.0,
            "setpoint_c": 60.0,
            "usage_split_factor": 0.6,
            "peak_hours": 2.0,
            "sched_morning": 0.7,
            "sched_peak": 1.0,
            "sched_afternoon": 0.2,
            "sched_evening": 0.8
        }
        # Log these if we want
        if assigned_dhw_log is not None and building_id is not None:
            for k, v in fallback.items():
                assigned_dhw_log[building_id][k] = v
                assigned_dhw_log[building_id][f"{k}_range"] = (v, v)
        return fallback

    # Found param ranges
    param_ranges = stage_dict[dhw_key]

    # 2) Gather user config overrides
    matches = find_dhw_overrides(building_id, dhw_key, user_config_dhw)

    def override_range(current_range, override_dict):
        """
        Convert override row to new (min_val, max_val) or (fixed_value, fixed_value).
        """
        if "fixed_value" in override_dict:
            fv = override_dict["fixed_value"]
            return (fv, fv)
        # If they give us min_val & max_val
        if "min_val" in override_dict and "max_val" in override_dict:
            return (override_dict["min_val"], override_dict["max_val"])
        return current_range

    # Extract param ranges from param_ranges
    occdens_rng = param_ranges.get("occupant_density_m2_per_person_range", (None, None))
    liters_rng  = param_ranges.get("liters_per_person_per_day_range", (50.0, 50.0))
    vol_rng     = param_ranges.get("default_tank_volume_liters_range", (200.0, 200.0))
    cap_rng     = param_ranges.get("default_heater_capacity_w_range", (4000.0, 4000.0))
    setp_rng    = param_ranges.get("setpoint_c_range", (60.0, 60.0))
    usplit_rng  = param_ranges.get("usage_split_factor_range", (0.6, 0.6))
    peak_rng    = param_ranges.get("peak_hours_range", (2.0, 2.0))

    sched_morn_rng   = param_ranges.get("sched_morning_range", (0.7, 0.7))
    sched_peak_rng   = param_ranges.get("sched_peak_range", (1.0, 1.0))
    sched_aftern_rng = param_ranges.get("sched_afternoon_range", (0.2, 0.2))
    sched_even_rng   = param_ranges.get("sched_evening_range", (0.8, 0.8))

    # 2b) Apply user_config overrides
    for row in matches:
        pname = row.get("param_name")
        if pname == "occupant_density_m2_per_person":
            occdens_rng = override_range(occdens_rng, row)
        elif pname == "liters_per_person_per_day":
            liters_rng = override_range(liters_rng, row)
        elif pname == "default_tank_volume_liters":
            vol_rng = override_range(vol_rng, row)
        elif pname == "default_heater_capacity_w":
            cap_rng = override_range(cap_rng, row)
        elif pname == "setpoint_c":
            setp_rng = override_range(setp_rng, row)
        elif pname == "usage_split_factor":
            usplit_rng = override_range(usplit_rng, row)
        elif pname == "peak_hours":
            peak_rng = override_range(peak_rng, row)
        elif pname == "sched_morning":
            sched_morn_rng = override_range(sched_morn_rng, row)
        elif pname == "sched_peak":
            sched_peak_rng = override_range(sched_peak_rng, row)
        elif pname == "sched_afternoon":
            sched_aftern_rng = override_range(sched_aftern_rng, row)
        elif pname == "sched_evening":
            sched_even_rng = override_range(sched_even_rng, row)

    # 3) If building is Residential & occupant_density is (None, None), compute from building_row
    if building_row is not None:
        bldg_func = str(building_row.get("building_function", "")).lower()
        if "residential" in bldg_func:
            area = building_row.get("area", 80.0)
            occupant_count = building_row.get("occupant_count", None)
            if occupant_count is None:
                occupant_count = 1
                if area > 50:
                    occupant_count += 0.01 * (area - 50)
                occupant_count = max(1, occupant_count)

            if occdens_rng == (None, None):
                occupant_density_val = area / occupant_count
                occupant_density_min = 0.9 * occupant_density_val
                occupant_density_max = 1.1 * occupant_density_val
                occdens_rng = (occupant_density_min, occupant_density_max)

    # 4) Now pick final numeric values for each parameter
    #    Storing them in assigned_dhw_log[building_id] if provided.
    logd = assigned_dhw_log[building_id] if (assigned_dhw_log and building_id in assigned_dhw_log) else None

    occupant_density = pick_val_with_range(occdens_rng, strategy, logd, "occupant_density_m2_per_person")
    liters_pp_day    = pick_val_with_range(liters_rng,  strategy, logd, "liters_per_person_per_day")
    tank_vol         = pick_val_with_range(vol_rng,     strategy, logd, "default_tank_volume_liters")
    heater_cap       = pick_val_with_range(cap_rng,     strategy, logd, "default_heater_capacity_w")
    setpoint_c       = pick_val_with_range(setp_rng,    strategy, logd, "setpoint_c")
    usage_split      = pick_val_with_range(usplit_rng,  strategy, logd, "usage_split_factor")
    peak_hrs         = pick_val_with_range(peak_rng,    strategy, logd, "peak_hours")

    sch_morn = pick_val_with_range(sched_morn_rng,   strategy, logd, "sched_morning")
    sch_peak = pick_val_with_range(sched_peak_rng,   strategy, logd, "sched_peak")
    sch_after= pick_val_with_range(sched_aftern_rng, strategy, logd, "sched_afternoon")
    sch_even = pick_val_with_range(sched_even_rng,   strategy, logd, "sched_evening")

    # 5) If use_nta => override occupant usage from building_row in a second pass
    if use_nta and (building_row is not None):
        bfunc = str(building_row.get("building_function", "")).lower()
        area  = building_row.get("area", 80.0)

        if "residential" in bfunc:
            # occupant_count from area
            if area <= 50:
                occupant_count = 1
            else:
                occupant_count = 1 + 0.01 * (area - 50)
            occupant_count = max(1, occupant_count)

            occupant_density = area / occupant_count
            total_daily_liters = occupant_count * 45.0
            liters_pp_day = total_daily_liters / occupant_count

            # Update log if present
            if logd is not None:
                logd["liters_per_person_per_day"] = liters_pp_day
                logd["occupant_density_m2_per_person"] = occupant_density

        else:
            # Non-res => annual or daily usage from area-based approach
            nrtype = dhw_key
            # Or building_row.get("non_residential_type", "")
            factor_kwh = dhw_lookup["TABLE_13_1_KWH_PER_M2"].get(nrtype, 1.4)
            annual_kwh = factor_kwh * area
            annual_liters = annual_kwh * 13.76
            daily_liters  = annual_liters / 365.0

            if occupant_density and occupant_density > 0:
                occupant_count = max(1, area / occupant_density)
                new_liters_pp_day = daily_liters / occupant_count
            else:
                occupant_count = 1
                occupant_density = area
                new_liters_pp_day = daily_liters

            liters_pp_day = new_liters_pp_day
            if logd is not None:
                logd["liters_per_person_per_day"] = liters_pp_day
                logd["occupant_density_m2_per_person"] = occupant_density

    # 6) Return final picks
    result = {
        "occupant_density_m2_per_person": occupant_density,
        "liters_per_person_per_day":      liters_pp_day,
        "default_tank_volume_liters":     tank_vol,
        "default_heater_capacity_w":      heater_cap,
        "setpoint_c":                     setpoint_c,
        "usage_split_factor":             usage_split,
        "peak_hours":                     peak_hrs,

        "sched_morning":   sch_morn,
        "sched_peak":      sch_peak,
        "sched_afternoon": sch_after,
        "sched_evening":   sch_even
    }
    return result
