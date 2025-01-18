# ventilation/ventilation_overrides_from_excel.py

import pandas as pd
import copy
import math

def read_ventilation_overrides_from_excel(excel_path):
    """
    Reads an Excel file with columns:
        - calibration_stage
        - main_key
        - sub_key
        - param_name
        - min_val
        - max_val
        - fixed_value

    Returns a nested dict: override_data[stage][main_key][sub_key][param_name] = ...
    
    Where the "..." can be:
      - a tuple (min, max) if numeric
      - a single string or numeric if 'fixed_value' is provided and is non-NaN
        (we store it as (val, val) if numeric, or keep as a plain string if textual).
    
    This can override infiltration ranges, year_factor ranges, OR new schedule info.
    For schedule overrides, 'main_key' might be "schedule_info",
    sub_key might be e.g. "residential", param_name might be "default_infiltration_schedule",
    and fixed_value could be e.g. "InfilResSched".

    Example row:
        calibration_stage = "pre_calibration"
        main_key          = "schedule_info"
        sub_key           = "residential"
        param_name        = "default_infiltration_schedule"
        min_val           = NaN
        max_val           = NaN
        fixed_value       = "MyInfilResSched"

    The resulting override_data will have:
        override_data["pre_calibration"]["schedule_info"]["residential"]["default_infiltration_schedule"] = "MyInfilResSched"
    """
    df = pd.read_excel(excel_path)

    required_cols = ["calibration_stage","main_key","sub_key","param_name","min_val","max_val","fixed_value"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    override_data = {}

    for _, row in df.iterrows():
        stage = str(row["calibration_stage"]).strip()
        mkey  = str(row["main_key"]).strip()       # e.g. "residential_infiltration_range" or "schedule_info"
        skey  = str(row["sub_key"]).strip()        # e.g. "A_corner" or "residential" or ""
        pname = str(row["param_name"]).strip()     # e.g. "f_ctrl_range", "default_infiltration_schedule", or ""

        fv = row["fixed_value"]  # could be numeric or string
        mn = row["min_val"]      # typically numeric or NaN
        mx = row["max_val"]      # typically numeric or NaN

        if stage not in override_data:
            override_data[stage] = {}
        if mkey not in override_data[stage]:
            override_data[stage][mkey] = {}

        # Decide how to store
        # 1) If fixed_value is not NaN => store that
        #    - If it's purely numeric, we store as (fv,fv) for consistency with min,max range
        #    - If it's a string, we'll store it as a plain string override
        # 2) Else if min_val and max_val are numeric => store as (min_val,max_val)
        # 3) Otherwise skip if all are NaN

        # Helper to test if something is numeric
        def is_number(x):
            try:
                float(x)
                return True
            except (ValueError, TypeError):
                return False

        if pd.notna(fv):
            # If the fixed_value is numeric => store as a numeric tuple (fv,fv)
            if is_number(fv):
                val_tuple = (float(fv), float(fv))
                final_value = val_tuple
            else:
                # It's likely a string => store it directly as that string
                final_value = str(fv).strip()
        elif pd.notna(mn) and pd.notna(mx) and is_number(mn) and is_number(mx):
            val_tuple = (float(mn), float(mx))
            final_value = val_tuple
        else:
            # skip if no valid data
            continue

        # Insert into override_data
        # Cases:
        #    (a) skey == "" and pname == "" => override_data[stage][mkey] = final_value
        #    (b) skey != "" and pname == "" => override_data[stage][mkey][skey] = final_value
        #    (c) skey + pname => override_data[stage][mkey][skey][pname] = final_value
        if skey == "" and pname == "":
            override_data[stage][mkey] = final_value
        elif skey != "" and pname == "":
            if not isinstance(override_data[stage][mkey], dict):
                override_data[stage][mkey] = {}
            override_data[stage][mkey][skey] = final_value
        else:
            # if we have a param_name => store in stage[mkey][skey][pname]
            if skey not in override_data[stage][mkey] or not isinstance(override_data[stage][mkey][skey], dict):
                override_data[stage][mkey][skey] = {}
            override_data[stage][mkey][skey][pname] = final_value

    return override_data


def apply_ventilation_overrides_to_lookup(default_lookup, override_data):
    """
    Merges override_data into default_lookup (similar to ventilation_lookup).
    
    override_data structure:
      override_data[stage][main_key][sub_key][param_name] = final_value
        (final_value can be a tuple (min,max), or a string for schedules)

    For each stage in override_data:
      - If stage doesn't exist in default_lookup, we create it.
      - For each main_key in override_data => if it's a tuple or string, override
        directly. If it's a dict => merge deeper.
    
    Example usage:
      new_lookup = apply_ventilation_overrides_to_lookup(ventilation_lookup, override_data)
    """
    # If you prefer not to mutate default_lookup in place, do a copy
    new_lookup = copy.deepcopy(default_lookup)

    for stage, stage_dict in override_data.items():
        if stage not in new_lookup:
            new_lookup[stage] = {}

        for mkey, val_mkey in stage_dict.items():
            # val_mkey might be:
            #   - a numeric tuple or string => direct override
            #   - a dict => deeper merges (subkeys, param_names)

            if not isinstance(val_mkey, dict):
                # So if it's a tuple or a string => direct override
                new_lookup[stage][mkey] = val_mkey
                continue

            # if it's a dict => we merge it
            if mkey not in new_lookup[stage]:
                new_lookup[stage][mkey] = {}

            for subk, subv in val_mkey.items():
                # subv might be a tuple, string, or another dict
                if not isinstance(subv, dict):
                    # direct override
                    new_lookup[stage][mkey][subk] = subv
                else:
                    # deeper dict => e.g. {param_name: (min,max) or string}
                    if subk not in new_lookup[stage][mkey]:
                        new_lookup[stage][mkey][subk] = {}
                    for param_key, param_val in subv.items():
                        # param_val could be tuple or string
                        new_lookup[stage][mkey][subk][param_key] = param_val

    return new_lookup
