# Elec/schedule_def.py

import pandas as pd # Keep import if excel reading functions are used

"""
This file holds:
1) A default SCHEDULE_DEFINITIONS dictionary for lighting usage patterns
   (weekday vs. weekend) for Residential & Non-Residential sub-types.
2) (Optional) Functions to read & apply schedule overrides from Excel.

NOTE (รอบนี้): The non-residential schedules below have been FURTHER REFINED
to represent more energy-conscious operational patterns. These are ILLUSTRATIVE
examples and MUST BE VALIDATED and customized based on specific project
requirements, occupancy data, control strategies, and local standards
(e.g., NTA 8800 usage profiles for the Netherlands).
"""

# 1) Default SCHEDULE Definitions
SCHEDULE_DEFINITIONS = {
    "Residential": {
        # Residential schedules - minor adjustments for potentially lower unoccupied use
        "Corner House": {
            "weekday": [(0, 6, 0.03), (6, 9, 0.25), (9, 17, 0.08), (17, 22, 0.45), (22, 24, 0.03)],
            "weekend": [(0, 7, 0.05), (7, 22, 0.35), (22, 24, 0.05)],
        },
        "Apartment": {
            "weekday": [(0, 6, 0.02), (6, 8, 0.20), (8, 18, 0.05), (18, 23, 0.40), (23, 24, 0.02)],
            "weekend": [(0, 8, 0.04), (8, 22, 0.30), (22, 24, 0.04)],
        },
        "Terrace or Semi-detached House": { # Similar to Corner House
            "weekday": [(0, 6, 0.03), (6, 9, 0.25), (9, 17, 0.08), (17, 22, 0.45), (22, 24, 0.03)],
            "weekend": [(0, 7, 0.05), (7, 22, 0.35), (22, 24, 0.05)],
        },
        "Detached House": {
            "weekday": [(0, 6, 0.04), (6, 9, 0.30), (9, 17, 0.10), (17, 22, 0.50), (22, 24, 0.04)],
            "weekend": [(0, 7, 0.06), (7, 23, 0.40), (23, 24, 0.06)],
        },
        "Two-and-a-half-story House": { # Similar to Detached or Corner House
            "weekday": [(0, 6, 0.03), (6, 9, 0.25), (9, 17, 0.08), (17, 22, 0.45), (22, 24, 0.03)],
            "weekend": [(0, 7, 0.05), (7, 22, 0.35), (22, 24, 0.05)],
        },
    },
    "Non-Residential": {
        "Office Function": { # Assumes good practice, e.g. 8:00-18:00 core hours
            "weekday": [
                (0, 7, 0.02),   # Unoccupied / Cleaning minimal
                (7, 8, 0.15),   # Early arrivals / Setup
                (8, 12, 0.80),  # Morning peak (potentially lower with daylighting)
                (12, 13, 0.30), # Lunch (reduced lighting in some areas)
                (13, 17, 0.80), # Afternoon peak
                (17, 18, 0.25), # Late leavers / Winding down
                (18, 24, 0.02),  # Unoccupied
            ],
            "weekend": [ # Minimal, for security/occasional access
                (0, 24, 0.02),
            ],
        },
        "Retail Function": { # Core hours e.g., 10:00-18:00/19:00
            "weekday": [
                (0, 8, 0.01),   # Closed, security minimal
                (8, 10, 0.20),  # Staff prep, partial lighting
                (10, 18, 0.80), # Open - peak (could be higher for specific display, lower for ambient)
                (18, 19, 0.30), # Closing
                (19, 24, 0.01),  # Closed
            ],
            "weekend": [ # Assuming Saturday is similar to weekday, Sunday potentially shorter/lower
                (0, 9, 0.01),
                (9, 17, 0.75),  # e.g. Sunday hours
                (17, 18, 0.25),
                (18, 24, 0.01),
            ],
        },
        "Education Function": { # Schools/Universities during term
            "weekday": [
                (0, 7, 0.01),   # Closed
                (7, 8, 0.20),   # Staff arrival
                (8, 12, 0.75),  # Morning classes (daylight responsive could lower this)
                (12, 13, 0.25), # Lunch break (some areas lit)
                (13, 16, 0.75), # Afternoon classes
                (16, 18, 0.15), # After school activities / cleaning
                (18, 24, 0.01),  # Closed
            ],
            "weekend": [
                (0, 24, 0.01),  # Mostly closed
            ],
        },
        "Healthcare Function": { # Highly complex; this profile attempts some variation.
                                 # Assumes lower ambient light at night in patient areas/corridors.
            "weekday": [
                (0, 6, 0.25),   # Night (essential + reduced ambient)
                (6, 20, 0.65),  # Daytime operational (average across various spaces)
                (20, 24, 0.30), # Evening/early night
            ],
            "weekend": [ # Similar pattern, potentially slightly less intensive in admin areas
                (0, 6, 0.20),
                (6, 20, 0.60),
                (20, 24, 0.25),
            ],
        },
        "Meeting Function": {
            "weekday": [
                (0, 8, 0.01),
                (8, 9, 0.25),
                (9, 12, 0.70),
                (12, 13, 0.30),
                (13, 17, 0.70),
                (17, 18, 0.20),
                (18, 24, 0.01),
            ],
            "weekend": [
                (0, 24, 0.01),
            ],
        },
        "Sport Function": {
            "weekday": [
                (0, 7, 0.01),
                (7, 16, 0.50), # Daytime use / classes
                (16, 22, 0.80), # Evening peak
                (22, 24, 0.02),
            ],
            "weekend": [
                (0, 8, 0.01),
                (8, 20, 0.70), # Weekend peak
                (20, 24, 0.02),
            ],
        },
        "Cell Function": { # Constant low level for safety/security might be needed
            "weekday": [(0, 24, 0.40)], # Assuming dimmable, efficient, not full blast 24/7
            "weekend": [(0, 24, 0.40)],
        },
        "Industrial Function": { # Assuming single or double shift, not 24/7 production
            "weekday": [
                (0, 6, 0.02),   # Unoccupied
                (6, 18, 0.70),  # Main operational hours (e.g. 1 or 2 shifts)
                (18, 22, 0.10), # Cleaning / end of day
                (22, 24, 0.02),
            ],
            "weekend": [(0, 24, 0.02)], # Mostly off
        },
        "Accommodation Function": { # Hotels: diverse use in rooms, common areas more consistent
            "weekday": [ # Weighted average behavior
                (0, 6, 0.20),   # Night (corridors, some room use)
                (6, 10, 0.40),  # Morning peak
                (10, 17, 0.25), # Daytime (rooms variable, common areas moderate)
                (17, 23, 0.60), # Evening
                (23, 24, 0.20),
            ],
            "weekend": [ # Similar pattern, potentially higher occupancy
                (0, 6, 0.25),
                (6, 11, 0.50),
                (11, 17, 0.35),
                (17, 23, 0.65),
                (23, 24, 0.25),
            ],
        },
        "Other Use Function": {
            "weekday": [
                (0, 7, 0.02),
                (7, 19, 0.50), 
                (19, 24, 0.02),
            ],
            "weekend": [
                (0, 24, 0.05), 
            ],
        },
    },
}

# Functions to read/apply Excel overrides (kept as is)
def read_schedule_overrides_from_excel(excel_path):
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
        dtype = str(row["day_type"]).strip().lower()
        sh = float(row["start_hour"])
        eh = float(row["end_hour"])
        frac = float(row["fraction_value"])
        overrides.setdefault(cat, {}).setdefault(stype, {}).setdefault(dtype, []).append((sh, eh, frac))
    return overrides

def apply_schedule_overrides_to_schedules(base_schedules, overrides):
    for cat, stype_dict in overrides.items():
        base_schedules.setdefault(cat, {})
        for stype, daytypes_dict in stype_dict.items():
            base_schedules[cat].setdefault(stype, {})
            for day_type, blocks_list in daytypes_dict.items():
                base_schedules[cat][stype][day_type] = blocks_list
    return base_schedules