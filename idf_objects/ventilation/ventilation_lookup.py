# ventilation_lookup.py

"""
This file defines a large nested dictionary called `ventilation_lookup`
that organizes infiltration/ventilation parameters by:
  1) scenario ("scenario1" or "scenario2")
  2) calibration stage ("pre_calibration" or "post_calibration")
Inside each stage, you have infiltration ranges, year factors, system controls, etc.

Example usage:
    from ventilation_lookup import ventilation_lookup

    # Suppose we want infiltration info for scenario2, pre_calibration, a "two_and_a_half_story_house"
    infiltration_ranges = ventilation_lookup["scenario2"]["pre_calibration"]["residential_infiltration_range"]
    infiltration_tuple = infiltration_ranges.get("two_and_a_half_story_house", (1.0, 1.2))
    # infiltration_tuple might be something like (1.3, 1.5) if you set it below
"""

ventilation_lookup = {
    # -------------------------------------------------------------------------
    # SCENARIO 1
    # -------------------------------------------------------------------------
    "scenario1": {
        "pre_calibration": {
            # -----------------------------------------------------------
            # 1) Infiltration ranges
            # -----------------------------------------------------------
            "residential_infiltration_range": {
                # Example new sub-type for a residential building
                "two_and_a_half_story_house": (1.1, 1.3),
                "apartment": (0.9, 1.1),
                "row_house": (1.0, 1.2),
            },
            "non_res_infiltration_range": {
                "meeting_function": (0.5, 0.7),
                "office_multi_lower": (0.4, 0.6),
                "office_multi_top": (0.6, 0.8)
            },

            # -----------------------------------------------------------
            # 2) Year-of-construction factor
            # -----------------------------------------------------------
            "year_factor_range": {
                "1900-2000":  (2.0, 2.4),
                "2000-2024":  (1.2, 1.4),
                "<1970":      (2.5, 3.5),
                "1970-1992":  (1.8, 2.2),
                "1992-2005":  (1.4, 1.6),
                "2005-2015":  (1.1, 1.3),
                ">2015":      (0.9, 1.1)
            },

            # -----------------------------------------------------------
            # 3) System control factors
            # -----------------------------------------------------------
            "system_control_range_res": {
                "A": {"f_ctrl_range": (0.9, 1.0)},
                "B": {"f_ctrl_range": (0.50, 0.60)},
                "C": {"f_ctrl_range": (0.80, 0.90)},
                "D": {"f_ctrl_range": (0.95, 1.05)}
            },
            "system_control_range_nonres": {
                "A": {"f_ctrl_range": (0.9, 1.0)},
                "B": {"f_ctrl_range": (0.80, 0.90)},
                "C": {"f_ctrl_range": (0.60, 0.70)},
                "D": {"f_ctrl_range": (0.75, 0.85)}
            },

            # -----------------------------------------------------------
            # 4) Fan pressure, HRV efficiency
            # -----------------------------------------------------------
            "fan_pressure_range": {
                "res_mech": (40, 60),
                "nonres_intake": (90, 110),
                "nonres_exhaust": (140, 160)
            },
            "hrv_sensible_eff_range": (0.7, 0.8)
        },

        "post_calibration": {
            "residential_infiltration_range": {
                "two_and_a_half_story_house": (1.2, 1.2),
                "apartment": (1.0, 1.0),
                "row_house": (1.1, 1.1)
            },
            "non_res_infiltration_range": {
                "meeting_function": (0.6, 0.6),
                "office_multi_lower": (0.5, 0.5),
                "office_multi_top": (0.7, 0.7)
            },

            "year_factor_range": {
                "1900-2000":  (2.2, 2.2),
                "2000-2024":  (1.3, 1.3),
                "<1970":      (3.0, 3.0),
                "1970-1992":  (2.0, 2.0),
                "1992-2005":  (1.5, 1.5),
                "2005-2015":  (1.2, 1.2),
                ">2015":      (1.0, 1.0)
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
            "hrv_sensible_eff_range": (0.75, 0.75)
        }
    },

    # -------------------------------------------------------------------------
    # SCENARIO 2
    # -------------------------------------------------------------------------
    "scenario2": {
        "pre_calibration": {
            "residential_infiltration_range": {
                # maybe scenario2 has slightly higher infiltration
                "two_and_a_half_story_house": (1.3, 1.5),
                "apartment": (1.0, 1.2),
                "row_house": (1.1, 1.3)
            },
            "non_res_infiltration_range": {
                # or scenario2 meeting_function infiltration a bit bigger
                "meeting_function": (0.6, 0.8),
                "office_multi_lower": (0.4, 0.7),
                "office_multi_top": (0.7, 0.9)
            },

            "year_factor_range": {
                "1900-2000":  (2.1, 2.5),
                "2000-2024":  (1.3, 1.5),
                "<1970":      (2.5, 3.5),
                "1970-1992":  (1.8, 2.2),
                "1992-2005":  (1.4, 1.6),
                "2005-2015":  (1.1, 1.3),
                ">2015":      (0.9, 1.1)
            },

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

            "fan_pressure_range": {
                "res_mech": (45, 65),
                "nonres_intake": (95, 115),
                "nonres_exhaust": (145, 165)
            },
            "hrv_sensible_eff_range": (0.65, 0.75)
        },

        "post_calibration": {
            "residential_infiltration_range": {
                "two_and_a_half_story_house": (1.4, 1.4),
                "apartment": (1.1, 1.1),
                "row_house": (1.2, 1.2)
            },
            "non_res_infiltration_range": {
                "meeting_function": (0.7, 0.7),
                "office_multi_lower": (0.6, 0.6),
                "office_multi_top": (0.75, 0.75)
            },

            "year_factor_range": {
                "1900-2000":  (2.3, 2.3),
                "2000-2024":  (1.4, 1.4),
                "<1970":      (3.2, 3.2),
                "1970-1992":  (2.2, 2.2),
                "1992-2005":  (1.6, 1.6),
                "2005-2015":  (1.3, 1.3),
                ">2015":      (1.0, 1.0)
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
            "hrv_sensible_eff_range": (0.70, 0.70)
        }
    }
}
