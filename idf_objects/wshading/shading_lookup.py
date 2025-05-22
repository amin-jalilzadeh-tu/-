"""
shading_lookup.py

Contains default (hardcoded) shading parameters for different blind types,
overhangs, louvers, etc. This is analogous to geometry_lookup.py or
materials_lookup.py, storing dictionary-based defaults.

Each key in the `shading_lookup` dictionary represents a specific type of shading.
The associated value is a dictionary of its parameters. Parameters intended
to be a range (min, max) from which a value will be picked should have a
key ending with "_range".

Example:
  "slat_width_range": (0.025, 0.050)  # Slat width can be between 0.025m and 0.050m

Values for these ranges will be selected by the `pick_val_from_range` function
in `assign_shading_values.py` based on the chosen strategy (e.g., midpoint, random).
"""

shading_lookup = {
    # Example: external horizontal louvers/blinds
    "my_external_louvers": {
        # This name will be used as a base for the EnergyPlus WindowMaterial:Blind object name
        "blind_name": "MyExternalLouvers",
        "slat_orientation": "Horizontal", # Or "Vertical"
        "slat_width_range": (0.025, 0.025), # Slat width in meters
        "slat_separation_range": (0.020, 0.020), # Slat separation (distance between front of one slat and next) in meters
        "slat_thickness_range": (0.001, 0.001), # Slat thickness in meters
        "slat_angle_deg_range": (45.0, 45.0), # Slat angle in degrees (0=horizontal, 90=vertical profile)
        "slat_conductivity_range": (160.0, 160.0), # Slat conductivity in W/m-K (e.g., for aluminum)

        # Solar trans/reflect properties (beam & diffuse):
        # These are for the slat material itself.
        "slat_beam_solar_transmittance_range": (0.0, 0.0), # Fraction of beam solar radiation transmitted directly through slat
        "slat_beam_solar_reflectance_range": (0.7, 0.7), # Fraction of beam solar radiation reflected by front/back of slat (assumed same for front/back here)
        "slat_diffuse_solar_transmittance_range": (0.0, 0.0),# Fraction of diffuse solar radiation transmitted directly through slat
        "slat_diffuse_solar_reflectance_range": (0.7, 0.7), # Fraction of diffuse solar radiation reflected by front/back of slat (assumed same for front/back here)

        # Visible trans/reflect properties (beam & diffuse):
        "slat_beam_visible_transmittance_range": (0.0, 0.0),
        "slat_beam_visible_reflectance_range": (0.7, 0.7), # Assumed same for front/back here
        "slat_diffuse_visible_transmittance_range": (0.0, 0.0),
        "slat_diffuse_visible_reflectance_range": (0.7, 0.7), # Assumed same for front/back here

        # IR / emissivity properties
        "slat_ir_transmittance_range": (0.0, 0.0), # Infrared transmittance of slat material
        "slat_ir_emissivity_range": (0.9, 0.9), # Infrared emissivity of slat material (assumed same for front/back here)

        # Blind geometry offsets and details
        "blind_to_glass_distance_range": (0.05, 0.05), # Distance from glazing to blind in meters (positive for exterior, negative for interior)
        
        # Slat_Opening_Multiplier for WindowMaterial:Blind (EnergyPlus has only one such field)
        # This replaces the previous four (top, bottom, left, right) multipliers for this specific blind type
        # to better align with the E+ WindowMaterial:Blind object.
        # The value 0.5 is chosen as it appeared in your sample IDF output. Adjust if another default is preferred.
        "slat_opening_multiplier_range": (0.5, 0.5), # Multiplier for air flow opening (0.0 = no opening, 0.5 = half open, 1.0 = fully open based on slat separation)

        # Slat angle limits (if dynamic control is used, not directly used by fixed angle in WindowMaterial:Blind)
        "slat_angle_min_deg_range": (0.0, 0.0), # Minimum slat angle in degrees
        "slat_angle_max_deg_range": (90.0, 90.0), # Maximum slat angle in degrees (some systems might go to 180)

        # For Shading:Building:Detailed type objects (if this key were for an overhang/fin)
        # These are examples and would typically be in a different lookup entry specific to those shading types.
        # "overhang_depth_range": (0.5, 1.0), 
        # "fin_depth_range": (0.3, 0.6),      
    },

    # Example: interior roller blind (dark)
    "my_interior_roller_blind_dark": {
        "blind_name": "InteriorRollerDark",
        "slat_orientation": "Horizontal", # Roller blinds are effectively horizontal slats of fabric
        # For a roller blind, "slat width" and "slat separation" are less about individual slats 
        # and more about the fabric properties when deployed. 
        # The E+ WindowMaterial:Blind model still uses these terms.
        # A "fully closed" roller blind effectively has slat width = separation if modeled as slats.
        # Thickness is the fabric thickness. Angle is 0 when flat.
        "slat_width_range": (0.05, 0.05), # Effective width; can be small if considering it as a continuous sheet.
        "slat_separation_range": (0.05, 0.05), # Effective separation
        "slat_thickness_range": (0.0005, 0.0005), # Fabric thickness
        "slat_angle_deg_range": (0.0, 0.0), # Always flat when down for a roller blind
        "slat_conductivity_range": (0.1, 0.1), # Fabric conductivity

        "slat_beam_solar_transmittance_range": (0.05, 0.05),
        "slat_beam_solar_reflectance_range": (0.1, 0.1),
        "slat_diffuse_solar_transmittance_range": (0.05, 0.05),
        "slat_diffuse_solar_reflectance_range": (0.1, 0.1),

        "slat_beam_visible_transmittance_range": (0.03, 0.03),
        "slat_beam_visible_reflectance_range": (0.05, 0.05),
        "slat_diffuse_visible_transmittance_range": (0.03, 0.03),
        "slat_diffuse_visible_reflectance_range": (0.05, 0.05),

        "slat_ir_transmittance_range": (0.0, 0.0),
        "slat_ir_emissivity_range": (0.85, 0.85),

        "blind_to_glass_distance_range": (-0.03, -0.03), # Negative for interior
        "slat_opening_multiplier_range": (0.0, 0.0), # Typically 0 for a closed roller blind (no gaps)
    },

    # Add more predefined shading “types” here as needed, for example:
    # "my_vertical_fins": {
    #     "shading_element_name": "VerticalFinSystem", # Generic name for the element
    #     "fin_depth_range": (0.3, 0.5),          # Depth of fins in meters
    #     "fin_spacing_range": (0.5, 0.7),        # Spacing between fins in meters
    #     "fin_height_or_length": "WindowHeight", # Placeholder, could be numeric or a keyword
    #     "fin_offset_from_window_edge_range": (0.0, 0.1) # Offset from the side of the window
    #     # ... other relevant geometric or material properties
    #     # Note: Geometric shading like fins/overhangs are typically Shading:Building:Detailed
    #     # or Shading:Zone:Detailed and don't use WindowMaterial:Blind parameters.
    # },
    # "my_fixed_overhang": {
    #     "shading_element_name": "FixedBuildingOverhang",
    #     "overhang_depth_range": (0.5, 1.2),       # Projection depth in meters
    #     "overhang_width_or_length": "WindowWidthPlusExtensions", # Placeholder
    #     "overhang_height_above_window_top_range": (0.0, 0.2) # Height above window top
    #     # ... other relevant geometric or material properties
    # },
}