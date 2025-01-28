"""
fenestration_structuring.py

This module provides a function to transform the flat 'assigned_fenez_params.csv'
into a structured CSV that merges final assigned values with min/max ranges
for each parameter, and associates them with E+ object type/name.

You can run it stand-alone or call it from your main script.

Usage:
    from idf_objects.structuring.fenestration_structuring import transform_fenez_log_to_structured_with_ranges

    transform_fenez_log_to_structured_with_ranges(
        csv_input="output/assigned/assigned_fenez_params.csv",
        csv_output="output/assigned/structured_fenez_params.csv"
    )
"""

import pandas as pd
import ast  # For safely parsing "(4.0, 5.0)" as a Python tuple

def transform_fenez_log_to_structured_with_ranges(
    csv_input="output/assigned/assigned_fenez_params.csv",
    csv_output="output/assigned/structured_fenez_params.csv",
):
    """
    Reads the 'flat' fenestration/material CSV (with param_name & assigned_value),
    and outputs a 'structured' CSV that:

      - Merges final assigned value + min/max range into one row per parameter.
      - Does NOT skip params that have empty or None values.
      - Always includes a row for any param that appears in the CSV, even if
        there's no final value or no range.

    Final columns in the output CSV:
        ogc_fid, sub_key, eplus_object_type, eplus_object_name,
        param_name, param_value, param_min, param_max

    - "sub_key" is something like "windows_opq" or "exterior_wall_win",
      derived from e.g. "fenez_exterior_wall_opq.Thickness".
    - "eplus_object_type" and "eplus_object_name" come from lines like 
      "fenez_exterior_wall_opq.obj_type" and "fenez_exterior_wall_opq.Name".
    - "param_name" is the base parameter (like "Thickness"), or just "wwr",
      or "obj_type" if you want to store them as param rows.
    - "param_value" is the final assigned numeric or string value.
    - "param_min" and "param_max" come from lines that end with "_range".
    """

    df = pd.read_csv(csv_input)

    # We'll keep track of data in a nested dict:
    # final_dict[(ogc_fid, sub_key)] = {
    #   "obj_type": <str or None>,
    #   "obj_name": <str or None>,
    #   "params": {
    #       "Thickness": {
    #          "value": <final assigned value or None>,
    #          "min": <float or None>,
    #          "max": <float or None>
    #       },
    #       "Conductivity": {...},
    #       etc.
    #   }
    # }

    final_dict = {}

    def get_subdict(fid, s_key):
        """Helper to retrieve or create the dictionary entry for (fid, s_key)."""
        if (fid, s_key) not in final_dict:
            final_dict[(fid, s_key)] = {
                "obj_type": None,
                "obj_name": None,
                "params": {}
            }
        return final_dict[(fid, s_key)]

    for i, row in df.iterrows():
        # Must have these columns
        if "ogc_fid" not in row or "param_name" not in row or "assigned_value" not in row:
            continue

        ogc_fid = row["ogc_fid"]
        param_name = str(row["param_name"])
        assigned_value = row["assigned_value"]

        # We only transform if param_name starts with "fenez_"
        # (Otherwise, skip non-fenestration logs.)
        if not param_name.startswith("fenez_"):
            continue

        # Remove the "fenez_" prefix => e.g. "doors_opq.Thermal_Resistance_range"
        remainder = param_name[len("fenez_"):]  # e.g. "doors_opq.Thermal_Resistance_range"

        if "." in remainder:
            sub_key, field = remainder.split(".", 1)
        else:
            # e.g. "wwr", "roughness" => treat them as sub_key=<that word>, no field
            sub_key = remainder
            field = None

        # Retrieve or create sub-dict for (ogc_fid, sub_key)
        subd = get_subdict(ogc_fid, sub_key)

        # (A) If this row indicates the E+ object type => e.g. "obj_type"
        if field == "obj_type":
            subd["obj_type"] = assigned_value

        # (B) If this row indicates the E+ object name => e.g. "Name"
        elif field == "Name":
            subd["obj_name"] = assigned_value

        # (C) If the field ends with "_range", parse as (min,max)
        elif field and field.endswith("_range"):
            # e.g. "Thermal_Resistance_range"
            base_param = field.replace("_range", "")  # => "Thermal_Resistance"

            if base_param not in subd["params"]:
                subd["params"][base_param] = {"value": None, "min": None, "max": None}

            # assigned_value might be something like "(4.0, 5.0)" or maybe "None"
            try:
                maybe_tuple = ast.literal_eval(str(assigned_value))
                if isinstance(maybe_tuple, (list, tuple)) and len(maybe_tuple) == 2:
                    min_val, max_val = maybe_tuple
                    subd["params"][base_param]["min"] = min_val
                    subd["params"][base_param]["max"] = max_val
            except:
                pass  # If parse fails or it's "None", we leave them as None

        # (D) If it's a 'normal' field => param_name like "Thermal_Resistance" or "wwr"
        else:
            if field is None:
                # e.g. remainder="wwr". We'll store param_name = "wwr"
                p_name = sub_key  # "wwr"
                if p_name not in subd["params"]:
                    subd["params"][p_name] = {"value": None, "min": None, "max": None}
                subd["params"][p_name]["value"] = assigned_value
            else:
                # e.g. field="Thermal_Resistance", assigned_value=4.23
                if field not in subd["params"]:
                    subd["params"][field] = {"value": None, "min": None, "max": None}
                subd["params"][field]["value"] = assigned_value

    # Now finalize. We'll produce a row for **every** param in subd["params"].
    structured_rows = []
    for (fid, s_key), info in final_dict.items():
        obj_type = info["obj_type"]
        obj_name = info["obj_name"]
        params = info["params"]  # e.g. { "Thickness": {"value":..., "min":..., "max":...} }

        if not params:
            # If no params => skip. (Or you can make a row with param_name="(none)".)
            continue

        for p_name, pvals in params.items():
            param_value = pvals["value"]
            param_min   = pvals["min"]
            param_max   = pvals["max"]

            structured_rows.append({
                "ogc_fid":            fid,
                "sub_key":            s_key,
                "eplus_object_type":  obj_type,
                "eplus_object_name":  obj_name,
                "param_name":         p_name,
                "param_value":        param_value,
                "param_min":          param_min,
                "param_max":          param_max
            })

    # Convert to DataFrame
    df_out = pd.DataFrame(structured_rows)

    # Attempt to convert param_value, param_min, param_max to float if possible
    def try_float(x):
        try:
            return float(x)
        except:
            return x

    for col in ["param_value", "param_min", "param_max"]:
        df_out[col] = df_out[col].apply(try_float)

    # Save
    df_out.to_csv(csv_output, index=False)
    print(f"[transform_fenez_log_to_structured_with_ranges] => wrote: {csv_output}")


if __name__ == "__main__":
    # Example direct CLI usage:
    transform_fenez_log_to_structured_with_ranges(
        csv_input="output/assigned/assigned_fenez_params.csv",
        csv_output="output/assigned/structured_fenez_params.csv"
    )


