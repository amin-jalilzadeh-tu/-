# HVAC/hvac_lookup.py




# HVAC/hvac_lookup.py
#
# A more extensive lookup that incorporates:
# - calibration_stage: "pre_calibration" or "post_calibration"
# - scenario: "scenario1" or "scenario2"
# - building_function: "residential" or "non_residential"
# - building_subtype: e.g. "Two-and-a-half-story House", "Meeting Function"
# - age_range: "1900-2000" or "2000-2024"
#
# The final nested dictionary includes setpoint ranges, supply air temps,
# and additional schedule hints (day/night times, occupancy patterns, etc.)
#
# You can expand or shrink as needed for your application.

hvac_lookup = {
    "pre_calibration": {
        "scenario1": {
            "residential": {
                "Two-and-a-half-story House": {
                    "1900-2000": {
                        # Typical setpoint ranges
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),

                        # Supply air temp assumptions (e.g. "LT" system)
                        "max_heating_supply_air_temp_range": (45.0, 55.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),

                        # Extra schedule info (example):
                        # We'll define day from 07:00-23:00, night otherwise
                        "schedule_details": {
                            "day_start": "07:00",
                            "day_end": "23:00",

                            # Possibly occupancy pattern (residential all week)
                            "occupancy_schedule": {
                                "weekday": "FullOccupancy",  # interpret later
                                "weekend": "FullOccupancy",
                            },
                            # You could add more granularity (e.g. arrays of hourly multipliers)
                        }
                    },
                    "2000-2024": {
                        # Maybe slightly narrower or slightly higher performance
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),

                        "max_heating_supply_air_temp_range": (45.0, 55.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),

                        "schedule_details": {
                            "day_start": "07:00",
                            "day_end": "23:00",
                            "occupancy_schedule": {
                                "weekday": "FullOccupancy",
                                "weekend": "FullOccupancy",
                            },
                        }
                    },
                }
            },
            "non_residential": {
                "Meeting Function": {
                    "1900-2000": {
                        "heating_day_setpoint_range": (20.0, 22.0),
                        "heating_night_setpoint_range": (15.0, 17.0),
                        "cooling_day_setpoint_range": (23.0, 25.0),
                        "cooling_night_setpoint_range": (25.0, 27.0),

                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),

                        "schedule_details": {
                            # Maybe it operates weekdays 08:00-22:00, weekends 08:00-18:00
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",

                            # Occupancy (some example text or keys you parse later)
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            }
                        }
                    },
                    "2000-2024": {
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),

                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),

                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            }
                        }
                    },
                }
            }
        },

        "scenario2": {
            # You can define similarly or override certain keys
            # We'll show just one example for brevity
            "residential": {
                "Two-and-a-half-story House": {
                    "1992-2005": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),

                        "max_heating_supply_air_temp_range": (50.0, 55.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),

                        "schedule_details": {
                            "day_start": "06:00",
                            "day_end": "22:00",
                            "occupancy_schedule": {
                                "weekday": "FullOccupancy",
                                "weekend": "FullOccupancy",
                            },
                        }
                    }
                }
            }
            # etc. ...
        }
    },

    "post_calibration": {
        # Possibly narrower/fixed values after calibration
        "scenario1": {
            "residential": {
                "Two-and-a-half-story House": {
                    "1900-2000": {
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (25.0, 25.0),
                        "cooling_night_setpoint_range": (27.0, 27.0),

                        "max_heating_supply_air_temp_range": (50.0, 50.0),
                        "min_cooling_supply_air_temp_range": (13.0, 13.0),

                        "schedule_details": {
                            "day_start": "07:00",
                            "day_end": "22:00",
                            "occupancy_schedule": {
                                "weekday": "FullOccupancy",
                                "weekend": "FullOccupancy",
                            },
                        }
                    },
                    # ... likewise for "2000-2024"
                }
            },
            "non_residential": {
                "Meeting Function": {
                    "1900-2000": {
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.0),
                        "cooling_night_setpoint_range": (26.0, 26.0),

                        "max_heating_supply_air_temp_range": (65.0, 65.0),
                        "min_cooling_supply_air_temp_range": (13.0, 13.0),

                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            }
                        }
                    }
                }
            }
        },
        "scenario2": {
            # etc. similarly...
        }
    }
}
