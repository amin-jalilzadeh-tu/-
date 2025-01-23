# geomz/assign_geometry_values.py

import random
from .geometry_lookup import geometry_lookup
from .geometry_overrides_from_excel import pick_geom_params_from_rules


def find_geom_overrides(building_id, building_type, user_config):
    """
    Returns any matching rows from user_config for the given building_id / building_type.
    Each override can define:
      - building_id (exact match, if provided)
      - building_type (exact match, if provided)
      - param_name in ["perimeter_depth", "has_core"]
      - min_val, max_val (for numeric overrides)
      - fixed_value (for boolean or "lock" numeric)
    """
    matches = []
    for row in (user_config or []):
        # Match building_id if specified
        if "building_id" in row:
            if row["building_id"] != building_id:
                continue
        # Match building_type if specified
        if "building_type" in row:
            if row["building_type"] != building_type:
                continue
        matches.append(row)
    return matches


def pick_val_with_range(
    rng_tuple,
    strategy="A",
    log_dict=None,      # e.g. assigned_geom_log[bldg_id]
    param_name=None
):
    """
    rng_tuple = (min_val, max_val)
    strategy  = "A" => midpoint
                "B" => random uniform
                else => pick min_val
    log_dict  => dictionary for logging (if not None)
    param_name=> e.g. "perimeter_depth"

    We log both the range and the final chosen value:
       log_dict["perimeter_depth_range"] = (2.0, 3.0)
       log_dict["perimeter_depth"]       = 2.45
    """
    min_v, max_v = rng_tuple

    if strategy == "A":         # midpoint
        chosen = (min_v + max_v) / 2.0
    elif strategy == "B":       # random uniform
        chosen = random.uniform(min_v, max_v)
    else:
        chosen = min_v          # fallback => min

    if log_dict is not None and param_name is not None:
        log_dict[f"{param_name}_range"] = (min_v, max_v)
        log_dict[param_name] = chosen

    return chosen


def assign_geometry_values(
    building_row,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config=None,         # optional list of partial overrides from JSON
    assigned_geom_log=None,   # dictionary for logging
    excel_rules=None          # optional excel-based geometry rules
):
    """
    1) Identify building_function => "residential" or "non_residential".
    2) Identify sub-type => read "residential_type" or "non_residential_type".
    3) Start from geometry_lookup[ building_function ][ sub_type ][ calibration_stage ] => param_dict
       e.g. { "perimeter_depth_range": (2.0,3.0), "has_core": False }
    4) If excel_rules => override further (pick_geom_params_from_rules(...)).
    5) If user_config => partial override for "perimeter_depth" or "has_core".
       - If param_name="perimeter_depth" with min_val & max_val => update perimeter_depth_range.
         If "fixed_value":true => interpret it as (min_val, min_val) => no randomness.
       - If param_name="has_core" and fixed_value => set has_core = that boolean
    6) We pick final perimeter_depth using pick_val_with_range(...).
    7) Return a dictionary => {"perimeter_depth": X, "has_core": Y}.
    8) Log final picks (and numeric range) in assigned_geom_log if provided.
    """

    # optional reproducibility
    if random_seed is not None:
        random.seed(random_seed)

    bldg_id        = building_row.get("ogc_fid", 0)
    bldg_function  = building_row.get("building_function", "residential").lower()
    area           = building_row.get("area", 100.0)
    perimeter      = building_row.get("perimeter", 40.0)

    # 1) get sub-type
    if bldg_function == "residential":
        sub_type = building_row.get("residential_type", "Two-and-a-half-story House")
        dict_for_function = geometry_lookup.get("residential", {}).get(sub_type, {})
    else:
        sub_type = building_row.get("non_residential_type", "Office Function")
        dict_for_function = geometry_lookup.get("non_residential", {}).get(sub_type, {})

    # 2) if calibration_stage not found => fallback
    if calibration_stage not in dict_for_function:
        param_dict = {
            "perimeter_depth_range": (2.0, 3.0),
            "has_core": False
        }
    else:
        param_dict = dict_for_function[calibration_stage]

    # Start with these defaults
    perimeter_depth_range = param_dict.get("perimeter_depth_range", (2.0, 3.0))
    has_core_default      = param_dict.get("has_core", False)

    # 3) If excel_rules => apply
    if excel_rules:
        rule_result = pick_geom_params_from_rules(
            building_function=bldg_function,
            building_type=sub_type,
            area=area,
            perimeter=perimeter,
            all_rules=excel_rules,
            calibration_stage=calibration_stage
        )
        if rule_result:
            perimeter_depth_range = rule_result["perimeter_depth_range"]
            core_val = rule_result["has_core_override"]
            if core_val is not None:
                has_core_default = core_val

    # 4) Check user_config partial overrides
    matched_rows = []
    if user_config:
        matched_rows = find_geom_overrides(bldg_id, sub_type, user_config)

    for row in matched_rows:
        pname = row.get("param_name", "")
        if pname == "perimeter_depth":
            mn = row.get("min_val")
            mx = row.get("max_val")
            if mn is not None and mx is not None:
                # If "fixed_value": true => make it (mn, mn)
                if row.get("fixed_value") is True:
                    perimeter_depth_range = (mn, mn)
                else:
                    perimeter_depth_range = (mn, mx)

        elif pname == "has_core":
            val = row.get("fixed_value")
            if val is not None:
                has_core_default = bool(val)

    # 5) Logging dict
    if assigned_geom_log is not None and bldg_id not in assigned_geom_log:
        assigned_geom_log[bldg_id] = {}
    log_dict = assigned_geom_log[bldg_id] if assigned_geom_log and bldg_id else None

    # 6) Pick final perimeter_depth
    perimeter_depth = pick_val_with_range(
        rng_tuple=perimeter_depth_range,
        strategy=strategy,
        log_dict=log_dict,
        param_name="perimeter_depth"
    )

    # 7) has_core => store directly
    if log_dict is not None:
        log_dict["has_core"] = has_core_default

    # 8) Return final dictionary
    result = {
        "perimeter_depth": perimeter_depth,
        "has_core": has_core_default
    }
    return result
