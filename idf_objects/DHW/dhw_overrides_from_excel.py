# dhw_overrides_from_excel.py

import pandas as pd
import copy

def override_dhw_lookup_from_excel(excel_path, default_dhw_lookup):
    """
    Reads an Excel file with columns like:
      - calibration_stage, dhw_key
      - occupant_density_m2_per_person_min, occupant_density_m2_per_person_max
      - setpoint_c_min, setpoint_c_max
      - (etc.)

    Only updates/extends the entries for which both `_min` and `_max` are non-empty.
    Returns a new dictionary with partial overrides applied.
    """
    new_dhw_lookup = copy.deepcopy(default_dhw_lookup)
    df = pd.read_excel(excel_path)

    # Map short param name => the keys used in dhw_lookup
    param_map = {
        "occupant_density_m2_per_person": "occupant_density_m2_per_person_range",
        "liters_per_person_per_day": "liters_per_person_per_day_range",
        "default_tank_volume_liters": "default_tank_volume_liters_range",
        "default_heater_capacity_w": "default_heater_capacity_w_range",
        "setpoint_c": "setpoint_c_range",
        "usage_split_factor": "usage_split_factor_range",
        "peak_hours": "peak_hours_range",

        "sched_morning": "sched_morning_range",
        "sched_peak": "sched_peak_range",
        "sched_afternoon": "sched_afternoon_range",
        "sched_evening": "sched_evening_range"
    }

    for _, row in df.iterrows():
        stage = str(row["calibration_stage"]).strip()
        dhw_key = str(row["dhw_key"]).strip()

        if stage not in new_dhw_lookup:
            new_dhw_lookup[stage] = {}
        if dhw_key not in new_dhw_lookup[stage]:
            new_dhw_lookup[stage][dhw_key] = {}

        entry_dict = new_dhw_lookup[stage][dhw_key]

        for base_param, lookup_key in param_map.items():
            col_min = f"{base_param}_min"
            col_max = f"{base_param}_max"
            if col_min in df.columns and col_max in df.columns:
                val_min = row[col_min]
                val_max = row[col_max]
                if pd.notna(val_min) and pd.notna(val_max):
                    entry_dict[lookup_key] = (float(val_min), float(val_max))

    return new_dhw_lookup
