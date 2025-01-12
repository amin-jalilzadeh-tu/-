# Elec/schedule_def.py

import pandas as pd

"""
This file holds:
1) A default SCHEDULE_DEFINITIONS dictionary for lighting usage patterns
   (weekday vs. weekend) for Residential & Non-Residential sub-types.
2) (Optional) Functions to read & apply schedule overrides from Excel,
   which lets you adjust the (start_hour, end_hour, fraction) blocks.

You can import SCHEDULE_DEFINITIONS and pass it to your 'create_lighting_schedule'
function in schedules.py or lighting.py.
"""

# 1) Default SCHEDULE Definitions
SCHEDULE_DEFINITIONS = {
    "Residential": {
        "Corner House": {
            "weekday": [
                (0, 6, 0.05),
                (6, 8, 0.30),
                (8, 17, 0.10),
                (17, 22, 0.50),
                (22, 24, 0.05),
            ],
            "weekend": [
                (0, 8, 0.10),
                (8, 22, 0.40),
                (22, 24, 0.10),
            ],
        },
        "Apartment": {
            "weekday": [
                (0, 6, 0.05),
                (6, 8, 0.20),
                (8, 18, 0.10),
                (18, 23, 0.60),
                (23, 24, 0.05),
            ],
            "weekend": [
                (0, 9, 0.15),
                (9, 22, 0.50),
                (22, 24, 0.15),
            ],
        },
        "Terrace or Semi-detached House": {
            "weekday": [
                (0, 7, 0.05),
                (7, 9, 0.20),
                (9, 17, 0.10),
                (17, 22, 0.60),
                (22, 24, 0.05),
            ],
            "weekend": [
                (0, 9, 0.10),
                (9, 22, 0.50),
                (22, 24, 0.10),
            ],
        },
        "Detached House": {
            "weekday": [
                (0, 7, 0.05),
                (7, 9, 0.20),
                (9, 17, 0.10),
                (17, 22, 0.60),
                (22, 24, 0.05),
            ],
            "weekend": [
                (0, 9, 0.10),
                (9, 22, 0.50),
                (22, 24, 0.10),
            ],
        },
        "Two-and-a-half-story House": {
            "weekday": [
                (0, 6, 0.05),
                (6, 9, 0.20),
                (9, 18, 0.10),
                (18, 23, 0.60),
                (23, 24, 0.05),
            ],
            "weekend": [
                (0, 9, 0.10),
                (9, 22, 0.50),
                (22, 24, 0.10),
            ],
        },
    },
    "Non-Residential": {
        "Meeting Function": {
            "weekday": [
                (0, 6, 0.05),
                (6, 9, 0.50),
                (9, 12, 0.80),
                (12, 13, 0.50),
                (13, 18, 0.80),
                (18, 20, 0.50),
                (20, 24, 0.10),
            ],
            "weekend": [
                (0, 24, 0.10),
            ],
        },
        "Healthcare Function": {
            "weekday": [
                (0, 24, 0.80),  # Healthcare often 24/7
            ],
            "weekend": [
                (0, 24, 0.80),
            ],
        },
        "Sport Function": {
            "weekday": [
                (0, 6, 0.05),
                (6, 9, 0.20),
                (9, 12, 0.70),
                (12, 14, 0.50),
                (14, 22, 0.70),
                (22, 24, 0.10),
            ],
            "weekend": [
                (0, 9, 0.10),
                (9, 22, 0.70),
                (22, 24, 0.10),
            ],
        },
        "Cell Function": {
            "weekday": [
                (0, 24, 0.90),
            ],
            "weekend": [
                (0, 24, 0.90),
            ],
        },
        "Retail Function": {
            "weekday": [
                (0, 6, 0.05),
                (6, 9, 0.30),
                (9, 19, 0.90),
                (19, 21, 0.50),
                (21, 24, 0.05),
            ],
            "weekend": [
                (0, 8, 0.10),
                (8, 19, 0.80),
                (19, 22, 0.30),
                (22, 24, 0.10),
            ],
        },
        "Industrial Function": {
            "weekday": [
                (0, 6, 0.20),
                (6, 8, 0.50),
                (8, 17, 0.80),
                (17, 20, 0.50),
                (20, 24, 0.20),
            ],
            "weekend": [
                (0, 24, 0.20),
            ],
        },
        "Accommodation Function": {
            "weekday": [
                (0, 24, 0.70),
            ],
            "weekend": [
                (0, 24, 0.70),
            ],
        },
        "Office Function": {
            "weekday": [
                (0, 6, 0.10),
                (6, 9, 0.50),
                (9, 12, 0.90),
                (12, 13, 0.70),
                (13, 18, 0.90),
                (18, 20, 0.50),
                (20, 24, 0.10),
            ],
            "weekend": [
                (0, 24, 0.10),
            ],
        },
        "Education Function": {
            "weekday": [
                (0, 7, 0.05),
                (7, 8, 0.50),
                (8, 16, 0.80),
                (16, 18, 0.50),
                (18, 24, 0.05),
            ],
            "weekend": [
                (0, 24, 0.10),
            ],
        },
        "Other Use Function": {
            "weekday": [
                (0, 24, 0.30),
            ],
            "weekend": [
                (0, 24, 0.20),
            ],
        },
    },
}


# 2) (Optional) Functions to read & apply schedule overrides from Excel.

def read_schedule_overrides_from_excel(excel_path):
    """
    Example function to read schedule overrides from an Excel file.

    Expected columns (you can adjust to your needs):
      - building_category   (e.g. "Residential" or "Non-Residential")
      - sub_type            (e.g. "Apartment", "Office Function", etc.)
      - day_type            (e.g. "weekday" or "weekend")
      - start_hour
      - end_hour
      - fraction_value

    Returns a dict of form:
      overrides[building_category][sub_type][day_type] = [
         (start_hour, end_hour, fraction),
         ...
      ]
    """
    df = pd.read_excel(excel_path)
    required_cols = ["building_category", "sub_type", "day_type", 
                     "start_hour", "end_hour", "fraction_value"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    overrides = {}
    for _, row in df.iterrows():
        cat = str(row["building_category"]).strip()
        stype = str(row["sub_type"]).strip()
        dtype = str(row["day_type"]).strip().lower()  # "weekday" or "weekend"
        sh   = float(row["start_hour"])
        eh   = float(row["end_hour"])
        frac = float(row["fraction_value"])

        if cat not in overrides:
            overrides[cat] = {}
        if stype not in overrides[cat]:
            overrides[cat][stype] = {}
        if dtype not in overrides[cat][stype]:
            overrides[cat][stype][dtype] = []

        overrides[cat][stype][dtype].append((sh, eh, frac))

    return overrides


def apply_schedule_overrides_to_schedules(base_schedules, overrides):
    """
    Applies the schedule overrides from 'overrides' to 'base_schedules' in-place.
    'base_schedules' is typically SCHEDULE_DEFINITIONS.
    'overrides' is from read_schedule_overrides_from_excel.

    For each (cat, stype, day_type), we replace the entire list
    of (start_hour, end_hour, fraction) blocks with the override list.

    If you want partial merges or something more advanced, adapt as needed.
    """
    for cat, stype_dict in overrides.items():
        if cat not in base_schedules:
            # Create it if it doesn't exist
            base_schedules[cat] = {}
        for stype, daytypes_dict in stype_dict.items():
            if stype not in base_schedules[cat]:
                base_schedules[cat][stype] = {}

            for day_type, blocks_list in daytypes_dict.items():
                # e.g. "weekday", "weekend", or any custom day type
                base_schedules[cat][stype][day_type] = blocks_list

    # Return the updated dictionary
    return base_schedules
