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
                (0, 7, 0.10),
                (7, 9, 0.35),
                (9, 17, 0.25),
                (17, 22, 0.55),
                (22, 24, 0.15),
            ],
            "weekend": [
                (0, 10, 0.20),
                (10, 20, 0.45),
                (20, 24, 0.25),
            ],
        },
        # Add more sub-types as needed...
    },
    "Non-Residential": {
        "Office Function": {
            "weekday": [
                (0, 6, 0.10),
                (6, 9, 0.50),
                (9, 12, 0.80),
                (12, 13, 0.60),
                (13, 17, 0.80),
                (17, 20, 0.50),
                (20, 24, 0.10),
            ],
            "weekend": [
                (0, 24, 0.15),
            ],
        },
        "Retail Function": {
            "weekday": [
                (0, 8, 0.10),
                (8, 10, 0.40),
                (10, 19, 0.80),
                (19, 21, 0.50),
                (21, 24, 0.20),
            ],
            "weekend": [
                (0, 9, 0.15),
                (9, 18, 0.70),
                (18, 22, 0.30),
                (22, 24, 0.15),
            ],
        },
        # Add more sub-types as needed...
    }
}
