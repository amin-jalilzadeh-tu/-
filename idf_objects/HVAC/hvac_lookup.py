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
# 
# 
hvac_lookup = {
    "pre_calibration": {
        "scenario1": {
            "residential": {
                # Residential Building Types
                "Corner House": {
                    "2015 and later": {
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
                    "2006 - 2014": {
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
                    "1992 - 2005": {
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
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (18.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.5, 25.5),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "< 1945": {
                        "heating_day_setpoint_range": (18.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                },
                "Apartment": {
                    # For brevity the values below are similar to the Corner House;
                    # you can adjust them as appropriate.
                    "2015 and later": {
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
                    "2006 - 2014": {  # Similar structure as above
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
                    "1992 - 2005": {
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
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (18.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.5, 25.5),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "< 1945": {
                        "heating_day_setpoint_range": (18.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                },
                "Terrace or Semi-detached House": {
                    # Here we replicate the structure.
                    "2015 and later": {
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
                    "2006 - 2014": {
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
                    "1992 - 2005": {
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
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (18.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.5, 25.5),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "< 1945": {
                        "heating_day_setpoint_range": (18.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                },
                "Detached House": {
                    # Again, similar structure.
                    "2015 and later": {
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
                    "2006 - 2014": {
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
                    "1992 - 2005": {
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
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (18.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.5, 25.5),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "< 1945": {
                        "heating_day_setpoint_range": (18.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                },
                "Two-and-a-half-story House": {
                    # Retaining your original values (with additional age ranges)
                    "2015 and later": {
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
                    "2006 - 2014": {
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
                    "1992 - 2005": {
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
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.0, 21.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 26.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (18.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.5, 25.5),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                    "< 1945": {
                        "heating_day_setpoint_range": (18.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 28.0),
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
                },
            },
            "non_residential": {
                # Non-Residential Building Types
                "Meeting Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.0),
                        "cooling_night_setpoint_range": (26.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            },
                        }
                    },
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.0),
                        "cooling_night_setpoint_range": (26.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
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
                            },
                        }
                    },
                    "1975 - 1991": {  # Using Meeting Function defaults for older vintages
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.0),
                        "cooling_night_setpoint_range": (26.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (20.0, 20.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.0),
                        "cooling_night_setpoint_range": (26.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.5, 20.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.0),
                        "cooling_night_setpoint_range": (25.5, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.0, 19.5),
                        "heating_night_setpoint_range": (15.0, 15.5),
                        "cooling_day_setpoint_range": (23.0, 23.5),
                        "cooling_night_setpoint_range": (25.0, 25.5),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "MeetingFunction_Weekday",
                                "weekend": "MeetingFunction_Weekend",
                            },
                        }
                    },
                },
                "Healthcare Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (21.0, 22.0),
                        "heating_night_setpoint_range": (17.0, 17.0),
                        "cooling_day_setpoint_range": (25.0, 26.0),
                        "cooling_night_setpoint_range": (27.0, 28.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                    # Repeat similar structures for the remaining age ranges
                    "2006 - 2014": { 
                        "heating_day_setpoint_range": (21.0, 22.0),
                        "heating_night_setpoint_range": (17.0, 17.0),
                        "cooling_day_setpoint_range": (25.0, 26.0),
                        "cooling_night_setpoint_range": (27.0, 28.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.5),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Healthcare_Weekday",
                                "weekend": "Healthcare_Weekend",
                            },
                        }
                    },
                },
                "Sport Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (21.0, 22.0),
                        "heating_night_setpoint_range": (17.0, 17.0),
                        "cooling_day_setpoint_range": (25.0, 26.0),
                        "cooling_night_setpoint_range": (27.0, 28.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "19:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                    # ... and similarly for the remaining age ranges
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (21.0, 22.0),
                        "heating_night_setpoint_range": (17.0, 17.0),
                        "cooling_day_setpoint_range": (25.0, 26.0),
                        "cooling_night_setpoint_range": (27.0, 28.0),
                        "max_heating_supply_air_temp_range": (60.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "19:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 17.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 17.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 17.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.5),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (65.0, 70.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Sport_Weekday",
                                "weekend": "Sport_Weekend",
                            },
                        }
                    },
                },
                "Cell Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                    # The remaining age ranges follow a similar pattern:
                    "2006 - 2014": { 
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": { 
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": { 
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": { 
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": { 
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                    "< 1945": { 
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 15.5),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (62.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Cell_Weekday",
                                "weekend": "Cell_Weekend",
                            },
                        }
                    },
                },
                "Retail Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                    # ... additional age ranges similar to the above pattern
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.0, 15.5),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 15.0),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (63.0, 68.0),
                        "min_cooling_supply_air_temp_range": (12.5, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "09:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "10:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Retail_Weekday",
                                "weekend": "Retail_Weekend",
                            },
                        }
                    },
                },
                "Industrial Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (21.0, 22.0),
                        "heating_night_setpoint_range": (17.0, 17.0),
                        "cooling_day_setpoint_range": (25.0, 26.0),
                        "cooling_night_setpoint_range": (27.0, 28.0),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                    # Additional age ranges can follow a similar pattern.
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (21.0, 22.0),
                        "heating_night_setpoint_range": (17.0, 17.0),
                        "cooling_day_setpoint_range": (25.0, 26.0),
                        "cooling_night_setpoint_range": (27.0, 28.0),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.5, 17.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.5, 17.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.5, 17.0),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "19:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "18:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.5),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "18:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (65.0, 75.0),
                        "min_cooling_supply_air_temp_range": (13.0, 15.0),
                        "schedule_details": {
                            "weekday_day_start": "06:00",
                            "weekday_day_end": "18:00",
                            "weekend_day_start": "07:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Industrial_Weekday",
                                "weekend": "Industrial_Weekend",
                            },
                        }
                    },
                },
                "Accommodation Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.5, 16.5),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (58.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "20:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                    # Additional age ranges follow a similar structure...
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (20.5, 21.5),
                        "heating_night_setpoint_range": (16.5, 16.5),
                        "cooling_day_setpoint_range": (24.5, 25.5),
                        "cooling_night_setpoint_range": (26.5, 27.5),
                        "max_heating_supply_air_temp_range": (58.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "22:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "20:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "20:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "20:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "21:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "20:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "19:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 15.5),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "07:00",
                            "weekday_day_end": "20:00",
                            "weekend_day_start": "08:00",
                            "weekend_day_end": "19:00",
                            "occupancy_schedule": {
                                "weekday": "Accommodation_Weekday",
                                "weekend": "Accommodation_Weekend",
                            },
                        }
                    },
                },
                "Office Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (58.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "18:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                    # Remaining age ranges follow similar patterns...
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (58.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "18:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "16:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "16:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "16:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 15.5),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "16:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (18.5, 19.5),
                        "heating_night_setpoint_range": (15.0, 15.0),
                        "cooling_day_setpoint_range": (22.5, 23.5),
                        "cooling_night_setpoint_range": (24.5, 25.5),
                        "max_heating_supply_air_temp_range": (60.0, 65.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "16:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Office_Weekday",
                                "weekend": "Office_Weekend",
                            },
                        }
                    },
                },
                "Education Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (58.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                    # The rest of the age ranges can follow a similar structure
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (20.0, 21.0),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 25.0),
                        "cooling_night_setpoint_range": (26.0, 27.0),
                        "max_heating_supply_air_temp_range": (58.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (60.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "16:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (60.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "16:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.5, 20.5),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.5),
                        "cooling_night_setpoint_range": (25.5, 26.5),
                        "max_heating_supply_air_temp_range": (60.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "16:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                    "1945 - 1964": {
                        "heating_day_setpoint_range": (19.0, 20.0),
                        "heating_night_setpoint_range": (15.0, 15.5),
                        "cooling_day_setpoint_range": (23.0, 24.0),
                        "cooling_night_setpoint_range": (25.0, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "15:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "14:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (18.5, 19.5),
                        "heating_night_setpoint_range": (15.0, 15.0),
                        "cooling_day_setpoint_range": (22.5, 23.5),
                        "cooling_night_setpoint_range": (24.5, 25.5),
                        "max_heating_supply_air_temp_range": (60.0, 64.0),
                        "min_cooling_supply_air_temp_range": (12.0, 14.0),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "15:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "14:00",
                            "occupancy_schedule": {
                                "weekday": "Education_Weekday",
                                "weekend": "Education_Weekend",
                            },
                        }
                    },
                },
                "Other Use Function": {
                    "2015 and later": {
                        "heating_day_setpoint_range": (20.0, 20.5),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.5),
                        "cooling_night_setpoint_range": (26.0, 26.5),
                        "max_heating_supply_air_temp_range": (58.0, 63.0),
                        "min_cooling_supply_air_temp_range": (12.0, 13.5),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "18:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "OtherUse_Weekday",
                                "weekend": "OtherUse_Weekend",
                            },
                        }
                    },
                    # Similar entries for the other age ranges would follow
                    "2006 - 2014": {
                        "heating_day_setpoint_range": (20.0, 20.5),
                        "heating_night_setpoint_range": (16.0, 16.0),
                        "cooling_day_setpoint_range": (24.0, 24.5),
                        "cooling_night_setpoint_range": (26.0, 26.5),
                        "max_heating_supply_air_temp_range": (58.0, 63.0),
                        "min_cooling_supply_air_temp_range": (12.0, 13.5),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "18:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "17:00",
                            "occupancy_schedule": {
                                "weekday": "OtherUse_Weekday",
                                "weekend": "OtherUse_Weekend",
                            },
                        }
                    },
                    "1992 - 2005": {
                        "heating_day_setpoint_range": (19.5, 20.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.0),
                        "cooling_night_setpoint_range": (25.5, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 63.0),
                        "min_cooling_supply_air_temp_range": (12.0, 13.5),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "16:00",
                            "occupancy_schedule": {
                                "weekday": "OtherUse_Weekday",
                                "weekend": "OtherUse_Weekend",
                            },
                        }
                    },
                    "1975 - 1991": {
                        "heating_day_setpoint_range": (19.5, 20.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.0),
                        "cooling_night_setpoint_range": (25.5, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 63.0),
                        "min_cooling_supply_air_temp_range": (12.0, 13.5),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "16:00",
                            "occupancy_schedule": {
                                "weekday": "OtherUse_Weekday",
                                "weekend": "OtherUse_Weekend",
                            },
                        }
                    },
                    "1965 - 1974": {
                        "heating_day_setpoint_range": (19.5, 20.0),
                        "heating_night_setpoint_range": (15.5, 16.0),
                        "cooling_day_setpoint_range": (23.5, 24.0),
                        "cooling_night_setpoint_range": (25.5, 26.0),
                        "max_heating_supply_air_temp_range": (60.0, 63.0),
                        "min_cooling_supply_air_temp_range": (12.0, 13.5),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "17:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "16:00",
                            "occupancy_schedule": {
                                "weekday": "OtherUse_Weekday",
                                "weekend": "OtherUse_Weekend",
                            },
                        }
                    },
                    "< 1945": {
                        "heating_day_setpoint_range": (19.0, 19.5),
                        "heating_night_setpoint_range": (15.0, 15.0),
                        "cooling_day_setpoint_range": (23.0, 23.5),
                        "cooling_night_setpoint_range": (25.0, 25.5),
                        "max_heating_supply_air_temp_range": (60.0, 63.0),
                        "min_cooling_supply_air_temp_range": (12.0, 13.5),
                        "schedule_details": {
                            "weekday_day_start": "08:00",
                            "weekday_day_end": "16:00",
                            "weekend_day_start": "09:00",
                            "weekend_day_end": "15:00",
                            "occupancy_schedule": {
                                "weekday": "OtherUse_Weekday",
                                "weekend": "OtherUse_Weekend",
                            },
                        },
                    },
                },
            },
        },
        
    },
    
}
