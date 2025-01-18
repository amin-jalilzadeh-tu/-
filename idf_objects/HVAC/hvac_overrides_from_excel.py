# HVAC/hvac_overrides_from_excel.py

import pandas as pd

def read_hvac_overrides_from_excel(excel_path):
    """
    Reads an Excel file with columns at least:
      - calibration_stage
      - scenario
      - building_function
      - residential_type
      - non_residential_type
      - age_range
      - param_name
      - min_val
      - max_val
      - fixed_value
      - schedule_key
      - schedule_value

    Returns a nested dict override_data such that:
      override_data[cal_stage][scenario][bldg_func][subtype][age_range]
        = {
           "param_overrides": { param_name -> (min_val,max_val) },
           "schedule_details": { key -> value, key2 -> value2, ... }
          }
    For each sub-block, we store both numeric param overrides and schedule details.

    If a row has both param_name and schedule_key, it will apply both. Usually you separate them.
    """

    df = pd.read_excel(excel_path)

    # Minimal required columns we expect
    must_have_cols = [
        "calibration_stage",
        "scenario",
        "building_function",
        "age_range",
        "param_name",
        "min_val",
        "max_val",
        "fixed_value",
        "schedule_key",
        "schedule_value"
    ]
    for c in must_have_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    override_data = {}

    for _, row in df.iterrows():
        cal_stage = str(row["calibration_stage"]).strip()
        scenario  = str(row["scenario"]).strip()
        bldg_func = str(row["building_function"]).strip()
        age_rng   = str(row["age_range"]).strip()

        # figure out subtype
        res_type = ""
        if "residential_type" in df.columns:
            res_type = row["residential_type"]
            if pd.isna(res_type):
                res_type = ""
            else:
                res_type = str(res_type).strip()

        nonres_type = ""
        if "non_residential_type" in df.columns:
            nonres_type = row["non_residential_type"]
            if pd.isna(nonres_type):
                nonres_type = ""
            else:
                nonres_type = str(nonres_type).strip()

        # decide final subtype
        if bldg_func.lower() == "residential":
            subtype = res_type if res_type else "DefaultResidential"
        else:
            subtype = nonres_type if nonres_type else "DefaultNonRes"

        # ensure we have that nested path
        if cal_stage not in override_data:
            override_data[cal_stage] = {}
        if scenario not in override_data[cal_stage]:
            override_data[cal_stage][scenario] = {}
        if bldg_func not in override_data[cal_stage][scenario]:
            override_data[cal_stage][scenario][bldg_func] = {}
        if subtype not in override_data[cal_stage][scenario][bldg_func]:
            override_data[cal_stage][scenario][bldg_func][subtype] = {}
        if age_rng not in override_data[cal_stage][scenario][bldg_func][subtype]:
            override_data[cal_stage][scenario][bldg_func][subtype][age_rng] = {
                "param_overrides": {},
                "schedule_details": {}
            }

        # param_name => numeric override
        param_name = str(row["param_name"]).strip()
        fixed_val = row["fixed_value"]
        min_val = row["min_val"]
        max_val = row["max_val"]

        if param_name != "":
            # user might specify numeric overrides
            if pd.notna(fixed_val):
                rng = (float(fixed_val), float(fixed_val))
                override_data[cal_stage][scenario][bldg_func][subtype][age_rng]["param_overrides"][param_name] = rng
            elif pd.notna(min_val) and pd.notna(max_val):
                rng = (float(min_val), float(max_val))
                override_data[cal_stage][scenario][bldg_func][subtype][age_rng]["param_overrides"][param_name] = rng
            # else skip if no valid numeric data

        # schedule_key => schedule_details override
        sch_key = str(row["schedule_key"]).strip()
        if sch_key != "":
            sch_val = row["schedule_value"]
            if pd.notna(sch_val):
                # store as string or interpret as needed
                sch_val_str = str(sch_val).strip()
                override_data[cal_stage][scenario][bldg_func][subtype][age_rng]["schedule_details"][sch_key] = sch_val_str

    return override_data


def apply_hvac_overrides_to_lookup(default_lookup, override_data):
    """
    For each nested path in override_data, update:
      - param_overrides => param_name + "_range"
      - schedule_details => key => value

    If something doesn't exist in default_lookup, we create it.
    """
    new_lookup = default_lookup  # or copy.deepcopy if you want a separate copy

    for cal_stage, scn_dict in override_data.items():
        if cal_stage not in new_lookup:
            new_lookup[cal_stage] = {}

        for scenario, bf_dict in scn_dict.items():
            if scenario not in new_lookup[cal_stage]:
                new_lookup[cal_stage][scenario] = {}

            for bldg_func, stypes_dict in bf_dict.items():
                if bldg_func not in new_lookup[cal_stage][scenario]:
                    new_lookup[cal_stage][scenario][bldg_func] = {}

                for subtype, ages_dict in stypes_dict.items():
                    if subtype not in new_lookup[cal_stage][scenario][bldg_func]:
                        new_lookup[cal_stage][scenario][bldg_func][subtype] = {}

                    for age_rng, data_dict in ages_dict.items():
                        # data_dict => { "param_overrides": {...}, "schedule_details": {...} }
                        if age_rng not in new_lookup[cal_stage][scenario][bldg_func][subtype]:
                            new_lookup[cal_stage][scenario][bldg_func][subtype][age_rng] = {}

                        # ensure "schedule_details" subdict at that final location
                        if "schedule_details" not in new_lookup[cal_stage][scenario][bldg_func][subtype][age_rng]:
                            new_lookup[cal_stage][scenario][bldg_func][subtype][age_rng]["schedule_details"] = {}

                        # 1) Param overrides
                        param_overrides = data_dict.get("param_overrides", {})
                        for pname, rng in param_overrides.items():
                            # Typically we store e.g. "heating_day_setpoint_range" = rng
                            range_key = f"{pname}_range"
                            new_lookup[cal_stage][scenario][bldg_func][subtype][age_rng][range_key] = rng

                        # 2) Schedule details
                        sch_dict = data_dict.get("schedule_details", {})
                        for k, v in sch_dict.items():
                            # put into schedule_details subdict
                            new_lookup[cal_stage][scenario][bldg_func][subtype][age_rng]["schedule_details"][k] = v

    return new_lookup
