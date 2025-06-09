"""
flatten_hvac.py

Transforms the "assigned_hvac_params.csv" file (with columns [ogc_fid, param_name, assigned_value])
into two structured CSVs:
  1) assigned_hvac_building.csv
  2) assigned_hvac_zones.csv

Usage (standalone):
    python flatten_hvac.py

Or import and call 'main()' or the lower-level functions.
"""

import pandas as pd
import ast
import os

def parse_assigned_value(value_str):
    """
    Safely convert the string in 'assigned_value' into a Python dict.
    Uses ast.literal_eval to parse e.g.:
      "{'heating_day_setpoint': 20.28, 'cooling_day_setpoint': 24.55, ...}"
    into a real Python dictionary.
    """
    try:
        return ast.literal_eval(str(value_str))
    except (SyntaxError, ValueError):
        return {}


def flatten_hvac_data(df_input, out_build_csv, out_zone_csv):
    """
    UPDATED: Takes a pre-flattened DataFrame and splits it into two files.
    - Rows where 'zone_name' is NaN/None are considered building-level.
    - Rows with a 'zone_name' are considered zone-level.

    :param df_input: pd.DataFrame
        Must contain columns => "ogc_fid", "zone_name", "param_name", "assigned_value"
    :param out_build_csv: str
        File path for building-level CSV output.
    :param out_zone_csv: str
        File path for zone-level CSV output.
    """

    # Ensure the 'zone_name' column exists, even if all values are NaN
    if 'zone_name' not in df_input.columns:
        df_input['zone_name'] = pd.NA

    # 1. Building-level data is where zone_name is null/NaN
    df_build = df_input[df_input['zone_name'].isnull()].copy()
    
    # 2. Zone-level data is where zone_name has a value
    df_zone = df_input[df_input['zone_name'].notnull()].copy()

    # Rename 'assigned_value' to 'param_value' for consistency with downstream scripts
    if 'assigned_value' in df_build.columns:
        df_build.rename(columns={'assigned_value': 'param_value'}, inplace=True)
    
    if 'assigned_value' in df_zone.columns:
        df_zone.rename(columns={'assigned_value': 'param_value'}, inplace=True)

    # Select and ensure columns exist, even if DataFrame is empty
    build_cols = ["ogc_fid", "param_name", "param_value"]
    zone_cols = ["ogc_fid", "zone_name", "param_name", "param_value"]

    df_build = df_build.reindex(columns=build_cols)
    df_zone = df_zone.reindex(columns=zone_cols)

    # Write to CSV
    os.makedirs(os.path.dirname(out_build_csv), exist_ok=True)
    df_build.to_csv(out_build_csv, index=False)

    os.makedirs(os.path.dirname(out_zone_csv), exist_ok=True)
    df_zone.to_csv(out_zone_csv, index=False)

    print(f"[INFO] Wrote building-level HVAC picks to {out_build_csv} ({len(df_build)} rows).")
    print(f"[INFO] Wrote zone-level HVAC picks to {out_zone_csv} ({len(df_zone)} rows).")


def main():
    """
    Example CLI entry point.
    """
    csv_in = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_params.csv"
    csv_build_out = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_building.csv"
    csv_zone_out  = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_zones.csv"

    # Check if the input file exists
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