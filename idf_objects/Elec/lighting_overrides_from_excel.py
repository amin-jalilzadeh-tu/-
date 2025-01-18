# lighting_overrides_from_excel.py
import pandas as pd
import copy

def read_lighting_overrides_from_excel(excel_path):
    """
    Reads lighting_overrides.xlsx and returns a structure like:
      override_data[calibration_stage][building_type][param_name] = (min_val, max_val) or (val, val)

    Expected columns:
      - calibration_stage
      - building_type
      - param_name (like 'lights_wm2', 'parasitic_wm2', 'tD', 'tN', etc.)
      - min_val
      - max_val
      - fixed_value
    """
    df = pd.read_excel(excel_path)

    required_cols = ["calibration_stage", "building_type", "param_name", "min_val", "max_val", "fixed_value"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    override_data = {}

    for _, row in df.iterrows():
        stage = str(row["calibration_stage"]).strip()
        btype = str(row["building_type"]).strip()
        pname = str(row["param_name"]).strip()   # e.g. "lights_wm2", "tD", "PARASITIC_WM2"
        fv = row["fixed_value"]
        mn = row["min_val"]
        mx = row["max_val"]

        if stage not in override_data:
            override_data[stage] = {}
        if btype not in override_data[stage]:
            override_data[stage][btype] = {}

        # final range
        if pd.notna(fv):
            # if fixed_value => (fv, fv)
            override_data[stage][btype][pname] = (float(fv), float(fv))
        elif pd.notna(mn) and pd.notna(mx):
            override_data[stage][btype][pname] = (float(mn), float(mx))
        else:
            # if neither => skip or store None
            continue

    return override_data


def apply_lighting_overrides_to_lookup(default_lookup, override_data):
    """
    Merges override_data into default_lookup in place (or you can copy first).
    default_lookup => e.g. lighting_lookup from lighting_lookup.py

    For each stage/btype/param_name, we set or override the 
      param_name_range in default_lookup[stage][btype].

    E.g. if param_name is "lights_wm2", we need to store it as "LIGHTS_WM2_range".
    If param_name is "tD", store it as "tD_range". 
    We'll do a small map or direct approach.
    """

    # you could do copy if you want:
    new_lookup = default_lookup

    for stage, btypes_dict in override_data.items():
        if stage not in new_lookup:
            new_lookup[stage] = {}
        for btype, param_dict in btypes_dict.items():
            if btype not in new_lookup[stage]:
                new_lookup[stage][btype] = {}
            for pname, rng_tuple in param_dict.items():
                # we transform e.g. "lights_wm2" => "LIGHTS_WM2_range"
                # or "tD" => "tD_range"
                # uppercase might matter if your existing dict uses "LIGHTS_WM2_range".
                
                # A small helper map:
                # If your existing keys are "LIGHTS_WM2_range", 
                # you might do a dictionary or just do pattern replacements:
                
                # pattern => uppercase param, + "_range"
                # e.g. "lights_wm2" => "LIGHTS_WM2_range"
                # if param_name already uppercase => "PARASITIC_WM2" => we might skip re-uppercasing
                # We'll do a naive approach:
                
                # Convert to uppercase (except tD/tN we keep as is?), up to you:
                if pname.lower() == "lights_wm2":
                    range_key = "LIGHTS_WM2_range"
                elif pname.lower() == "parasitic_wm2":
                    range_key = "PARASITIC_WM2_range"
                else:
                    # e.g. tD => "tD_range", tN => "tN_range"
                    range_key = f"{pname}_range"

                new_lookup[stage][btype][range_key] = rng_tuple

    return new_lookup
