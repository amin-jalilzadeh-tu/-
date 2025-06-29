"""
flatten_assigned_vent.py

Transforms the "assigned_ventilation.csv" file (with columns
[ogc_fid, zone_name, param_name, assigned_value]) into two structured CSVs:
  1) assigned_vent_building.csv (building-level, no zone_name)
  2) assigned_vent_zones.csv    (zone-level, with zone_name)

Usage (standalone):
    python flatten_assigned_vent.py
or
    from idf_objects.structuring.flatten_assigned_vent import main
    main()
"""

import os
import ast
import pandas as pd


def parse_assigned_value(value_str):
    """
    Safely convert the string in 'assigned_value' into a Python dict/list only
    if it starts with '{' or '['. Otherwise, keep it as a plain string.

    This ensures that schedule names or other non-dict strings (like "AlwaysOnSched")
    remain intact.
    """
    if not isinstance(value_str, str):
        # If it's already numeric or None, just return as-is
        return value_str

    trimmed = value_str.strip()
    # If it looks like a dict or list, try literal_eval
    if trimmed.startswith("{") or trimmed.startswith("["):
        try:
            return ast.literal_eval(trimmed)
        except (SyntaxError, ValueError, TypeError):
            # If parsing fails, fall back to returning the raw string
            return trimmed
    else:
        # It's a normal string like "AlwaysOnSched"—return as-is
        return trimmed


def flatten_ventilation_data(df_input, out_build_csv, out_zone_csv):
    """
    Splits the input DataFrame into two files:
      - Building-level rows (where 'zone_name' is NaN/None)
      - Zone-level rows (where 'zone_name' is not null)

    Also renames 'assigned_value' -> 'param_value' for downstream scripts.

    :param df_input: pd.DataFrame
        Must contain columns => "ogc_fid", "zone_name", "param_name", "assigned_value"
    :param out_build_csv: str
        File path for building-level CSV output.
    :param out_zone_csv: str
        File path for zone-level CSV output.
    """

    # 1. Parse 'assigned_value' so that dictionaries or lists remain structured,
    #    while strings like "AlwaysOnSched" remain unmodified
    if "assigned_value" in df_input.columns:
        df_input["assigned_value"] = df_input["assigned_value"].apply(parse_assigned_value)
    else:
        pass  # Possibly it already has 'param_value' instead

    # 2. Ensure 'zone_name' exists (some files might be purely building-level)
    if "zone_name" not in df_input.columns:
        df_input["zone_name"] = pd.NA

    # 3. Split out building-level vs zone-level
    df_build = df_input[df_input["zone_name"].isnull()].copy()
    df_zone  = df_input[df_input["zone_name"].notnull()].copy()

    # 4. Rename 'assigned_value' -> 'param_value'
    if "assigned_value" in df_build.columns:
        df_build.rename(columns={"assigned_value": "param_value"}, inplace=True)
    if "assigned_value" in df_zone.columns:
        df_zone.rename(columns={"assigned_value": "param_value"}, inplace=True)

    # 5. Re-index columns so they're in the expected order
    build_cols = ["ogc_fid", "param_name", "param_value"]
    zone_cols  = ["ogc_fid", "zone_name", "param_name", "param_value"]
    df_build = df_build.reindex(columns=build_cols)
    df_zone  = df_zone.reindex(columns=zone_cols)

    # 6. Write them
    os.makedirs(os.path.dirname(out_build_csv), exist_ok=True)
    df_build.to_csv(out_build_csv, index=False)
    os.makedirs(os.path.dirname(out_zone_csv), exist_ok=True)
    df_zone.to_csv(out_zone_csv, index=False)

    print(f"[INFO] Wrote building-level ventilation picks to {out_build_csv} ({len(df_build)} rows).")
    print(f"[INFO] Wrote zone-level ventilation picks to {out_zone_csv} ({len(df_zone)} rows).")


def main():
    """
    Example CLI entry point:
        python flatten_assigned_vent.py
    """
    csv_in       = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_ventilation.csv"
    csv_build_out= r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_vent_building.csv"
    csv_zone_out = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_vent_zones.csv"

    if not os.path.exists(csv_in):
        print(f"Error: Input file not found at {csv_in}")
        return

    df_assigned = pd.read_csv(csv_in)

    flatten_ventilation_data(
        df_input=df_assigned,
        out_build_csv=csv_build_out,
        out_zone_csv=csv_zone_out
    )


if __name__ == "__main__":
    main()
