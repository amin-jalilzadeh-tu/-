# eequip/equip_lookup.py
"""
Equipment Lookup Table (Pre/Post Calibration)
---------------------------------------------
This file defines default electric equipment parameters for both 
residential and non-residential buildings.

We store everything in a nested dictionary `equip_lookup`, keyed by:
    1) Calibration stage: "pre_calibration" or "post_calibration"
    2) Building category: e.g. "Residential" or "Non-Residential"
    3) Sub-type: e.g. "Corner House", "Office Function", etc.
    4) Parameter key: "EQUIP_WM2_range", "tD_range", "tN_range", etc.

Adjust the default values/ranges for your real-world scenario.
"""

equip_lookup = {
    "pre_calibration": {
        # ===============================
        # 1) RESIDENTIAL (example sub-types)
        # ===============================
        "Residential": {
            "Corner House": {
                # A hypothetical range for typical equipment loads
                "EQUIP_WM2_range": (3.0, 5.0),
                "tD_range": (400, 600),  # daytime usage hours
                "tN_range": (100, 200)   # nighttime usage hours
            },
            "Apartment": {
                "EQUIP_WM2_range": (2.0, 4.0),
                "tD_range": (300, 500),
                "tN_range": (100, 200)
            },
            "Terrace or Semi-detached House": {
                "EQUIP_WM2_range": (3.0, 5.0),
                "tD_range": (400, 600),
                "tN_range": (100, 200)
            },
            "Detached House": {
                "EQUIP_WM2_range": (4.0, 6.0),
                "tD_range": (500, 700),
                "tN_range": (200, 300)
            }
        },
        # ===============================
        # 2) NON-RESIDENTIAL (example sub-types)
        # ===============================
        "Non-Residential": {
            "Office Function": {
                "EQUIP_WM2_range": (8.0, 10.0),
                "tD_range": (2000, 2200),
                "tN_range": (300, 400)
            },
            "Retail Function": {
                "EQUIP_WM2_range": (10.0, 12.0),
                "tD_range": (2500, 2700),
                "tN_range": (400, 500)
            },
            "Industrial Function": {
                "EQUIP_WM2_range": (12.0, 15.0),
                "tD_range": (3000, 3200),
                "tN_range": (600, 800)
            },
            "Other Use Function": {
                "EQUIP_WM2_range": (5.0, 8.0),
                "tD_range": (1500, 2000),
                "tN_range": (200, 400)
            }
        }
    },

    # ------------------------------------------
    #  POST-CALIBRATION (example narrower ranges)
    # ------------------------------------------
    "post_calibration": {
        "Residential": {
            "Corner House": {
                "EQUIP_WM2_range": (4.0, 4.0),
                "tD_range": (500, 500),
                "tN_range": (150, 150)
            },
            "Apartment": {
                "EQUIP_WM2_range": (3.0, 3.0),
                "tD_range": (400, 400),
                "tN_range": (150, 150)
            },
            "Terrace or Semi-detached House": {
                "EQUIP_WM2_range": (4.0, 4.0),
                "tD_range": (500, 500),
                "tN_range": (150, 150)
            },
            "Detached House": {
                "EQUIP_WM2_range": (5.0, 5.0),
                "tD_range": (600, 600),
                "tN_range": (250, 250)
            }
        },
        "Non-Residential": {
            "Office Function": {
                "EQUIP_WM2_range": (9.0, 9.0),
                "tD_range": (2100, 2100),
                "tN_range": (350, 350)
            },
            "Retail Function": {
                "EQUIP_WM2_range": (11.0, 11.0),
                "tD_range": (2600, 2600),
                "tN_range": (450, 450)
            },
            "Industrial Function": {
                "EQUIP_WM2_range": (13.0, 13.0),
                "tD_range": (3100, 3100),
                "tN_range": (700, 700)
            },
            "Other Use Function": {
                "EQUIP_WM2_range": (6.0, 6.0),
                "tD_range": (1800, 1800),
                "tN_range": (300, 300)
            }
        }
    }
}
