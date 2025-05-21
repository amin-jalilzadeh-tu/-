# eequip/schedule_def.py

"""
EQUIP_SCHEDULE_DEFINITIONS
===========================
This dictionary defines typical usage patterns for electric equipment
throughout the day, differentiating weekday vs. weekend, and by building
category (Residential vs. Non-Residential) and sub-type.

NOTE (รอบนี้): The non-residential schedules below have been FURTHER REFINED
to represent more energy-conscious or typical operational patterns for general
plug loads and office-type equipment. These are ILLUSTRATIVE examples and
MUST BE VALIDATED and customized based on specific project requirements,
occupancy data, equipment types, and local standards (e.g., NTA 8800).
"""

EQUIP_SCHEDULE_DEFINITIONS = {
    "Residential": {
        # Residential equipment schedules - adjusted slightly for plausibility
        "Corner House": {
            "weekday": [(0, 6, 0.08), (6, 9, 0.35), (9, 17, 0.18), (17, 21, 0.50), (21, 24, 0.15)],
            "weekend": [(0, 7, 0.10), (7, 22, 0.45), (22, 24, 0.15)],
        },
        "Apartment": {
            "weekday": [(0, 6, 0.06), (6, 8, 0.25), (8, 18, 0.12), (18, 23, 0.45), (23, 24, 0.08)],
            "weekend": [(0, 8, 0.08), (8, 22, 0.40), (22, 24, 0.10)],
        },
        "Terrace or Semi-detached House": {
            "weekday": [(0, 6, 0.08), (6, 9, 0.35), (9, 17, 0.18), (17, 22, 0.50), (22, 24, 0.15)],
            "weekend": [(0, 7, 0.10), (7, 22, 0.45), (22, 24, 0.15)],
        },
        "Detached House": {
            "weekday": [(0, 6, 0.10), (6, 9, 0.40), (9, 17, 0.20), (17, 22, 0.55), (22, 24, 0.20)],
            "weekend": [(0, 7, 0.12), (7, 23, 0.50), (23, 24, 0.20)],
        },
        "Two-and-a-half-story House": {
            "weekday": [(0, 6, 0.08), (6, 9, 0.35), (9, 17, 0.18), (17, 22, 0.50), (22, 24, 0.15)],
            "weekend": [(0, 7, 0.10), (7, 22, 0.45), (22, 24, 0.15)],
        },
    },
    "Non-Residential": {
        "Office Function": { # Equipment (PCs, monitors) often on during work hours
            "weekday": [
                (0, 7, 0.05),   # Night standby (network gear, some PCs in sleep)
                (7, 8, 0.30),   # Arrival, boot up
                (8, 12, 0.75),  # Core work hours (PCs active)
                (12, 13, 0.50), # Lunch (some PCs sleep/idle, some active)
                (13, 17, 0.75), # Core work hours
                (17, 18, 0.40), # Winding down, some shutdown
                (18, 24, 0.05),  # Night standby
            ],
            "weekend": [ # Minimal, mainly server/network gear or essential services
                (0, 24, 0.05),
            ],
        },
        "Retail Function": { # POS, back-office. Excludes major refrigeration/process loads.
            "weekday": [
                (0, 8, 0.03),   # Closed, essential standby
                (8, 10, 0.40),  # Staff prep, systems on
                (10, 18, 0.70), # Open - active POS, back office
                (18, 19, 0.35), # Closing tasks
                (19, 24, 0.03),  # Closed
            ],
            "weekend": [
                (0, 9, 0.03),
                (9, 17, 0.65),  # Weekend opening hours
                (17, 18, 0.25),
                (18, 24, 0.03),
            ],
        },
        "Education Function": { # Computers in labs/classrooms, staff PCs
            "weekday": [
                (0, 7, 0.02),
                (7, 8, 0.30),   # Staff arrive, systems on
                (8, 12, 0.65),  # Classes, computer use
                (12, 13, 0.20), # Lunch, lower use
                (13, 16, 0.65), # Classes
                (16, 18, 0.10), # Staff finishing up
                (18, 24, 0.02),
            ],
            "weekend": [(0, 24, 0.02)], # Mostly off
        },
        "Healthcare Function": { # Office equip, nurse stations, patient monitoring (not heavy medical imaging)
            "weekday": [ # Assumes some 24/7 base for critical, higher for admin/clinic hours
                (0, 7, 0.40),   # Night essentials
                (7, 19, 0.60),  # Daytime higher activity
                (19, 22, 0.50), # Evening
                (22, 24, 0.40),
            ],
            "weekend": [
                (0, 7, 0.35),
                (7, 19, 0.55),
                (19, 22, 0.45),
                (22, 24, 0.35),
            ],
        },
        "Meeting Function": { # AV, laptops
            "weekday": [
                (0, 8, 0.02),
                (8, 9, 0.20),
                (9, 12, 0.50), # Intermittent use of AV/laptops
                (12, 13, 0.15),
                (13, 17, 0.50),
                (17, 18, 0.10),
                (18, 24, 0.02),
            ],
            "weekend": [(0, 24, 0.02)],
        },
        "Sport Function": { # Office/reception, some electronic fitness if applicable
            "weekday": [
                (0, 7, 0.01),
                (7, 16, 0.30), 
                (16, 22, 0.60), 
                (22, 24, 0.02),
            ],
            "weekend": [
                (0, 8, 0.01),
                (8, 20, 0.50), 
                (20, 24, 0.02),
            ],
        },
        "Cell Function": { # Minimal in-cell equipment
            "weekday": [(0, 24, 0.20)], # Reduced
            "weekend": [(0, 24, 0.20)],
        },
        "Industrial Function": { # Assumes office/control part of industrial, not main machinery
            "weekday": [
                (0, 6, 0.05),
                (6, 18, 0.60), # Operational hours for support equipment
                (18, 22, 0.08),
                (22, 24, 0.05),
            ],
            "weekend": [(0, 24, 0.05)],
        },
        "Accommodation Function": { # Guest room + common area office/lobby equip
            "weekday": [
                (0, 6, 0.20),
                (6, 10, 0.35),
                (10, 17, 0.20),
                (17, 23, 0.50),
                (23, 24, 0.20),
            ],
            "weekend": [
                (0, 6, 0.22),
                (6, 11, 0.40),
                (11, 17, 0.30),
                (17, 23, 0.55),
                (23, 24, 0.22),
            ],
        },
        "Other Use Function": {
            "weekday": [
                (0, 7, 0.03),
                (7, 19, 0.40), 
                (19, 24, 0.03),
            ],
            "weekend": [
                (0, 24, 0.05),
            ],
        },
    },
}

# Optional: Functions to read/apply Excel overrides (kept from original)
def read_schedule_overrides_from_excel(excel_path):
    """Read Excel overrides for schedule definitions."""
    import pandas as pd # Ensure pandas is available

    df = pd.read_excel(excel_path)
    required = [
        "building_category", "sub_type", "day_type",
        "start_hour", "end_hour", "fraction_value",
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
        base_schedules.setdefault(cat, {})
        for stype, days in stypes.items():
            base_schedules[cat].setdefault(stype, {})
            for day_type, blocks in days.items():
                base_schedules[cat][stype][day_type] = blocks
    return base_schedules