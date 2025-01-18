# wshading/shading_overrides_from_excel.py

"""
If you want to read shading overrides from an Excel file 
(e.g., different blind angles per season, or custom user settings 
for certain building IDs), you can do that here.

Analogous to geometry_overrides_from_excel.py or dict_override_excel.py:
- parse the Excel
- store each row in a rules dictionary
- 'pick_shading_params_from_rules' uses those rules to find 
  the best match for a building/window context
"""

import pandas as pd

def read_shading_overrides_excel(excel_path):
    """
    Reads an Excel file containing shading override rules.
    Example columns might be:
        building_id
        shading_type_key
        slat_angle_deg_min
        slat_angle_deg_max
        ...
    Returns a list of dict rules, each describing a row from the sheet.
    """
    df = pd.read_excel(excel_path)

    # We define a minimal required set of columns
    required_cols = ["building_id", "shading_type_key"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in shading_overrides Excel: {missing}")

    override_rules = []
    for _, row in df.iterrows():
        # Build a single dictionary from the row
        rule = {}
        rule["building_id"] = str(row["building_id"]).strip()  # or int if you prefer
        rule["shading_type_key"] = str(row["shading_type_key"]).strip()
        
        # If present, read additional fields like slat_angle_deg_min/max
        if "slat_angle_deg_min" in df.columns and "slat_angle_deg_max" in df.columns:
            min_ang = row["slat_angle_deg_min"]
            max_ang = row["slat_angle_deg_max"]
            if pd.notna(min_ang) and pd.notna(max_ang):
                rule["slat_angle_deg_range"] = (float(min_ang), float(max_ang))
        
        # Similarly for other shading parameters
        # if "slat_width_min" in df.columns, etc.

        override_rules.append(rule)

    return override_rules


def pick_shading_params_from_rules(
    building_id,
    shading_type_key,
    all_rules,
    fallback=None
):
    """
    Look through the list of override_rules (from read_shading_overrides_excel) 
    to find a matching rule for this building_id and shading_type_key.
    Returns a dict of override fields or 'fallback' if none found.

    Example override dict might look like:
        {
          "slat_angle_deg_range": (30, 60),
          ...
        }
    """
    best_rule = None
    for rule in all_rules:
        # building_id must match
        if str(rule.get("building_id", "")).lower() != str(building_id).lower():
            continue
        # shading_type_key must match
        if str(rule.get("shading_type_key", "")).lower() != shading_type_key.lower():
            continue
        # If multiple matches, we can pick the last or first. Let's pick the last match for demonstration.
        best_rule = rule

    if best_rule is None:
        return fallback

    # remove the top-level fields "building_id" and "shading_type_key"
    # the rest are actual overrides
    overrides = dict(best_rule)
    overrides.pop("building_id", None)
    overrides.pop("shading_type_key", None)

    return overrides
