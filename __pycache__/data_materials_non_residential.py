# fenez/data_materials_non_residential.py

"""
We define a dictionary for non_residential_materials_data
keyed by (non_residential_type, age_range, scenario, calibration_stage).

Each entry can have:
 - older fields like "roughness", "wwr_range"
 - overall references: "material_opaque_lookup", "material_window_lookup"
 - plus per-element sub-dicts for 'ground_floor', 'walls', 'windows', 'doors', etc.
"""

non_residential_materials_data = {
    # Example: Meeting Function, 2015 and later, scenario1, pre_calibration
    ("Meeting Function", "2015 and later", "scenario1", "pre_calibration"): {
        "roughness": "MediumRough",
        "wwr_range": (0.3, 0.35),
        "material_opaque_lookup": "Concrete_200mm",
        "material_window_lookup": "Glazing_Clear_3mm",

        # Also define sub-elements if you want
        "ground_floor": {
            "area_m2": 120.0,
            "R_value_range": (2.5, 3.0),
            "U_value_range": (0.33, 0.4),
            "material_opaque_lookup": "InsulationBoard_R2"
        },
        "exterior_wall": {
            "area_m2": 300.0,
            "R_value_range": (2.0, 2.5),
            "U_value_range": (0.40, 0.50),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "flat_roof": {
            "area_m2": 200.0,
            "R_value_range": (3.0, 3.5),
            "U_value_range": (0.28, 0.33),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "windows": {
            "area_m2": 80.0,
            "U_value_range": (2.2, 2.4),
            "material_window_lookup": "Glazing_Clear_3mm"
        },
        "doors": {
            "area_m2": 10.0,
            "U_value_range": (3.0, 3.2),
            "material_opaque_lookup": "DoorPanel_Range"
        }
    },

    # Another example: Meeting Function, 2015 and later, scenario1, post_calibration
    ("Meeting Function", "2015 and later", "scenario1", "post_calibration"): {
        "roughness": "Smooth",
        "wwr_range": (0.32, 0.32),
        "material_opaque_lookup": "Concrete_200mm",
        "material_window_lookup": "Glazing_Clear_3mm_Post",

        "ground_floor": {
            "area_m2": 120.0,
            "R_value_range": (3.0, 3.0),
            "U_value_range": (0.33, 0.33),
            "material_opaque_lookup": "InsulationBoard_R2"
        },
        "exterior_wall": {
            "area_m2": 300.0,
            "R_value_range": (2.3, 2.3),
            "U_value_range": (0.36, 0.36),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "flat_roof": {
            "area_m2": 200.0,
            "R_value_range": (3.0, 3.0),
            "U_value_range": (0.3, 0.3),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "windows": {
            "area_m2": 80.0,
            "U_value_range": (2.1, 2.1),
            "material_window_lookup": "Glazing_Clear_3mm_Post"
        },
        "doors": {
            "area_m2": 10.0,
            "U_value_range": (3.0, 3.0),
            "material_opaque_lookup": "DoorPanel_Range"
        }
    },

    # add more combos for other non_res types, ages, scenarios, stages
}
