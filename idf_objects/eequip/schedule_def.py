# eequip/schedule_def.py

"""
EQUIP_SCHEDULE_DEFINITIONS
===========================
This dictionary defines typical usage patterns for electric equipment
throughout the day, differentiating weekday vs. weekend, and by building
category (Residential vs. Non-Residential) and sub-type (e.g. "Corner House", 
"Office Function", etc.).

Each sub-type entry contains two keys:
 - "weekday": a list of (start_hour, end_hour, fraction)
 - "weekend": a list of (start_hour, end_hour, fraction)

The fraction represents the fraction of peak equipment load during that time.
"""

EQUIP_SCHEDULE_DEFINITIONS = {
    "Residential": {
        "Corner House": {
            "weekday": [
                (0, 6, 0.10),
                (6, 9, 0.40),
                (9, 17, 0.20),
                (17, 21, 0.60),
                (21, 24, 0.20),
            ],
            "weekend": [
                (0, 9, 0.25),
                (9, 22, 0.50),
                (22, 24, 0.25),
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
                (0, 24, 0.80),
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


def read_schedule_overrides_from_excel(excel_path):
    """Read Excel overrides for schedule definitions."""
    import pandas as pd

    df = pd.read_excel(excel_path)
    required = [
        "building_category",
        "sub_type",
        "day_type",
        "start_hour",
        "end_hour",
        "fraction_value",
    ]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    overrides = {}
    for _, row in df.iterrows():
        cat = str(row["building_category"]).strip()
        stype = str(row["sub_type"]).strip()
        dtype = str(row["day_type"]).strip().lower()
        block = (float(row["start_hour"]), float(row["end_hour"]), float(row["fraction_value"]))

        overrides.setdefault(cat, {}).setdefault(stype, {}).setdefault(dtype, []).append(block)

    return overrides


def apply_schedule_overrides_to_schedules(base_schedules, overrides):
    """Merge schedule overrides into ``base_schedules`` in-place."""
    for cat, stypes in overrides.items():
        if cat not in base_schedules:
            base_schedules[cat] = {}
        for stype, days in stypes.items():
            if stype not in base_schedules[cat]:
                base_schedules[cat][stype] = {}
            for day_type, blocks in days.items():
                base_schedules[cat][stype][day_type] = blocks

    return base_schedules
