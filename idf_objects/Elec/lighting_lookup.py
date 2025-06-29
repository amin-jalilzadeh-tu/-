# Elec/lighting_lookup.py

"""
Lighting Lookup Table (Pre/Post Calibration)
---------------------------------------------
This version includes fraction parameters for both LIGHTS
and ELECTRICEQUIPMENT objects.

NOTE (รอบนี้): The "LIGHTS_WM2_range" values below for non-residential pre_calibration
have been FURTHER ADJUSTED to represent MORE ENERGY-EFFICIENT lighting scenarios.
These are ILLUSTRATIVE examples aiming for good practice levels and MUST BE
VALIDATED against specific project requirements and local standards (e.g., NTA 8800).
The tD_range and tN_range are NOT directly used by the EnergyPlus LIGHTS object's
energy calculation in the provided scripts; schedules from schedule_def.py are used.
"""

lighting_lookup = {
    "pre_calibration": {
        # ===============================
        # 1) RESIDENTIAL (all sub-types)
        # ===============================
        # LPD values remain 0.0 as per original; implies residential lighting
        # is accounted for elsewhere or via a different methodology in your project.
        "Residential": {
            "Corner House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0), # No separate parasitic if main LPD is 0
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Apartment": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Terrace or Semi-detached House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Detached House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Two-and-a-half-story House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            }
        },

        # ===============================
        # 2) NON-RESIDENTIAL (Values further adjusted for higher efficiency)
        # ===============================
        "Non-Residential": {
            "Office Function": {
                "LIGHTS_WM2_range": (3.2, 5.6),    # Efficient office LPD
                "PARASITIC_WM2_range": (0.1, 0.15), # Lowered for efficient drivers
                "tD_range": (2000, 2500),
                "tN_range": (100, 200),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Retail Function": { # General ambient lighting; display can be extra or averaged in
                "LIGHTS_WM2_range": (4.8, 9.6),   # Lowered significantly
                "PARASITIC_WM2_range": (0.15, 0.25),
                "tD_range": (3000, 4000),
                "tN_range": (200, 400),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Education Function": { # Classrooms, libraries
                "LIGHTS_WM2_range": (2.8, 4.8),    # Efficient school lighting
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (1500, 1800),
                "tN_range": (50, 100),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Healthcare Function": { # General areas; labs/surgery distinct
                "LIGHTS_WM2_range": (4.0, 7.2),    # Lowered for general patient/corridor areas
                "PARASITIC_WM2_range": (0.15, 0.25),
                "tD_range": (3000, 5000),
                "tN_range": (500, 1000),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Meeting Function": {
                "LIGHTS_WM2_range": (4.0, 6.4),
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (1800, 2200),
                "tN_range": (200, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Sport Function": {
                "LIGHTS_WM2_range": (5.6, 8.8), # Maintained, as sports lighting can be intensive
                "PARASITIC_WM2_range": (0.15, 0.25),
                "tD_range": (2000, 2500),
                "tN_range": (500, 800),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Cell Function": {
                "LIGHTS_WM2_range": (3.2, 5.6), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (6000, 8000),
                "tN_range": (6000, 8000),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Industrial Function": { # General lighting, not process-specific
                "LIGHTS_WM2_range": (4.0, 7.2), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.2),
                "tD_range": (2500, 4000),
                "tN_range": (100, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Accommodation Function": { # Guest rooms / dorms
                "LIGHTS_WM2_range": (2.4, 4.8), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (1500, 2500),
                "tN_range": (3000, 5000),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Other Use Function": {
                "LIGHTS_WM2_range": (4.0, 6.4), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.2),
                "tD_range": (2000, 2500),
                "tN_range": (100, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            }
        }
    },
    "post_calibration": {
        # Post-calibration values are highly project-specific and should be
        # determined by actual calibration efforts.
        # The structure from your original file is maintained as a placeholder.
        "Residential": {
            "Corner House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Apartment": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Terrace or Semi-detached House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Detached House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Two-and-a-half-story House": {
                "LIGHTS_WM2_range": (0.0, 0.0),
                "PARASITIC_WM2_range": (0.0, 0.0),
                "tD_range": (0, 0),
                "tN_range": (0, 0),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            }
        },
        "Non-Residential": {
            "Meeting Function": {
                "LIGHTS_WM2_range": (13.6, 13.6),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (2200, 2200),
                "tN_range": (300, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Healthcare Function": {
                "LIGHTS_WM2_range": (14.4, 14.4),
                "PARASITIC_WM2_range": (0.29, 0.29),
                "tD_range": (4000, 4000),
                "tN_range": (1000, 1000),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Sport Function": {
                "LIGHTS_WM2_range": (13.6, 13.6),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (2200, 2200),
                "tN_range": (800, 800),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Cell Function": {
                "LIGHTS_WM2_range": (13.6, 13.6),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (4000, 4000),
                "tN_range": (1000, 1000),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Retail Function": {
                "LIGHTS_WM2_range": (24.0, 24.0),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (2700, 2700),
                "tN_range": (400, 400),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Industrial Function": {
                "LIGHTS_WM2_range": (13.6, 13.6),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (2200, 2200),
                "tN_range": (300, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Accommodation Function": {
                "LIGHTS_WM2_range": (13.6, 13.6),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (4000, 4000),
                "tN_range": (1000, 1000),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Office Function": {
                "LIGHTS_WM2_range": (12.8, 12.8),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (2200, 2200),
                "tN_range": (300, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Education Function": {
                "LIGHTS_WM2_range": (12.0, 12.0),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (1600, 1600),
                "tN_range": (300, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            },
            "Other Use Function": {
                "LIGHTS_WM2_range": (12.8, 12.8),
                "PARASITIC_WM2_range": (0.285, 0.285),
                "tD_range": (2200, 2200),
                "tN_range": (300, 300),
                "lights_fraction_radiant_range": (0.1, 0.1),
                "lights_fraction_visible_range": (0.1, 0.1),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "lights_fraction_return_air_range": (0.8, 0.8),
                "equip_fraction_radiant_range": (0.1, 0.1),
                "equip_fraction_lost_range": (0.8, 0.8),
            }
        }
    }
}