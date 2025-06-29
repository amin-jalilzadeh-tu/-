"""
shading_overrides_from_excel.py

If you want to read shading overrides from an Excel file (e.g., different
blind angles per season, or custom user settings for certain building IDs),
you can do that here.

Analogous to geometry_overrides_from_excel.py or dict_override_excel.py:
 - parse the Excel
 - store each row in a rules dictionary
 - 'pick_shading_params_from_rules' uses those rules to find
   the best match for a building/window context
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

def read_shading_overrides_excel(excel_path):
    """
    Reads an Excel file containing shading override rules.

    Example columns might be:
        building_id
        shading_type_key
        slat_angle_deg_min
        slat_angle_deg_max
        slat_width  # Example of a single value override
        # ... other parameters ...

    Returns
    -------
    list
        A list of dictionaries, where each dictionary represents a row (a rule)
        from the Excel sheet. Returns an empty list if the file cannot be read
        or is empty.
    
    Raises
    ------
    ValueError
        If required columns are missing.
    """
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        logger.error(f"Excel override file not found: {excel_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading Excel override file {excel_path}: {e}")
        return []

    if df.empty:
        logger.warning(f"Shading overrides Excel file is empty: {excel_path}")
        return []

    # We define a minimal required set of columns
    required_cols = ["building_id", "shading_type_key"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in shading_overrides Excel ({excel_path}): {missing}")

    override_rules = []
    for index, row in df.iterrows():
        rule = {}
        try:
            rule["building_id"] = str(row["building_id"]).strip()
            rule["shading_type_key"] = str(row["shading_type_key"]).strip()

            # --- Handle range parameters ---
            # Example: slat_angle_deg_range
            if "slat_angle_deg_min" in df.columns and "slat_angle_deg_max" in df.columns:
                min_ang = row["slat_angle_deg_min"]
                max_ang = row["slat_angle_deg_max"]
                if pd.notna(min_ang) and pd.notna(max_ang):
                    try:
                        rule["slat_angle_deg_range"] = (float(min_ang), float(max_ang))
                    except ValueError:
                        logger.warning(
                            f"Invalid float value for slat_angle_deg_min/max in Excel row {index + 2}. "
                            f"Skipping slat_angle_deg_range for this rule."
                        )
                elif pd.notna(min_ang) or pd.notna(max_ang):
                    logger.warning(
                        f"Partial slat_angle_deg_min/max definition in Excel row {index + 2}. "
                        f"Both must be provided. Skipping slat_angle_deg_range for this rule."
                    )
            
            # TODO: Add more explicit range parameter handling here if needed
            # Example for another range parameter "parameter_foo_range":
            # if "parameter_foo_min" in df.columns and "parameter_foo_max" in df.columns:
            #     min_val = row["parameter_foo_min"]
            #     max_val = row["parameter_foo_max"]
            #     if pd.notna(min_val) and pd.notna(max_val):
            #         try:
            #             rule["parameter_foo_range"] = (float(min_val), float(max_val))
            #         except ValueError:
            #              logger.warning(f"Invalid float for parameter_foo_min/max in Excel row {index + 2}.")
            #     elif pd.notna(min_val) or pd.notna(max_val):
            #         logger.warning(f"Partial parameter_foo_min/max in Excel row {index + 2}.")


            # --- Handle single value parameters ---
            # Add other specific single-value parameters that can be overridden from Excel.
            # Ensure they are parsed to the correct type.
            # Example:
            # if "slat_width" in df.columns and pd.notna(row["slat_width"]):
            #     try:
            #         rule["slat_width"] = float(row["slat_width"])
            #     except ValueError:
            #         logger.warning(f"Invalid float value for slat_width in Excel row {index + 2}. Skipping.")
            
            # Generic approach: Add all other non-empty columns from the Excel row to the rule.
            # These will be used as direct overrides in `pick_shading_params`.
            # The `pick_shading_params` function will then decide how to use them (e.g., if it's a range or single value).
            for col_name in df.columns:
                if col_name not in required_cols and \
                   not col_name.endswith(("_min", "_max")) and \
                   col_name not in rule and \
                   pd.notna(row[col_name]):
                    rule[col_name] = row[col_name] # Keep original type for now, or convert as needed

            override_rules.append(rule)
        except Exception as e:
            logger.error(f"Error processing row {index + 2} in {excel_path}: {e}. Skipping this rule.")
            continue
            
    return override_rules


def pick_shading_params_from_rules(
    building_id,
    shading_type_key,
    all_rules,
    fallback=None
):
    """
    Looks through the list of override_rules (from read_shading_overrides_excel)
    to find a matching rule for the given building_id and shading_type_key.

    The matching is case-insensitive for building_id and shading_type_key.
    If multiple rules match, the last one found in the `all_rules` list takes precedence.

    Parameters
    ----------
    building_id : str or int
        The identifier of the building.
    shading_type_key : str
        The key identifying the type of shading (e.g., "my_external_louvers").
    all_rules : list
        A list of rule dictionaries, typically from `read_shading_overrides_excel`.
    fallback : any, optional
        Value to return if no matching rule is found. Defaults to None.

    Returns
    -------
    dict or any
        A dictionary containing the override parameters if a match is found.
        These parameters are the ones to be applied, excluding "building_id"
        and "shading_type_key". Returns `fallback` if no rule matches.
        Example override dict: {"slat_angle_deg_range": (30, 60), "slat_width": 0.05}
    """
    if not all_rules:
        return fallback

    best_rule_content = None
    building_id_str = str(building_id).lower()
    shading_type_key_str = str(shading_type_key).lower()

    for rule in all_rules:
        # building_id must match (case-insensitive)
        rule_building_id = str(rule.get("building_id", "")).lower()
        if rule_building_id != building_id_str:
            continue

        # shading_type_key must match (case-insensitive)
        rule_shading_type_key = str(rule.get("shading_type_key", "")).lower()
        if rule_shading_type_key != shading_type_key_str:
            continue
        
        # If we are here, both IDs matched.
        # The last match in the list takes precedence.
        current_overrides = dict(rule)
        current_overrides.pop("building_id", None)
        current_overrides.pop("shading_type_key", None)
        best_rule_content = current_overrides

    if best_rule_content is None:
        return fallback

    return best_rule_content