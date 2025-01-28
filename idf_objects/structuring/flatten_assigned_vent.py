"""
flatten_assigned_vent.py

Transforms the "assigned_ventilation.csv" file (which has [ogc_fid, param_name, assigned_value])
into two structured CSVs:
  1) assigned_vent_building.csv
  2) assigned_vent_zones.csv

Usage:
    python flatten_assigned_vent.py
or
    from idf_objects.structuring.flatten_assigned_vent import main
    main()
"""

import pandas as pd
import ast
import os

def parse_assigned_value(value_str):
    """
    Safely convert the string in 'assigned_value' into a Python dict,
    e.g. literal_eval("{'infiltration_base': 1.23}")
    """
    try:
        return ast.literal_eval(str(value_str))
    except (SyntaxError, ValueError):
        return {}

def flatten_ventilation_data(df_input, out_build_csv, out_zone_csv):
    """
    Takes a DataFrame with columns [ogc_fid, param_name, assigned_value].
    Splits it into two DataFrames:
      1) building-level (flattening 'building_params')
      2) zone-level (flattening 'zones').

    Then writes them to CSV (out_build_csv, out_zone_csv).

    :param df_input: pd.DataFrame
        Must contain columns => "ogc_fid", "param_name", "assigned_value"
        where assigned_value is already a dict (not a raw string).
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

        # param_name might be "building_params" or "zones" based on your code's structure
        if param_name == "building_params":
            # assigned_val is a dict => e.g. {"infiltration_base": 1.23, "fan_pressure": 30, ...}
            for k, v in assigned_val.items():
                building_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": k,
                    "param_value": v
                })

        elif param_name == "zones":
            # assigned_val is a dict: { "Zone1": {...}, "Zone2": {...}, ... }
            for zone_name, zone_dict in assigned_val.items():
                # zone_dict might be => {"vent_mech": True, "vent_flow_rate": 150.0, ...}
                for zparam_name, zparam_val in zone_dict.items():
                    zone_rows.append({
                        "ogc_fid": bldg_id,
                        "zone_name": zone_name,
                        "param_name": zparam_name,
                        "param_value": zparam_val
                    })

        else:
            # If there's something else or unknown param_name, we ignore or handle differently
            pass

    # Convert to DataFrame
    df_build = pd.DataFrame(building_rows)
    df_zone = pd.DataFrame(zone_rows)

    # If they're empty, columns might not exist => ensure minimal columns
    if not df_build.empty:
        df_build = df_build[["ogc_fid", "param_name", "param_value"]]
    if not df_zone.empty:
        df_zone = df_zone[["ogc_fid", "zone_name", "param_name", "param_value"]]

    # Write them to CSV
    os.makedirs(os.path.dirname(out_build_csv), exist_ok=True)
    df_build.to_csv(out_build_csv, index=False)

    os.makedirs(os.path.dirname(out_zone_csv), exist_ok=True)
    df_zone.to_csv(out_zone_csv, index=False)

    print(f"[INFO] Wrote building-level picks to {out_build_csv} ({len(df_build)} rows).")
    print(f"[INFO] Wrote zone-level picks to {out_zone_csv} ({len(df_zone)} rows).")


def main():
    """
    Example CLI entry point:
      - Reads 'D:/Documents/E_Plus_2030_py/output/assigned/assigned_ventilation.csv'
      - Parses 'assigned_value' into dict
      - Writes building-level & zone-level CSVs
    """
    # 1) Path to your original CSV
    csv_in = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_ventilation.csv"

    # 2) Paths for output
    csv_build_out = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_vent_building.csv"
    csv_zone_out = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_vent_zones.csv"

    # 3) Read the CSV
    df_assigned = pd.read_csv(csv_in)

    # 4) Convert 'assigned_value' from string to dict
    df_assigned["assigned_value"] = df_assigned["assigned_value"].apply(parse_assigned_value)

    # 5) Flatten
    flatten_ventilation_data(
        df_input=df_assigned,
        out_build_csv=csv_build_out,
        out_zone_csv=csv_zone_out
    )


if __name__ == "__main__":
    main()
