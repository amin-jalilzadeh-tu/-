"""
create_shading_objects.py

This module creates EnergyPlus shading objects in the IDF
(e.g., WindowMaterial:Blind, WindowShadingControl,
 Shading:Building:Detailed, schedules, etc.).

It calls pick_shading_params(...) from assign_shading_values.py
to get final numeric parameter values. You can pass user/Excel overrides
to customize these parameters.

Usage:
  from idf_objects.wshading.create_shading_objects import add_shading_objects

  add_shading_objects(
      idf=idf,
      building_row=some_dict, # Or other context identifier
      shading_type_key="my_external_louvers",
      strategy="A", # Or "B"
      random_seed=42,
      user_config_shading=shading_overrides_for_this_type, # Dict of overrides for this specific shading_type_key
      assigned_shading_log=shading_log_dict,
      create_blinds=True,
      create_geometry_shading=False
  )
"""

import random
import logging
from .assign_shading_values import pick_shading_params

# from geomeppy import IDF # Ensure your IDF object type matches
# from eppy.bunch_subclass import EpBunch # Ensure your IDF object type matches

logger = logging.getLogger(__name__)


def add_shading_objects(
    idf,
    building_row,  # Used for context, e.g., if shading depends on building properties
    shading_type_key="my_external_louvers",
    strategy="A",
    random_seed=42,
    user_config_shading=None,
    assigned_shading_log=None,
    create_blinds=True,
    create_geometry_shading=False,
):
    """
    Creates the necessary shading objects in the IDF: e.g. WindowMaterial:Blind,
    WindowShadingControl, or geometry-based Shading:Building:Detailed.

    1) Loops over fenestration surfaces (if creating blinds per window) or processes
       once for global shading elements.
    2) Calls pick_shading_params(...) to get final numeric values (slat angles, etc.).
    3) Creates EnergyPlus shading devices (e.g., WindowMaterial:Blind + ShadingControl).
    4) Optionally, creates an E+ schedule if dynamic shading is needed (example provided).
    5) Optionally, creates Shading:Building:Detailed geometry if requested.

    Parameters
    ----------
    idf : IDF object
        The IDF object (e.g., from geomeppy or eppy) where new objects will be added.
    building_row : dict or pandas.Series or object
        Contextual data for the building/element being processed. Can be used to
        derive window IDs or influence shading choices if needed.
    shading_type_key : str
        Key in shading_lookup (from shading_lookup.py) to define the base shading
        parameters, e.g., "my_external_louvers".
    strategy : str
        Strategy for picking values from ranges ("A" for midpoint, "B" for random,
        other for min_val). Passed to pick_shading_params.
    random_seed : int, optional
        Seed for random number generation if strategy="B". Defaults to 42.
    user_config_shading : dict or None
        A dictionary of overrides for the specified `shading_type_key`.
        E.g., {"slat_angle_deg_range": (30, 60), "slat_width": 0.05}.
        These are applied on top of `shading_lookup` defaults.
    assigned_shading_log : dict or None
        If provided, final shading params are stored here. Keys could be window_id
        or another relevant identifier.
    create_blinds : bool
        If True, attempts to create blind-based shading objects (WindowMaterial:Blind
        + WindowShadingControl) for fenestration surfaces.
    create_geometry_shading : bool
        If True, attempts to create Shading:Building:Detailed geometry-based shading
        (e.g., overhangs), using an example function.
    """
    if random_seed is not None:
        random.seed(random_seed)

    if not idf:
        logger.error("IDF object is None. Cannot add shading objects.")
        return

    # --- Create Blind Shading for Fenestration Surfaces ---
    if create_blinds:
        try:
            fen_surfaces = idf.idfobjects.get("FENESTRATIONSURFACE:DETAILED", [])
            if not fen_surfaces:
                logger.info(
                    "No 'FENESTRATIONSURFACE:DETAILED' objects found in IDF. Skipping blind creation."
                )
        except Exception as e:
            logger.error(
                f"Could not retrieve FENESTRATIONSURFACE:DETAILED from IDF: {e}"
            )
            fen_surfaces = []

        for fen_idx, fen in enumerate(fen_surfaces):
            try:
                window_id = getattr(fen, "Name", f"FenestrationSurface_{fen_idx}")
                if not window_id:  # Fallback if Name is empty
                    window_id = f"FenestrationSurface_{fen_idx}"
                logger.info(
                    f"Processing blinds for window: {window_id} using shading_type_key: '{shading_type_key}'"
                )

                # 1) Pick shading params (combines shading_lookup + user overrides)
                shading_params = pick_shading_params(
                    window_id=window_id,  # Used for logging within pick_shading_params
                    shading_type_key=shading_type_key,
                    strategy=strategy,
                    user_config=user_config_shading,  # Pass the specific overrides for this type
                    assigned_shading_log=assigned_shading_log,
                )

                if not shading_params:
                    logger.warning(
                        f"No shading parameters resolved for window '{window_id}' with key '{shading_type_key}'. Skipping blind creation for this window."
                    )
                    continue

                # 2) Create a WindowMaterial:Blind object
                blind_mat_name = (
                    shading_params.get("blind_name", "DefaultBlindMaterial")
                    + f"_{window_id}"
                )

                # Check if blind material already exists to prevent duplicates
                existing_blind_mats = [
                    bm.Name for bm in idf.idfobjects.get("WINDOWMATERIAL:BLIND", [])
                ]
                if blind_mat_name in existing_blind_mats:
                    logger.info(
                        f"WindowMaterial:Blind '{blind_mat_name}' already exists. Reusing."
                    )
                    # Potentially fetch the existing object if needed, or just use its name
                else:
                    blind_mat = idf.newidfobject("WINDOWMATERIAL:BLIND")
                    blind_mat.Name = blind_mat_name

                    # --- Assign common blind material properties with defaults ---
                    blind_mat.Slat_Orientation = shading_params.get(
                        "slat_orientation", "Horizontal"
                    )
                    blind_mat.Slat_Width = shading_params.get(
                        "slat_width", 0.025
                    )  # Default 25mm
                    blind_mat.Slat_Separation = shading_params.get(
                        "slat_separation", 0.020
                    )  # Default 20mm
                    blind_mat.Slat_Thickness = shading_params.get(
                        "slat_thickness", 0.001
                    )  # Default 1mm
                    blind_mat.Slat_Angle = shading_params.get(
                        "slat_angle_deg", 45.0
                    )  # Default 45 degrees
                    blind_mat.Slat_Conductivity = shading_params.get(
                        "slat_conductivity", 160.0
                    )  # Default for Aluminum

                    # --- Optical Properties with defaults (0.0 for transmittance, sensible reflectance/emissivity) ---
                    # Solar Transmittance/Reflectance
                    blind_mat.Slat_Beam_Solar_Transmittance = shading_params.get(
                        "slat_beam_solar_transmittance", 0.0
                    )
                    sbsr = shading_params.get("slat_beam_solar_reflectance", 0.7)
                    blind_mat.Front_Side_Slat_Beam_Solar_Reflectance = sbsr
                    blind_mat.Back_Side_Slat_Beam_Solar_Reflectance = (
                        sbsr  # Assuming symmetric
                    )

                    blind_mat.Slat_Diffuse_Solar_Transmittance = shading_params.get(
                        "slat_diffuse_solar_transmittance", 0.0
                    )
                    sdsr = shading_params.get("slat_diffuse_solar_reflectance", 0.7)
                    blind_mat.Front_Side_Slat_Diffuse_Solar_Reflectance = sdsr
                    blind_mat.Back_Side_Slat_Diffuse_Solar_Reflectance = (
                        sdsr  # Assuming symmetric
                    )

                    # Visible Transmittance/Reflectance
                    blind_mat.Slat_Beam_Visible_Transmittance = shading_params.get(
                        "slat_beam_visible_transmittance", 0.0
                    )
                    sbvr = shading_params.get("slat_beam_visible_reflectance", 0.7)
                    blind_mat.Front_Side_Slat_Beam_Visible_Reflectance = sbvr
                    blind_mat.Back_Side_Slat_Beam_Visible_Reflectance = (
                        sbvr  # Assuming symmetric
                    )

                    blind_mat.Slat_Diffuse_Visible_Transmittance = shading_params.get(
                        "slat_diffuse_visible_transmittance", 0.0
                    )
                    sdvr = shading_params.get("slat_diffuse_visible_reflectance", 0.7)
                    blind_mat.Front_Side_Slat_Diffuse_Visible_Reflectance = sdvr
                    blind_mat.Back_Side_Slat_Diffuse_Visible_Reflectance = (
                        sdvr  # Assuming symmetric
                    )

                    # IR Transmittance/Emissivity
                    blind_mat.Slat_Infrared_Hemispherical_Transmittance = (
                        shading_params.get("slat_ir_transmittance", 0.0)
                    )
                    sir_em = shading_params.get("slat_ir_emissivity", 0.9)
                    blind_mat.Front_Side_Slat_Infrared_Hemispherical_Emissivity = sir_em
                    blind_mat.Back_Side_Slat_Infrared_Hemispherical_Emissivity = (
                        sir_em  # Assuming symmetric
                    )

                    # Other optional fields (EnergyPlus often defaults these if left blank)
                    # Check E+ I/O reference for which fields are truly optional vs. required.
                    if "blind_to_glass_distance" in shading_params:
                        blind_mat.Distance_between_Slat_and_Glazing = (
                            shading_params.get("blind_to_glass_distance")
                        )
                    if "blind_top_opening_multiplier" in shading_params:
                        blind_mat.Slat_Opening_Multiplier = shading_params.get(
                            "blind_top_opening_multiplier"
                        )  # Note: E+ has one Slat_Opening_Multiplier
                        # if distinct top/bottom/left/right are needed, model might be more complex.
                        # Using top as a proxy here.

                    logger.debug(f"Created WindowMaterial:Blind '{blind_mat.Name}'.")

                # 3) Create WindowShadingControl object
                shading_ctrl_name = f"ShadingCtrl_{window_id}"

                # Check if shading control already exists
                existing_ctrls = [
                    sc.Name for sc in idf.idfobjects.get("WINDOWSHADINGCONTROL", [])
                ]
                if shading_ctrl_name in existing_ctrls:
                    logger.info(
                        f"WindowShadingControl '{shading_ctrl_name}' already exists. Reusing."
                    )
                    shading_ctrl_obj_to_assign = shading_ctrl_name  # Use the name
                else:
                    shading_ctrl = idf.newidfobject("WINDOWSHADINGCONTROL")
                    shading_ctrl.Name = shading_ctrl_name
                    shading_ctrl.Shading_Type = (
                        "ExteriorBlind"  # Or "InteriorBlind", "ExteriorScreen" etc.
                    )
                    # This should ideally come from shading_params or shading_type_key logic
                    shading_ctrl.Shading_Device_Material_Name = (
                        blind_mat_name  # Use the potentially unique name
                    )

                    # Defaulting to FixedSlatAngle. More complex control types would need schedule names etc.
                    shading_ctrl.Type_of_Slats_Control_for_Blinds = (
                        "FixedSlatAngle"  # E.g., FixedSlatAngle, ScheduledSlatAngle
                    )
                    # Slat_Angle_Schedule_Name would be needed for ScheduledSlatAngle

                    # Use the same slat angle as in the blind material for fixed control
                    shading_ctrl.Slat_Angle_Control_for_Fixed_Slat_Angle = (
                        shading_params.get("slat_angle_deg", 45.0)
                    )

                    shading_ctrl.Shading_Control_Is_Scheduled = (
                        "No"  # Set to "Yes" if using a schedule
                    )
                    # Shading_Control_Schedule_Name would be needed if "Yes"

                    shading_ctrl.Glare_Control_Is_Active = (
                        "No"  # Defaulting, can be "Yes"
                    )
                    # Other fields like Setpoint, ShadingControlSetpointScheduleName etc. for advanced control

                    logger.debug(f"Created WindowShadingControl '{shading_ctrl.Name}'.")
                    shading_ctrl_obj_to_assign = shading_ctrl.Name

                # Link the shading control to this fenestration surface
                # Ensure the fen object allows direct attribute assignment for Shading_Control_Name
                try:
                    fen.Shading_Control_Name = shading_ctrl_obj_to_assign
                except Exception as e_assign:
                    logger.error(
                        f"Failed to assign Shading_Control_Name to {window_id}: {e_assign}"
                    )

            except Exception as e_fen:
                logger.error(
                    f"Error processing blind for fenestration surface {getattr(fen, 'Name', 'UnnamedFen')}: {e_fen}"
                )
                continue  # Move to the next fenestration surface

    # --- Create Geometry-Based Shading (e.g., Overhangs, Fins) ---
    if create_geometry_shading:
        logger.info(
            f"Attempting to create geometry-based shading using shading_type_key: '{shading_type_key}'"
        )
        # This typically would not loop per window unless geometry is window-specific.
        # The _create_overhang_example is a global example.
        # You might need a list of building elements or a different context for these.
        _create_overhang_example(
            idf,
            building_row,  # Pass context
            shading_type_key=shading_type_key,  # Use the main key, or a specific one for geometry
            strategy=strategy,
            user_config_shading=user_config_shading,  # Pass overrides if applicable to geometry
        )


def _create_overhang_example(
    idf, building_row_context, shading_type_key, strategy, user_config_shading
):
    """
    Example function to demonstrate geometry-based shading (Shading:Building:Detailed).
    In real usage, you’d compute or retrieve the overhang geometry from
    building_row_context, other geometric inputs, or detailed shading_params.
    This is a placeholder and creates a fixed, illustrative overhang.

    Parameters
    ----------
    idf : IDF object
    building_row_context : dict or object
        Contextual data (e.g., building dimensions, orientation) that could inform geometry.
    shading_type_key : str
        Key to look up base parameters, potentially for overhang depth, etc.
    strategy : str
        Strategy for picking values from ranges.
    user_config_shading : dict or None
        Overrides for parameters relevant to this geometric shading.
    """
    logger.info("Executing _create_overhang_example.")
    # Suppose we pick some shading params that define the overhang depth
    # For geometry, the 'window_id' for pick_shading_params might be a generic name
    # if the overhang is not tied to a specific window but rather a facade or building.
    shading_params = pick_shading_params(
        window_id="Global_Overhang_Example",  # Generic ID for logging these params
        shading_type_key=shading_type_key,  # Could be a specific key like "my_building_overhang"
        strategy=strategy,
        user_config=user_config_shading,  # Pass relevant part of user_config
    )

    if not shading_params:
        logger.warning(
            f"No parameters resolved for overhang example with key '{shading_type_key}'. Skipping overhang creation."
        )
        return

    # Let's say we expect an "overhang_depth" from shading_params
    # or use a default if not found.
    overhang_depth = shading_params.get("overhang_depth", 1.0)  # Default 1m depth
    overhang_name = shading_params.get("overhang_name", "Overhang_North_Example")

    # Check if this shading object already exists
    existing_shading_geom = [
        sg.Name for sg in idf.idfobjects.get("SHADING:BUILDING:DETAILED", [])
    ]
    if overhang_name in existing_shading_geom:
        logger.info(
            f"Shading:Building:Detailed '{overhang_name}' already exists. Skipping creation."
        )
        return

    try:
        shading_obj = idf.newidfobject("SHADING:BUILDING:DETAILED")
        shading_obj.Name = overhang_name
        # Base_Surface_Name: Optional, if the overhang is attached to a specific surface.
        # Transmittance_Schedule_Name: Optional, if transmittance varies.

        # Hard-coded example geometry (4 vertices for a simple rectangular overhang):
        # This is purely illustrative. You’d typically compute X/Y/Z coordinates based on
        # building_row_context (e.g., facade width, window position, orientation),
        # and parameters like overhang_depth, width, tilt from shading_params.

        # Example: A 5m wide overhang, 1m deep, at Z=3.0, on a North facade (Y positive)
        # Vertices are typically counter-clockwise when viewed from outside.
        shading_obj.Number_of_Vertices = 4

        # Vertex 1 (Bottom-Left from outside view)
        shading_obj.Vertex_1_X_coordinate = (
            0.0  # Assuming start at X=0 of facade segment
        )
        shading_obj.Vertex_1_Y_coordinate = (
            0.0  # Y=0 is the facade plane for this local definition
        )
        shading_obj.Vertex_1_Z_coordinate = 3.0  # Height

        # Vertex 2 (Bottom-Right)
        shading_obj.Vertex_2_X_coordinate = 5.0  # Width of overhang = 5m
        shading_obj.Vertex_2_Y_coordinate = 0.0
        shading_obj.Vertex_2_Z_coordinate = 3.0

        # Vertex 3 (Top-Right, projecting outwards)
        shading_obj.Vertex_3_X_coordinate = 5.0
        shading_obj.Vertex_3_Y_coordinate = overhang_depth  # Projects 'overhang_depth' outwards (e.g., in positive Y if North wall is at Y=0)
        shading_obj.Vertex_3_Z_coordinate = 3.0  # Assuming flat overhang for simplicity

        # Vertex 4 (Top-Left, projecting outwards)
        shading_obj.Vertex_4_X_coordinate = 0.0
        shading_obj.Vertex_4_Y_coordinate = overhang_depth
        shading_obj.Vertex_4_Z_coordinate = 3.0

        # Note: The coordinate system for SHADING:BUILDING:DETAILED is absolute world coordinates.
        # The example above assumes a local definition relative to a point, which would then
        # need to be transformed to world coordinates based on building_row_context.
        # For simplicity here, these are treated as if they are already world coordinates.

        logger.debug(
            f"Created Shading:Building:Detailed '{shading_obj.Name}' with depth {overhang_depth}m."
        )

    except Exception as e:
        logger.error(f"Error creating Shading:Building:Detailed '{overhang_name}': {e}")


def add_shading_schedule(
    idf, schedule_name="DefaultShadingSchedule", schedule_type="Fraction"
):
    """
    Example of how you might create a schedule for dynamic shading control
    (e.g., for Shading_Control_Schedule_Name in WindowShadingControl).

    Parameters
    ----------
    idf : IDF object
    schedule_name : str
        Name for the new schedule.
    schedule_type : str
        Type of schedule, e.g., "Fraction", "OnOff", "Temperature".

    Returns
    -------
    EpBunch or equivalent schedule object
        The created schedule object, or None if creation fails.
    """
    logger.info(
        f"Attempting to create schedule: '{schedule_name}' of type '{schedule_type}'."
    )

    # Check if schedule already exists
    existing_schedules = [
        s.Name for s in idf.idfobjects.get("SCHEDULE:COMPACT", [])
    ]  # Also check SCHEDULE:YEAR, SCHEDULE:FILE etc.
    if schedule_name in existing_schedules:
        logger.info(f"Schedule:Compact '{schedule_name}' already exists. Reusing.")
        # Find and return the existing schedule object if needed by the caller
        for s in idf.idfobjects["SCHEDULE:COMPACT"]:
            if s.Name == schedule_name:
                return s
        return None  # Should not happen if name was found

    try:
        # Using SCHEDULE:COMPACT for simplicity.
        # Other types: SCHEDULE:YEAR, SCHEDULE:CONSTANT, SCHEDULE:FILE
        sched = idf.newidfobject("SCHEDULE:COMPACT")
        sched.Name = schedule_name

        # Schedule_Type_Limits_Name links to a ScheduleTypeLimits object.
        # Common types: "Fraction" (0-1), "OnOff" (0 or 1), "Temperature" (degrees C)
        # Make sure a ScheduleTypeLimits object with this name exists in the IDF.
        # If not, it needs to be created.
        # Example: Ensure "Fraction" ScheduleTypeLimits exists.
        stl_name = schedule_type  # Assuming ScheduleTypeLimits Name matches type for simplicity
        existing_stls = [
            stl.Name for stl in idf.idfobjects.get("SCHEDULETYPELIMITS", [])
        ]
        if stl_name not in existing_stls:
            logger.warning(
                f"ScheduleTypeLimits '{stl_name}' not found. Creating a basic one for '{schedule_name}'."
            )
            new_stl = idf.newidfobject("SCHEDULETYPELIMITS")
            new_stl.Name = stl_name
            if schedule_type == "Fraction":
                new_stl.Lower_Limit_Value = 0.0
                new_stl.Upper_Limit_Value = 1.0
                new_stl.Numeric_Type = "Continuous"
            elif schedule_type == "OnOff":
                new_stl.Lower_Limit_Value = 0.0
                new_stl.Upper_Limit_Value = 1.0
                new_stl.Numeric_Type = "Discrete"
            # Add more types as needed
            else:
                logger.warning(
                    f"No default setup for ScheduleTypeLimits '{schedule_type}'. It might be invalid."
                )

        sched.Schedule_Type_Limits_Name = stl_name

        # Simple example: always 1.0 (e.g., shades always active if scheduled)
        # Field format for SCHEDULE:COMPACT: "Through: MM/DD", "For: Days", "Until: HH:MM, Value", ...
        sched.Field_1 = "Through: 12/31"  # Through end of year
        sched.Field_2 = "For: AllDays"  # For all day types
        sched.Field_3 = "Until: 24:00, 1.0"  # Until midnight, value is 1.0
        # Add more fields for complex schedules.

        logger.debug(f"Created Schedule:Compact '{sched.Name}'.")
        return sched
    except Exception as e:
        logger.error(f"Error creating schedule '{schedule_name}': {e}")
        return None
