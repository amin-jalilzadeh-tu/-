# fenez/materials_lookup.py

"""
materials_lookup.py

Defines a dictionary 'material_lookup' where each key is a label like
"Concrete_200mm" or "Glazing_Clear_3mm". Each value is a dict containing:
  - obj_type (e.g. "MATERIAL", "MATERIAL:NOMASS", "WINDOWMATERIAL:GLAZING", etc.)
  - Name (the actual name in the IDF)
  - Roughness
  - Range-based fields like "Thickness_range", "Conductivity_range", etc.
  - Possibly optical properties for glazing, etc.
"""

material_lookup = {
    "N/A": {
        "obj_type": "MATERIAL",
        "Name": "Not_Applicable",
        "Description": "Placeholder for assemblies that have no relevant opaque or window material."
    },

    # -------------------------------------------------------------------
    #  OPAQUE MATERIALS
    # -------------------------------------------------------------------
    "Concrete_200mm": {
        "obj_type": "MATERIAL",
        "Name": "Concrete_200mm",
        "Roughness": "MediumRough",
        "Thickness_range": (0.195, 0.205),
        "Conductivity_range": (1.5, 1.7),
        "Density_range": (2250, 2350),
        "Specific_Heat_range": (850, 950),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "GroundContactFloor_Generic": {
        "obj_type": "MATERIAL",
        "Name": "GroundContactFloor_Generic",
        "Roughness": "MediumRough",
        "Thickness_range": (0.10, 0.12),
        "Conductivity_range": (1.0, 1.2),
        "Density_range": (2100, 2300),
        "Specific_Heat_range": (850, 900),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "InternalFloor_Generic": {
        "obj_type": "MATERIAL",
        "Name": "InternalFloor_Generic",
        "Roughness": "MediumSmooth",
        "Thickness_range": (0.12, 0.15),
        "Conductivity_range": (0.7, 1.2),
        "Density_range": (1800, 2000),
        "Specific_Heat_range": (800, 900),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "Insulated_Roof_R5": {
        "obj_type": "MATERIAL:NOMASS",
        "Name": "Insulated_Roof_R5",
        "Roughness": "MediumRough",
        # If your R-value range is 4–5, we model it as Thermal_Resistance_range
        "Thermal_Resistance_range": (4.0, 5.0),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "InteriorWall_Generic": {
        "obj_type": "MATERIAL",
        "Name": "InteriorWall_Generic",
        "Roughness": "MediumSmooth",
        "Thickness_range": (0.10, 0.15),
        "Conductivity_range": (0.4, 0.6),
        "Density_range": (700, 900),
        "Specific_Heat_range": (800, 1000),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "DoorPanel_Range": {
        "obj_type": "MATERIAL",
        "Name": "DoorPanel_Range",
        "Roughness": "MediumRough",
        "Thickness_range": (0.14, 0.25),
        "Conductivity_range": (1.4, 1.7),
        "Density_range": (600, 700),
        "Specific_Heat_range": (2200, 2400),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    # -------------------------------------------------------------------
    #  WINDOWS / GLAZING
    # -------------------------------------------------------------------
    "Glazing_Clear_3mm": {
        "obj_type": "WINDOWMATERIAL:GLAZING",
        "Name": "Glazing_Clear_3mm",
        "Optical_Data_Type": "SpectralAverage",
        "Thickness_range": (0.003, 0.003),
        "Solar_Transmittance_range": (0.76, 0.78),
        "Front_Solar_Reflectance_range": (0.07, 0.08),
        "Back_Solar_Reflectance_range": (0.07, 0.08),
        "Visible_Transmittance_range": (0.86, 0.88),
        "Front_Visible_Reflectance_range": (0.06, 0.07),
        "Back_Visible_Reflectance_range": (0.06, 0.07),
        "IR_Transmittance": 0.0,
        "Front_IR_Emissivity_range": (0.84, 0.84),
        "Back_IR_Emissivity_range": (0.84, 0.84),
        "Conductivity_range": (0.95, 1.05),
        "Dirt_Correction_Factor_range": (1.0, 1.0),
        "Solar_Diffusing": "No"
    },

    "Glazing_Clear_3mm_Post": {
        "obj_type": "WINDOWMATERIAL:GLAZING",
        "Name": "Glazing_Clear_3mm_Post",
        "Optical_Data_Type": "SpectralAverage",
        "Thickness_range": (0.003, 0.003),
        "Solar_Transmittance_range": (0.75, 0.75),
        "Front_Solar_Reflectance_range": (0.07, 0.07),
        "Back_Solar_Reflectance_range": (0.07, 0.07),
        "Visible_Transmittance_range": (0.85, 0.85),
        "Front_Visible_Reflectance_range": (0.07, 0.07),
        "Back_Visible_Reflectance_range": (0.07, 0.07),
        "IR_Transmittance": 0.0,
        "Front_IR_Emissivity_range": (0.84, 0.84),
        "Back_IR_Emissivity_range": (0.84, 0.84),
        "Conductivity_range": (1.0, 1.0),
        "Dirt_Correction_Factor_range": (1.0, 1.0),
        "Solar_Diffusing": "No"
    },

    # -------------------------------------------------------------------
    #  OPTIONAL / LEGACY ENTRIES
    # -------------------------------------------------------------------
    "DoorPanel_Range2": {
        "obj_type": "MATERIAL",
        "Name": "DoorPanel_Range2",
        "Roughness": "MediumSmooth",
        "Thickness_range": (0.04, 0.05),
        "Conductivity_range": (0.4, 0.5),
        "Density_range": (600, 700),
        "Specific_Heat_range": (1200, 1300),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "Ceiling_Insulation_R3": {
        "obj_type": "MATERIAL",
        "Name": "Ceiling_Insulation_R3",
        "Roughness": "MediumRough",
        "Thickness_range": (0.02, 0.03),
        "Conductivity_range": (0.035, 0.045),
        "Density_range": (20, 25),
        "Specific_Heat_range": (1400, 1500),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "Roof_Insulation_R5": {
        "obj_type": "MATERIAL",
        "Name": "Roof_Insulation_R5",
        "Roughness": "MediumRough",
        "Thickness_range": (0.04, 0.05),
        "Conductivity_range": (0.03, 0.04),
        "Density_range": (25, 30),
        "Specific_Heat_range": (1400, 1500),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    },

    "AdiabaticWall_Generic": {
        "obj_type": "MATERIAL",
        "Name": "AdiabaticWall_Generic",
        "Roughness": "MediumSmooth",
        "Thickness_range": (0.15, 0.20),
        "Conductivity_range": (0.30, 0.40),
        "Density_range": (200, 300),
        "Specific_Heat_range": (1000, 1100),
        "Thermal_Absorptance_range": (0.9, 0.9),
        "Solar_Absorptance_range": (0.7, 0.7),
        "Visible_Absorptance_range": (0.7, 0.7)
    }
}





""""


('Two-and-a-half-story House', '1946-1964', 'scenario1', 'pre_calibration'): {
    "roughness": "MediumRough",
    "wwr_range": (0.2, 0.25),
    "material_opaque_lookup": "Concrete_200mm",  # fallback for exterior walls
    "material_window_lookup": "Glazing_Clear_3mm",

    # 1) Exterior walls
    "exterior_wall": {
        "area_m2": 70.0,
        "R_value_range": (0.5, 1.0),
        "U_value_range": (1.0, 2.0),
        "material_opaque_lookup": "Concrete_200mm"
    },

    # 2) Ground floor
    "ground_floor": {
        "area_m2": 40.0,
        "R_value_range": (1.0, 1.5),
        "U_value_range": (0.7, 1.0),
        "material_opaque_lookup": "GroundContactFloor_Generic"
    },

    # 3) Intermediate floor (between stories)
    "inter_floor": {
        "area_m2": 40.0,
        "R_value_range": (0.6, 1.0),
        "U_value_range": (1.0, 1.7),
        "material_opaque_lookup": "InternalFloor_Generic"
    },

    # 4) Roof
    "flat_roof": {
        "area_m2": 30.0,
        "R_value_range": (4.0, 5.0),
        "U_value_range": (0.2, 0.25),
        "material_opaque_lookup": "Insulated_Roof_R5"
    },

    # 5) Interior walls
    "interior_wall": {
        "area_m2": 60.0,
        "R_value_range": (0.5, 0.8),
        "U_value_range": (1.25, 2.0),
        "material_opaque_lookup": "InteriorWall_Generic"
    },

    # Doors & windows
    "doors": {
        "area_m2": 4.0,
        "R_value_range": (None, None),
        "U_value_range": (3.4, 3.4),
        "material_opaque_lookup": "DoorPanel_Range"
    },
    "windows": {
        "area_m2": 10.0,
        "R_value_range": (None, None),
        "U_value_range": (1.4, 2.9),
        "material_window_lookup": "Glazing_Clear_3mm"
    }
}


"""	