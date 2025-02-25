# ventilation_lookup.py

"""
This file defines a large nested dictionary called `ventilation_lookup`
that organizes infiltration/ventilation parameters AND the chosen system type
by:
  1) scenario ("scenario1" or "scenario2")
  2) calibration stage ("pre_calibration" or "post_calibration")

Within each stage, we have:
  - residential_infiltration_range
  - non_res_infiltration_range
  - year_factor_range
  - system_control_range_res
  - system_control_range_nonres
  - fan_pressure_range (optional)
  - hrv_sensible_eff_range
  - system_type_map (dictating system A/B/C/D)
"""

ventilation_lookup = {
    # -------------------------------------------------------------------------
    # SCENARIO 1
    # -------------------------------------------------------------------------
    "scenario1": {
        # =====================================================================
        # A) PRE-CALIBRATION
        # =====================================================================
        "pre_calibration": {
            # -----------------------------------------------------------
            # 1) Infiltration ranges (for Residential sub‐types)
            # -----------------------------------------------------------
            "residential_infiltration_range": {
                "Corner House": (1.2, 1.4),
                "Apartment": (0.8, 1.0),
                "Terrace or Semi-detached House": (1.0, 1.2),
                "Detached House": (1.2, 1.5),
                "Two-and-a-half-story House": (1.1, 1.3),
                "other_res": (1.0, 1.2)
            },

            # -----------------------------------------------------------
            # 2) Infiltration ranges (for Non-Residential sub‐types)
            # -----------------------------------------------------------
            "non_res_infiltration_range": {
                "Meeting Function": (0.5, 0.7),
                "Healthcare Function": (0.6, 0.8),
                "Sport Function": (0.4, 0.6),
                "Cell Function": (0.5, 0.7),
                "Retail Function": (0.6, 0.8),
                "Industrial Function": (0.6, 0.9),
                "Accommodation Function": (0.5, 0.7),
                "Office Function": (0.6, 0.8),
                "Education Function": (0.6, 0.8),
                "Other Use Function": (0.5, 0.7),
                "other_nonres": (0.5, 0.7)
            },

            # -----------------------------------------------------------
            # 3) Year-of-construction factor ranges (7 age bands)
            # -----------------------------------------------------------
            "year_factor_range": {
                "< 1945": (2.0, 2.3),
                "1945 - 1964": (1.8, 2.0),
                "1965 - 1974": (1.5, 1.7),
                "1975 - 1991": (1.3, 1.5),
                "1992 - 2005": (1.1, 1.3),
                "2006 - 2014": (0.9, 1.1),
                "2015 and later": (0.7, 0.9)
            },

            # -----------------------------------------------------------
            # 4) System control factors (f_ctrl range) for each system
            # -----------------------------------------------------------
            "system_control_range_res": {
                "A": {"f_ctrl_range": (0.90, 1.00)},
                "B": {"f_ctrl_range": (0.50, 0.60)},
                "C": {"f_ctrl_range": (0.80, 0.90)},
                "D": {"f_ctrl_range": (0.95, 1.05)}
            },
            "system_control_range_nonres": {
                "A": {"f_ctrl_range": (0.90, 1.00)},
                "B": {"f_ctrl_range": (0.80, 0.90)},
                "C": {"f_ctrl_range": (0.60, 0.70)},
                "D": {"f_ctrl_range": (0.75, 0.85)}
            },

            # -----------------------------------------------------------
            # 5) Optional fan pressure ranges (if used)
            # -----------------------------------------------------------
            "fan_pressure_range": {
                "res_mech": (40, 60),
                "nonres_intake": (90, 110),
                "nonres_exhaust": (140, 160)
            },

            # -----------------------------------------------------------
            # 6) HRV sensible efficiency
            # -----------------------------------------------------------
            "hrv_sensible_eff_range": (0.70, 0.80),

            # -----------------------------------------------------------
            # 7) system_type_map - new table picking A/B/C/D
            # -----------------------------------------------------------
            "system_type_map": {
                "residential": {
                    "< 1945": {
                        "Corner House": "A",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "B",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "1945 - 1964": {
                        "Corner House": "B",
                        "Apartment": "A",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "C"
                    },
                    "1965 - 1974": {
                        "Corner House": "A",
                        "Apartment": "B",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "C"
                    },
                    "1975 - 1991": {
                        "Corner House": "C",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "B",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "1992 - 2005": {
                        "Corner House": "B",
                        "Apartment": "A",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "D"
                    },
                    "2006 - 2014": {
                        "Corner House": "D",
                        "Apartment": "D",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "2015 and later": {
                        "Corner House": "D",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "A",
                        "Detached House": "B",
                        "Two-and-a-half-story House": "D"
                    }
                },
                "non_residential": {
                    "< 1945": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "1945 - 1964": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1965 - 1974": {
                        "Meeting Function": "B",
                        "Healthcare Function": "C",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "C",
                        "Industrial Function": "C",
                        "Accommodation Function": "B",
                        "Office Function": "B",
                        "Education Function": "D",
                        "Other Use Function": "A"
                    },
                    "1975 - 1991": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1992 - 2005": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "2006 - 2014": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "2015 and later": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    }
                }
            }
        },  # end pre_calibration

        # =====================================================================
        # B) POST-CALIBRATION
        # =====================================================================
        "post_calibration": {
            "residential_infiltration_range": {
                "Corner House": (1.3, 1.3),
                "Apartment": (0.9, 0.9),
                "Terrace or Semi-detached House": (1.1, 1.1),
                "Detached House": (1.3, 1.3),
                "Two-and-a-half-story House": (1.2, 1.2),
                "other_res": (1.1, 1.1)
            },

            "non_res_infiltration_range": {
                "Meeting Function": (0.6, 0.6),
                "Healthcare Function": (0.7, 0.7),
                "Sport Function": (0.5, 0.5),
                "Cell Function": (0.6, 0.6),
                "Retail Function": (0.7, 0.7),
                "Industrial Function": (0.7, 0.7),  # example if you like
                "Accommodation Function": (0.6, 0.6),
                "Office Function": (0.6, 0.6),
                "Education Function": (0.6, 0.6),
                "Other Use Function": (0.6, 0.6),
                "other_nonres": (0.6, 0.6)
            },

            "year_factor_range": {
                "< 1945": (2.2, 2.2),
                "1945 - 1964": (1.9, 1.9),
                "1965 - 1974": (1.6, 1.6),
                "1975 - 1991": (1.4, 1.4),
                "1992 - 2005": (1.2, 1.2),
                "2006 - 2014": (1.0, 1.0),
                "2015 and later": (0.8, 0.8)
            },

            "system_control_range_res": {
                "A": {"f_ctrl_range": (1.0, 1.0)},
                "B": {"f_ctrl_range": (0.57, 0.57)},
                "C": {"f_ctrl_range": (0.85, 0.85)},
                "D": {"f_ctrl_range": (1.0, 1.0)}
            },
            "system_control_range_nonres": {
                "A": {"f_ctrl_range": (1.0, 1.0)},
                "B": {"f_ctrl_range": (0.85, 0.85)},
                "C": {"f_ctrl_range": (0.65, 0.65)},
                "D": {"f_ctrl_range": (0.8, 0.8)}
            },

            "fan_pressure_range": {
                "res_mech": (50, 50),
                "nonres_intake": (100, 100),
                "nonres_exhaust": (150, 150)
            },
            "hrv_sensible_eff_range": (0.75, 0.75),

            "system_type_map": {
                "residential": {
                    "< 1945": {
                        "Corner House": "B",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "A"
                    },
                    "1945 - 1964": {
                        "Corner House": "A",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "D",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "C"
                    },
                    "1965 - 1974": {
                        "Corner House": "C",
                        "Apartment": "B",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "A"
                    },
                    "1975 - 1991": {
                        "Corner House": "B",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "B",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "1992 - 2005": {
                        "Corner House": "C",
                        "Apartment": "A",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "D"
                    },
                    "2006 - 2014": {
                        "Corner House": "D",
                        "Apartment": "D",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "2015 and later": {
                        "Corner House": "D",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "A",
                        "Detached House": "B",
                        "Two-and-a-half-story House": "D"
                    }
                },
                "non_residential": {
                    "< 1945": {
                        "Meeting Function": "D",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "1945 - 1964": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1965 - 1974": {
                        "Meeting Function": "B",
                        "Healthcare Function": "C",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "C",
                        "Industrial Function": "C",
                        "Accommodation Function": "B",
                        "Office Function": "B",
                        "Education Function": "D",
                        "Other Use Function": "A"
                    },
                    "1975 - 1991": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1992 - 2005": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "2006 - 2014": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "2015 and later": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    }
                }
            }
        }
    },

    # -------------------------------------------------------------------------
    # SCENARIO 2
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # SCENARIO 2 (fully populated, no placeholders)
    # -------------------------------------------------------------------------
    "scenario2": {
        # =====================================================================
        # A) PRE-CALIBRATION
        # =====================================================================
        "pre_calibration": {
            # -----------------------------------------------------------
            # 1) Infiltration ranges (for Residential sub‐types)
            # -----------------------------------------------------------
            "residential_infiltration_range": {
                "Corner House": (1.2, 1.4),
                "Apartment": (0.8, 1.0),
                "Terrace or Semi-detached House": (1.0, 1.2),
                "Detached House": (1.2, 1.5),
                "Two-and-a-half-story House": (1.1, 1.3),
                "other_res": (1.0, 1.2)
            },

            # -----------------------------------------------------------
            # 2) Infiltration ranges (for Non-Residential sub‐types)
            # -----------------------------------------------------------
            "non_res_infiltration_range": {
                "Meeting Function": (0.6, 0.8),
                "Healthcare Function": (0.7, 0.9),
                "Sport Function": (0.5, 0.7),
                "Cell Function": (0.6, 0.8),
                "Retail Function": (0.7, 0.9),
                "Industrial Function": (0.7, 1.0),
                "Accommodation Function": (0.5, 0.7),
                "Office Function": (0.6, 0.8),
                "Education Function": (0.6, 0.8),
                "Other Use Function": (0.6, 0.8),
                "other_nonres": (0.6, 0.8)
            },

            # -----------------------------------------------------------
            # 3) Year-of-construction factor ranges (7 age bands)
            # -----------------------------------------------------------
            "year_factor_range": {
                "< 1945": (2.1, 2.5),
                "1945 - 1964": (1.8, 2.2),
                "1965 - 1974": (1.6, 1.8),
                "1975 - 1991": (1.4, 1.6),
                "1992 - 2005": (1.2, 1.4),
                "2006 - 2014": (1.0, 1.2),
                "2015 and later": (0.8, 1.0)
            },

            # -----------------------------------------------------------
            # 4) System control factors (f_ctrl range) for each system
            # -----------------------------------------------------------
            "system_control_range_res": {
                "A": {"f_ctrl_range": (0.85, 0.95)},
                "B": {"f_ctrl_range": (0.45, 0.55)},
                "C": {"f_ctrl_range": (0.70, 0.80)},
                "D": {"f_ctrl_range": (0.90, 1.00)}
            },
            "system_control_range_nonres": {
                "A": {"f_ctrl_range": (0.85, 0.95)},
                "B": {"f_ctrl_range": (0.75, 0.85)},
                "C": {"f_ctrl_range": (0.55, 0.65)},
                "D": {"f_ctrl_range": (0.70, 0.80)}
            },

            # -----------------------------------------------------------
            # 5) Optional fan pressure ranges (if used)
            # -----------------------------------------------------------
            "fan_pressure_range": {
                "res_mech": (45, 65),
                "nonres_intake": (95, 115),
                "nonres_exhaust": (145, 165)
            },

            # -----------------------------------------------------------
            # 6) HRV sensible efficiency
            # -----------------------------------------------------------
            "hrv_sensible_eff_range": (0.65, 0.75),

            # -----------------------------------------------------------
            # 7) system_type_map - new table picking A/B/C/D
            # -----------------------------------------------------------
            "system_type_map": {
                "residential": {
                    "< 1945": {
                        "Corner House": "A",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "B",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "1945 - 1964": {
                        "Corner House": "C",
                        "Apartment": "B",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "C"
                    },
                    "1965 - 1974": {
                        "Corner House": "B",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "A",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "C"
                    },
                    "1975 - 1991": {
                        "Corner House": "C",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "B",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "1992 - 2005": {
                        "Corner House": "B",
                        "Apartment": "A",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "D"
                    },
                    "2006 - 2014": {
                        "Corner House": "D",
                        "Apartment": "D",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "2015 and later": {
                        "Corner House": "D",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "A",
                        "Detached House": "B",
                        "Two-and-a-half-story House": "D"
                    }
                },
                "non_residential": {
                    "< 1945": {
                        "Meeting Function": "D",
                        "Healthcare Function": "C",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "1945 - 1964": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1965 - 1974": {
                        "Meeting Function": "B",
                        "Healthcare Function": "C",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "C",
                        "Industrial Function": "C",
                        "Accommodation Function": "B",
                        "Office Function": "B",
                        "Education Function": "D",
                        "Other Use Function": "A"
                    },
                    "1975 - 1991": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1992 - 2005": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "2006 - 2014": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "2015 and later": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    }
                }
            }
        },  # end pre_calibration

        # =====================================================================
        # B) POST-CALIBRATION
        # =====================================================================
        "post_calibration": {
            "residential_infiltration_range": {
                "Corner House": (1.3, 1.3),
                "Apartment": (0.9, 0.9),
                "Terrace or Semi-detached House": (1.1, 1.1),
                "Detached House": (1.3, 1.3),
                "Two-and-a-half-story House": (1.2, 1.2),
                "other_res": (1.1, 1.1)
            },

            "non_res_infiltration_range": {
                "Meeting Function": (0.7, 0.7),
                "Healthcare Function": (0.8, 0.8),
                "Sport Function": (0.6, 0.6),
                "Cell Function": (0.7, 0.7),
                "Retail Function": (0.8, 0.8),
                "Industrial Function": (0.8, 0.8),
                "Accommodation Function": (0.7, 0.7),
                "Office Function": (0.7, 0.7),
                "Education Function": (0.7, 0.7),
                "Other Use Function": (0.7, 0.7),
                "other_nonres": (0.7, 0.7)
            },

            "year_factor_range": {
                "< 1945": (2.3, 2.3),
                "1945 - 1964": (2.0, 2.0),
                "1965 - 1974": (1.7, 1.7),
                "1975 - 1991": (1.5, 1.5),
                "1992 - 2005": (1.3, 1.3),
                "2006 - 2014": (1.1, 1.1),
                "2015 and later": (0.9, 0.9)
            },

            "system_control_range_res": {
                "A": {"f_ctrl_range": (1.0, 1.0)},
                "B": {"f_ctrl_range": (0.60, 0.60)},
                "C": {"f_ctrl_range": (0.80, 0.80)},
                "D": {"f_ctrl_range": (0.95, 0.95)}
            },
            "system_control_range_nonres": {
                "A": {"f_ctrl_range": (1.0, 1.0)},
                "B": {"f_ctrl_range": (0.80, 0.80)},
                "C": {"f_ctrl_range": (0.60, 0.60)},
                "D": {"f_ctrl_range": (0.75, 0.75)}
            },

            "fan_pressure_range": {
                "res_mech": (55, 55),
                "nonres_intake": (105, 105),
                "nonres_exhaust": (155, 155)
            },
            "hrv_sensible_eff_range": (0.70, 0.70),

            "system_type_map": {
                "residential": {
                    "< 1945": {
                        "Corner House": "B",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "A"
                    },
                    "1945 - 1964": {
                        "Corner House": "A",
                        "Apartment": "B",
                        "Terrace or Semi-detached House": "D",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "C"
                    },
                    "1965 - 1974": {
                        "Corner House": "C",
                        "Apartment": "B",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "A"
                    },
                    "1975 - 1991": {
                        "Corner House": "B",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "B",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "1992 - 2005": {
                        "Corner House": "C",
                        "Apartment": "A",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "D",
                        "Two-and-a-half-story House": "D"
                    },
                    "2006 - 2014": {
                        "Corner House": "D",
                        "Apartment": "D",
                        "Terrace or Semi-detached House": "C",
                        "Detached House": "C",
                        "Two-and-a-half-story House": "A"
                    },
                    "2015 and later": {
                        "Corner House": "D",
                        "Apartment": "C",
                        "Terrace or Semi-detached House": "A",
                        "Detached House": "B",
                        "Two-and-a-half-story House": "D"
                    }
                },
                "non_residential": {
                    "< 1945": {
                        "Meeting Function": "D",
                        "Healthcare Function": "C",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "1945 - 1964": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1965 - 1974": {
                        "Meeting Function": "B",
                        "Healthcare Function": "C",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "C",
                        "Industrial Function": "C",
                        "Accommodation Function": "B",
                        "Office Function": "B",
                        "Education Function": "D",
                        "Other Use Function": "A"
                    },
                    "1975 - 1991": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "1992 - 2005": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    },
                    "2006 - 2014": {
                        "Meeting Function": "C",
                        "Healthcare Function": "D",
                        "Sport Function": "B",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "A",
                        "Accommodation Function": "D",
                        "Office Function": "D",
                        "Education Function": "B",
                        "Other Use Function": "A"
                    },
                    "2015 and later": {
                        "Meeting Function": "A",
                        "Healthcare Function": "D",
                        "Sport Function": "C",
                        "Cell Function": "C",
                        "Retail Function": "B",
                        "Industrial Function": "B",
                        "Accommodation Function": "A",
                        "Office Function": "C",
                        "Education Function": "A",
                        "Other Use Function": "B"
                    }
                }
            }
        }
    }
}
