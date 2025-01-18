# geomz\geometry_overrides_from_excel.py
import pandas as pd
import copy
import math

def read_geometry_overrides_excel(excel_path):
    """
    Reads an Excel file with geometry rules for perimeter depth & has_core 
    based on building_function, building_type, area, perimeter, etc.

    Returns a list (or dataframe) of rules, each rule a dict:
      {
        "building_function": "residential",
        "building_type": "Two-and-a-half-story House",
        "min_area": 0.0,
        "max_area": 999.0,
        "min_perimeter": 0.0,
        "max_perimeter": 999.0,
        "perimeter_depth_min": 2.0,
        "perimeter_depth_max": 3.0,
        "has_core_value": True/False/None
        ...
      }
    """
    df = pd.read_excel(excel_path)

    # You can define required columns or handle them gracefully
    required_cols = [
        "building_function",
        "building_type",
        "min_area",
        "max_area",
        "min_perimeter",
        "max_perimeter",
        "perimeter_depth_min",
        "perimeter_depth_max",
        "has_core_value"
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in geometry_overrides.xlsx: {missing}")

    # Convert each row to a dict
    rules = []
    for _, row in df.iterrows():
        # e.g. if has_core_value is "True"/"False"/"None" in Excel, convert it properly
        has_core_raw = row["has_core_value"]
        if pd.isna(has_core_raw):
            has_core_val = None
        else:
            # attempt to parse "True"/"False" or just store as bool
            # or None if you want no override
            if str(has_core_raw).strip().lower() in ["true", "1"]:
                has_core_val = True
            elif str(has_core_raw).strip().lower() in ["false", "0"]:
                has_core_val = False
            else:
                has_core_val = None

        rule = {
            "building_function": str(row["building_function"]).strip().lower(),
            "building_type": str(row["building_type"]).strip(),
            "min_area": float(row["min_area"]),
            "max_area": float(row["max_area"]),
            "min_perimeter": float(row["min_perimeter"]),
            "max_perimeter": float(row["max_perimeter"]),
            "perimeter_depth_min": float(row["perimeter_depth_min"]),
            "perimeter_depth_max": float(row["perimeter_depth_max"]),
            "has_core_value": has_core_val
        }
        rules.append(rule)

    return rules

def pick_geom_params_from_rules(
    building_function,
    building_type,
    area,
    perimeter,
    all_rules,
    calibration_stage=None
):
    """
    Finds the first (or last) matching rule among all_rules that covers:
      - building_function
      - building_type (if not empty)
      - calibration_stage (if present in rule and function call)
      - area in [min_area, max_area]
      - perimeter in [min_perimeter, max_perimeter]

    Returns a dict with {
      "perimeter_depth_range": (x, y),
      "has_core_override": True/False/None
    }
    or None if no rule matched.
    """
    # Convert to lower if needed
    building_function_lower = building_function.lower() if building_function else ""
    building_type_str = building_type or ""

    best_rule = None
    for rule in all_rules:
        # 1) building_function must match
        rule_func_lower = str(rule["building_function"]).strip().lower()
        if rule_func_lower != building_function_lower:
            continue

        # 2) building_type must match (if rule has one)
        rule_type_str = str(rule["building_type"]).strip()
        if rule_type_str and rule_type_str != building_type_str:
            continue

        # 3) calibration_stage must match if it's present in the rule & we are filtering by stage
        if calibration_stage is not None and "calibration_stage" in rule:
            rule_stage_str = str(rule["calibration_stage"]).strip()
            # If rule specifies a stage, skip if it doesn't match
            if rule_stage_str and rule_stage_str != calibration_stage:
                continue

        # 4) Check area
        if not (rule["min_area"] <= area <= rule["max_area"]):
            continue

        # 5) Check perimeter
        if not (rule["min_perimeter"] <= perimeter <= rule["max_perimeter"]):
            continue

        # If we get here => rule matches
        best_rule = rule
        # If you want the *first* matching rule, add 'break'. 
        # If you want the *last* matching rule, let the loop continue.
        # break

    # If none matched => return None
    if best_rule is None:
        return None

    # Pull values from best_rule
    pmin = best_rule["perimeter_depth_min"]
    pmax = best_rule["perimeter_depth_max"]
    
    # has_core_value might be True, False, or None
    has_core_val = best_rule["has_core_value"]

    # Return the final picks
    return {
        "perimeter_depth_range": (pmin, pmax),
        # If None => do not override has_core
        "has_core_override": has_core_val  
    }
