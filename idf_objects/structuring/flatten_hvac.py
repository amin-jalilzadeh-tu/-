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
    Takes a DataFrame with columns [ogc_fid, param_name, assigned_value].
    Splits it into two DataFrames:
      1) building-level (where param_name == "hvac_params")
      2) zone-level (where param_name == "zones").

    Then writes them to CSV (out_build_csv, out_zone_csv).

    :param df_input: pd.DataFrame
        Must contain columns => "ogc_fid", "param_name", "assigned_value"
        where assigned_value is a dict (not raw text).
    :param out_build_csv: str
        File path for building-level CSV output.
    :param out_zone_csv: str
        File path for zone-level CSV output.
    """

    building_rows = []
    zone_rows = []

    for idx, row in df_input.iterrows():
        bldg_id = row.get("ogc_fid")
        param_name = row.get("param_name")
        assigned_val = row.get("assigned_value", {})

        if param_name == "hvac_params":
            # assigned_val is a dict, e.g.:
            # {
            #   "heating_day_setpoint": 20.28,
            #   "cooling_day_setpoint": 24.55,
            #   "schedule_details": {...},
            #   ...
            # }
            for k, v in assigned_val.items():
                building_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": k,
                    "param_value": v
                })

        elif param_name == "zones":
            # assigned_val is a dict => { zoneName: {...}, zoneName2: {...}, ... }
            # e.g. { "Zone1": {"hvac_object_name": "Ideal1", "cooling_setpoint": 25}, ... }
            for zone_name, zone_dict in assigned_val.items():
                for zparam, zval in zone_dict.items():
                    zone_rows.append({
                        "ogc_fid": bldg_id,
                        "zone_name": zone_name,
                        "param_name": zparam,
                        "param_value": zval
                    })

        else:
            # If there's any other param_name, skip or handle differently
            pass

    # Convert to DataFrames
    df_build = pd.DataFrame(building_rows)
    df_zone = pd.DataFrame(zone_rows)

    # Reorder columns or ensure they exist
    if not df_build.empty:
        df_build = df_build[["ogc_fid", "param_name", "param_value"]]
    if not df_zone.empty:
        df_zone = df_zone[["ogc_fid", "zone_name", "param_name", "param_value"]]

    # Write to CSV
    os.makedirs(os.path.dirname(out_build_csv), exist_ok=True)
    df_build.to_csv(out_build_csv, index=False)

    os.makedirs(os.path.dirname(out_zone_csv), exist_ok=True)
    df_zone.to_csv(out_zone_csv, index=False)

    print(f"[INFO] Wrote building-level picks to {out_build_csv} ({len(df_build)} rows).")
    print(f"[INFO] Wrote zone-level picks to {out_zone_csv} ({len(df_zone)} rows).")


def main():
    """
    Example CLI entry point:
      - Reads 'D:/Documents/E_Plus_2030_py/output/assigned/assigned_hvac_params.csv'
      - Parses 'assigned_value' into dict
      - Writes building-level & zone-level CSVs
    """
    # 1) Path to your original HVAC CSV file
    csv_in = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_params.csv"

    # 2) Paths for output CSVs
    csv_build_out = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_building.csv"
    csv_zone_out  = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_zones.csv"

    # 3) Load the CSV
    df_assigned = pd.read_csv(csv_in)

    # 4) Convert assigned_value from string to dict
    df_assigned["assigned_value"] = df_assigned["assigned_value"].apply(parse_assigned_value)

    # 5) Flatten
    flatten_hvac_data(
        df_input=df_assigned,
        out_build_csv=csv_build_out,
        out_zone_csv=csv_zone_out
    )


if __name__ == "__main__":
    main()
