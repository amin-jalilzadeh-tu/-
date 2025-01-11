# 1946

1. Characteristic Data

characteristic_data = {
    ("Corner Townhouse", "<1946", "pre_calibration"): {
        "usable_floor_area_m2": 110.75,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Single-family house with roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner Townhouse", "<1946", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (0.15, 0.15),
            "U_value_range": (2.44, 2.44)
        },
        "solid_wall": {
            "area_m2": 86.72,
            "R_value_range": (0.19, 0.35),
            "U_value_range": (2.78, 1.92)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (0.22, 0.25),
            "U_value_range": (2.56, 2.37)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (2.90, 1.40)
        },
        "doors": {
            "area_m2": 7.73,
            "U_value_range": (3.40, 1.40)
        }
    },
    ("Corner Townhouse", "<1946", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (0.15, 0.15),
            "U_value_range": (2.44, 2.44)
        },
        "solid_wall": {
            "area_m2": 86.72,
            "R_value_range": (0.35, 0.35),
            "U_value_range": (1.92, 1.92)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (0.25, 0.25),
            "U_value_range": (2.37, 2.37)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (2.90, 1.40)
        },
        "doors": {
            "area_m2": 7.73,
            "U_value_range": (3.40, 1.40)
        }
    },
    ("Corner Townhouse", "<1946", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 86.72,
            "R_value_range": (1.70, 0.53),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 7.73,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner Townhouse", "<1946", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 86.72,
            "R_value_range": (1.70, 0.53),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 7.73,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner Townhouse", "<1946", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 86.72,
            "R_value_range": (1.70, 0.53),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 7.73,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner Townhouse", "<1946", "scenario1", "pre_calibration"): {
        "ventilation_system": "Fully natural ventilation",
        "ventilation_provision": "A1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner Townhouse", "<1946", "scenario2", "pre_calibration"): {
        "ventilation_system": "Fully natural ventilation",
        "ventilation_provision": "A1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner Townhouse", "<1946", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner Townhouse", "<1946", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner Townhouse", "<1946", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner Townhouse", "<1946", "scenario1", "pre_calibration"): {
        "main_heating": "Local Heating",
        "system_type": "Individual",
        "heating_appliance": "Local Heating",
        "boiler_air_heating": "With Exhaust",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner Townhouse", "<1946", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Gas boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner Townhouse", "<1946", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Gas boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner Townhouse", "<1946", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner Townhouse", "<1946", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner Townhouse", "<1946", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner Townhouse", "<1946", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur) HR/CW",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner Townhouse", "<1946", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur) HR/CW",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner Townhouse", "<1946", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner Townhouse", "<1946", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner Townhouse", "<1946", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.04,
        "standard_value_kWh_m2": 169.22,
        "heat_demand_Q_H_nd_kWh_m2": 312.84
    },
    ("Corner Townhouse", "<1946", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.04,
        "standard_value_kWh_m2": 169.22,
        "heat_demand_Q_H_nd_kWh_m2": 259.57
    },
    ("Corner Townhouse", "<1946", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.04,
        "standard_value_kWh_m2": 169.22,
        "heat_demand_Q_H_nd_kWh_m2": 73.82
    },
    ("Corner Townhouse", "<1946", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.04,
        "standard_value_kWh_m2": 169.22,
        "heat_demand_Q_H_nd_kWh_m2": 73.82
    },
    ("Corner Townhouse", "<1946", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.04,
        "standard_value_kWh_m2": 169.22,
        "heat_demand_Q_H_nd_kWh_m2": 56.60
    }
}


# 1946-1964



1. Characteristic Data

characteristic_data = {
    ("Corner townhouse", "1946-1964", "pre_calibration"): {
        "usable_floor_area_m2": 110.90,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Corner townhouse with gable roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner townhouse", "1946-1964", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (0.15, 0.15),
            "U_value_range": (2.44, 2.44)
        },
        "solid_wall": {
            "area_m2": 86.02,
            "R_value_range": (0.35, 0.35),
            "U_value_range": (1.92, 1.92)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (0.22, 0.22),
            "U_value_range": (2.56, 2.56)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (5.10, 5.10)
        },
        "doors": {
            "area_m2": 5.31,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1946-1964", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (0.15, 0.15),
            "U_value_range": (2.44, 2.44)
        },
        "solid_wall": {
            "area_m2": 86.02,
            "R_value_range": (0.35, 0.35),
            "U_value_range": (1.92, 1.92)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (0.25, 0.25),
            "U_value_range": (2.37, 2.37)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.80, 1.80)
        },
        "doors": {
            "area_m2": 5.31,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1946-1964", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 86.02,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.31,
            "U_value_range": (2.00, 2.00)
        }
    },
    ("Corner townhouse", "1946-1964", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 86.02,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.31,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner townhouse", "1946-1964", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 54.15,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 86.02,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 72.28,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 21.32,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.31,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner townhouse", "1946-1964", "scenario1", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1946-1964", "scenario2", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1946-1964", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1946-1964", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1946-1964", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner townhouse", "1946-1964", "scenario1", "pre_calibration"): {
        "main_heating": "Local heating",
        "system_type": "Individual",
        "heating_appliance": "Local heating",
        "boiler_air_heating": "With exhaust",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1946-1964", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1946-1964", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1946-1964", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1946-1964", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner townhouse", "1946-1964", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1946-1964", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1946-1964", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1946-1964", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1946-1964", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner townhouse", "1946-1964", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.03,
        "standard_value_kWh_m2": 84.24,
        "heat_demand_Q_H_nd_kWh_m2": 258.12
    },
    ("Corner townhouse", "1946-1964", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.03,
        "standard_value_kWh_m2": 84.24,
        "heat_demand_Q_H_nd_kWh_m2": 208.22
    },
    ("Corner townhouse", "1946-1964", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.03,
        "standard_value_kWh_m2": 84.24,
        "heat_demand_Q_H_nd_kWh_m2": 70.49
    },
    ("Corner townhouse", "1946-1964", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.03,
        "standard_value_kWh_m2": 84.24,
        "heat_demand_Q_H_nd_kWh_m2": 70.49
    },
    ("Corner townhouse", "1946-1964", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 2.03,
        "standard_value_kWh_m2": 84.24,
        "heat_demand_Q_H_nd_kWh_m2": 53.89
    }
}



# 1965-1974



1. Characteristic Data

characteristic_data = {
    ("Corner townhouse", "1965-1974", "pre_calibration"): {
        "usable_floor_area_m2": 115.96,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Corner townhouse with gable roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner townhouse", "1965-1974", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (0.17, 0.17),
            "U_value_range": (2.33, 2.33)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (0.43, 0.43),
            "U_value_range": (1.67, 1.67)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (0.86, 0.86),
            "U_value_range": (0.97, 0.97)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (5.10, 5.10)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1965-1974", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (0.17, 0.17),
            "U_value_range": (2.33, 2.33)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (0.43, 0.43),
            "U_value_range": (1.67, 1.67)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (0.86, 0.86),
            "U_value_range": (0.97, 0.97)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (2.90, 2.90)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1965-1974", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (2.00, 2.00)
        }
    },
    ("Corner townhouse", "1965-1974", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner townhouse", "1965-1974", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner townhouse", "1965-1974", "scenario1", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1965-1974", "scenario2", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1965-1974", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1965-1974", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1965-1974", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner townhouse", "1965-1974", "scenario1", "pre_calibration"): {
        "main_heating": "Local heating",
        "system_type": "Individual",
        "heating_appliance": "Local heating",
        "boiler_air_heating": "With exhaust",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1965-1974", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1965-1974", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1965-1974", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1965-1974", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner townhouse", "1965-1974", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1965-1974", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1965-1974", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1965-1974", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1965-1974", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner townhouse", "1965-1974", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.81,
        "standard_value_kWh_m2": 75.55,
        "heat_demand_Q_H_nd_kWh_m2": 205.35
    },
    ("Corner townhouse", "1965-1974", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.81,
        "standard_value_kWh_m2": 75.55,
        "heat_demand_Q_H_nd_kWh_m2": 183.59
    },
    ("Corner townhouse", "1965-1974", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.81,
        "standard_value_kWh_m2": 75.55,
        "heat_demand_Q_H_nd_kWh_m2": 65.02
    },
    ("Corner townhouse", "1965-1974", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.81,
        "standard_value_kWh_m2": 75.55,
        "heat_demand_Q_H_nd_kWh_m2": 65.02
    },
    ("Corner townhouse", "1965-1974", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.81,
        "standard_value_kWh_m2": 75.55,
        "heat_demand_Q_H_nd_kWh_m2": 48.71
    }
}



# 1975 - 1991

1. Characteristic Data

characteristic_data = {
    ("Corner townhouse", "1975-1991", "pre_calibration"): {
        "usable_floor_area_m2": 112.97,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Corner townhouse with gable roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner townhouse", "1975-1991", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (0.52, 0.52),
            "U_value_range": (2.33, 2.33)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (0.43, 0.43),
            "U_value_range": (1.67, 1.67)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (0.86, 0.86),
            "U_value_range": (0.97, 0.97)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (5.10, 5.10)
        },
        "doors": {
            "area_m2": 4.57,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1975-1991", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (0.52, 0.52),
            "U_value_range": (2.33, 2.33)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (0.43, 0.43),
            "U_value_range": (1.67, 1.67)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (0.86, 0.86),
            "U_value_range": (0.97, 0.97)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (2.90, 2.90)
        },
        "doors": {
            "area_m2": 4.57,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1975-1991", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 4.57,
            "U_value_range": (2.00, 2.00)
        }
    },
    ("Corner townhouse", "1975-1991", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 4.57,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner townhouse", "1975-1991", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner townhouse", "1975-1991", "scenario1", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1975-1991", "scenario2", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1975-1991", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1975-1991", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1975-1991", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner townhouse", "1975-1991", "scenario1", "pre_calibration"): {
        "main_heating": "Local heating",
        "system_type": "Individual",
        "heating_appliance": "Local heating",
        "boiler_air_heating": "With exhaust",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1975-1991", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1975-1991", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1975-1991", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1975-1991", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner townhouse", "1975-1991", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1975-1991", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1975-1991", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1975-1991", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1975-1991", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner townhouse", "1975-1991", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 144.97
    },
    ("Corner townhouse", "1975-1991", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 132.32
    },
    ("Corner townhouse", "1975-1991", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 65.02
    },
    ("Corner townhouse", "1975-1991", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 65.02
    },
    ("Corner townhouse", "1975-1991", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 48.71
    }
}



# 1992 - 2005


1. Characteristic Data

characteristic_data = {
    ("Corner townhouse", "1992-2005", "pre_calibration"): {
        "usable_floor_area_m2": 128.79,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Corner townhouse with gable roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner townhouse", "1992-2005", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (0.52, 0.52),
            "U_value_range": (2.33, 2.33)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (0.43, 0.43),
            "U_value_range": (1.67, 1.67)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (0.86, 0.86),
            "U_value_range": (0.97, 0.97)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (5.10, 5.10)
        },
        "doors": {
            "area_m2": 7.00,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1992-2005", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (0.52, 0.52),
            "U_value_range": (2.33, 2.33)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (0.43, 0.43),
            "U_value_range": (1.67, 1.67)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (0.86, 0.86),
            "U_value_range": (0.97, 0.97)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (2.90, 2.90)
        },
        "doors": {
            "area_m2": 7.00,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "1992-2005", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (2.00, 2.00)
        }
    },
    ("Corner townhouse", "1992-2005", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner townhouse", "1992-2005", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 50.00,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 87.40,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 56.53,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.60,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 9.35,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner townhouse", "1992-2005", "scenario1", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1992-2005", "scenario2", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "1992-2005", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1992-2005", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "1992-2005", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner townhouse", "1992-2005", "scenario1", "pre_calibration"): {
        "main_heating": "Local heating",
        "system_type": "Individual",
        "heating_appliance": "Local heating",
        "boiler_air_heating": "With exhaust",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1992-2005", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "1992-2005", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1992-2005", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "1992-2005", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner townhouse", "1992-2005", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1992-2005", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1992-2005", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1992-2005", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "1992-2005", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner townhouse", "1992-2005", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 144.97
    },
    ("Corner townhouse", "1992-2005", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 132.32
    },
    ("Corner townhouse", "1992-2005", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 65.02
    },
    ("Corner townhouse", "1992-2005", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 65.02
    },
    ("Corner townhouse", "1992-2005", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.82,
        "standard_value_kWh_m2": 75.78,
        "heat_demand_Q_H_nd_kWh_m2": 48.71
    }
}




# 2006 - 2014

1. Characteristic Data

characteristic_data = {
    ("Corner townhouse", "2006-2014", "pre_calibration"): {
        "usable_floor_area_m2": 136.67,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Corner townhouse with gable roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner townhouse", "2006-2014", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 56.80,
            "R_value_range": (2.50, 2.50),
            "U_value_range": (0.36, 0.36)
        },
        "solid_wall": {
            "area_m2": 110.98,
            "R_value_range": (2.50, 2.50),
            "U_value_range": (0.37, 0.37)
        },
        "sloping_flat_roof": {
            "area_m2": 69.60,
            "R_value_range": (2.50, 2.50),
            "U_value_range": (0.37, 0.37)
        },
        "windows": {
            "area_m2": 26.93,
            "U_value_range": (1.80, 1.80)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "2006-2014", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 56.80,
            "R_value_range": (2.50, 2.50),
            "U_value_range": (0.36, 0.36)
        },
        "solid_wall": {
            "area_m2": 110.98,
            "R_value_range": (2.50, 2.50),
            "U_value_range": (0.37, 0.37)
        },
        "sloping_flat_roof": {
            "area_m2": 69.60,
            "R_value_range": (2.50, 2.50),
            "U_value_range": (0.37, 0.37)
        },
        "windows": {
            "area_m2": 26.93,
            "U_value_range": (1.80, 1.80)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner townhouse", "2006-2014", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 56.80,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 110.98,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 69.60,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.93,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (2.00, 2.00)
        }
    },
    ("Corner townhouse", "2006-2014", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 56.80,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 110.98,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 69.60,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.93,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner townhouse", "2006-2014", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 56.80,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 110.98,
            "R_value_range": (1.70, 1.70),
            "U_value_range": (0.53, 0.53)
        },
        "sloping_flat_roof": {
            "area_m2": 69.60,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "windows": {
            "area_m2": 26.93,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner townhouse", "2006-2014", "scenario1", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "2006-2014", "scenario2", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner townhouse", "2006-2014", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "2006-2014", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner townhouse", "2006-2014", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner townhouse", "2006-2014", "scenario1", "pre_calibration"): {
        "main_heating": "Boiler HR100-boiler",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR100-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "2006-2014", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner townhouse", "2006-2014", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "2006-2014", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner townhouse", "2006-2014", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner townhouse", "2006-2014", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "2006-2014", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "2006-2014", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "2006-2014", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner townhouse", "2006-2014", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner townhouse", "2006-2014", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 91.77
    },
    ("Corner townhouse", "2006-2014", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 91.77
    },
    ("Corner townhouse", "2006-2014", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 61.54
    },
    ("Corner townhouse", "2006-2014", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 61.54
    },
    ("Corner townhouse", "2006-2014", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 45.75
    }
}


# 2015-2018

1. Characteristic Data

characteristic_data = {
    ("Corner row house", "2015-2018", "pre_calibration"): {
        "usable_floor_area_m2": 119.70,
        "number_of_floors_within_dwelling": 3,
        "number_of_floors_entire_building": 3,
        "number_of_units_entire_building": 1,
        "building_type": "Corner row house with gable roof",
        "type_of_unit_variant": "Corner",
        "building_height_m": 9.00,
        "ground_floor_boundary": "Crawl space"
    }
}

2. Building Envelope Data

building_envelop_data = {
    ("Corner row house", "2015-2018", "scenario1", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 55.70,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 95.20,
            "R_value_range": (4.50, 4.50),
            "U_value_range": (0.21, 0.21)
        },
        "sloping_flat_roof": {
            "area_m2": 61.60,
            "R_value_range": (6.00, 6.00),
            "U_value_range": (0.16, 0.16)
        },
        "windows": {
            "area_m2": 19.22,
            "U_value_range": (1.80, 1.80)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner row house", "2015-2018", "scenario2", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 55.70,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 95.20,
            "R_value_range": (4.50, 4.50),
            "U_value_range": (0.21, 0.21)
        },
        "sloping_flat_roof": {
            "area_m2": 61.60,
            "R_value_range": (6.00, 6.00),
            "U_value_range": (0.16, 0.16)
        },
        "windows": {
            "area_m2": 19.22,
            "U_value_range": (1.80, 1.80)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (3.40, 3.40)
        }
    },
    ("Corner row house", "2015-2018", "scenario3", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 55.70,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 95.20,
            "R_value_range": (4.50, 4.50),
            "U_value_range": (0.21, 0.21)
        },
        "sloping_flat_roof": {
            "area_m2": 61.60,
            "R_value_range": (6.00, 6.00),
            "U_value_range": (0.16, 0.16)
        },
        "windows": {
            "area_m2": 19.22,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (2.00, 2.00)
        }
    },
    ("Corner row house", "2015-2018", "scenario4", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 55.70,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 95.20,
            "R_value_range": (4.50, 4.50),
            "U_value_range": (0.21, 0.21)
        },
        "sloping_flat_roof": {
            "area_m2": 61.60,
            "R_value_range": (6.00, 6.00),
            "U_value_range": (0.16, 0.16)
        },
        "windows": {
            "area_m2": 19.22,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (1.40, 1.40)
        }
    },
    ("Corner row house", "2015-2018", "scenario5", "pre_calibration"): {
        "ground_floor": {
            "area_m2": 55.70,
            "R_value_range": (3.50, 3.50),
            "U_value_range": (0.27, 0.27)
        },
        "solid_wall": {
            "area_m2": 95.20,
            "R_value_range": (4.50, 4.50),
            "U_value_range": (0.21, 0.21)
        },
        "sloping_flat_roof": {
            "area_m2": 61.60,
            "R_value_range": (6.00, 6.00),
            "U_value_range": (0.16, 0.16)
        },
        "windows": {
            "area_m2": 19.22,
            "U_value_range": (1.40, 1.40)
        },
        "doors": {
            "area_m2": 5.08,
            "U_value_range": (1.40, 1.40)
        }
    }
}

3. Ventilation Data

ventilation_data = {
    ("Corner row house", "2015-2018", "scenario1", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner row house", "2015-2018", "scenario2", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C1 standard",
        "heat_recovery": "None",
        "air_tightness_qv10": "\"Forfaitair\" (default)"
    },
    ("Corner row house", "2015-2018", "scenario3", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner row house", "2015-2018", "scenario4", "pre_calibration"): {
        "ventilation_system": "Natural supply, mechanical exhaust",
        "ventilation_provision": "C5a (pressure supply, CO₂ exhaust, zoning)",
        "heat_recovery": "None",
        "air_tightness_qv10": "0.7 dm³/s·m²"
    },
    ("Corner row house", "2015-2018", "scenario5", "pre_calibration"): {
        "ventilation_system": "Fully mechanical (balanced)",
        "ventilation_provision": "Central heat recovery (WTW), CO₂ multi-zone",
        "heat_recovery": "With heat recovery",
        "air_tightness_qv10": "0.4 dm³/s·m²"
    }
}

4. Space Heating Data

space_heating_data = {
    ("Corner row house", "2015-2018", "scenario1", "pre_calibration"): {
        "main_heating": "Boiler HR100-boiler",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR100-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner row house", "2015-2018", "scenario2", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "90/70 °C"
    },
    ("Corner row house", "2015-2018", "scenario3", "pre_calibration"): {
        "main_heating": "Boiler HR107",
        "system_type": "Individual",
        "heating_appliance": "Boiler",
        "boiler_air_heating": "HR107-boiler",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner row house", "2015-2018", "scenario4", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    },
    ("Corner row house", "2015-2018", "scenario5", "pre_calibration"): {
        "main_heating": "Electric heat pump",
        "system_type": "Individual",
        "heating_appliance": "Electric heat pump",
        "boiler_air_heating": "(Not applicable)",
        "emission_system": "Radiators",
        "temperature_regime": "55/47 °C"
    }
}

5. Domestic Hot Water Data

domestic_hot_water_data = {
    ("Corner row house", "2015-2018", "scenario1", "pre_calibration"): {
        "dhw_system": "Individual gas kitchen geyser",
        "installation_type": "Individual",
        "specific_appliance": "Gas kitchen geyser",
        "cw_class_hot_water_comfort": "CW1",
        "shower_heat_recovery_present": "No"
    },
    ("Corner row house", "2015-2018", "scenario2", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner row house", "2015-2018", "scenario3", "pre_calibration"): {
        "dhw_system": "Individual gas combi boiler with gas label HR/CW",
        "installation_type": "Individual",
        "specific_appliance": "Gas combi boiler (gaskeur HR/CW)",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner row house", "2015-2018", "scenario4", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    },
    ("Corner row house", "2015-2018", "scenario5", "pre_calibration"): {
        "dhw_system": "Individual combi heat pump",
        "installation_type": "Individual",
        "specific_appliance": "Combi heat pump",
        "cw_class_hot_water_comfort": "CW4/5/6",
        "shower_heat_recovery_present": "No"
    }
}

6. Standard Dwelling Insulation Data

standard_dwelling_insulation_data = {
    ("Corner row house", "2015-2018", "scenario1", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 91.77
    },
    ("Corner row house", "2015-2018", "scenario2", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 91.77
    },
    ("Corner row house", "2015-2018", "scenario3", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 61.54
    },
    ("Corner row house", "2015-2018", "scenario4", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 61.54
    },
    ("Corner row house", "2015-2018", "scenario5", "pre_calibration"): {
        "form_factor_A_loss_A_use_m2_per_m2": 1.85,
        "standard_value_kWh_m2": 76.86,
        "heat_demand_Q_H_nd_kWh_m2": 45.75
    }
}
















