"""Automatically generated ventilation_lookup. Do not edit manually."""

ventilation_lookup = {
    "scenario1": {
        "pre_calibration": {
            "residential_infiltration_range": {
                "two_and_a_half_story_house": (1.1, 1.3),
                "apartment": (0.9, 1.1),
                "row_house": (1.0, 1.2),
            },
            "non_res_infiltration_range": {
                "meeting_function": (0.5, 0.7),
            },
            "year_factor_range": {
                "1900-2000": (2.0, 2.4),
            },
            "system_control_range_res": {
                "A": {
                    "f_ctrl_range": (0.9, 1.0),
                },
                "B": {
                    "f_ctrl_range": (0.5, 0.6),
                },
            },
            "fan_pressure_range": {
                "res_mech": (40.0, 60.0),
            },
            "hrv_sensible_eff_range": (0.7, 0.8),
        },
        "post_calibration": {
            "residential_infiltration_range": {
                "two_and_a_half_story_house": (1.2, 1.2),
            },
        },
    },
}
