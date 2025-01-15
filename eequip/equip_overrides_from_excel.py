# eequip/equip_overrides_from_excel.py

import pandas as pd

def read_equipment_overrides_from_excel(excel_path):
    """
    Reads an Excel file (e.g. 'equipment_overrides.xlsx') and returns a structure 
    that can override the default equipment parameters in 'equip_lookup.py'.

    Expected columns in the Excel file:
      - calibration_stage
      - building_type
      - param_name   (like 'equip_wm2', 'tD', 'tN', etc.)
      - min_val
      - max_val
      - fixed_value

    Example usage:
      override_data = read_equipment_overrides_from_excel("equipment_overrides.xlsx")
      # override_data => { stage -> { btype -> { param_name -> (mn, mx) } } }

    You can then merge it into your default lookup with a function like
    `apply_equipment_overrides_to_lookup(...).`
    """

    df = pd.read_excel(excel_path)

    required_cols = ["calibration_stage", "building_type", "param_name", 
                     "min_val", "max_val", "fixed_value"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    override_data = {}

    for _, row in df.iterrows():
        stage = str(row["calibration_stage"]).strip()
        btype = str(row["building_type"]).strip()
        pname = str(row["param_name"]).strip()   # e.g. "equip_wm2", "tD", "tN"
        fv = row["fixed_value"]
        mn = row["min_val"]
        mx = row["max_val"]

        if stage not in override_data:
            override_data[stage] = {}
        if btype not in override_data[stage]:
            override_data[stage][btype] = {}

        # If there's a fixed_value, we treat it as (fv, fv)
        if pd.notna(fv):
            override_data[stage][btype][pname] = (float(fv), float(fv))
        elif pd.notna(mn) and pd.notna(mx):
            override_data[stage][btype][pname] = (float(mn), float(mx))
        else:
            # If neither is valid, skip or store a default
            continue

    return override_data


def apply_equipment_overrides_to_lookup(default_lookup, override_data):
    """
    Integrates override_data into the given default_lookup (in-place or by returning a new copy).

    For each (stage -> btype -> param_name -> range), 
    we store it in default_lookup[stage][btype], 
    converting param_name to the appropriate key if needed:
       - "equip_wm2" -> "EQUIP_WM2_range"
       - "tD"        -> "tD_range"
       - "tN"        -> "tN_range"
       etc.

    Example usage:
        from .equip_lookup import equip_lookup
        from .equip_overrides_from_excel import read_equipment_overrides_from_excel, apply_equipment_overrides_to_lookup

        override_data = read_equipment_overrides_from_excel("my_overrides.xlsx")
        new_equip_lookup = apply_equipment_overrides_to_lookup(equip_lookup, override_data)
    """

    new_lookup = default_lookup  # or do copy.deepcopy(default_lookup) if you want a separate object

    for stage, btypes_dict in override_data.items():
        if stage not in new_lookup:
            new_lookup[stage] = {}
        for btype, param_dict in btypes_dict.items():
            if btype not in new_lookup[stage]:
                new_lookup[stage][btype] = {}
            for pname, rng_tuple in param_dict.items():
                # Convert param_name to the key format used in equip_lookup
                # E.g. "equip_wm2" => "EQUIP_WM2_range"
                # We can handle tD/tN similarly, just appending "_range"
                if pname.lower() == "equip_wm2":
                    range_key = "EQUIP_WM2_range"
                else:
                    # e.g. "tD" => "tD_range", "tN" => "tN_range"
                    range_key = f"{pname}_range"

                new_lookup[stage][btype][range_key] = rng_tuple

    return new_lookup
