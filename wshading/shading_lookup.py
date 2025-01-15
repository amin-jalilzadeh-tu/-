# wshading/shading_lookup.py

"""
Contains default (hardcoded) shading parameters for different blind types, 
overhangs, louvers, etc. This is analogous to geometry_lookup.py or 
materials_lookup.py, storing dictionary-based defaults.
 
You can store various fields such as slat width, slat angle ranges, 
reflectances, etc. for each shading 'key' (e.g., "my_external_louvers").
"""

shading_lookup = {
    # Example key => "my_external_louvers"
    # You can store default values or ranges for slat angles, widths, reflectances, etc.
    "my_external_louvers": {
        # This name will appear in EnergyPlus as the Blind material name
        "blind_name": "MyExternalLouvers",
        "slat_orientation": "Horizontal",
        "slat_width_range": (0.025, 0.025),
        "slat_separation_range": (0.02, 0.02),
        "slat_thickness_range": (0.001, 0.001),
        "slat_angle_deg_range": (45.0, 45.0),   # If you want a fixed 45°, keep min=max
        "slat_conductivity_range": (160.0, 160.0),
        
        # Solar trans/reflect properties (beam & diffuse):
        "slat_beam_solar_transmittance_range": (0.0, 0.0),
        "slat_beam_solar_reflectance_range": (0.2, 0.2),  # front/back same in this example
        "slat_diffuse_solar_transmittance_range": (0.0, 0.0),
        "slat_diffuse_solar_reflectance_range": (0.2, 0.2),
        
        # Visible trans/reflect properties (beam & diffuse):
        "slat_beam_visible_transmittance_range": (0.0, 0.0),
        "slat_beam_visible_reflectance_range": (0.5, 0.5),
        "slat_diffuse_visible_transmittance_range": (0.0, 0.0),
        "slat_diffuse_visible_reflectance_range": (0.5, 0.5),
        
        # IR / emissivity
        "slat_ir_transmittance_range": (0.0, 0.0),
        "slat_ir_emissivity_range": (0.9, 0.9),  # front/back same in this example
        
        # Blind geometry offsets
        "blind_to_glass_distance_range": (0.05, 0.05),
        "blind_opening_multiplier_top": (1.0, 1.0),
        "blind_opening_multiplier_bottom": (1.0, 1.0),
        "blind_opening_multiplier_left": (1.0, 1.0),
        "blind_opening_multiplier_right": (1.0, 1.0),
        
        # Slat angle limits
        "slat_angle_min_range": (0.0, 0.0),
        "slat_angle_max_range": (90.0, 90.0),
    },

    # Add more shading “types” here if needed, e.g.:
    # "my_vertical_fins": {...},
    # "my_overhang": {...},
}
