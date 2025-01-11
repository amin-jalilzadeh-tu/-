# fenez/data_materials_residential.py

residential_materials_data = {
    # Example: Two-and-a-half-story House, <1965, scenario1, pre_calibration
    ("Two-and-a-half-story House", "<1965", "scenario1", "pre_calibration"): {
        "roughness": "MediumRough",
        "wwr_range": (0.2, 0.3),

        # older style top-level references
        "material_opaque_lookup": "Concrete_200mm",
        "material_window_lookup": "Glazing_Clear_3mm_Post",

        # new sub-elements
        "ground_floor": {
            "area_m2": 68.95,
            "R_value_range": (2.5, 2.5),
            "U_value_range": (0.36, 0.36),
            "material_opaque_lookup": "InsulationBoard_R2"
        },
        "solid_wall": {
            "area_m2": 103.3,
            "R_value_range": (2.5, 2.5),
            "U_value_range": (0.37, 0.37),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "sloping_flat_roof": {
            "area_m2": 84.14,
            "R_value_range": (2.5, 2.5),
            "U_value_range": (0.37, 0.37),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "windows": {
            "area_m2": 27.22,
            "U_value_range": (2.9, 2.9),
            "material_window_lookup": "Glazing_Clear_3mm"
        },
        "doors": {
            "area_m2": 6.93,
            "U_value_range": (3.4, 3.4),
            "material_opaque_lookup": "DoorPanel_Range"
        }
    },

    # Another example for scenario2 or different age range
    ("Two-and-a-half-story House", "<1965", "scenario1", "post_calibration"): {
        "roughness": "Smooth",
        "wwr_range": (0.25, 0.25),

        "material_opaque_lookup": "Concrete_200mm",
        "material_window_lookup": "Glazing_Clear_3mm_Post",

        "ground_floor": {
            "area_m2": 70.0,
            "R_value_range": (3.0, 3.0),
            "U_value_range": (0.33, 0.33),
            "material_opaque_lookup": "InsulationBoard_R2"
        },
        "solid_wall": {
            "area_m2": 105.0,
            "R_value_range": (3.0, 3.0),
            "U_value_range": (0.33, 0.33),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "sloping_flat_roof": {
            "area_m2": 82.0,
            "R_value_range": (3.0, 3.0),
            "U_value_range": (0.33, 0.33),
            "material_opaque_lookup": "Concrete_200mm"
        },
        "windows": {
            "area_m2": 25.0,
            "U_value_range": (2.7, 3.0),
            "material_window_lookup": "Glazing_Clear_3mm"
        },
        "doors": {
            "area_m2": 7.0,
            "U_value_range": (3.2, 3.4),
            "material_opaque_lookup": "DoorPanel_Range"
        }
    },

    # more combos...
}
