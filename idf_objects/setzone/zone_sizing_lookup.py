# setzone/zone_sizing_lookup.py

zone_sizing_lookup = {
    "pre_calibration": {
        "residential": {
            "cooling_supply_air_temp_range": (13.5, 14.5),
            "heating_supply_air_temp_range": (48.0, 52.0),
            "cooling_supply_air_hr_range": (0.0085, 0.0095),
            "heating_supply_air_hr_range": (0.0035, 0.0045),
            "cooling_design_air_flow_method": "DesignDayWithLimit",
            "heating_design_air_flow_method": "DesignDay"
        },
        "non_residential": {
            "cooling_supply_air_temp_range": (12.0, 14.0),
            "heating_supply_air_temp_range": (40.0, 45.0),
            "cooling_supply_air_hr_range": (0.009, 0.010),
            "heating_supply_air_hr_range": (0.004, 0.005),
            "cooling_design_air_flow_method": "DesignDay",
            "heating_design_air_flow_method": "DesignDay"
        }
    },
    "post_calibration": {
        "residential": {
            "cooling_supply_air_temp_range": (14.0, 14.0),  # fixed
            "heating_supply_air_temp_range": (50.0, 50.0),  # fixed
            "cooling_supply_air_hr_range": (0.009, 0.009),
            "heating_supply_air_hr_range": (0.004, 0.004),
            "cooling_design_air_flow_method": "Flow/Zone",
            "heating_design_air_flow_method": "DesignDayWithLimit"
        },
        "non_residential": {
            "cooling_supply_air_temp_range": (13.0, 13.0),
            "heating_supply_air_temp_range": (42.0, 42.0),
            "cooling_supply_air_hr_range": (0.0095, 0.0095),
            "heating_supply_air_hr_range": (0.0045, 0.0045),
            "cooling_design_air_flow_method": "DesignDay",
            "heating_design_air_flow_method": "Flow/Zone"
        }
    }
}
