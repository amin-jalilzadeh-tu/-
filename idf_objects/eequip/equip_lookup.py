# eequip/equip_lookup.py
"""
Equipment Lookup Table (Pre/Post Calibration)
---------------------------------------------
This file defines default electric equipment parameters for both 
residential and non-residential buildings.

NOTE (รอบนี้): The "EQUIP_WM2_range" values below for non-residential pre_calibration
have been FURTHER ADJUSTED to represent MORE ENERGY-EFFICIENT or typical office/plug load
scenarios. Heavy process loads (e.g., large refrigeration in retail, industrial machinery)
are typically modeled separately. These are ILLUSTRATIVE examples and MUST BE VALIDATED
against specific project requirements and local standards (e.g., NTA 8800).
The tD_range and tN_range are NOT directly used by the EnergyPlus ELECTRICEQUIPMENT
object's energy calculation in the provided scripts; schedules from schedule_def.py are used.
"""

equip_lookup = {
    "pre_calibration": {
        # ===============================
        # 1) RESIDENTIAL (example sub-types) - Values seem generally plausible
        # ===============================
        "Residential": {
            "Corner House":                 { "EQUIP_WM2_range": (2.5, 4.0), "tD_range": (400, 600), "tN_range": (100, 200),
                                               "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_LOST_range": (1.0, 1.0) },
            "Apartment":                    { "EQUIP_WM2_range": (1.5, 3.0), "tD_range": (300, 500), "tN_range": (100, 200),
                                               "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_LOST_range": (1.0, 1.0) },
            "Terrace or Semi-detached House":{ "EQUIP_WM2_range": (2.5, 4.0), "tD_range": (400, 600), "tN_range": (100, 200),
                                               "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_LOST_range": (1.0, 1.0) },
            "Detached House":               { "EQUIP_WM2_range": (3.0, 5.0), "tD_range": (500, 700), "tN_range": (200, 300),
                                               "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_LOST_range": (1.0, 1.0) },
            "Two-and-a-half-story House":   { "EQUIP_WM2_range": (3.0, 5.0), "tD_range": (500, 700), "tN_range": (200, 300),
                                               "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                                               "EQUIP_FRACTION_LOST_range": (1.0, 1.0) }
        },
        # ===============================
        # 2) NON-RESIDENTIAL (Values adjusted for more typical/efficient plug loads)
        # ===============================
        "Non-Residential": {
            "Office Function": { # Standard office: PCs, monitors, printers, etc.
                "EQUIP_WM2_range": (4.0, 7.0),   # Adjusted from 8-10 previously
                "tD_range": (2000, 2400),
                "tN_range": (100, 250),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Retail Function": { # POS, back-office computers. Does NOT include large display refrigeration.
                "EQUIP_WM2_range": (3.0, 7.0),   # Adjusted from 10-12 (for general equipment)
                "tD_range": (2500, 3000),
                "tN_range": (200, 400),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Education Function": { # Classrooms: few PCs/projector, Staff rooms: more PCs
                "EQUIP_WM2_range": (2.5, 5.0),   # Adjusted from 7-9
                "tD_range": (1400, 1800),
                "tN_range": (100, 200),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Healthcare Function": { # General areas: nurse stations, office equip. Excludes specialized medical.
                "EQUIP_WM2_range": (4.0, 8.0),   # Adjusted from 10-12
                "tD_range": (3000, 4000),
                "tN_range": (500, 700),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Meeting Function": { # AV equipment, laptops if BYOD
                "EQUIP_WM2_range": (2.0, 5.0),   # Adjusted from 8-10
                "tD_range": (1800, 2200),
                "tN_range": (100, 200),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Sport Function": { # Reception PCs, small office, potentially some small fitness equip electronics
                "EQUIP_WM2_range": (1.5, 4.0),   # Adjusted from 9-11
                "tD_range": (2000, 2500),
                "tN_range": (300, 500),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Cell Function": { # Minimal in-cell, e.g. small TV or radio.
                "EQUIP_WM2_range": (1.0, 2.5),   # Adjusted from 8-10
                "tD_range": (3500, 4000),
                "tN_range": (800, 1000),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Industrial Function": { # Office/admin areas within industrial, not process machinery.
                "EQUIP_WM2_range": (3.0, 6.0),   # Adjusted from 12-15
                "tD_range": (2800, 3500),
                "tN_range": (300, 600),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Accommodation Function": { # Guest rooms: TV, charging, clock. Lobby: PCs.
                "EQUIP_WM2_range": (2.0, 4.0),   # Adjusted from 6-8
                "tD_range": (2000, 2800),
                "tN_range": (400, 700),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            },
            "Other Use Function": { # Generic non-residential equipment
                "EQUIP_WM2_range": (3.0, 6.0),   # Adjusted from 5-8
                "tD_range": (1500, 2000),
                "tN_range": (100, 300),
                "EQUIP_FRACTION_LATENT_range": (0.0, 0.0),
                "EQUIP_FRACTION_RADIANT_range": (0.0, 0.0),
                "EQUIP_FRACTION_LOST_range": (1.0, 1.0)
            }
        }
    },
    "post_calibration": {
        # Post-calibration values are highly project-specific.
        # Structure from your original file is maintained.
        "Residential": {
            "Corner House": {"EQUIP_WM2_range": (4.0,4.0), "tD_range": (500,500), "tN_range": (150,150),
                             "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                             "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                             "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Apartment": {"EQUIP_WM2_range": (3.0,3.0), "tD_range": (400,400), "tN_range": (150,150),
                         "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                         "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                         "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Terrace or Semi-detached House": {"EQUIP_WM2_range": (4.0,4.0), "tD_range": (500,500), "tN_range": (150,150),
                                               "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                               "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                               "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Detached House": {"EQUIP_WM2_range": (5.0,5.0), "tD_range": (600,600), "tN_range": (250,250),
                             "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                             "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                             "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Two-and-a-half-story House": {"EQUIP_WM2_range": (5.0,5.0), "tD_range": (600,600), "tN_range": (250,250),
                                         "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                         "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                         "EQUIP_FRACTION_LOST_range": (1.0,1.0)}
        },
        "Non-Residential": { # Copying one example, others would follow similar calibrated pattern
            "Office Function": {"EQUIP_WM2_range": (5.0,5.0), "tD_range": (2300,2300), "tN_range": (150,150),
                              "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                              "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                              "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            # ... other non-residential types with their calibrated values ...
            "Meeting Function": {"EQUIP_WM2_range": (4.0,4.0), "tD_range": (2000,2000), "tN_range": (150,150),
                               "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                               "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                               "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Healthcare Function": {"EQUIP_WM2_range": (7.0,7.0), "tD_range": (3800,3800), "tN_range": (600,600),
                                   "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                   "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                   "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Sport Function": {"EQUIP_WM2_range": (3.0,3.0), "tD_range": (2200,2200), "tN_range": (400,400),
                              "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                              "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                              "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Cell Function": {"EQUIP_WM2_range": (2.0,2.0), "tD_range": (3800,3800), "tN_range": (900,900),
                            "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                            "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                            "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Retail Function": {"EQUIP_WM2_range": (6.0,6.0), "tD_range": (2800,2800), "tN_range": (300,300),
                               "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                               "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                               "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Industrial Function": {"EQUIP_WM2_range": (5.0,5.0), "tD_range": (3000,3000), "tN_range": (400,400),
                                  "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                  "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                  "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Accommodation Function": {"EQUIP_WM2_range": (3.0,3.0), "tD_range": (2500,2500), "tN_range": (500,500),
                                     "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                     "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                     "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Education Function": {"EQUIP_WM2_range": (4.0,4.0), "tD_range": (1600,1600), "tN_range": (150,150),
                                 "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                 "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                 "EQUIP_FRACTION_LOST_range": (1.0,1.0)},
            "Other Use Function": {"EQUIP_WM2_range": (4.0,4.0), "tD_range": (1800,1800), "tN_range": (200,200),
                                 "EQUIP_FRACTION_LATENT_range": (0.0,0.0),
                                 "EQUIP_FRACTION_RADIANT_range": (0.0,0.0),
                                 "EQUIP_FRACTION_LOST_range": (1.0,1.0)}
        }
    }
}
