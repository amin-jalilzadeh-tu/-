"""
flatten_hvac.py

Transforms the "assigned_hvac_params.csv" file (with columns [ogc_fid, zone_name, param_name, assigned_value])
into two structured CSVs:
  1) assigned_hvac_building.csv  (building-level, no zone_name)
  2) assigned_hvac_zones.csv     (zone-level, with zone_name)

Usage (standalone):
    python flatten_hvac.py

Or import and call 'main()' or the lower-level functions.
"""

import os
import ast
import pandas as pd


def parse_assigned_value(value_str):
    """
    Safely convert a string from 'assigned_value' into either:
      - A real Python dict or list (if the string starts with '{' or '[')
      - A numeric (if it can parse easily, but we rely on literal_eval)
      - A plain string (if it's just "AlwaysOnSched", "N/A", etc.)

    This prevents losing plain strings like "AlwaysOnSched" or "DAY_SCHEDULE".
    """
    if not isinstance(value_str, str):
        # e.g. it's already numeric or None
        return value_str

    trimmed = value_str.strip()
    # If it looks like a Python dict or list, try literal_eval
    if trimmed.startswith("{") or trimmed.startswith("["):
        try:
            return ast.literal_eval(trimmed)
        except (SyntaxError, ValueError, TypeError):
            # Fallback to returning the raw string if parsing fails
            return trimmed
    else:
        # It's presumably just a normal string (or numeric in string form).
        # If you want to parse numeric strings here, you could attempt float(trimmed).
        # But commonly we just keep it as-is unless you're sure it's numeric.
        return trimmed


def flatten_hvac_data(df_input, out_build_csv, out_zone_csv):
    """
    Splits the DataFrame into two separate CSVs:
      - building-level (where zone_name is NaN/None)
      - zone-level (where zone_name is not null)

    Also renames 'assigned_value' -> 'param_value' for downstream scripts.

    :param df_input: pd.DataFrame
         Must contain columns => "ogc_fid", "zone_name", "param_name", "assigned_value"
    :param out_build_csv: str
         File path for building-level CSV output.
    :param out_zone_csv: str
         File path for zone-level CSV output.
    """

    # 1) Parse the assigned_value to keep or convert it properly
    if "assigned_value" in df_input.columns:
        df_input["assigned_value"] = df_input["assigned_value"].apply(parse_assigned_value)
    else:
        # If there's no assigned_value column, you can't parse. Possibly param_value is already there.
        pass

    # 2) Ensure a 'zone_name' column exists (some files might be purely building-level)
    if "zone_name" not in df_input.columns:
        df_input["zone_name"] = pd.NA

    # 3) Split into building-level vs. zone-level
    df_build = df_input[df_input["zone_name"].isnull()].copy()
    df_zone  = df_input[df_input["zone_name"].notnull()].copy()

    # 4) Rename 'assigned_value' -> 'param_value' for uniform usage
    if "assigned_value" in df_build.columns:
        df_build.rename(columns={"assigned_value": "param_value"}, inplace=True)
    if "assigned_value" in df_zone.columns:
        df_zone.rename(columns={"assigned_value": "param_value"}, inplace=True)

    # 5) Re-index columns so they appear in the desired order
    build_cols = ["ogc_fid", "param_name", "param_value"]
    zone_cols  = ["ogc_fid", "zone_name", "param_name", "param_value"]
    df_build = df_build.reindex(columns=build_cols)
    df_zone  = df_zone.reindex(columns=zone_cols)

    # 6) Save them
    os.makedirs(os.path.dirname(out_build_csv), exist_ok=True)
    df_build.to_csv(out_build_csv, index=False)
    os.makedirs(os.path.dirname(out_zone_csv), exist_ok=True)
    df_zone.to_csv(out_zone_csv, index=False)

    print(f"[INFO] Wrote building-level HVAC picks to {out_build_csv} ({len(df_build)} rows).")
    print(f"[INFO] Wrote zone-level HVAC picks to {out_zone_csv} ({len(df_zone)} rows).")


def main():
    """
    Example CLI entry point, if you run this file standalone:
        python flatten_hvac.py
    """
    # You can customize these defaults:
    csv_in        = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_params.csv"
    csv_build_out = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_building.csv"
    csv_zone_out  = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_zones.csv"

    # Check if the input file exists:
    if not os.path.exists(csv_in):
        print(f"Error: Input file not found at {csv_in}")
        return

    df_assigned = pd.read_csv(csv_in)

    flatten_hvac_data(
        df_input=df_assigned,
        out_build_csv=csv_build_out,
        out_zone_csv=csv_zone_out
    )


if __name__ == "__main__":
    main()
