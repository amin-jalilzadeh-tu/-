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
                "lights_fraction_radiant_range": (0.7, 0.7),
                "lights_fraction_visible_range": (0.2, 0.2),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (1.0, 1.0),
            },
            "Apartment": { "LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Terrace or Semi-detached House": { "LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Detached House": { "LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Two-and-a-half-story House": { "LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)}
        },

        # ===============================
        # 2) NON-RESIDENTIAL (Values further adjusted for higher efficiency)
        # ===============================
        "Non-Residential": {
            "Office Function": {
                "LIGHTS_WM2_range": (4.0, 7.0),    # Efficient office LPD
                "PARASITIC_WM2_range": (0.1, 0.15), # Lowered for efficient drivers
                "tD_range": (2000, 2500),
                "tN_range": (100, 200),
                "lights_fraction_radiant_range": (0.6, 0.7),
                "lights_fraction_visible_range": (0.2, 0.25),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0), # Parasitic equip heat gain
                "equip_fraction_lost_range": (0.0, 0.0),    # Assume parasitic heat contributes to zone
            },
            "Retail Function": { # General ambient lighting; display can be extra or averaged in
                "LIGHTS_WM2_range": (6.0, 12.0),   # Lowered significantly
                "PARASITIC_WM2_range": (0.15, 0.25),
                "tD_range": (3000, 4000),
                "tN_range": (200, 400),
                "lights_fraction_radiant_range": (0.6, 0.7),
                "lights_fraction_visible_range": (0.2, 0.25),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Education Function": { # Classrooms, libraries
                "LIGHTS_WM2_range": (3.5, 6.0),    # Efficient school lighting
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (1500, 1800),
                "tN_range": (50, 100),
                "lights_fraction_radiant_range": (0.6, 0.7),
                "lights_fraction_visible_range": (0.2, 0.25),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Healthcare Function": { # General areas; labs/surgery distinct
                "LIGHTS_WM2_range": (5.0, 9.0),    # Lowered for general patient/corridor areas
                "PARASITIC_WM2_range": (0.15, 0.25),
                "tD_range": (3000, 5000),
                "tN_range": (500, 1000),
                "lights_fraction_radiant_range": (0.6, 0.7),
                "lights_fraction_visible_range": (0.2, 0.25),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Meeting Function": {
                "LIGHTS_WM2_range": (5.0, 8.0),
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (1800, 2200),
                "tN_range": (200, 300),
                "lights_fraction_radiant_range": (0.6, 0.7),
                "lights_fraction_visible_range": (0.2, 0.25),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Sport Function": {
                "LIGHTS_WM2_range": (7.0, 11.0), # Maintained, as sports lighting can be intensive
                "PARASITIC_WM2_range": (0.15, 0.25),
                "tD_range": (2000, 2500),
                "tN_range": (500, 800),
                "lights_fraction_radiant_range": (0.5, 0.6),
                "lights_fraction_visible_range": (0.25, 0.3),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Cell Function": {
                "LIGHTS_WM2_range": (4.0, 7.0), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (6000, 8000),
                "tN_range": (6000, 8000),
                "lights_fraction_radiant_range": (0.7, 0.7),
                "lights_fraction_visible_range": (0.2, 0.2),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Industrial Function": { # General lighting, not process-specific
                "LIGHTS_WM2_range": (5.0, 9.0), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.2),
                "tD_range": (2500, 4000),
                "tN_range": (100, 300),
                "lights_fraction_radiant_range": (0.5, 0.6),
                "lights_fraction_visible_range": (0.25, 0.3),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Accommodation Function": { # Guest rooms / dorms
                "LIGHTS_WM2_range": (3.0, 6.0), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.15),
                "tD_range": (1500, 2500),
                "tN_range": (3000, 5000),
                "lights_fraction_radiant_range": (0.7, 0.7),
                "lights_fraction_visible_range": (0.2, 0.2),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            },
            "Other Use Function": {
                "LIGHTS_WM2_range": (5.0, 8.0), # Lowered
                "PARASITIC_WM2_range": (0.1, 0.2),
                "tD_range": (2000, 2500),
                "tN_range": (100, 300),
                "lights_fraction_radiant_range": (0.7, 0.7),
                "lights_fraction_visible_range": (0.2, 0.2),
                "lights_fraction_replaceable_range": (1.0, 1.0),
                "equip_fraction_radiant_range": (0.0, 0.0),
                "equip_fraction_lost_range": (0.0, 0.0),
            }
        }
    },
    "post_calibration": {
        # Post-calibration values are highly project-specific and should be
        # determined by actual calibration efforts.
        # The structure from your original file is maintained as a placeholder.
        "Residential": {
            "Corner House": {"LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Apartment": {"LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Terrace or Semi-detached House": {"LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Detached House": {"LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)},
            "Two-and-a-half-story House": {"LIGHTS_WM2_range": (0.0,0.0), "PARASITIC_WM2_range": (0.0,0.0), "tD_range": (0,0), "tN_range": (0,0), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (1.0,1.0)}
        },
        "Non-Residential": { # Copying one example, others would follow similar calibrated pattern
            "Office Function": {"LIGHTS_WM2_range": (5.0,5.0), "PARASITIC_WM2_range": (0.1,0.1), "tD_range": (2300,2300), "tN_range": (150,150), "lights_fraction_radiant_range": (0.6,0.6), "lights_fraction_visible_range": (0.25,0.25), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            # ... other non-residential types should be filled with actual calibrated values ...
            "Meeting Function": {"LIGHTS_WM2_range": (6.0,6.0), "PARASITIC_WM2_range": (0.1,0.1), "tD_range": (2000,2000), "tN_range": (200,200), "lights_fraction_radiant_range": (0.6,0.6), "lights_fraction_visible_range": (0.25,0.25), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Healthcare Function": {"LIGHTS_WM2_range": (7.0,7.0), "PARASITIC_WM2_range": (0.2,0.2), "tD_range": (4000,4000), "tN_range": (600,600), "lights_fraction_radiant_range": (0.65,0.65), "lights_fraction_visible_range": (0.22,0.22), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Sport Function": {"LIGHTS_WM2_range": (9.0,9.0), "PARASITIC_WM2_range": (0.2,0.2), "tD_range": (2200,2200), "tN_range": (550,550), "lights_fraction_radiant_range": (0.55,0.55), "lights_fraction_visible_range": (0.28,0.28), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Cell Function": {"LIGHTS_WM2_range": (5.0,5.0), "PARASITIC_WM2_range": (0.1,0.1), "tD_range": (7000,7000), "tN_range": (7000,7000), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Retail Function": {"LIGHTS_WM2_range": (10.0,10.0), "PARASITIC_WM2_range": (0.2,0.2), "tD_range": (3200,3200), "tN_range": (250,250), "lights_fraction_radiant_range": (0.65,0.65), "lights_fraction_visible_range": (0.22,0.22), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Industrial Function": {"LIGHTS_WM2_range": (7.0,7.0), "PARASITIC_WM2_range": (0.1,0.1), "tD_range": (3000,3000), "tN_range": (150,150), "lights_fraction_radiant_range": (0.55,0.55), "lights_fraction_visible_range": (0.28,0.28), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Accommodation Function": {"LIGHTS_WM2_range": (4.0,4.0), "PARASITIC_WM2_range": (0.1,0.1), "tD_range": (2000,2000), "tN_range": (3500,3500), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Education Function": {"LIGHTS_WM2_range": (4.0,4.0), "PARASITIC_WM2_range": (0.1,0.1), "tD_range": (1600,1600), "tN_range": (60,60), "lights_fraction_radiant_range": (0.65,0.65), "lights_fraction_visible_range": (0.22,0.22), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)},
            "Other Use Function": {"LIGHTS_WM2_range": (6.0,6.0), "PARASITIC_WM2_range": (0.15,0.15), "tD_range": (2200,2200), "tN_range": (150,150), "lights_fraction_radiant_range": (0.7,0.7), "lights_fraction_visible_range": (0.2,0.2), "lights_fraction_replaceable_range": (1.0,1.0), "equip_fraction_radiant_range": (0.0,0.0), "equip_fraction_lost_range": (0.0,0.0)}
        }
    }
}